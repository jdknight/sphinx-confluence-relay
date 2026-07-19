# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from base64 import b64decode
from binascii import crc32
from collections.abc import Awaitable
from collections.abc import Callable
from email.utils import mktime_tz
from email.utils import parsedate_tz
from fastapi import status
from functools import wraps
from sphinx_confluence_relay.logger import logger
from sphinx_confluence_relay.state import AppState
from typing import Any
from typing import Concatenate
from typing import ParamSpec
from typing import TypeAlias
from typing import TypeVar
from urllib.parse import parse_qsl
from urllib.parse import urlparse
import asyncio
import httpx
import math
import random
import time


# number of elements to fetch for bulk requests
# (Confluence v2 APIs indicate a max of 250; a good enough number as any)
BULK_LIMIT = 250

# maximum limit (in seconds) to automatically drop processing
MAX_RATE_LIMIT = 120

# key to use for property tracking
PROP_KEY = 'sphinx-confluence-relay'

# the maximum times a request will be retried until stopping (rate limiting)
RATE_LIMITED_MAX_RETRIES = 5

# the maximum duration (in seconds) a retry on a rate-limited request can be
# delayed
RATE_LIMITED_MAX_RETRY_DURATION = 30

# the maximum times a request will be retried until stopping (erred instance)
REMOTE_ERR_MAX_RETRIES = 2

# the maximum duration (in seconds) a retry on a erred request can be delayed
REMOTE_ERR_MAX_RETRY_DURATION = 4

# errors to auto-retry publishing on; see:
# https://everything.curl.dev/usingcurl/downloads/retry.html#retry
TRANSIENT_ERRORS = (
    408,
    500,
    502,
    503,
    504,
)


P = ParamSpec('P')
R = TypeVar('R')
AsyncFunc: TypeAlias = Callable[P, Awaitable[R]]
AsyncFuncWithState = Callable[Concatenate[AppState, P], Awaitable[R]]


