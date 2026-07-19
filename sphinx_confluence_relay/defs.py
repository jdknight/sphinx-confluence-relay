# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from enum import StrEnum
from pathlib import Path
import sys

# list of support configuration names
if sys.platform != 'win32':
    SUPPORTED_SETTINGS_LOCATIONS = [
        Path('sphinx-confluence-relay.toml'),
        Path('/etc/sphinx-confluence-relay.toml'),
    ]
else:
    SUPPORTED_SETTINGS_LOCATIONS = [
        Path('sphinx-confluence-relay.toml'),
    ]

# expected section to parse configuration data in the toml file
CONFIG_BASE_SECTION = 'sphinx-confluence-relay'

# expected section to parse space data in the toml file
CONFIG_SPACE_SECTION = 'sphinx-confluence-relay-space'

# time (in seconds) for all rest connection requests
DEFAULT_REST_CONNECTION_TIMEOUT = 5.0

# size limit (in bytes) for incoming manifest files
DEFAULT_SIZE_LIMIT = 20_000_000  # 20mb

# file flag to report an unhealthy status
UNHEALTHY_STATUS_FLAG = Path('/run/sphinx-confluence-relay/unhealthy')

# duration to wait (in seconds) between trying to process a queue item
# but delaying since the target confluence instance is down
INSTANCE_DOWN_DELAY = 60


class CfgKey(StrEnum):
    """
    configuration keys

    Defines a series of attributes which define various keys used to hold
    various configuration values.

    Attributes:
        BANNER: the banner to add at the top of the homepage
        CA_CERTIFICATE: the ca certificate to use
        CONFLUENCE_TOKEN: token needed to interface with confluence
        CONFLUENCE_URL: the confluence instance url
        DROP_RESTRICTED: whether requests to drop requests is restricted
        IGNORE_TLS: whether to ignore tls certificate issues
        PUBLISH_TOKENS: tokens needed for users to publish to this space
        SESSION_HEADERS: the session headers to apply for all api requests
        SIZE_LIMIT: the size limit for provided manifest files
        SPACES: explicit list of spaces permitted
        TIMEOUT: the timeout for connection api requests
    """
    BANNER = 'banner'
    CA_CERTIFICATE = 'ca-certificate'
    CONFLUENCE_TOKEN = 'confluence-token'  # noqa: S105
    CONFLUENCE_URL = 'confluence-url'
    DROP_RESTRICTED = 'drop-restricted'
    IGNORE_TLS = 'ignore-tls'
    PUBLISH_TOKENS = 'publish-tokens'
    SESSION_HEADERS = 'session-headers'
    SIZE_LIMIT = 'size-limit'
    SPACES = 'spaces'
    TIMEOUT = 'timeout'


class CfgSpaceKey(StrEnum):
    """
    space-specific configuration keys

    Defines a series of attributes which define various keys used to hold
    various space-specific configuration values.

    Attributes:
        PUBLISH_TOKEN: the token needed for users to publish to this space
        SPACE: the space
    """
    PUBLISH_TOKEN = 'publish-token'  # noqa: S105
    SPACE = 'space'
