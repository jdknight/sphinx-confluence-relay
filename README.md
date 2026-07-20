# Sphinx Confluence Relay

[![pip Version](https://badgen.net/pypi/v/sphinx-confluence-relay?label=PyPI)](https://pypi.python.org/pypi/sphinx-confluence-relay)
[![Build Status](https://github.com/jdknight/sphinx-confluence-relay/actions/workflows/build.yml/badge.svg)](https://github.com/jdknight/sphinx-confluence-relay/actions/workflows/build.yml)

## Overview

The project provides the ability to create a "relay" service that accepts
generated manifest files from
[Atlassian Confluence Builder for Sphinx][confluencebuilder]
([GitHub][confluencebuilder-github]), powered by [Sphinx][sphinx]
([GitHub][sphinx-github]), and publish them to a pre-configured Confluence
Data Center instance (Confluence Cloud is not supported). Using such a service
allows system administrators to setup publish relaying where users do not need
to expose their Confluence tokens.

## Requirements

* [Python][python] 3.11+
* [APScheduler][apscheduler]
* [FastAPI][fastapi]
* [SQLModel][sqlmodel]

# Usage

Users of a running service will publish using at least three key components:

- A [data-embedded manifest][confluence-manifest-data] generated from
  Atlassian Confluence Builder for Sphinx.
- The key of a space to publish into.
- The parent page name/identifier to publish documentation under.

A publish event will take a manifest and upload all pages/attachments into
a given target space. After pages/attachments are uploaded, any legacy content
hosted on Confluence will be removed. Publication and removals are contained
to the descendants of the configured parent page. Requests that would require
moving pages in a space into the parent page's descendants will be ignored.

Publish events are queued. The service can accept multiple requests and will
process them in a first-in-first-out (FIFO) order. Pages/attachments are only
uploaded if required (i.e. changed).

Users may use the REST interface of a hosted service utilizing any common
tools (e.g. [curl][curl]). Alternatively, if this package is installed on a
client system, users may utilize the publish helper tool:

```none
sphinx-confluence-relay-publish --help
 (or)
python -m sphinx_confluence_relay --help
```

For example:

```none
sphinx-confluence-relay-publish http://upload.wiki.example.com/ --space-key MYSPACE --parent-page Documentation
```

Command line options can be replaced using respective environment options:

```
SPHINX_CONFLUENCE_RELAY_PUBLISH_PARENT
SPHINX_CONFLUENCE_RELAY_PUBLISH_SPACE
SPHINX_CONFLUENCE_RELAY_PUBLISH_URL
```

If a manifest file is not provided via the `--manifest` argument, the default
paths searched for will be:

```none
scb-manifest.json
 (or)
_build/confluence/scb-manifest.json
 (or)
_build/singleconfluence/scb-manifest.json
```

If a system administrator has configured authentication requirements, a token
can be passed a couple of ways. The utility accepts a token value from the
environment:

```
SPHINX_CONFLUENCE_RELAY_PUBLISH_TOKEN
```

Passed in using the standard input stream with `--password-stdin`:

```none
cat ~/.token | sphinx-confluence-relay-publish ... --password-stdin
```

Or passed in using the `--token` argument:

```none
sphinx-confluence-relay-publish ... --token <TOKEN>
```

# Service Installation

## Configuration

The relay service relies on a TOML configuration file. A template of this
configuration can be found in the root of this repository:

```none
sphinx-confluence-relay.toml.default
```

A system administrator will typically prepare a `sphinx-confluence-relay.toml`
file on a host. sphinx-confluence-relay will search for configurations found
in the following paths:

```none
sphinx-confluence-relay.toml
 (or)
/etc/sphinx-confluence-relay.toml  (non-Windows)
```

The bare minimum configuration required is the configuration of the Confluence
Data Center API URL and the token that will be used for REST interaction:

```toml
[sphinx-confluence-relay]
confluence-url = 'https://wiki.example.com/rest/api/'
confluence-token = ''
```

If a system administrator wishes to require tokens for publish requests,
they can register one or more tokens in a `publish-tokens` option:

```toml
publish-tokens = [
    'SOME_TOKEN',
]
```

By default, all spaces the Confluence token can access could be published to.
If an environment is looking to restrict only publishing to specific pages,
individual spaces can be populated in a `spaces` option:

```toml
spaces = [
    'MYSPACE',
]
```

For additional advanced options, refer to the template configuration.

## Manual Service Setup

System administrators may manually set up using the following instructions.
Adjusts paths to desired preferences.

Build a path to hold packages:

```none
mkdir /opt/sphinx-confluence-relay
cd /opt/sphinx-confluence-relay
```

Create a virtual environment:

```none
python -m venv .venv
source .venv/bin/activate
```

Install this service using [pip][pip]:

```none
pip install sphinx-confluence-relay
```

Place the prepared configuration file in the local directory with the name:

```none
sphinx-confluence-relay.toml
```

Run this service:

```none
uvicorn sphinx_confluence_relay.main:app --host 0.0.0.0 --port 8080
```

## Docker

This project supports multiple ways to use this utility inside a Docker
environment. A recommended choice is to use a pre-built image available
from GitHub's container registry.

### Pre-built image

A pre-built image can be acquired using the following command:

```none
docker pull ghcr.io/jdknight/sphinx-confluence-relay
```

On the host that will run Docker, copy the configuration file into this path:

```none
/etc/sphinx-confluence-relay.toml
```

Ensure the path is available for holding a database of queued requests and
status information:

```none
/var/lib/sphinx-confluence-relay/
```

The container then can be run using the following command:

```none
docker run --name sphinx-confluence-relay --detach --restart unless-stopped \
    -p 8080:8080 \
    -v /etc/sphinx-confluence-relay.toml:/etc/sphinx-confluence-relay.toml:ro \
    -v /var/lib/sphinx-confluence-relay/database.db:/database.db \
    ghcr.io/jdknight/sphinx-confluence-relay
```

### Self-built image

Users who wish to manage their own image can do so with the Docker
definitions found inside this repository. This can be done by cloning
this repository on the host wanting to run the container. A Docker
build can be run using:

```none
docker build -t ghcr.io/jdknight/sphinx-confluence-relay \
    --detach -f docker/Dockerfile .
```

Then running the same `docker run` call mentioned above.

### Self-managed Docker Compose

Users can also take advantage of the Docker compose definition. For a
working directory to hold Docker Compose content, ensure a settings file
is setup:

```none
sphinx-confluence-relay.toml
```

Next, load up the container using `docker compose`:

```none
docker compose build
docker compose up --detach
```

Both Docker build calls will by default load a container with the
PyPI version of sphinx-confluence-relay. Users wanting to use the local
implementation in their container can do so by performing a Docker build
with the `--build-arg local` argument.

For example:

```none
docker compose build --build-arg BUILD_MODE=local
docker compose up --detach
```


[apscheduler]: https://apscheduler.readthedocs.io/
[confluence-manifest-data]: https://sphinxcontrib-confluencebuilder.readthedocs.io/configuration/#confval-confluence_manifest_data
[confluencebuilder-github]: https://github.com/sphinx-contrib/confluencebuilder
[confluencebuilder]: https://sphinxcontrib-confluencebuilder.readthedocs.io/
[curl]: https://curl.se/
[fastapi]: https://fastapi.tiangolo.com/
[pip]: https://pip.pypa.io/
[python]: https://www.python.org/
[sphinx-github]: https://github.com/sphinx-doc/sphinx
[sphinx]: https://www.sphinx-doc.org/
[sqlmodel]: https://sqlmodel.tiangolo.com/
