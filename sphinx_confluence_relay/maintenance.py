# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from sphinx_confluence_relay.models import QueueModel
from sphinx_confluence_relay.models import SpaceKeyCacheModel
from sphinx_confluence_relay.models import StatusModel
from sqlalchemy.engine import Engine
from sqlmodel import col
from sqlmodel import delete
from sqlmodel import Session


# duration to consider status data to be stale
STALE_KEY_CACHE = timedelta(minutes=1)

# duration to consider status data to be stale
STALE_STATUS = timedelta(days=5)

# duration to consider queued requests to be stale
STALE_QUEUED_REQUESTS = timedelta(days=1)


def cleanup_key_cache(engine: Engine) -> None:
    """
    maintenance task to cleanup cached keys

    The application will hold in a table a cached state tracking whether
    or not a given key value is a valid space for the Confluence instance.
    This call is used to clean out old cached states from the database.

    Args:
        the sql engine
    """

    now = datetime.now(UTC)
    stale_cache = now - STALE_KEY_CACHE

    with Session(engine) as session:
        # remove old cache entries
        sc_statement = delete(SpaceKeyCacheModel) \
            .where(col(SpaceKeyCacheModel.updated) < stale_cache)
        session.exec(sc_statement)
        session.commit()


def cleanup_stale(engine: Engine) -> None:
    """
    maintenance task to cleanup stale queue/status entries

    The application will hold queued requests and statuses for periods of
    time. To ensure the tables are cleaned out, this call ensures never
    consumed queued entries are dropped. In addition, after several days,
    old status results from requests are dropped.

    Args:
        the sql engine
    """

    now = datetime.now(UTC)
    stale_statuses = now - STALE_STATUS
    stale_queued = now - STALE_QUEUED_REQUESTS

    with Session(engine) as session:
        # remove old queued entries
        sq_statement = delete(QueueModel) \
            .where(col(QueueModel.updated) < stale_queued)
        session.exec(sq_statement)
        session.commit()

        # remove old status entries
        ss_statement = delete(StatusModel) \
            .where(col(StatusModel.updated) < stale_statuses)
        session.exec(ss_statement)
        session.commit()
