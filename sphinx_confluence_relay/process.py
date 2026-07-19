# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from datetime import UTC
from datetime import datetime
from fastapi import status
from sphinx_confluence_relay.defs import INSTANCE_DOWN_DELAY
from sphinx_confluence_relay.logger import logger
from sphinx_confluence_relay.models import QueueModel
from sphinx_confluence_relay.models import StatusModel
from sphinx_confluence_relay.publish import publish
from sphinx_confluence_relay.state import AppState
from sphinx_confluence_relay.validate import validate_confluence
from sqlmodel import Session
from sqlmodel import col
from sqlmodel import func
from sqlmodel import select
import asyncio
import httpx
import json


# initial wait time before we start trying to publish queued requests
INITIAL_WAIT = 10


# interval (in seconds) to wait for another queue item
MIN_INTERVAL = 5


async def process(state: AppState) -> None:
    """
    publishing process thread

    This call drives the publish events in the application. It will poll
    for queued publish requests in the database.

    Args:
        state: the application state
    """

    try:
        # initial wait before we start
        await asyncio.sleep(INITIAL_WAIT)

        # cycle forever, waiting for queued requests to process
        while True:
            result = await process_event(state)
            if not result:
                # if we had nothing processed, wait a moment
                await asyncio.sleep(MIN_INTERVAL)

    # triggered when the application's lifecycle has ended
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception('unhandled process exception')


async def process_event(state: AppState) -> bool:
    """
    attempt to process a queued request

    This call helps trigger a publish event. First, it will check in the
    database if there is a request to process. If one is found, it will
    pull the request out of the database and begin publishing. This call
    will wait until publishing has completed. Once completed, it will update
    the final result of the publish event in the status database.

    Args:
        state: the application state

    Returns:
        whether a request was processed this invoke
    """

    sid: int | None = None
    rid: int | None = None
    space_key: str | None = None
    parent_page: str | None = None
    raw_data: str | None = None

    # find the next available queued request (if any)
    with Session(state.engine) as session:
        # pylint: disable=not-callable
        count_statement = select(func.count(col(QueueModel.id)))
        total_count = session.scalar(count_statement) or 0

        # if more than one in the queue, print a summary
        if total_count > 1:
            logger.info(f'total detected in queue: {total_count}')


        # if we have any in the queue, check to see if the instance is
        # up before pulling an item out of the queue
        attempt_publish = False
        if total_count > 0:
            if await validate_confluence(state.settings, state.http_client):
                attempt_publish = True
            else:
                # instance is not available; wait a bit
                logger.info('confluence instance down; waiting a moment...')
                await asyncio.sleep(INSTANCE_DOWN_DELAY)

        # if we are good to process, claim one
        if attempt_publish:
            qr_statement = select(QueueModel).order_by(col(QueueModel.updated))
            queued_request = session.exec(qr_statement).first()

            if queued_request:
                rid = queued_request.id
                space_key = queued_request.space_key
                parent_page = queued_request.parent_page
                raw_data = queued_request.data

                new_status = StatusModel(
                    rid=rid,
                    status='publishing',
                    created=queued_request.updated,
                    started=datetime.now(UTC),
                )

                session.add(new_status)
                session.delete(queued_request)
                session.commit()

                sid = new_status.id

    # if we have a request to process, attempt to publish now
    if sid:
        assert parent_page is not None
        assert raw_data is not None
        assert rid is not None
        assert space_key is not None
        logger.info(f'[R{rid}]: processing request')

        # attempt to perform a publish event
        data = json.loads(raw_data)

        detail = None
        result = 'error'
        suffix = ''
        try:
            try:
                total = await publish(state, rid, space_key, data, parent_page)

                result = 'complete'
                suffix = f'; pages: {total}'
            except httpx.HTTPStatusError as exc:
                match exc.response.status_code:
                    case status.HTTP_401_UNAUTHORIZED \
                            | status.HTTP_403_FORBIDDEN:
                        logger.exception(f'[R{rid}]: failed to publish')
                        detail = 'backend not authenticated'

                    case _:
                        raise
        except Exception as exc:
            logger.exception(f'[R{rid}]: failed to publish')
            detail = str(exc)

        logger.info(f'[R{rid}]: finished request ({result}{suffix})')

        # update the status entry
        with Session(state.engine) as session:
            sts_statement = select(StatusModel).where(StatusModel.id == sid)
            status_entry = session.exec(sts_statement).first()
            if status_entry:
                status_entry.detail = detail
                status_entry.status = result
                status_entry.completed = datetime.now(UTC)
                status_entry.updated = datetime.now(UTC)
                session.add(status_entry)
                session.commit()

    # return whether we processed an entry
    return sid is not None
