#!/usr/bin/env sh
set -e

. /opt/sphinx-confluence-relay/venv/bin/activate

exec uvicorn sphinx_confluence_relay.main:app \
    --host 0.0.0.0 \
    --port 8080 \
    $SPHINX_CONFLUENCE_RELAY_EXTRA_ARGS
