# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from collections.abc import Generator
from fastapi import Depends
from functools import lru_cache
from sphinx_confluence_relay.models import metadata
from sqlalchemy.engine import Engine
from sqlmodel import Session
from sqlmodel import create_engine
from typing import Annotated


@lru_cache
def get_engine() -> Engine:
    """
    request to acquire the database engine

    This call is used to build the default database engine for the application.
    It is used in the main startup of the application and also used through
    database session building. Only a single instance is generated in
    production through the use of `lru_cache`.

    Note that this call is overridden through dependency injection during
    unit testing.

    Returns:
        the engine
    """
    return create_engine(
        'sqlite:///./database.db',
        connect_args={
            'check_same_thread': False,
        },
    )


# provides an engine instance which fastapi can use with dependency injection
EngineDep = Annotated[Engine, Depends(get_engine)]


def create_db_and_tables(engine: Engine) -> None:
    """
    create the database/tables for this application

    Helps build the database and required tables based on the registered
    models in the application.

    Args:
        engine: the engine to create tables in
    """
    metadata.create_all(engine)


def get_session(engine: EngineDep) -> Generator[Session, None, None]:
    """
    acquire a database session for the given database engine

    Will generate a new database session which a caller can use to query and
    update database content.

    Args:
        engine: the engine dependency to use

    Returns:
        the session
    """
    with Session(engine) as session:
        yield session


# provides a session instance which fastapi can use with dependency injection
SessionDep = Annotated[Session, Depends(get_session)]
