# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from sphinx_confluence_relay.publish import publish
from sphinx_confluence_relay.settings import Settings
from sphinx_confluence_relay.state import AppState
from tests import DATA_FOLDER
from tests import ScrTestCase
from tests.support.http_daemon import httpd_context
import httpx
import json


# sample manifest file
MOCK_MANIFEST = DATA_FOLDER / 'scb-manifest.json'


class TestPublish(ScrTestCase):
    async def test_publish(self) -> None:
        manifest_data = MOCK_MANIFEST.read_text(encoding='utf-8')
        manifest = json.loads(manifest_data)
        space_key = 'UNITTEST_SPACE'

        async with httpx.AsyncClient() as http_client:
            state = AppState(
                engine=None,
                http_client=http_client,
                settings=Settings(),
                rate_limit_last=0.,
                rate_limit_next=None,
            )

            with httpd_context() as httpd:
                host, port = httpd.server_address
                state.settings.confluence_url = f'http://{host}:{port}'

                #######
                # SETUP
                #######

                # hint no descendants
                httpd.rsp.append((200, {
                    'results': [
                    ],
                }))

                ########
                # PAGE 1
                ########

                # hint no existing page
                httpd.rsp.append((200, {
                    'results': [
                    ],
                }))

                # response for published page
                httpd.rsp.append((200, {
                    'id': 12345,
                    'version': {
                        'number': 1,
                    },
                }))

                # response for un-watch
                httpd.rsp.append((204, None))

                # response for property update
                httpd.rsp.append((200, {
                    'id': 12346,
                }))

                ########
                # PAGE 2
                ########

                # hint no existing page
                httpd.rsp.append((200, {
                    'results': [
                    ],
                }))

                # response for published page
                httpd.rsp.append((200, {
                    'id': 12347,
                    'version': {
                        'number': 1,
                    },
                }))

                # response for un-watch
                httpd.rsp.append((204, None))

                # response for property update
                httpd.rsp.append((200, {
                    'id': 12348,
                }))

                ############
                # ATTACHMENT
                ############

                # hint no existing attachment
                httpd.rsp.append((200, {
                    'results': [
                    ],
                }))

                # response for published attachment
                httpd.rsp.append((200, {
                    'id': 12348,
                }))

                rv = await publish(state, 123, space_key, manifest, '98765')

        self.assertEqual(rv, 2)

        # descendants population
        path, _ = httpd.req['GET'].pop(0)
        self.assertTrue(path.startswith('/content/search'))

        # first page publish checks
        path, _ = httpd.req['GET'].pop(0)
        self.assertTrue(path.startswith('/content'))
        self.assertIn(f'spaceKey={space_key}', path)
        self.assertIn('title=Test+Project', path)

        path, _ = httpd.req['POST'].pop(0)
        self.assertEqual(path, '/content')

        path, _ = httpd.req['DELETE'].pop(0)
        self.assertEqual(path, '/user/watch/content/12345')

        path, _ = httpd.req['POST'].pop(0)
        self.assertEqual(path, '/content/12345/property')

        # second page publish checks
        path, _ = httpd.req['GET'].pop(0)
        self.assertTrue(path.startswith('/content'))
        self.assertIn(f'spaceKey={space_key}', path)
        self.assertIn('title=Second+Page', path)

        path, _ = httpd.req['POST'].pop(0)
        self.assertEqual(path, '/content')

        path, _ = httpd.req['DELETE'].pop(0)
        self.assertEqual(path, '/user/watch/content/12347')

        path, _ = httpd.req['POST'].pop(0)
        self.assertEqual(path, '/content/12347/property')

        # attachment publish checks
        path, _ = httpd.req['GET'].pop(0)
        self.assertTrue(path.startswith('/content/12347/child/attachment'))
        self.assertIn('af6a4603e039cca2f6823d287f6c87e561aa6e68.png', path)
