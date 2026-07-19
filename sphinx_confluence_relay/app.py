# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sphinx_confluence_relay import __version__ as scr_version
from sphinx_confluence_relay.cache import create_db_and_tables
from sphinx_confluence_relay.cache import get_engine
from sphinx_confluence_relay.logger import logger
from sphinx_confluence_relay.maintenance import cleanup_key_cache
from sphinx_confluence_relay.maintenance import cleanup_stale
from sphinx_confluence_relay.models import SpaceKeyCacheModel
from sphinx_confluence_relay.process import process
from sphinx_confluence_relay.routes import router
from sphinx_confluence_relay.settings import Settings
from sphinx_confluence_relay.settings import get_settings
from sphinx_confluence_relay.swagger import router as swagger_router
from sphinx_confluence_relay.validate import validate_confluence
from sqlalchemy.engine import Engine
from sqlmodel import Session
from sqlmodel import delete
from typing import TYPE_CHECKING
from typing import cast
import asyncio
import httpx
import ssl

if TYPE_CHECKING:
    from sphinx_confluence_relay.state import AppState


# base path for this applications sources/resources
BASE_DIR = Path(__file__).parent

# document holding the API service description
SERVICE_DESC = BASE_DIR / 'description.md'


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    the lifespan of the application

    Provides a lifespan context, allowing the registration of various
    resources to be available for the lifecycle of our application. We
    setup:

    - Our database/tables.
    - A web client for interaction with external services.
    - Scheduler to perform maintenance tasks.
    - Rate-limit task to drive publish events.

    Args:
        app: the application
    """

    # prepare sql models
    create_db_and_tables(app.state.engine)

    # when starting up, clear any cached space key states
    with Session(app.state.engine) as session:
        clear_skcache_statement = delete(SpaceKeyCacheModel)
        session.exec(clear_skcache_statement)
        session.commit()

    # prepare an http client for requests
    limits = httpx.Limits(
        max_connections=100,
        max_keepalive_connections=10,
    )

    timeout = httpx.Timeout(
        connect=app.state.settings.timeout,
        read=15.0,
        write=5.0,
        pool=5.0,
    )

    headers: dict[str, str] = {}
    headers |= app.state.settings.session_headers
    headers |= {
        # will only process json
        'Accept': 'application/json',
        # configure confluence pat to perform publish events with
        'Authorization': f'Bearer {app.state.settings.confluence_token}',
        # user agent for our interactions
        'User-Agent': f'SphinxConfluenceRelay/{scr_version}',
        # ignore csrf
        'X-Atlassian-Token': 'no-check',
    }

    # setup ssl context
    ssl_context = ssl.create_default_context()
    if app.state.settings.ca_certificate:
        ssl_context.load_verify_locations(
            cafile=app.state.settings.ca_certificate)
    elif app.state.settings.ignore_tls:
        ssl_context = False  # type: ignore[assignment]

    async with httpx.AsyncClient(
                headers=headers,
                limits=limits,
                timeout=timeout,
                verify=ssl_context,
            ) as client:
        app.state.http_client = client

        logger.info('validating availability of confluence instance...')
        if await validate_confluence(app.state.settings, client):
            logger.info('confluence instance appears to be online')
        else:
            logger.warning('unable to access confluence instance at this time')

        # maintenance every hour to check for stale entries
        app.state.scheduler.add_job(
            cleanup_key_cache,
            CronTrigger(minute='*'),
            args=[app.state.engine],
        )
        app.state.scheduler.add_job(
            cleanup_stale,
            CronTrigger(hour='*', minute=0, second=0),
            args=[app.state.engine],
        )
        app.state.scheduler.start()

        # add poll to check for queued items
        process_polling = asyncio.create_task(
            process(cast('AppState', app.state)),
        )

        try:
            # run fast api
            yield
        finally:
            if app.state.scheduler.running:
                app.state.scheduler.shutdown()

            process_polling.cancel()
            await asyncio.gather(process_polling, return_exceptions=True)


def create_app(
        engine: Engine | None = None,
        settings: Settings | None = None,
    ) -> FastAPI:
    """
    create the application instance

    This call builds our application.

    An engine and settings instance can be provided, but mostly used for
    testing scenarios. By default, an application will internally setup the
    engine and settings instance.

    Args:
        engine (optional): the sql engine to use
        settings (optional): the settings for the application

    Returns:
        the application
    """

    # load/validate settings before starting
    settings = settings or get_settings()

    # warn if operating in anonymous publishing mode
    if not settings.publish_tokens:
        logger.warning('no token configured; anonymous publishing enabled')

    # build a scheduled for cleanup/maintenance work
    scheduler = AsyncIOScheduler()

    # prepare the fast api service
    app = FastAPI(
        description=SERVICE_DESC.read_text(encoding='utf-8'),
        lifespan=lifespan,
        title='Confluence Relay Publisher for Sphinx Documentation',
        version=scr_version,
    )

    # track entities in state for lifespan/routes to use
    app.state.engine = engine or get_engine()
    app.state.rate_limit_last = 1
    app.state.rate_limit_next = None
    app.state.scheduler = scheduler
    app.state.settings = settings

    # register static resources to serve
    app.mount('/static',
        StaticFiles(directory=str(BASE_DIR / 'static')), name='static')

    # register various routes
    app.include_router(router)
    app.include_router(swagger_router)

    return app
