# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from typing import TextIO
import logging
import os
import sys


# build our logger
logger = logging.getLogger('sphinxcontrib-confluencebuilder-relay')


# prepare a handler that writes to the standard output stream that flushes
class FlushingStreamHandler(logging.StreamHandler):
    @property
    def stream(self) -> TextIO:
        return sys.stdout

    @stream.setter
    def stream(self, value: TextIO) -> None:
        pass

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


logger_handler = FlushingStreamHandler()
logger.addHandler(logger_handler)


# configure formatter to include tailored prefixes
PREFIXES = {
    logging.CRITICAL: '(critical) ',
    logging.DEBUG:    '(debug) ',
    logging.ERROR:    '(error) ',
    logging.WARNING:  '(warn) ',
}


class Formatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        prefix = PREFIXES.get(record.levelno, '')
        msg = super().format(record)
        return f'{prefix}{msg}'


logger_handler.setFormatter(Formatter())

# prepare logging levels
logger_level = os.getenv('SPHINX_CONFLUENCE_RELAY_LOG_LEVEL', 'INFO').upper()
logger.setLevel(logger_level)
logger_handler.setLevel(logger_level)
