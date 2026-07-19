# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from fastapi import APIRouter
from fastapi import File
from fastapi import Form
from fastapi import Header
from fastapi import HTTPException
from fastapi import Path
from fastapi import Request
from fastapi import UploadFile
from fastapi import status
from pydantic import ValidationError
from sphinx_confluence_relay.cache import SessionDep
from sphinx_confluence_relay.logger import logger
from sphinx_confluence_relay.manifest import parse_manifest
from sphinx_confluence_relay.models import QueueBase
from sphinx_confluence_relay.models import QueueModel
from sphinx_confluence_relay.models import StatusBase
from sphinx_confluence_relay.models import StatusModel
from sphinx_confluence_relay.settings import SettingsDep
from sphinx_confluence_relay.token import SecurityDep
from sphinx_confluence_relay.token import verify_token
from sphinx_confluence_relay.validate import validate_confluence
from sphinx_confluence_relay.validate import validate_page
from sphinx_confluence_relay.validate import validate_space
from sqlmodel import col
from sqlmodel import func
from sqlmodel import select
from typing import Annotated
from typing import Any
import json


# router for publishing-related endpoints
router = APIRouter()


# route for accepting a publish request to be queued
@router.post(
    '/publish',
    summary='Publish a manifest to the configured Confluence instance.',
)
async def request_publish(
        req: Request,
        session: SessionDep,
        settings: SettingsDep,
        credentials: SecurityDep,
        space_key: Annotated[
            str,
            Form(
                min_length=1,
                max_length=255,
                pattern=r'^[a-zA-Z0-9]+$',
                description='Confluence space key.',
                json_schema_extra={
                    'example': '',
                },
            ),
        ],
        file: Annotated[
            UploadFile,
            File(
                description='The manifest.',
            ),
        ],
        parent_page: Annotated[
            str,
            Form(
                min_length=1,
                max_length=255,
                description='Confluence page to publish under '
                            '(string for name; numeric for page identifier).',
                json_schema_extra={
                    'example': '',
                },
            ),
        ],
        content_length: Annotated[str | None, Header(
            include_in_schema=False,
        )] = None,
    ) -> dict:
    '''
    This endpoint provides a means to publish a manifest file generated from
    Atlassian Confluence Builder for Sphinx extension (`scb-manifest.json`).

    The manifest must include page/attachment data using the
    [`confluence_manifest_data`][1] configuration.

    [1]: https://sphinxcontrib-confluencebuilder.readthedocs.io/configuration/#confval-confluence_manifest_data
    '''

    verify_token(credentials, settings, space_key)

    target_space_key = space_key.upper()

    if parent_page:
        parent_page = parent_page.strip()

        if parent_page.isdigit() and int(parent_page) < 1:
            raise HTTPException(
                status_code=status.HTTP_411_LENGTH_REQUIRED,
                detail='unexpected parent page identifier',
            )

    # verify a proper file type is received
    if file.content_type != 'application/json':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='unexpected file type',
        )

    # sanity check file limits
    if content_length is None:
        raise HTTPException(
            status_code=status.HTTP_411_LENGTH_REQUIRED,
            detail='content-length header missing',
        )

    if not content_length.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='invalid content-length header',
        )

    if int(content_length) > settings.size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail='manifest exceeds maximum allowed size.',
        )

    # if we have explicit list of spaces allowed to publish on, verify that
    # the provided space key is found
    if settings.spaces and target_space_key not in settings.spaces:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='provided space key not permitted',
        )

    # read manifest file
    file_bytes = await file.read()
    await file.close()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='empty manifest file',
        )

    # verify proper encoding
    try:
        data = file_bytes.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='unexpected file encoding',
        ) from exc

    # verify valid json data
    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='unexpected json structure',
        ) from exc

    # process the data into a manifest data that works for us
    manifest = parse_manifest(parsed_data)

    # test space exists
    http_client = req.app.state.http_client
    valid = await validate_space(
        session, settings, http_client, target_space_key)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='unable to find space',
        )

    # test parent page exists
    valid = await validate_page(
        settings, http_client, target_space_key, parent_page)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='unable to find parent page',
        )

    # build queued request from this information
    try:
        new_entry = QueueBase(
            space_key=target_space_key,
            parent_page=parent_page,
            data=json.dumps(manifest),
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='invalid request',
        ) from exc

    # validate the content to be persisted
    db_entry = QueueModel.model_validate(new_entry)

    # persist the queued request
    session.add(db_entry)
    session.commit()

    return {
        'rid': db_entry.id,
        'space_key': space_key,
        'parent_page': parent_page,
    }


# route for requesting the status of a system
@router.get(
    '/status',
    summary='Request the status of the system.',
)
async def request_system_status(
        req: Request,
        session: SessionDep,
        settings: SettingsDep,
    ) -> dict[str, Any]:

    # pylint: disable=not-callable
    confluence_up = await validate_confluence(
        settings, req.app.state.http_client)
    count_statement = select(func.count(col(QueueModel.id)))
    total_count = session.scalar(count_statement) or 0

    return {
        'confluence-healthy': confluence_up,
        'confluence-instance': settings.confluence_url,
        'queued': total_count,
    }


# route for requesting the status of a request
@router.get(
    '/status/{id}',
    summary='Request the status of a queued publish request.',
)
async def request_status(
        session: SessionDep,
        id: Annotated[  # noqa: A002
            int,
            Path(
                gt=0,
                description='The request identifier.',
            ),
        ],
    ) -> StatusBase:

    # check if the identifier is in the queue
    queued_statement = select(QueueModel).where(QueueModel.id == id)
    queued_entry = session.exec(queued_statement).first()

    if queued_entry:
        return StatusBase(
            rid=id,
            created=queued_entry.updated,
            status='pending',
        )

    # if not in the queue, check if we are/have processed it
    status_statement = select(StatusModel).where(StatusModel.rid == id)
    status_entry = session.exec(status_statement).first()

    if status_entry:
        return status_entry

    # not found, report unknown identifier
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='unknown identifier',
    )


# route for dropping a queued request
@router.delete(
    '/drop/{id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Drop a queued request that has not yet started.',
)
async def request_drop(
        session: SessionDep,
        settings: SettingsDep,
        credentials: SecurityDep,
        id: Annotated[  # noqa: A002
            int,
            Path(
                gt=0,
                description='The request identifier.',
            ),
        ],
    ) -> None:

    verify_token(credentials, settings)

    if settings.drop_restricted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='instance does not allow submitting drop requests',
        )

    statement = select(QueueModel).where(QueueModel.id == id)
    entry = session.exec(statement).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='unable to find request',
        )

    session.delete(entry)
    session.commit()
    logger.info(f'[R{id}]: dropped request by a user')
