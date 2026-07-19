# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from __future__ import annotations
from collections import defaultdict
from fastapi import Depends
from functools import lru_cache
from pathlib import Path
from sphinx_confluence_relay.defs import CONFIG_BASE_SECTION
from sphinx_confluence_relay.defs import CONFIG_SPACE_SECTION
from sphinx_confluence_relay.defs import CfgKey
from sphinx_confluence_relay.defs import CfgSpaceKey
from sphinx_confluence_relay.defs import DEFAULT_REST_CONNECTION_TIMEOUT
from sphinx_confluence_relay.defs import DEFAULT_SIZE_LIMIT
from sphinx_confluence_relay.defs import SUPPORTED_SETTINGS_LOCATIONS
from sphinx_confluence_relay.logger import logger
from typing import Annotated
from typing import Any
from urllib.parse import urlparse
import tomllib


class Settings:
    def __init__(self) -> None:
        """
        settings instance

        Holds the extracted settings information from a
        sphinx-confluence-relay TOML file.
        """
        self._reset()

    def _reset(self) -> None:
        """
        reset the settings state

        Clears the internally cached settings state populated from a
        `load()` event.
        """

        self.banner: str | None = None
        self.ca_certificate: Path | None = None
        self.confluence_token: str | None = None
        self.confluence_url: str | None = None
        self.drop_restricted = False
        self.ignore_tls = False
        self.publish_tokens: set[str] = set()
        self.session_headers: dict[str, str] = {}
        self.size_limit = DEFAULT_SIZE_LIMIT
        self.space_tokens: dict[str, set[str]] = defaultdict(set)
        self.spaces: set[str] = set()
        self.timeout = DEFAULT_REST_CONNECTION_TIMEOUT

    def load(self, path: Path) -> bool:
        """
        load settings information from a provided file

        This call will open a TOML settings file and populate various
        settings options.

        Args:
            path: the path of the settings file to load

        Returns:
            whether a file was loaded
        """

        self._reset()

        try:
            logger.debug(f'attempting to load settings file: {path}')
            with path.open('rb') as f:
                raw_config = tomllib.load(f)
                cfg: dict[str, Any] = raw_config.get(CONFIG_BASE_SECTION, {})

                raw_confluence_url = cfg.get(CfgKey.CONFLUENCE_URL, '')
                if not self._parse_confluence_url(raw_confluence_url):
                    logger.error('(cfg) missing confluence url')
                    return False

                self.confluence_token = \
                    cfg.get(CfgKey.CONFLUENCE_TOKEN, '').strip()
                if not self.confluence_token:
                    logger.error('(cfg) missing confluence token')
                    return False

                self.banner = cfg.get(CfgKey.BANNER, '').strip()

                raw_cert = cfg.get(CfgKey.CA_CERTIFICATE)
                if raw_cert:
                    self.ca_certificate = Path(raw_cert)
                    if not self.ca_certificate.is_file():
                        logger.error('(cfg) ca certificate not a file')
                        return False

                self.drop_restricted = bool(cfg.get(CfgKey.DROP_RESTRICTED))

                self.ignore_tls = bool(cfg.get(CfgKey.IGNORE_TLS))

                for token in cfg.get(CfgKey.PUBLISH_TOKENS, []):
                    if not isinstance(token, str) or not token.strip():
                        logger.error('(cfg) invalid publish token')
                        return False
                    self.publish_tokens.add(token.strip())

                raw_sh = cfg.get(CfgKey.SESSION_HEADERS, {})
                for entry in raw_sh:
                    if 'name' not in entry:
                        logger.error('(cfg) missing name in session headers')
                        return False
                    if 'value' not in entry:
                        logger.error('(cfg) missing value in session headers')
                        return False
                    entry_name = entry.get('name')
                    entry_value = entry.get('value')
                    self.session_headers[entry_name] = entry_value

                raw_size_limit = cfg.get(CfgKey.SIZE_LIMIT)
                if raw_size_limit:
                    parsed_size_limit = self._parse_positive_int(
                        'size-limit', raw_size_limit)
                    if parsed_size_limit:
                        # megabytes to bytes
                        self.size_limit = parsed_size_limit * 1_000_000
                    else:
                        return False

                for key in cfg.get(CfgKey.SPACES, []):
                    if not isinstance(key, str) or not key.strip():
                        logger.error('(cfg) invalid space key')
                        return False
                    self.spaces.add(key.strip().upper())

                raw_timeout = cfg.get(CfgKey.TIMEOUT)
                if raw_timeout:
                    parsed_timeout = self._parse_positive_int(
                        'timeout', raw_timeout)
                    if parsed_timeout:
                        self.timeout = float(parsed_timeout)
                    else:
                        return False

                for key in cfg:
                    if key not in [item.value for item in CfgKey]:
                        logger.error(f'(cfg) unknown settings key: {key}')
                        return False

                spaces_cfg = raw_config.get(CONFIG_SPACE_SECTION, [])
                for scfg in spaces_cfg:
                    if CfgSpaceKey.SPACE not in scfg:
                        logger.error('(cfg) space settings missing key')
                        return False

                    if CfgSpaceKey.PUBLISH_TOKEN not in scfg:
                        logger.error('(cfg) space settings missing token')
                        return False

                    key = scfg.get(CfgSpaceKey.SPACE)
                    if not isinstance(key, str):
                        logger.error('(cfg) space settings invalid key')
                        return False

                    token = scfg.get(CfgSpaceKey.PUBLISH_TOKEN)
                    if not isinstance(token, str):
                        logger.error('(cfg) space settings invalid token')
                        return False

                    key = key.strip().upper()
                    if not key:
                        logger.error('(cfg) space settings empty key')
                        return False

                    token = token.strip()
                    if not token:
                        logger.error('(cfg) space settings empty token')
                        return False

                    logger.debug(f'(cfg) registering token for space: {key}')
                    self.space_tokens[key].add(token)

                return True

        except tomllib.TOMLDecodeError:
            logger.exception(f'(cfg) unable to load settings file: {path}')
        except FileNotFoundError:
            logger.error(f'(cfg) settings file does not exist: {path}')
        except OSError:
            logger.exception(f'(cfg) unable to load settings file: {path}')

        return False

    def _parse_confluence_url(self, value: str) -> bool:
        """
        parse a raw confluence url

        Validate a user-provided Confluence URL.

        Args:
            value: the raw value

        Returns:
            whether the url could be successfully parsed
        """

        self.confluence_url = value.strip('/')

        try:
            parsed_server_name = urlparse(self.confluence_url)
        except ValueError:
            logger.error('(cfg) confluence-url is not a valid value')
            return False

        if parsed_server_name.scheme not in ('http', 'https'):
            logger.error('(cfg) confluence-url  must start with http(s)://')
            return False

        if not parsed_server_name.hostname:
            logger.error('(cfg) confluence-url missing a valid hostname')
            return False

        return True

    def _parse_positive_int(self, desc: str, value: str | None) -> int | None:
        """
        parse a raw positive integer value

        Validate a user-provided value that should be a positive integer is
        one.

        Args:
            value: the raw value

        Returns:
            the positive integer value or `None` if not a positive integer
        """

        if not value:
            return None

        try:
            result = int(value)
        except ValueError:
            logger.error(f'(cfg) invalid {desc} value')
            return None
        else:
            if result < 0:
                logger.error(f'(cfg) invalid negative {desc}')
                return None

        return result


def find_settings() -> Path | None:
    """
    find a settings in a provided path

    This call can be used to find an expected sphinx-confluence-relay
    settings file in a provided path (of known default names). If no
    settings file can be found, this call will return ``None``.

    Returns:
        the settings filename; otherwise ``None``
    """

    for cfg_file in SUPPORTED_SETTINGS_LOCATIONS:
        if cfg_file.is_file():
            return cfg_file

    return None


# shared settings fetch call
@lru_cache
def get_settings() -> Settings:
    """
    request to acquire the active settings

    This call is used to fetch the settings for the application. This may be
    used/preloaded in the main startup of the application and also used in
    various routes. Only a single instance is generated in production through
    the use of `lru_cache`.

    Note that this call is overridden through dependency injection during
    unit testing.

    Returns:
        the settings

    Raises:
        AppSettingsError: when failed to load settings
    """

    settings = Settings()

    settings_path = find_settings()
    if not settings_path:
        msg = 'unable to find a settings file'
        raise AppSettingsError(msg)

    if not settings.load(settings_path):
        msg = 'failed to load the settings file'
        raise AppSettingsError(msg)

    return settings


class AppSettingsError(RuntimeError):
    """exception raised when failing to load settings"""


# provides a settings instance which fastapi can use with dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
