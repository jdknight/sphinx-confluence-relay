# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from datetime import UTC
from datetime import datetime
from sphinx_confluence_relay.models import QueueModel
from sqlmodel import Session
from tests import DATA_FOLDER
from tests import ScrAppTestCase
from sqlmodel import select
from unittest.mock import AsyncMock
from unittest.mock import patch


# sample manifest file
MOCK_MANIFEST_FILE = DATA_FOLDER / 'scb-manifest.json'


class TestQueuingDb(ScrAppTestCase):
    def test_queuing_active(self) -> None:
        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'TESTSPACE',
                    'parent_page': 'Sample Parent',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        rid = data.get('rid')
        self.assertIsNotNone(rid)

        with Session(self.engine) as session:
            statement = select(QueueModel).where(QueueModel.id == rid)
            entry = session.exec(statement).first()
            self.assertIsNotNone(entry)

        self.assertEqual(entry.space_key, 'TESTSPACE')
        self.assertEqual(entry.parent_page, 'Sample Parent')

        now = datetime.now(UTC)
        updated = entry.updated.replace(tzinfo=UTC)
        self.assertLessEqual(updated, now)

    @patch('sphinx_confluence_relay.routes.validate_space',
        new=AsyncMock(return_value=False))
    def test_queuing_space_missing(self) -> None:
        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'TESTSPACE',
                    'parent_page': '1234',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 404)
