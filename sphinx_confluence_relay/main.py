# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from sphinx_confluence_relay.app import create_app


# provides an application instance which asgi implementations can use; e.g.
#
#   uvicorn sphinx_confluence_relay.main:app --host 127.0.0.1 --port 29981
app = create_app()
