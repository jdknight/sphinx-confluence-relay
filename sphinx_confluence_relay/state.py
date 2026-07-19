# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from dataclasses import dataclass
from httpx import AsyncClient
from sphinx_confluence_relay.settings import Settings
from sqlalchemy.engine import Engine


@dataclass
class AppState:
    """
    application state representation

    State class mainly used for type checking.
    """

    engine: Engine
    http_client: AsyncClient
    settings: Settings
    rate_limit_last: float
    rate_limit_next: int | None
