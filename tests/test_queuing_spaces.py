# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from tests import DATA_FOLDER
from tests import ScrAppTestCase
from unittest.mock import AsyncMock
from unittest.mock import patch


# sample manifest file
MOCK_MANIFEST_FILE = DATA_FOLDER / 'scb-manifest.json'


class TestQueuingSpace(ScrAppTestCase):
    def test_queuing_space_allowed(self) -> None:
        self.settings.spaces.add('GOODSPACE')

        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'GOODSPACE',
                    'parent_page': '1234',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 200)

    @patch('sphinx_confluence_relay.routes.validate_space',
        new=AsyncMock(return_value=False))
    def test_queuing_space_denied(self) -> None:
        self.settings.spaces.add('GOODSPACE')

        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'BADSPACE',
                    'parent_page': '1234',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 403)
