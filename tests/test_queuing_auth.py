# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from tests import DATA_FOLDER
from tests import ScrAppTestCase


# sample manifest file
MOCK_MANIFEST_FILE = DATA_FOLDER / 'scb-manifest.json'


class TestQueuingAuth(ScrAppTestCase):
    def test_queuing_auth_failed_multiple(self) -> None:
        self.settings.publish_tokens = {
            'UNIT-TEST-TOKEN1',
            'UNIT-TEST-TOKEN2',
        }

        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'TESTSPACE',
                    'parent_page': '1234',
                },
                headers={
                    'Authorization': 'Bearer DIFFERENT-TOKEN',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 401)

    def test_queuing_auth_failed_single(self) -> None:
        self.settings.publish_tokens = {
            'UNIT-TEST-TOKEN',
        }

        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'TESTSPACE',
                    'parent_page': '1234',
                },
                headers={
                    'Authorization': 'Bearer DIFFERENT-TOKEN',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 401)

    def test_queuing_auth_missing(self) -> None:
        self.settings.publish_tokens = {
            'UNIT-TEST-TOKEN',
        }

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

        self.assertEqual(response.status_code, 401)

    def test_queuing_auth_space_allowed(self) -> None:
        self.settings.publish_tokens = {
            'UNIT-TEST-TOKEN',
        }
        self.settings.space_tokens = {
            'TESTSPACE': {
                'ANOTHER-TOKEN',
            },
        }

        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'TESTSPACE',
                    'parent_page': '1234',
                },
                headers={
                    'Authorization': 'Bearer ANOTHER-TOKEN',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 200)

    def test_queuing_auth_space_denied(self) -> None:
        self.settings.publish_tokens = {
            'UNIT-TEST-TOKEN',
        }
        self.settings.space_tokens = {
            'TESTSPACE': {
                'ANOTHER-TOKEN',
            },
        }

        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'TESTSPACE',
                    'parent_page': '1234',
                },
                headers={
                    'Authorization': 'Bearer UNIT-TEST-TOKEN',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 401)

    def test_queuing_auth_success_default(self) -> None:
        self.settings.publish_tokens = {
            'UNIT-TEST-TOKEN',
        }

        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'TESTSPACE',
                    'parent_page': '1234',
                },
                headers={
                    'Authorization': 'Bearer UNIT-TEST-TOKEN',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 200)

    def test_queuing_auth_success_multiple(self) -> None:
        self.settings.publish_tokens = {
            'UNIT-TEST-TOKEN1',
            'UNIT-TEST-TOKEN2',
        }

        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'TESTSPACE',
                    'parent_page': '1234',
                },
                headers={
                    'Authorization': 'Bearer UNIT-TEST-TOKEN2',
                },
                files={
                    'file': f,
                },
            )

        self.assertEqual(response.status_code, 200)
