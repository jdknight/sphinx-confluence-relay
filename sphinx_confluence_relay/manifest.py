# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from fastapi import HTTPException
from fastapi import status
import mimetypes
import os


# maximum number of entries (pages/attachments) before we deny a request
MAX_ENTRIES = int(os.getenv('SPHINX_CONFLUENCE_RELAY_MAX_ENTRIES', '500'))

# maximum confluence page title value
MAX_TITLE_VALUE = 255


def parse_manifest(data: dict) -> dict:
    """
    process a sphinx confluence builder manifest file

    This call helps sanity check the manifest file being provided. Checks
    include (but not limited to) manifest type checks, ensures data is
    included and more. After this run, a processed/prepared manifest
    entry should be ready for a publish engine to process requests.

    Args:
        data: the manifest data

    Returns:
        the updated manifest

    Raises:
        BadRequestException: unexpected data is detected
    """

    # validate a sphinx confluence builder manifest
    if data.get('type') != 'SphinxConfluenceBuilder/Manifest':
        msg = 'unsupported manifest type'
        raise BadRequestException(msg)

    # validate a manifest specification
    if not data.get('spec') or not isinstance(data['spec'], int) \
            or data['spec'] < 1:
        msg = 'unexpected manifest specification'
        raise BadRequestException(msg)

    # we only accept data-embedded manifests
    if not data.get('includesData'):
        msg = 'non-data manifest'
        raise BadRequestException(msg)

    if not isinstance(data['includesData'], bool):
        msg = 'unexpected includes-data type'
        raise BadRequestException(msg)

    # no pages to process?
    if 'pages' not in data:
        msg = 'non-page data in manifest'
        raise BadRequestException(msg)

    # validate pages is a list
    if not isinstance(data['pages'], list):
        msg = 'unexpected pages type in manifest'
        raise BadRequestException(msg)

    # too many pages to process?
    if len(data['pages']) > MAX_ENTRIES:
        msg = 'exceeded page limit in manifest'
        raise BadRequestException(msg)

    # too many attachments to process?
    try:
        if len(data.get('attachments', [])) > MAX_ENTRIES:
            msg = 'exceeded attachment limit in manifest'
            raise BadRequestException(msg)
    except TypeError as exc:
        msg = 'unexpected attachment type in manifest'
        raise BadRequestException(msg) from exc

    # parse manifest data (at this time, only spec-1)
    parsed_manifest = parse_manifest_spec01(data)

    # sanity checks on the data
    # (note: pre-parse should already verify page ids)
    verify_valid_pages(parsed_manifest)
    verify_valid_attachments(parsed_manifest)
    verify_valid_ids(parsed_manifest)

    return parsed_manifest


def parse_manifest_spec01(data: dict) -> dict:
    """
    process a spec-1 manifest file

    This call helps check and rework the manifest data to make it flexible
    for relay publishing to occur. The first iteration of the specification
    requires is not entirely flexible for given the required order of pages
    needed to be published (since some pages depend on each other). We have
    to cycle through the page entries and build a new order of data.

    Args:
        data: the manifest data

    Returns:
        the updated manifest

    Raises:
        BadRequestException: unexpected data is detected
    """

    # specification 1 is not sorted for easy published; we will have to
    # cycle through all the pages and order by root then nested pages
    db: dict[str, dict] = {}
    root_doc = None

    orphan_pages = []
    for page in data['pages']:
        if not isinstance(page, dict):
            msg = 'invalid page entry in manifest'
            raise BadRequestException(msg)

        page_id = page.get('id')
        if not page_id:
            msg = 'page with no id in manifest'
            raise BadRequestException(msg)

        if not isinstance(page_id, str) or page_id != page_id.strip():
            msg = 'page with invalid id in manifest'
            raise BadRequestException(msg)

        if page_id not in db:
            db[page_id] = {
                'children': [],
            }
        elif 'data' in db[page_id]:
            msg = 'duplicate page id detected'
            raise BadRequestException(msg)

        db[page_id]['data'] = page

        if page.get('isRoot'):
            if not isinstance(page['isRoot'], bool):
                msg = 'unexpected page root type hint'
                raise BadRequestException(msg)

            root_doc = page_id
        elif 'parentId' not in page:
            orphan_pages.append(page_id)

        if 'parentId' in page:
            parent_id = page['parentId']

            if not isinstance(parent_id, str) or parent_id != parent_id.strip():
                msg = 'page with invalid parent id in manifest'
                raise BadRequestException(msg)

            if parent_id not in db:
                db[parent_id] = {
                    'children': [],
                }
            db[parent_id]['children'].append(page_id)

    # no root document?
    if not root_doc:
        msg = 'no root document in manifest'
        raise BadRequestException(msg)

    # walk all document ids to help us compile a list of publish-ordered
    # sorted pages
    tracked_ids = set()
    sorted_ids = []

    def walk_ids(id_: str) -> None:
        if id_ in tracked_ids:
            return

        tracked_ids.add(id_)
        sorted_ids.append(id_)

        for child_id in db[id_]['children']:
            walk_ids(child_id)

    walk_ids(root_doc)

    for orphan_page in orphan_pages:
        walk_ids(orphan_page)

    # re-sort pages to be in order needed for publication
    sorted_pages = []
    for id_ in sorted_ids:
        page = db[id_]['data']
        sorted_pages.append(page)

    # swap to use the new sorted pages
    data['pages'] = sorted_pages

    return data


