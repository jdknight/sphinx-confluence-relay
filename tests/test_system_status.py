# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from sphinx_confluence_relay.models import QueueModel
from sqlmodel import Session
from tests import ScrAppTestCase


class TestSystemStatus(ScrAppTestCase):
    def test_system_status_confluence_instance(self) -> None:
        self.settings.confluence_url = 'http://unit-test.example.org/wiki'

        response = self.client.get('/status')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        reported_confluence_instance = data.get('confluence-instance')
        self.assertEqual(
            reported_confluence_instance, 'http://unit-test.example.org/wiki')

    def test_system_status_queued(self) -> None:
        with Session(self.engine) as session:
            for idx in range(4):
                new_entry = QueueModel(
                    space_key=f'TESTSPACE{idx}',
                    data='mock-data',
                    parent_page='1234',
                )

                session.add(new_entry)
                session.commit()

        response = self.client.get('/status')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        reported_queued = data.get('queued')
        self.assertEqual(reported_queued, 4)
