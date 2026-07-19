# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from pathlib import Path
from sphinx_confluence_relay import __version__ as sphinx_confluence_relay_version
from urllib.parse import urlparse
import argparse
import httpx
import json
import os
import sys


# default path of a manifest file to upload
DEFAULT_MANIFESTS = [
    # local file
    Path('scb-manifest.json'),
    # common sphinx output build paths
    Path('_build') / 'confluence' / 'scb-manifest.json',
    Path('_build') / 'singleconfluence' / 'scb-manifest.json',
]

def main() -> None:
    """
    publish helper mainline

    The mainline for sphinx-confluence-relay's publisher helper utility.
    """

    parser = argparse.ArgumentParser(
        prog='sphinx-confluence-relay-publish',
    )

    parser.add_argument(
        'url',
        help='url of the publish service to send a manifest to',
    )
    parser.add_argument(
        '--header',
        '-H',
        action='append',
        help='http headers to include in request',
    )
    parser.add_argument(
        '--manifest',
        help='manifest file to upload (default: scb-manifest.json)',
    )
    parser.add_argument(
        '--parent-page',
        required=True,
        help='parent page to publish into',
    )
    parser.add_argument(
        '--password-stdin',
        action='store_true',
        help='pass in the token via the standard input stream',
    )
    parser.add_argument(
        '--space-key',
        required=True,
        help='space to publish to',
    )
    parser.add_argument(
        '--token',
        help='token to pass into bearer header',
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s ' + sphinx_confluence_relay_version,
    )

    args = parser.parse_args()

    # verify the url is something sane
    service_url = args.url.strip('/')

    try:
        parsed_server_name = urlparse(service_url)
    except ValueError:
        msg = 'url is not a valid value'
        raise SystemExit(msg)

    if parsed_server_name.scheme not in ('http', 'https'):
        msg = 'url must start with http:// or https://'
        raise SystemExit(msg)

    if not parsed_server_name.hostname:
        msg = 'url missing a valid hostname'
        raise SystemExit(msg)

    # verify any raw headers provided
    provided_headers = {}
    if args.header:
        for header in args.header:
            if ':' not in header:
                msg = f'invalid header entry: {header}'
                raise SystemExit(msg)

            key, value = header.split(':', 1)
            key = key.strip()

            if not key:
                msg = f'invalid header key for argument: {header}'
                raise SystemExit(msg)

            provided_headers[key] = value.strip()

    # verify we have a manifest to work with
    manifest = None

    if args.manifest:
        manifest = Path(args.manifest)
        if not manifest.is_file():
            msg = f'failed to find manifest file: {manifest.as_posix()}'
            raise SystemExit(msg)
    else:
        for check_manifest in DEFAULT_MANIFESTS:
            if check_manifest.is_file():
                manifest = check_manifest

        if not manifest:
            msg = 'failed to detect a manifest file'
            raise SystemExit(msg)

    # sanity check the manifest file
    try:
        manifest_content = manifest.read_text(encoding='utf-8')
        parsed_data = json.loads(manifest_content)
    except json.JSONDecodeError:
        msg = 'invalid manifest file detected (non-json)'
        raise SystemExit(msg)

    if parsed_data.get('type') != 'SphinxConfluenceBuilder/Manifest':
        msg = 'invalid manifest file detected'
        raise SystemExit(msg)

    if not parsed_data.get('includesData'):
        msg = 'manifest does not include data (required)'
        raise SystemExit(msg)

    space_key = args.space_key.strip().upper()
    if not space_key:
        msg = 'space key not provided'
        raise SystemExit(msg)

    parent_page = args.parent_page.strip()
    if not parent_page:
        msg = 'parent page not provided'
        raise SystemExit(msg)

    if args.token:
        token = args.token
    elif args.password_stdin:
        for line in sys.stdin:
            token = line.strip()
    else:
        token = os.getenv('SPHINX_CONFLUENCE_RELAY_PUBLISH_TOKEN', '')

    token = token.strip()
    token_desc = '(set)' if token else '(unset)'

    print(f'sphinx-confluence-relay-publish {sphinx_confluence_relay_version}')
    print()
    print(f'       Manifest: {manifest.as_posix()}')
    print(f'      Space Key: {space_key}')
    print(f'    Parent Page: {parent_page}')
    print(f' Upload service: {service_url}')
    print(f'          Token: {token_desc}')
    print()
    print('Uploading... ', end='')

    payload = {
        'space_key': space_key,
        'parent_page': parent_page,
    }

    files = {
        'file': ('scb-manifest.json', manifest_content, 'application/json'),
    }

    headers: dict[str, str] = {}
    headers |= provided_headers

    if token:
        headers['Authorization'] = f'Bearer {token}'

    try:
        rsp = httpx.post(
            f'{service_url}/publish',
            data=payload,
            headers=headers,
            files=files,
        )
        rsp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print('failed.')
        msg = f'Server returned status code ({exc.response.status_code}).'
        raise SystemExit(msg)
    except httpx.RequestError as exc:
        print('failed.')
        msg = f'Failed to connect to the server: ({exc})'
        raise SystemExit(msg)
    else:
        print('success!')


if __name__ == '__main__':
    main()  # pragma: no cover
