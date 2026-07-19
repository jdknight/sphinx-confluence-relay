# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from fastapi import HTTPException
from fastapi import status
from sphinx_confluence_relay.health import update_health_status
from sphinx_confluence_relay.logger import logger
from sphinx_confluence_relay.models import SpaceKeyCacheModel
from sphinx_confluence_relay.settings import Settings
from sqlmodel import Session
from sqlmodel import select
import httpx


async def validate_confluence(
        settings: Settings,
        http_client: httpx.AsyncClient,
    ) -> bool:
    """
    validate the confluence instance is accessible

    This call is used to sanity check the configured Confluence instance is
    accessible. It is used to help hold of processing queued requests due to
    authentication or availability issues.

    Args:
        settings: the application settings
        http_client: the web client used to query confluence

    Returns:
        whether the page exists

    Raises:
        HTTPException: on backend error
    """

    confluence_up = False

    try:
        query_api = f'{settings.confluence_url}/server-information'
        rsp = await http_client.get(query_api)
        rsp.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f'confluence instance not available ({exc})')
    except httpx.HTTPStatusError as exc:
        logger.error(
            f'confluence instance not available ({exc.response.status_code})')
    else:
        confluence_up = True

    # synchronize health status
    update_health_status(healthy=confluence_up)

    return confluence_up


async def validate_page(
        settings: Settings,
        http_client: httpx.AsyncClient,
        space_key: str,
        page: int | str,
    ) -> bool:
    """
    validate a given page key exists

    This call is used to sanity check a given page exists on the configured
    Confluence instance. It is mainly used to help pre-check publish events
    to fail requests faster without having to wait for a queued publish event
    to be processed.

    Args:
        settings: the application settings
        http_client: the web client used to query confluence
        space_key: the space key holding the page
        page: the page being checked

    Returns:
        whether the page exists

    Raises:
        HTTPException: on backend error
    """

    page_id = None
    page_exists = False

    try:
        try:
            # check via page identifier
            page_id = int(page)
            fetch_api = f'{settings.confluence_url}/content/{page_id}'
            rsp = await http_client.get(fetch_api)
        except ValueError:
            # or change via page name
            fetch_api = f'{settings.confluence_url}/content'
            rsp = await http_client.get(fetch_api, params={
                'spaceKey': space_key,
                'title': page,
            })

        rsp.raise_for_status()
    except httpx.RequestError as exc:
        # synchronize health status
        update_health_status(healthy=False)

        logger.error(f'confluence instance not available ({exc})')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='backend unable to access the confluence instance',
        ) from exc
    except httpx.HTTPStatusError as exc:
        match exc.response.status_code:
            case status.HTTP_401_UNAUTHORIZED | status.HTTP_403_FORBIDDEN:
                # synchronize health status
                update_health_status(healthy=False)

                logger.error('not authenticate with confluence instance')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='backend not authenticated with confluence instance',
                ) from exc

            case status.HTTP_404_NOT_FOUND:
                # ignore if not found
                pass

            case _:
                logger.error('unexpected status from confluence instance'
                            f'({exc.response.status_code})')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='unexpected backend response '
                          f'({exc.response.status_code})',
                ) from exc
    else:
        if not page_id:
            data = rsp.json()
            page_exists = bool(data['results'])
        else:
            page_exists = True

    # synchronize health status
    update_health_status(healthy=True)

    return page_exists


async def validate_space(
        session: Session,
        settings: Settings,
        http_client: httpx.AsyncClient,
        space_key: str,
    ) -> bool:
    """
    validate a given space key exists

    This call is used to sanity check a given space exists on the configured
    Confluence instance. It is mainly used to help pre-check publish events
    to fail requests faster without having to wait for a queued publish event
    to be processed.

    The existence check will cache in a database as well. Maintenance engine
    will be responsible for clearing our old states over time.

    Args:
        session: the sql engine session
        settings: the application settings
        http_client: the web client used to query confluence
        space_key: the space key being checked

    Returns:
        whether the space key exists

    Raises:
        HTTPException: on backend error
    """

    # check if this space key is already cached; if so, use its last state
    statement = select(SpaceKeyCacheModel) \
        .where(SpaceKeyCacheModel.key == space_key)
    entry = session.exec(statement).first()
    if entry:
        return entry.exists

    # query to see if the space exists
    space_exists = False

    try:
        fetch_api = f'{settings.confluence_url}/space/{space_key}'
        rsp = await http_client.get(fetch_api)
        rsp.raise_for_status()
    except httpx.RequestError as exc:
        # synchronize health status
        update_health_status(healthy=False)

        logger.error(f'confluence instance not available ({exc})')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='backend unable to access the confluence instance',
        ) from exc
    except httpx.HTTPStatusError as exc:
        match exc.response.status_code:
            case status.HTTP_401_UNAUTHORIZED | status.HTTP_403_FORBIDDEN:
                # synchronize health status
                update_health_status(healthy=False)

                logger.error('not authenticate with confluence instance')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='backend not authenticated with confluence instance',
                ) from exc

            case status.HTTP_404_NOT_FOUND:
                # ignore if not found
                pass

            case _:
                logger.error('unexpected status from confluence instance'
                            f'({exc.response.status_code})')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='unexpected backend response '
                          f'({exc.response.status_code})',
                ) from exc
    else:
        space_exists = True

    # cache the new state for this key
    statement = select(SpaceKeyCacheModel) \
        .where(SpaceKeyCacheModel.key == space_key)
    entry = session.exec(statement).first()
    if entry:
        entry.exists = space_exists
    else:
        db_entry = SpaceKeyCacheModel(
            key=space_key,
            exists=space_exists,
        )
        session.add(db_entry)

    session.commit()

    # synchronize health status
    update_health_status(healthy=True)

    return space_exists
