# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from sphinx_confluence_relay.settings import Settings
from tests import ScrAppTestCase


class TestRestHeaders(ScrAppTestCase):
    def settings_hook(self, settings: Settings) -> None:
        settings.session_headers = {
            'Test-Header': 'Some-Value',
        }

    def test_rest_headers_session_headers(self) -> None:
        http_client_headers = self.app.state.http_client.headers
        self.assertIn('Test-Header', http_client_headers)
        self.assertEqual(http_client_headers['Test-Header'], 'Some-Value')
