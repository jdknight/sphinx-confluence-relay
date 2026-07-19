# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from threading import Thread
import json
import time


# http server endpoint to use a local/free random port
LOCAL_RANDOM_PORT = ('127.0.0.1', 0)


class MockServerRequestHandler(BaseHTTPRequestHandler):
    """
    mock server request handler

    Provides a handler for managing HTTP requests and responses for unit
    testing.
    """

    def do_DELETE(self) -> None:
        self._track_request('DELETE')
        self._process_rsp()

    def do_GET(self) -> None:
        self._track_request('GET')
        self._process_rsp()

    def do_POST(self) -> None:
        self._track_request('POST')
        self._process_rsp()

    def _process_rsp(self) -> None:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            self.rfile.read(content_length)

        try:
            code, data = self.server.rsp.pop(0)
        except IndexError:
            code = 501
            data = None

        data_bytes = json.dumps(data).encode('utf-8') \
            if data is not None else None

        self.send_response(code)
        self.send_header('Connection', 'close')
        if data_bytes:
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data_bytes)))
        self.end_headers()
        if data_bytes:
            self.wfile.write(data_bytes)

    def _track_request(self, action: str) -> None:
        requests = self.server.req.setdefault(action, [])
        requests.append((self.path, dict(self.headers)))


@contextmanager
def httpd_context(handler: BaseHTTPRequestHandler | None = None) -> None:
    """
    create an http daemon context

    Builds a context-enabled HTTP server instance on a random local port which
    can be used to verify HTTP interaction with API services. The built HTTP
    server is served by an internally managed thread.

    Yields:
        the http server
    """

    httpd_thread = None
    handler = handler or MockServerRequestHandler

    try:
        httpd = HTTPServer(LOCAL_RANDOM_PORT, handler)
        httpd.req = {}
        httpd.rsp = []

        # start accepting requests
        def serve_forever(httpd: HTTPServer) -> None:
            httpd.serve_forever()

        httpd_thread = Thread(target=serve_forever, args=(httpd,))
        httpd_thread.start()

        # yield context for a moment to help threads to ready up
        time.sleep(0)

        yield httpd

    finally:
        if httpd_thread:
            httpd.shutdown()
            httpd_thread.join()

        httpd.server_close()
