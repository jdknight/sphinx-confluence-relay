# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from datetime import UTC
from datetime import datetime
from sqlalchemy import MetaData
from sqlalchemy.orm import registry
from sqlmodel import Field
from sqlmodel import SQLModel


# metadata for all cache-specific models
metadata = MetaData()


class Entity(SQLModel, registry=registry(metadata=metadata)):
    # date this entry was last updated in this database
    updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        index=True,
    )


class QueueBase(SQLModel):
    # key of the confluence space being targeted
    space_key: str

    # parent page reference for the confluence space to publish under
    parent_page: str

    # manifest data to be published
    data: str


class QueueModel(QueueBase, Entity, table=True):
    __tablename__ = 'queue'
    __table_args__ = {
        'sqlite_autoincrement': True,
    }

    id: int | None = Field(
        default=None,
        primary_key=True,
    )


class QueueData(QueueBase):
    id: int


class QueueState(QueueData, Entity):
    pass


class SpaceKeyCacheBase(SQLModel):
    # the space key
    key: str = Field(
        index=True,
        unique=True,
    )

    # whether this space key is considered to exist
    exists: bool


class SpaceKeyCacheModel(SpaceKeyCacheBase, Entity, table=True):
    __tablename__ = 'space_key_cache'
    id: int | None = Field(
        default=None,
        primary_key=True,
    )


class SpaceKeyCacheData(SpaceKeyCacheBase):
    id: int


class SpaceKeyCacheState(SpaceKeyCacheData, Entity):
    pass


class StatusBase(SQLModel):
    # identifier of the request
    rid: int = Field(
        index=True,
        unique=True,
    )

    # status of this publish request
    status: str

    # date this publish request was considered created/queued
    created: datetime | None = None

    # date this publish request started publishing
    started: datetime | None = None

    # date this publish request completed publishing
    completed: datetime | None = None

    # any details from this status state
    detail: str | None = None


class StatusModel(StatusBase, Entity, table=True):
    __tablename__ = 'status'
    id: int | None = Field(
        default=None,
        primary_key=True,
    )


class StatusData(StatusBase):
    id: int


class StatusState(StatusData, Entity):
    pass
