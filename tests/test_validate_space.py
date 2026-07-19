# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from functools import cache
from sphinx_confluence_relay.models import SpaceKeyCacheModel
from sqlmodel import Session
from sqlmodel import select
from tests import DATA_FOLDER
from tests import ScrAppTestCase
from tests.support.http_daemon import httpd_context
from unittest.mock import AsyncMock
import httpx


# sample manifest file
MOCK_MANIFEST = DATA_FOLDER / 'scb-manifest.json'


class TestValidateSpace(ScrAppTestCase):
    def setUp(self) -> None:
        self.mock_validate_page.stop()
        self.mock_validate_space.stop()

    def test_validate_space_exists_cached(self) -> None:
        new_entry = SpaceKeyCacheModel(
            key='TESTSPACE',
            exists=True,
        )

        with Session(self.engine) as session:
            session.add(new_entry)
            session.commit()

        with MOCK_MANIFEST.open(mode='rb') as f, httpd_context() as httpd:
            host, port = httpd.server_address
            self.settings.confluence_url = f'http://{host}:{port}'

            # mock api response good parent page
            httpd.rsp.append((200, {
                'dummy': 'data',
            }))

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

        self.assertEqual(response.status_code, 200)

    def test_validate_space_exists_rest(self) -> None:
        with MOCK_MANIFEST.open(mode='rb') as f, httpd_context() as httpd:
            host, port = httpd.server_address
            self.settings.confluence_url = f'http://{host}:{port}'

            # mock api response good space
            httpd.rsp.append((200, {
                'dummy': 'data',
            }))

            # mock api response good parent page
            httpd.rsp.append((200, {
                'dummy': 'data',
            }))

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

        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            statement = select(SpaceKeyCacheModel)\
                .where(SpaceKeyCacheModel.key == 'TESTSPACE')
            entry = session.exec(statement).first()
            self.assertIsNotNone(entry)
            self.assertTrue(entry.exists)

    def test_validate_space_forbidden(self) -> None:
        with MOCK_MANIFEST.open(mode='rb') as f, httpd_context() as httpd:
            host, port = httpd.server_address
            self.settings.confluence_url = f'http://{host}:{port}'

            # mock an api response
            httpd.rsp.append((403, {
                'detail': 'not authenticated',
            }))

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

        self.assertEqual(response.status_code, 500)

    def test_validate_space_missing_cached(self) -> None:
        new_entry = SpaceKeyCacheModel(
            key='TESTSPACE',
            exists=False,
        )

        with Session(self.engine) as session:
            session.add(new_entry)
            session.commit()

        with MOCK_MANIFEST.open(mode='rb') as f:
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

    def test_validate_space_missing_fetch(self) -> None:
        with MOCK_MANIFEST.open(mode='rb') as f, httpd_context() as httpd:
            host, port = httpd.server_address
            self.settings.confluence_url = f'http://{host}:{port}'

            # mock an api response
            httpd.rsp.append((404, {
                'detail': 'does not exist',
            }))

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

        with Session(self.engine) as session:
            statement = select(SpaceKeyCacheModel)\
                .where(SpaceKeyCacheModel.key == 'TESTSPACE')
            entry = session.exec(statement).first()
            self.assertIsNotNone(entry)
            self.assertFalse(entry.exists)

    def test_validate_space_tracking_race(self) -> None:
        mock_client = AsyncMock()
        self.app.state.http_client.get = mock_client

        @cache
        def emulate_another_db_update() -> None:
            new_entry = SpaceKeyCacheModel(
                key='TESTSPACE',
                exists=False,
            )

            with Session(self.engine) as session:
                session.add(new_entry)
                session.commit()

        mock_client.side_effect = lambda url: \
            emulate_another_db_update() or \
            httpx.Response(
                200,
                json={'dummy': 'data'},
                request=httpx.Request('GET', url),
            )

        with MOCK_MANIFEST.open(mode='rb') as f:
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

        self.assertEqual(response.status_code, 200)

        with Session(self.engine) as session:
            statement = select(SpaceKeyCacheModel)\
                .where(SpaceKeyCacheModel.key == 'TESTSPACE')
            entry = session.exec(statement).first()
            self.assertIsNotNone(entry)
            self.assertTrue(entry.exists)

    def test_validate_space_unexpected(self) -> None:
        with MOCK_MANIFEST.open(mode='rb') as f, httpd_context() as httpd:
            host, port = httpd.server_address
            self.settings.confluence_url = f'http://{host}:{port}'

            # mock an api response
            httpd.rsp.append((418, {
                'detail': 'teapot',
            }))

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

        self.assertEqual(response.status_code, 500)