async def publish(
        state: AppState,
        rid: int,
        space_key: str,
        manifest: dict,
        parent_page: str,
    ) -> int:
    """
    request to publish a manifest to a confluence instance

    This call accepts a manifest and attempts to publish this information to
    the configured Confluence instance. It will cycle through the data,
    determine pages to publish, publish these pages; followed by cycling
    through any attachments to publish.

    Args:
        state: the application state
        rid: the identifier of the request
        space_key: the space the manifest will be published under
        manifest: the manifest to publish
        parent_page: the parent page to publish under

    Returns:
        how many pages where published
    """

    api_url = state.settings.confluence_url

    page_ids: dict[str, int] = {}

    # prepare/find the parent page identifier
    try:
        parent_page_id = int(parent_page)
    except ValueError as exc:
        parent_page_id, _, _ = await fetch_page(
            state, api_url, space_key, parent_page)
        if not parent_page_id:
            msg = f'failed to find parent page: {parent_page}'
            raise KeyError(msg) from exc

    # check the initial descendant of pages to see if we later want to
    # remove old pages
    initial_descendants = await fetch_descendant_pages_aggressive(
        state, api_url, parent_page_id)

    # keep track of update-to-date pages/attachments
    good_attachments: set[int] = set()
    good_pages: set[int] = set()
    existing_pages: set[int] = set()

    # cycle through pages to publish
    page_count = 1
    total_pages = len(manifest['pages'])

    for page_entry in manifest['pages']:
        page_docid = page_entry.get('id')
        parent_docid = page_entry.get('parentId')
        page_title = page_entry.get('title')
        page_data = page_entry.get('data')

        binary_data = b64decode(page_data, validate=True)
        storage_format = binary_data.decode()

        # build our initial page data
        publish_data = build_page(
            space_key, page_title, storage_format)

        # configure page parent
        if page_count == 1 and parent_page_id:
            # root document under configured parent page
            target_parent_page_id = parent_page_id
        elif parent_docid:
            # leaf document under respective parent pages
            target_parent_page_id = page_ids[parent_docid]
        else:
            # orphan pages forced under configured parent page
            target_parent_page_id = parent_page_id

        publish_data['ancestors'] = [{'id': target_parent_page_id}]

        # query if this page already exists
        page_id, page_version, current_parent_page = await fetch_page(
            state, api_url, space_key, page_title)

        # determine hash with target version hint
        current_page_version = (page_version or 1)
        current_hash_int = crc32(binary_data) + current_page_version
        current_hash_key = f'SCR_KEY:{current_hash_int}'

        # if there is an existing page, set the page identifier and
        # version number that we can rework the request to be an update
        property_version: int | None = None
        property_value: Any = None

        if page_id and page_version:
            publish_data['id'] = page_id
            publish_data['version']['number'] = page_version + 1

            # check for a property holding a possible hash from a previous
            # publish run
            property_version, property_value = \
                await fetch_property(state, api_url, page_id)

            # ready if next property version
            if property_version:
                property_version += 1

        # if this is an existing page, ensure it is not a page that resides
        # outside our container page
        if current_parent_page and current_parent_page != parent_page_id and \
                current_parent_page not in initial_descendants:
            msg = f'page exists outside of container: {page_title}'
            raise PermissionError(msg)

        # verify we should publish
        should_publish = False

        # publish if our parent page is different
        if current_parent_page != target_parent_page_id:
            should_publish = True

        # perform a hash check and compare top see if we can skip publishing
        if property_value != current_hash_key:
            should_publish = True

        # publish the page
        if should_publish:
            page_id, reported_page_version = await publish_page(
                state, api_url, publish_data)

            # determine new hash using version hint
            new_hash_int = crc32(binary_data) + reported_page_version
            new_hash_key = f'SCR_KEY:{new_hash_int}'

            # track page hash in a property (to limit future updates)
            await publish_property(
                state=state,
                api_url=api_url,
                property_version=property_version,
                page_id=page_id,
                value=new_hash_key,
            )

            good_pages.add(page_id)
            status = 'published'
        else:
            good_pages.add(page_id)
            existing_pages.add(page_id)
            status = 'skipped'

        assert page_id
        page_ids[page_docid] = page_id

        logger.info(f'[R{rid}]: {status} page '
                    f'({page_count}/{total_pages}): {page_docid}')
        page_count += 1

    # cycle through attachments to publish
    attachment_count = 1
    attachments = manifest.get('attachments', [])
    total_attachments = len(attachments)

    for attachment_entry in attachments:
        filename = attachment_entry['id']
        target_page = attachment_entry['pageId']
        target_page_id = page_ids[target_page]

        # query if this attachment already exists
        attachment_id, attachment_hash = await fetch_attachment(
            state, api_url, target_page_id, filename)

        # ready data
        binary_data = b64decode(attachment_entry['data'], validate=True)
        hash_int = crc32(binary_data)
        hash_key = f'SCR_KEY:{hash_int}'

        # perform a hash check and compare top see if we can skip publishing
        if attachment_hash != hash_key:
            # publish the attachment
            attachment_id = await publish_attachment(
                state=state,
                api_url=api_url,
                attachment_id=attachment_id,
                page_id=target_page_id,
                filename=filename,
                data=binary_data,
                mimetype=attachment_entry['mimeType'],
                hash_id=hash_key,
            )

            good_attachments.add(attachment_id)
            status = 'published'
        else:
            good_attachments.add(attachment_id)
            status = 'skipped'

        logger.info(f'[R{rid}]: {status} attachment '
                    f'({attachment_count}/{total_attachments}): '
                    f'{filename}')
        attachment_count += 1

    # determine old pages to remove
    old_pages = initial_descendants - good_pages

    total_old_pages = len(old_pages)
    page_count = 1
    for page_id in old_pages:
        logger.info(f'[R{rid}]: removing old page '
                    f'[{page_count}/{total_old_pages}]')
        await state.http_client.delete(f'{api_url}/content/{page_id}')
        page_count += 1

    # determine old attachments to remove (if any)
    old_attachments: set[int] = set()
    for existing_page in existing_pages:
        # find attachments
        attachments = await fetch_attachments(state, api_url, existing_page)

        # determine which ones are old
        pages_old_attachments = attachments - good_attachments
        old_attachments.update(pages_old_attachments)

    attachment_count = 1
    total_old_attachments = len(old_attachments)
    for attachment_id in old_attachments:
        logger.info(f'[R{rid}]: removing old attachment '
                    f'[{attachment_count}/{total_old_attachments}]')
        await state.http_client.delete(f'{api_url}/content/{attachment_id}')
        attachment_count += 1

    # indicate publishing was successful
    return len(page_ids)