def verify_valid_ids(data: dict) -> None:
    """
    call will validate that identifiers in a manifest are sane

    This call helps validate that the identifiers provided in a manifest
    is good for processing. We use this to ensure various keys/data exists
    to make it easier to deal with when publishing a request.

    Args:
        data: the manifest data

    Raises:
        BadRequestException: unexpected data is detected
    """

    valid_ids = set()
    target_ids = set()

    # search through all pages for valid identifiers
    for page in data.get('pages', []):
        valid_ids.add(page['id'])

        if 'parentId' in page:
            target_ids.add(page['parentId'])

    # search through all attachments for valid identifiers
    for attachment in data.get('attachments', []):
        page_id = attachment['pageId']
        target_ids.add(page_id)

    # verify each target references a valid page identifier
    if not target_ids.issubset(valid_ids):
        msg = 'invalid parent id in manifest'
        raise BadRequestException(msg)


def verify_valid_pages(data: dict) -> None:
    """
    call will validate that the pages data in a manifest is sane

    This call helps validate that the pages data provided in a manifest
    is good for processing. We use this to ensure various keys/data exists
    to make it easier to deal with when publishing a request.

    Args:
        data: the manifest data

    Raises:
        BadRequestException: unexpected data is detected
    """

    # search through all pages to ensure required data exists
    for page in data.get('pages', []):
        if 'title' not in page:
            msg = 'page with missing title in manifest'
            raise BadRequestException(msg)

        page_title = page['title']
        if not isinstance(page_title, str):
            msg = 'page with invalid title type in manifest'
            raise BadRequestException(msg)

        if not page_title or page_title != page_title.strip():
            msg = 'page with bad title in manifest'
            raise BadRequestException(msg)

        if len(page_title) > MAX_TITLE_VALUE:
            msg = 'page with a too long of a title'
            raise BadRequestException(msg)

        raw_data = page.get('data')
        if not raw_data:
            msg = 'page with no data manifest'
            raise BadRequestException(msg)


def verify_valid_attachments(data: dict) -> None:
    """
    call will validate that the attachment data in a manifest is sane

    This call helps validate that the attachment data provided in a manifest
    is good for processing. We use this to ensure various keys/data exists
    to make it easier to deal with when publishing a request.

    Args:
        data: the manifest data

    Raises:
        BadRequestException: unexpected data is detected
    """

    # search through all attachments to ensure required data exists
    for attachment in data.get('attachments', []):
        if not isinstance(attachment, dict):
            msg = 'invalid attachment entry in manifest'
            raise BadRequestException(msg)

        if 'id' not in attachment:
            msg = 'attachment with missing id in manifest'
            raise BadRequestException(msg)

        attachment_id = attachment['id']
        if not attachment_id or not isinstance(attachment_id, str) or \
                attachment_id != attachment_id.strip():
            msg = 'attachment with bad id in manifest'
            raise BadRequestException(msg)

        if 'pageId' not in attachment:
            msg = 'attachment with missing page id in manifest'
            raise BadRequestException(msg)

        page_id = attachment['pageId']
        if not page_id or not isinstance(page_id, str) or \
                page_id != page_id.strip():
            msg = 'attachment with bad page id in manifest'
            raise BadRequestException(msg)

        if 'mimeType' not in attachment:
            msg = 'attachment missing mime-type in manifest'
            raise BadRequestException(msg)

        mime_type = attachment.get('mimeType')
        if not mime_type or not isinstance(mime_type, str) or \
                mime_type != mime_type.strip():
            msg = 'attachment with bad mime-type in manifest'
            raise BadRequestException(msg)

        if not mimetypes.guess_extension(mime_type):
            msg = 'attachment with unknown mime-type in manifest'
            raise BadRequestException(msg)

        raw_data = attachment.get('data')
        if not raw_data:
            msg = 'attachment with no data manifest'
            raise BadRequestException(msg)


class BadRequestException(HTTPException):
    def __init__(self, detail: str) -> None:
        """
        a bad request exception

        A simple exception used to reflect a 400 state.

        Args:
            detail: the message to include
        """
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
