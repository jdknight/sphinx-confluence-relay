# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from sphinx_confluence_relay.models import QueueModel
from sqlmodel import Session
from sqlmodel import select
from tests import ScrAppTestCase


class TestRequestStatus(ScrAppTestCase):
    def setUp(self) -> None:
        new_entry = QueueModel(
            space_key='TESTSPACE',
            data='mock-data',
            parent_page='1234',
        )

        with Session(self.engine) as session:
            session.add(new_entry)
            session.commit()

            self.entry_id = new_entry.id

    def test_request_drop_auth_allowed(self) -> None:
        self.settings.publish_tokens = {
            'UNIT-TEST-TOKEN',
        }

        response = self.client.delete(
            f'/drop/{self.entry_id}',
            headers={
                'Authorization': 'Bearer UNIT-TEST-TOKEN',
            },
        )
        self.assertEqual(response.status_code, 204)

        with Session(self.engine) as session:
            statement = select(QueueModel).where(QueueModel.id == self.entry_id)
            entry = session.exec(statement).first()
            self.assertIsNone(entry)

    def test_request_drop_auth_denied(self) -> None:
        self.settings.publish_tokens = {
            'UNIT-TEST-TOKEN',
        }

        response = self.client.delete(f'/drop/{self.entry_id}')
        self.assertEqual(response.status_code, 401)

        with Session(self.engine) as session:
            statement = select(QueueModel).where(QueueModel.id == self.entry_id)
            entry = session.exec(statement).first()
            self.assertIsNotNone(entry)

    def test_request_drop_ignored(self) -> None:
        response = self.client.delete('/drop/12345')
        self.assertEqual(response.status_code, 404)

    def test_request_drop_performed(self) -> None:
        response = self.client.delete(f'/drop/{self.entry_id}')
        self.assertEqual(response.status_code, 204)

        with Session(self.engine) as session:
            statement = select(QueueModel).where(QueueModel.id == self.entry_id)
            entry = session.exec(statement).first()
            self.assertIsNone(entry)

    def test_request_drop_restricted(self) -> None:
        self.settings.drop_restricted = True

        response = self.client.delete(f'/drop/{self.entry_id}')
        self.assertEqual(response.status_code, 403)

        with Session(self.engine) as session:
            statement = select(QueueModel).where(QueueModel.id == self.entry_id)
            entry = session.exec(statement).first()
            self.assertIsNotNone(entry)