def build_page(space_key: str, title: str, data: str) -> dict:
    """
    build the skeleton for a new page

    Provides the initial API request data needed for a new page for
    Confluence.

    Args:
        space_key: the space key
        title: the title of the page
        data: the storage format of the page

    Returns:
        the page data
    """

    return {
        'type': 'page',
        'title': title,
        'space': {
            'key': space_key,
        },
        'body': {
            'storage': {
                'representation': 'storage',
                'value': data,
            },
        },
        'status': 'current',
        'version': {
            'message': 'sphinx-confluence-relay',
            # always hint as minor edit to avoid noise
            'minorEdit': True,
        },
    }


def confluence_error_retries() -> Callable[[AsyncFunc], AsyncFunc]:
    """
    a confluence error retry "decorator"

    A utility "decorator" to handle automatic attempt to retry an API call
    if Confluence reports an unexpected server error (e.g. a 5xx error).
    There can be issues where Confluence may have issues with a transaction
    on a page update, or an unexpected error processing properties on a page.
    If such a call is detected, the call will be retried again in hopes that
    it was a one time occurrence.
    """
    def _decorator(func: AsyncFunc[P, R]) -> AsyncFunc[P, R]:
        @wraps(func)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            attempt = 1
            while True:
                try:
                    return await func(*args, **kwargs)
                except httpx.HTTPStatusError as exc:
                    # if max attempts have been reached, stop any more attempts
                    if attempt > REMOTE_ERR_MAX_RETRIES:
                        raise

                    # retry on transient errors
                    if exc.response.status_code not in TRANSIENT_ERRORS:
                        raise

                    # configure the delay
                    delay = float(REMOTE_ERR_MAX_RETRY_DURATION)

                    # add jitter
                    delay += random.uniform(0.0, 0.5)  # noqa: S311

                    # wait the calculated delay before retrying again
                    reported_delay = math.ceil(delay)
                    logger.info('unexpected rest response detected; '
                                f'retrying in {reported_delay} seconds...')
                    await asyncio.sleep(delay)
                    attempt += 1

        return _wrapper
    return _decorator


def rate_limited_retries() -> Callable[[AsyncFuncWithState], AsyncFuncWithState]:
    """
    a rest rate limited "decorator"

    A utility "decorator" to handle rate-limited retries if Confluence reports
    that API calls should be limited.
    """
    def _decorator(func: AsyncFuncWithState[P, R]) -> AsyncFuncWithState[P, R]:
        @wraps(func)
        async def _wrapper(state: AppState,
                *args: P.args, **kwargs: P.kwargs) -> R:
            # if confluence asked us to wait so many seconds before a next
            # api request, wait a moment
            if state.rate_limit_next:
                delay = float(state.rate_limit_next)
                logger.debug('rate-limit header detected; '
                            f'waiting {math.ceil(delay)} seconds...')
                await asyncio.sleep(delay)
                state.rate_limit_next = None

            # if we have imposed some rate-limiting requests where confluence
            # did not provide retry information, slowly decrease our tracked
            # delay if requests are going through
            state.rate_limit_last = max(state.rate_limit_last / 2, 1)

            attempt = 1
            while True:
                try:
                    return await func(state, *args, **kwargs)
                except httpx.HTTPStatusError as exc:
                    # ignore non-rate limited
                    code = exc.response.status_code
                    if code != status.HTTP_429_TOO_MANY_REQUESTS:
                        raise

                    # if max attempts have been reached, stop any more attempts
                    if attempt > RATE_LIMITED_MAX_RETRIES:
                        raise

                    # if confluence or a proxy reports a retry-after delay
                    # (to pace us), track it to delay the next request made
                    # (https://datatracker.ietf.org/doc/html/rfc2616.html#section-14.37)
                    raw_delay = exc.response.headers.get('Retry-After')
                    if raw_delay:
                        new_delay = 0
                        try:
                            # attempt to parse a seconds value from the header
                            new_delay = int(raw_delay)
                        except ValueError:
                            # if seconds are not provided, attempt to parse
                            parsed_dtz = parsedate_tz(raw_delay)
                            if parsed_dtz:
                                target_datetime = mktime_tz(parsed_dtz)
                                new_delay = int(target_datetime - time.time())

                        if new_delay > 0:
                            state.rate_limit_next = new_delay

                            # if this is a long rate-limit, do not even try
                            # to interact; either rate limiting is disabled
                            # or administration/proxy is having issues or is
                            # too strict in quota
                            if new_delay >= MAX_RATE_LIMIT:
                                logger.warning(
                                    'long rate-limit duration; will stop')
                                state.rate_limit_next = None
                                raise

                    # determine the amount of delay to wait again -- either
                    # from the provided delay (if any) or exponential back-off
                    if state.rate_limit_next:
                        delay = float(state.rate_limit_next)
                        state.rate_limit_next = None
                    else:
                        delay = 2 * state.rate_limit_last

                    # cap delay to a maximum
                    delay = min(delay, RATE_LIMITED_MAX_RETRY_DURATION)

                    # add jitter
                    delay += random.uniform(0.3, 1.3)  # noqa: S311

                    # wait the calculated delay before retrying again
                    logger.debug('rate-limit response detected; '
                                f'waiting {math.ceil(delay)} seconds...')
                    await asyncio.sleep(delay)
                    state.rate_limit_last = delay
                    attempt += 1

        return _wrapper
    return _decorator


