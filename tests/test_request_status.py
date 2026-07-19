# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import status
from sphinx_confluence_relay.models import QueueBase
from sphinx_confluence_relay.models import QueueModel
from sphinx_confluence_relay.models import StatusBase
from sphinx_confluence_relay.models import StatusModel
from sqlmodel import Session
from tests import ScrAppTestCase


class TestRequestStatus(ScrAppTestCase):
    def test_request_status_founded_active(self) -> None:
        entry_date = datetime.now(UTC)
        entry_id = 42

        new_entry = StatusBase(
            rid=entry_id,
            status='publishing',
            created=entry_date,
            started=entry_date,
        )
        db_entry = StatusModel.model_validate(new_entry)

        with Session(self.engine) as session:
            session.add(db_entry)
            session.commit()

        response = self.client.get(f'/status/{entry_id}')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        rid = data.pop('rid', None)
        completed = data.pop('completed', None)
        created = data.pop('created', None)
        detail = data.pop('detail', None)
        started = data.pop('started', None)
        status = data.pop('status', None)

        self.assertEqual(rid, entry_id)
        self.assertEqual(status, 'publishing')
        self.assertIsNone(completed)
        self.assertIsNone(detail)
        self.assertIsNotNone(created)
        self.assertIsNotNone(started)

        created_dt = datetime.fromisoformat(created) \
            .replace(tzinfo=UTC)
        self.assertLessEqual(created_dt, entry_date)

        started_dt = datetime.fromisoformat(started) \
            .replace(tzinfo=UTC)
        self.assertLessEqual(started_dt, entry_date)

        self.assertFalse(data, 'additional entries detected')

    def test_request_status_founded_completed(self) -> None:
        entry_id = 42
        entry_created_date = datetime.now(UTC)
        entry_started_date = entry_created_date + timedelta(minutes=1)
        entry_completed_date = entry_started_date + timedelta(minutes=1)

        new_entry = StatusBase(
            rid=entry_id,
            status='complete',
            created=entry_created_date,
            started=entry_started_date,
            completed=entry_completed_date,
        )
        db_entry = StatusModel.model_validate(new_entry)

        with Session(self.engine) as session:
            session.add(db_entry)
            session.commit()

        response = self.client.get(f'/status/{entry_id}')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        rid = data.pop('rid', None)
        completed = data.pop('completed', None)
        created = data.pop('created', None)
        detail = data.pop('detail', None)
        started = data.pop('started', None)
        status = data.pop('status', None)

        self.assertEqual(rid, entry_id)
        self.assertEqual(status, 'complete')
        self.assertIsNone(detail)
        self.assertIsNotNone(completed)
        self.assertIsNotNone(created)
        self.assertIsNotNone(started)

        completed = datetime.fromisoformat(completed) \
            .replace(tzinfo=UTC)
        self.assertLessEqual(completed, entry_completed_date)

        created_dt = datetime.fromisoformat(created) \
            .replace(tzinfo=UTC)
        self.assertLessEqual(created_dt, entry_created_date)

        started_dt = datetime.fromisoformat(started) \
            .replace(tzinfo=UTC)
        self.assertLessEqual(started_dt, entry_started_date)

        self.assertFalse(data, 'additional entries detected')

    def test_request_status_founded_queue(self) -> None:
        new_entry = QueueBase(
            space_key='TESTSPACE',
            data='mock-data',
            parent_page='1234',
        )
        db_entry = QueueModel.model_validate(new_entry)

        with Session(self.engine) as session:
            session.add(db_entry)
            session.commit()

            new_id = db_entry.id

        response = self.client.get(f'/status/{new_id}')
        self.assertEqual(response.status_code, 200)

        data = response.json()

        rid = data.pop('rid', None)
        completed = data.pop('completed', None)
        created = data.pop('created', None)
        detail = data.pop('detail', None)
        started = data.pop('started', None)
        status = data.pop('status', None)

        self.assertEqual(rid, new_id)
        self.assertEqual(status, 'pending')
        self.assertIsNone(completed)
        self.assertIsNone(detail)
        self.assertIsNone(started)
        self.assertIsNotNone(created)

        now = datetime.now(UTC)

        created_dt = datetime.fromisoformat(created) \
            .replace(tzinfo=UTC)
        self.assertLessEqual(created_dt, now)

        self.assertFalse(data, 'additional entries detected')

    def test_request_status_invalid(self) -> None:
        response = self.client.get('/status/-1')
        self.assertEqual(response.status_code, 422)

        response = self.client.get('/status/0')
        self.assertEqual(response.status_code, 422)

        response = self.client.get('/status/some-value')
        self.assertEqual(response.status_code, 422)

    def test_request_status_missing(self) -> None:
        response = self.client.get('/status/12345')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
