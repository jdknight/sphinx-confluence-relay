# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from sphinx_confluence_relay.maintenance import cleanup_key_cache
from sphinx_confluence_relay.maintenance import cleanup_stale
from sphinx_confluence_relay.models import QueueModel
from sphinx_confluence_relay.models import SpaceKeyCacheModel
from sphinx_confluence_relay.models import StatusModel
from sqlmodel import Session
from sqlmodel import select
from tests import ScrAppTestCase


class TestValidateMaintenance(ScrAppTestCase):
    def test_maintenance_key_cache_no_change(self) -> None:
        new_entry = SpaceKeyCacheModel(
            key='TESTSPACE',
            exists=True,
        )

        with Session(self.engine) as session:
            session.add(new_entry)
            session.commit()

        cleanup_key_cache(self.engine)

        with Session(self.engine) as session:
            statement = select(SpaceKeyCacheModel) \
                .where(SpaceKeyCacheModel.key == 'TESTSPACE')
            entry = session.exec(statement).first()
            self.assertIsNotNone(entry)

    def test_maintenance_key_cache_removed(self) -> None:
        new_entry = SpaceKeyCacheModel(
            key='TESTSPACE',
            exists=True,
            updated=datetime.now(UTC) - timedelta(days=365),
        )

        with Session(self.engine) as session:
            session.add(new_entry)
            session.commit()

        cleanup_key_cache(self.engine)

        with Session(self.engine) as session:
            statement = select(SpaceKeyCacheModel) \
                .where(SpaceKeyCacheModel.key == 'TESTSPACE')
            entry = session.exec(statement).first()
            self.assertIsNone(entry)

    def test_maintenance_queue_cache_no_change(self) -> None:
        new_entry = QueueModel(
            space_key='TESTSPACE',
            data='mock-data',
            parent_page='1234',
        )

        with Session(self.engine) as session:
            session.add(new_entry)
            session.commit()

        cleanup_stale(self.engine)

        with Session(self.engine) as session:
            statement = select(QueueModel) \
                .where(QueueModel.space_key == 'TESTSPACE')
            entry = session.exec(statement).first()
            self.assertIsNotNone(entry)

    def test_maintenance_queue_cache_removed(self) -> None:
        new_entry = QueueModel(
            space_key='TESTSPACE',
            data='mock-data',
            parent_page='1234',
            updated=datetime.now(UTC) - timedelta(days=365),
        )

        with Session(self.engine) as session:
            session.add(new_entry)
            session.commit()

        cleanup_stale(self.engine)

        with Session(self.engine) as session:
            statement = select(QueueModel) \
                .where(QueueModel.space_key == 'TESTSPACE')
            entry = session.exec(statement).first()
            self.assertIsNone(entry)

    def test_maintenance_status_cache_no_change(self) -> None:
        new_entry = StatusModel(
            rid=123,
            status='completed',
        )

        with Session(self.engine) as session:
            session.add(new_entry)
            session.commit()

        cleanup_stale(self.engine)

        with Session(self.engine) as session:
            statement = select(StatusModel) \
                .where(StatusModel.rid == 123)
            entry = session.exec(statement).first()
            self.assertIsNotNone(entry)

    def test_maintenance_status_cache_removed(self) -> None:
        new_entry = StatusModel(
            rid=123,
            status='completed',
            updated=datetime.now(UTC) - timedelta(days=365),
        )

        with Session(self.engine) as session:
            session.add(new_entry)
            session.commit()

        cleanup_stale(self.engine)

        with Session(self.engine) as session:
            statement = select(StatusModel) \
                .where(StatusModel.rid == 123)
            entry = session.exec(statement).first()
            self.assertIsNone(entry)