@confluence_error_retries()
@rate_limited_retries()
async def fetch_attachments(state: AppState, api_url: str,
        page_id: int) -> set[int]:
    """
    fetch page data from the confluence instance

    This call is used to fetch page data from a Confluence instance, if the
    page exists.

    Args:
        state: the application state
        api_url: the api url base to use
        page_id: the page id

    Returns:
        set of found page identifiers
    """

    attachments: set[int] = set()
    search_fields = {
        'limit': f'{BULK_LIMIT}',
    }

    # query for this page's attachments
    fetch_api = f'{api_url}/content/{page_id}/child/attachment'
    rsp = await state.http_client.get(fetch_api, params=search_fields)

    rsp.raise_for_status()
    data = rsp.json()

    idx = 0
    while data.get('results'):
        for result in data['results']:
            attachments.add(int(result['id']))

        count = len(data['results'])
        if count != BULK_LIMIT:
            break

        idx += count
        next_fields = _next_page_fields(data, search_fields, idx)
        if not next_fields:
            break

        rsp = await state.http_client.get(fetch_api, params=next_fields)
        rsp.raise_for_status()
        data = rsp.json()

    return attachments


@confluence_error_retries()
@rate_limited_retries()
async def fetch_descendant_pages(state: AppState, api_url: str,
        page_id: int) -> set[int]:
    """
    fetch page data from the confluence instance

    This call is used to fetch page data from a Confluence instance, if the
    page exists.

    Args:
        state: the application state
        api_url: the api url base to use
        page_id: the page id

    Returns:
        set of found page identifiers
    """

    descendants: set[int] = set()
    search_fields = {
        'cql': f'ancestor={page_id}',
        'limit': f'{BULK_LIMIT}',
    }

    # query for this page's descendants
    fetch_api = f'{api_url}/content/search'
    rsp = await state.http_client.get(fetch_api, params=search_fields)

    rsp.raise_for_status()
    data = rsp.json()

    idx = 0
    while data.get('results'):
        for result in data['results']:
            descendants.add(int(result['id']))

        count = len(data['results'])
        if count != BULK_LIMIT:
            break

        idx += count
        next_fields = _next_page_fields(data, search_fields, idx)
        if not next_fields:
            break

        rsp = await state.http_client.get(fetch_api, params=next_fields)
        rsp.raise_for_status()
        data = rsp.json()

    return descendants


@confluence_error_retries()
@rate_limited_retries()
async def fetch_descendant_pages_aggressive(state: AppState, api_url: str,
        page_id: int) -> set[int]:

    visited_pages: set[int] = set()

    async def _fetch_descendant(page_id: int) -> None:
        descendants = await fetch_descendant_pages(state, api_url, page_id)
        for descendant in descendants:
            if descendant not in visited_pages:
                visited_pages.add(descendant)
                await _fetch_descendant(descendant)

    await _fetch_descendant(page_id)

    return visited_pages


