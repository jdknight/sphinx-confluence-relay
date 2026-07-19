# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from __future__ import annotations
from pathlib import Path
from sphinx_confluence_relay.defs import DEFAULT_REST_CONNECTION_TIMEOUT
from sphinx_confluence_relay.defs import DEFAULT_SIZE_LIMIT
from sphinx_confluence_relay.settings import Settings
from tests import ScrTestCase
from typing import Self


class TestConfiguration(ScrTestCase):
    @classmethod
    def setUpClass(cls: type[Self]) -> None:
        test_dir = Path(__file__).parent
        cls.dataset = test_dir / 'data' / 'configs'

    def setUp(self) -> None:
        self.cfg = Settings()

    def test_config_none(self) -> None:
        self.assertIsNone(None)

    def test_config_file_invalid(self) -> None:
        fname = self.dataset / 'invalid.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_file_missing(self) -> None:
        fname = self.dataset / 'missing.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_banner(self) -> None:
        fname = self.dataset / 'confluence-banner.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.banner, 'test banner')

    def test_config_ca_certificate_exists(self) -> None:
        with self.temp_dir() as wd, self.working_dir(wd):
            # create a dummy "certificate"
            with Path('dummy.crt').open('wb'):
                pass

            fname = self.dataset / 'ca-certificate-exists.toml'
            loaded = self.cfg.load(fname)
            self.assertTrue(loaded)
            self.assertTrue(self.cfg.ca_certificate.exists())

    def test_config_ca_certificate_missing(self) -> None:
        fname = self.dataset / 'ca-certificate-missing.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_confluence_schema_http(self) -> None:
        fname = self.dataset / 'confluence-schema-http.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.confluence_url, 'http://wiki.example.com')

    def test_config_confluence_schema_https(self) -> None:
        fname = self.dataset / 'confluence-schema-https.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.confluence_url, 'https://wiki.example.com')

    def test_config_confluence_schema_missing(self) -> None:
        fname = self.dataset / 'confluence-schema-missing.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_confluence_token_empty(self) -> None:
        fname = self.dataset / 'confluence-token-empty.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_confluence_url_empty(self) -> None:
        fname = self.dataset / 'confluence-url-empty.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_drop_restricted_disabled(self) -> None:
        fname = self.dataset / 'drop-restricted-disabled.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertFalse(self.cfg.drop_restricted)

    def test_config_drop_restricted_enabled(self) -> None:
        fname = self.dataset / 'drop-restricted-enabled.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertTrue(self.cfg.drop_restricted)

    def test_config_ignore_tls_disabled(self) -> None:
        fname = self.dataset / 'ignore-tls-disabled.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertFalse(self.cfg.ignore_tls)

    def test_config_ignore_tls_enabled(self) -> None:
        fname = self.dataset / 'ignore-tls-enabled.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertTrue(self.cfg.ignore_tls)

    def test_config_publish_tokens_empty(self) -> None:
        fname = self.dataset / 'publish-tokens-empty.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertFalse(self.cfg.publish_tokens)

    def test_config_publish_tokens_invalid(self) -> None:
        fname = self.dataset / 'publish-tokens-invalid.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_publish_tokens_valid(self) -> None:
        fname = self.dataset / 'publish-tokens-valid.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.publish_tokens, {
            'another-token',
            'some-token',
        })

    def test_config_session_headers_invalid_name(self) -> None:
        fname = self.dataset / 'session-headers-invalid-name.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_session_headers_invalid_value(self) -> None:
        fname = self.dataset / 'session-headers-invalid-value.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_session_headers_valid(self) -> None:
        fname = self.dataset / 'session-headers-valid.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.session_headers, {
            'SESSION_ID': 'DuMmYa',
            'U_ID': 'DuMmYb',
        })

    def test_config_size_limit_invalid_int(self) -> None:
        fname = self.dataset / 'size-limit-invalid-int.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_size_limit_invalid_unknown(self) -> None:
        fname = self.dataset / 'size-limit-invalid-unknown.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_size_limit_valid_default(self) -> None:
        fname = self.dataset / 'size-limit-valid-default.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.size_limit, DEFAULT_SIZE_LIMIT)

    def test_config_size_limit_valid_set(self) -> None:
        fname = self.dataset / 'size-limit-valid-set.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.size_limit, 500_000_000)

    def test_config_space_token_empty_space(self) -> None:
        fname = self.dataset / 'space-token-empty-space.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_space_token_empty_token(self) -> None:
        fname = self.dataset / 'space-token-empty-token.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_space_token_invalid_space(self) -> None:
        fname = self.dataset / 'space-token-invalid-space.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_space_token_invalid_token(self) -> None:
        fname = self.dataset / 'space-token-invalid-token.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_space_token_missing_space(self) -> None:
        fname = self.dataset / 'space-token-missing-space.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_space_token_missing_token(self) -> None:
        fname = self.dataset / 'space-token-missing-token.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_space_token_valid(self) -> None:
        fname = self.dataset / 'space-token-valid.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertTrue(self.cfg.space_tokens)
        self.assertIn('TEST', self.cfg.space_tokens)
        self.assertEqual(self.cfg.space_tokens['TEST'], {'TOKEN'})

    def test_config_spaces_empty(self) -> None:
        fname = self.dataset / 'spaces-empty.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertFalse(self.cfg.spaces)

    def test_config_spaces_invalid(self) -> None:
        fname = self.dataset / 'spaces-invalid.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_spaces_valid(self) -> None:
        fname = self.dataset / 'spaces-valid.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.spaces, {
            'SPACE-A',
            'SPACE-B',
            'SPACE-C',
        })

    def test_config_timeout_invalid_int(self) -> None:
        fname = self.dataset / 'timeout-invalid-int.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_timeout_invalid_unknown(self) -> None:
        fname = self.dataset / 'timeout-invalid-unknown.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)

    def test_config_timeout_valid_default(self) -> None:
        fname = self.dataset / 'timeout-valid-default.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.timeout, DEFAULT_REST_CONNECTION_TIMEOUT)

    def test_config_timeout_valid_set(self) -> None:
        fname = self.dataset / 'timeout-valid-set.toml'
        loaded = self.cfg.load(fname)
        self.assertTrue(loaded)
        self.assertEqual(self.cfg.timeout, 10.0)

    def test_config_unknown_value(self) -> None:
        fname = self.dataset / 'unknown-entry.toml'
        loaded = self.cfg.load(fname)
        self.assertFalse(loaded)
