# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from collections.abc import AsyncGenerator
from tests import DATA_FOLDER
from tests import ScrAppTestCase


# sample manifest file
MOCK_MANIFEST_FILE = DATA_FOLDER / 'scb-manifest.json'

# identifier used for generated http request data
BOUNDARY = '----UnitTest'


def generator(data: bytes) -> AsyncGenerator[None, None]:
    """
    generator to pass into httpx to allow custom header work
    """

    # push our space key
    yield f'--{BOUNDARY}\r\n'.encode()
    yield b'Content-Disposition: form-data; name="space_key"\r\n\r\n'
    yield b'KEY\r\n'

    # push our parent page
    yield f'--{BOUNDARY}\r\n'.encode()
    yield b'Content-Disposition: form-data; name="parent_page"\r\n\r\n'
    yield b'1234\r\n'

    # push our data
    yield f'--{BOUNDARY}\r\n'.encode()
    yield b'Content-Disposition: form-data; name="file"; filename="z.json"\r\n'
    yield b'Content-Type: application/json\r\n\r\n'
    if data:
        yield data
    yield b'\r\n'

    # eom
    yield f'--{BOUNDARY}--\r\n'.encode()


class TestQueuingBadData(ScrAppTestCase):
    def test_queuing_bad_space_key(self) -> None:
        with MOCK_MANIFEST_FILE.open(mode='rb') as f:
            response = self.client.post(
                '/publish',
                data={
                    'space_key': 'KEY',
                    'parent_page': '1234',
                },
                files={
                    'file': ('test.bin', f, 'application/octet-stream'),
                },
            )

        self.assertEqual(response.status_code, 400)

    def test_queuing_bad_file_no_content_length(self) -> None:
        response = self.client.post(
            '/publish',
            content=generator(b'\0' * 1024),
            headers={
                'Content-Type': f'multipart/form-data; boundary={BOUNDARY}',
            },
        )

        self.assertEqual(response.status_code, 411)

    def test_queuing_bad_file_nonint_content_length(self) -> None:
        response = self.client.post(
            '/publish',
            content=generator(b'\0' * 1024),
            headers={
                'Content-Length': 'data',
                'Content-Type': f'multipart/form-data; boundary={BOUNDARY}',
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_queuing_bad_file_too_large(self) -> None:
        response = self.client.post(
            '/publish',
            content=generator(b'\0' * 1024),
            headers={
                'Content-Length': '999999999',
                'Content-Type': f'multipart/form-data; boundary={BOUNDARY}',
            },
        )

        self.assertEqual(response.status_code, 413)

    def test_queuing_bad_file_empty(self) -> None:
        test_data = b''
        content_length = sum(len(c) for c in generator(test_data))

        response = self.client.post(
            '/publish',
            content=generator(test_data),
            headers={
                'Content-Length': str(content_length),
                'Content-Type': f'multipart/form-data; boundary={BOUNDARY}',
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_queuing_bad_file_encoding(self) -> None:
        test_data = b'\xff\xfe'
        content_length = sum(len(c) for c in generator(test_data))

        response = self.client.post(
            '/publish',
            content=generator(test_data),
            headers={
                'Content-Length': str(content_length),
                'Content-Type': f'multipart/form-data; boundary={BOUNDARY}',
            },
        )

        self.assertEqual(response.status_code, 400)