def _next_page_fields(rsp: dict, fields: dict, offset: int) -> dict | None:
    """
    extract next query fields from a response

    For paged search requests, Confluence can report a "next" link to use
    for the "next page". This call can be used to extract the query options
    provided by Confluence that should be included in a next request.

    Original CQL search calls would use a "start" offset to manage pages.
    Note on Confluence Data Center, the "start" offset may still be used.

    Args:
        rsp: the response to pull a next query from
        fields: the recommended search fields
        offset: the recommended start offset

    Returns:
        the extract query fields
    """

    reported_links = rsp.get('_links')
    if reported_links:
        next_query = reported_links.get('next')
        if next_query:
            try:
                parsed = urlparse(next_query)
                return dict(parse_qsl(parsed.query))
            except ValueError:
                return None

            return None

    total_sz = rsp.get('totalSize')
    if total_sz and total_sz > offset:
        sub_search_fields = dict(fields)
        sub_search_fields['start'] = offset
        return sub_search_fields

    return None


@confluence_error_retries()
@rate_limited_retries()
async def fetch_page(state: AppState, api_url: str, space_key: str,
        title: str) -> tuple[int | None, int | None, int | None]:
    """
    fetch page data from the confluence instance

    This call is used to fetch page data from a Confluence instance, if the
    page exists.

    Args:
        state: the application state
        api_url: the api url base to use
        space_key: the space key
        title: the title of the page

    Returns:
        tuple of the page id, version and parent id; if a page is found
    """

    page_id: int | None = None
    page_version: int | None = None
    parent_id: int | None = None

    # query if this page already exists
    fetch_api = f'{api_url}/content'
    rsp = await state.http_client.get(fetch_api, params={
        'spaceKey': space_key,
        'title': title,
        'expand': 'ancestors,version',
    })

    rsp.raise_for_status()
    data = rsp.json()

    # if there is an existing page, extract the page identifier and
    # version number that we can rework the request to be an update
    if data.get('results'):
        existing_page = data['results'][0]

        page_id = int(existing_page['id'])
        page_version = int(existing_page['version']['number'])

        logger.debug(f'found page ({page_id}; v{page_version}): '
                     f'{existing_page["title"]}')

        ancestor_entries = existing_page.get('ancestors')
        if ancestor_entries:
            parent_id = int(existing_page['ancestors'][-1]['id'])

    return page_id, page_version, parent_id


@confluence_error_retries()
@rate_limited_retries()
async def publish_page(state: AppState, api_url: str,
        data: dict) -> tuple[int, int]:
    """
    publish a page

    Requests to publish a page to the configured Confluence instance.
    This call will either publish a new page or update an existing one.

    Args:
        state: the application state
        api_url: the api url base to use
        data: the page data

    Returns:
        the page identifier and the page version
    """

    # page update
    if 'id' in data:
        logger.debug(f'publishing page update: {data["id"]}')
        publish_api = f'{api_url}/content/{data["id"]}'
        rsp = await state.http_client.put(publish_api, json=data)
    # new page
    else:
        logger.debug('publishing new page')
        publish_api = f'{api_url}/content'
        rsp = await state.http_client.post(publish_api, json=data)
    rsp.raise_for_status()

    new_page_state = rsp.json()
    page_id = int(new_page_state['id'])
    page_version = int(new_page_state['version']['number'])

    # auto-clear any watch state
    await state.http_client.delete(f'{api_url}/user/watch/content/{page_id}')

    return page_id, page_version


@confluence_error_retries()
@rate_limited_retries()
async def fetch_property(state: AppState, api_url: str,
        page_id: int) -> tuple[int | None, str | None]:
    """
    fetch property data from the confluence instance

    This call is used to fetch property data from a Confluence instance, if
    the property exists.

    Args:
        state: the application state
        api_url: the api url base to use
        page_id: the identifier of the page holding the property

    Returns:
        tuple of the property version and value, if a property exists
    """

    property_version: int | None = None
    property_value: str | None = None

    # query if this property exists
    fetch_api = f'{api_url}/content/{page_id}/property/{PROP_KEY}'
    rsp = await state.http_client.get(fetch_api)

    try:
        rsp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != status.HTTP_404_NOT_FOUND:
            raise
    else:
        data = rsp.json()
        property_version = int(data['version']['number'])
        property_value = data['value']

        logger.debug(f'found property: {page_id}')

    return property_version, property_value


@confluence_error_retries()
@rate_limited_retries()
async def publish_property(
        state: AppState,
        api_url: str,
        property_version: int | None,
        page_id: int,
        value: str,
    ) -> int:
    """
    publish a property

    Requests to publish a property value to the configured Confluence instance.
    This call will either publish a new property for a page or update an
    existing one.

    Args:
        state: the application state
        api_url: the api url base to use
        property_version: the existing property id (if updated)
        page_id: the page the property resides
        value: the value of the new property

    Returns:
        the property identifier
    """

    publish_api = f'{api_url}/content/{page_id}/property'
    if property_version:
        publish_api += f'/{PROP_KEY}'

    data: dict[str, Any] = {
        'key': PROP_KEY,
        'value': value,
        'version': {
            'message': 'sphinx-confluence-relay',
            'minorEdit': True,
        },
    }

    # property update
    if property_version:
        logger.debug(f'publishing property update: {page_id}')
        data['version']['number'] = property_version
        rsp = await state.http_client.put(publish_api, json=data)
    # new property
    else:
        logger.debug(f'publishing new property: {page_id}')
        rsp = await state.http_client.post(publish_api, json=data)
    rsp.raise_for_status()

    new_property_state = rsp.json()
    return int(new_property_state['id'])


@confluence_error_retries()
@rate_limited_retries()
async def fetch_attachment(state: AppState, api_url: str,
        page_id: int, filename: str) -> tuple[int | None, str | None]:
    """
    fetch attachment data from the confluence instance

    This call is used to fetch attachment data from a Confluence instance, if
    the attachment exists.

    Args:
        state: the application state
        api_url: the api url base to use
        page_id: the identifier of the page holding the attachment
        filename: the name of the attachment

    Returns:
        tuple of the attachment id and reported "hash" (i.e. comment field),
        if an attachment exists
    """

    attachment_id: int | None = None
    attachment_hash: str | None = None

    # query if this attachment already exists
    fetch_api = f'{api_url}/content/{page_id}/child/attachment'
    rsp = await state.http_client.get(fetch_api, params={
        'filename': filename,
    })

    rsp.raise_for_status()
    data = rsp.json()

    # if there is an existing attachment, extract the identifier and
    # version number that we can rework the request to be an update
    if data.get('results'):
        found_attachment = data['results'][0]
        attachment_id = int(found_attachment['id'])
        attachment_hash = found_attachment.get('metadata', {}).get('comment')

        logger.debug(f'found attachment ({attachment_id}): '
                     f'{found_attachment["title"]}')

    return attachment_id, attachment_hash


@confluence_error_retries()
@rate_limited_retries()
async def publish_attachment(
        state: AppState,
        api_url: str,
        attachment_id: int | None,
        page_id: int,
        filename: str,
        data: bytes,
        mimetype: str,
        hash_id: str,
    ) -> int:
    """
    publish an attachment

    Requests to publish an attachment to the configured Confluence instance.
    This call will either publish a new attachment for a page or update an
    existing one.

    Args:
        state: the application state
        api_url: the api url base to use
        attachment_id: the existing attachment id (if updated)
        page_id: the page the attachment resides
        filename: the name of the attachment
        data: the attachment data
        mimetype: the mime-type of the data
        hash_id: the hash value to use

    Returns:
        the attachment identifier
    """

    form_data = {
        'comment': hash_id,
        'status': 'current',
        'minorEdit': True,
        'hidden': True,
    }

    files = {
        'file': (filename, data, mimetype),
    }

    logger.debug(f'publishing attachment: {attachment_id}')

    publish_api = f'{api_url}/content/{page_id}/child/attachment'
    if attachment_id:
        publish_api += f'/{attachment_id}/data'
    rsp = await state.http_client.post(publish_api, data=form_data, files=files)
    rsp.raise_for_status()

    new_attachment_state = rsp.json()
    if 'results' in new_attachment_state:
        new_attachment_state = new_attachment_state['results'][0]
    attachment_id = int(new_attachment_state['id'])

    # auto-clear any watch state
    await state.http_client.delete(
        f'{api_url}/user/watch/content/{attachment_id}')

    return attachment_id
