# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from collections.abc import Generator
from contextlib import contextmanager
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from fastapi.testclient import TestClient
from pathlib import Path
from sphinx_confluence_relay.app import create_app
from sphinx_confluence_relay.cache import get_engine
from sphinx_confluence_relay.cache import get_session
from sphinx_confluence_relay.settings import Settings
from sphinx_confluence_relay.settings import get_settings
from sqlalchemy.pool import StaticPool
from sqlmodel import Session
from sqlmodel import create_engine
from unittest import IsolatedAsyncioTestCase
from unittest import TestResult
from unittest.mock import AsyncMock
from unittest.mock import patch
import errno
import os
import shutil
import tempfile


# folder holding on sample/test data
DATA_FOLDER = Path(__file__).parent / 'data'


class ScrTestCase(IsolatedAsyncioTestCase):
    """
    base unit test for all tests
    """

    @contextmanager
    def temp_dir(self, dir_: Path | str | None = None) -> None:
        """
        generate a context-supported temporary directory

        Creates a temporary directory in the provided directory ``dir_`` (or
        system default, is not provided). This is a context-supported call
        and will automatically remove the directory when completed. If the
        provided directory does not exist, it will created.

        Args:
            dir_ (optional): the directory to create the temporary directory in
        """

        if dir_ :
            target = Path(dir_)
            target.mkdir(exist_ok=True)

        dir_ = tempfile.mkdtemp(prefix='.scr-tmp-', dir=dir_)
        try:
            yield dir_
        finally:
            try:
                shutil.rmtree(dir_)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

    @contextmanager
    def working_dir(self, dir_: Path | str) -> None:
        """
        move into a context-supported working directory

        Moves the current context into the provided working directory ``dir``.
        When returned, the original working directory will be restored. If the
        provided directory does not exist, it will created.

        Args:
            dir_: the target working directory
        """
        owd = Path.cwd()

        target = Path(dir_)
        target.mkdir(exist_ok=True)

        os.chdir(target)
        try:
            yield target
        finally:
            os.chdir(owd)


class ScrAppTestCase(ScrTestCase):
    def run(self, result: TestResult | None = None) -> None:
        """
        run the test

        Run the test, collecting the result into the TestResult object passed
        as result. See `unittest.TestCase.run()` for more details.

        Args:
            result (optional): the test result to populate
        """

        buffer_mode = getattr(result, 'buffer', False)

        # if running in a buffered mode, suppress all pre-run generated output
        if buffer_mode:
            with Path(os.devnull).open('w') as f:
                with redirect_stdout(f), redirect_stderr(f):
                    self._run(result)
        else:
            self._run(result)

    def _run(self, result: TestResult | None = None) -> None:
        """
        run the actual test

        Args:
            result (optional): the test result to populate
        """

        # create a custom settings instance for this test
        self.settings = Settings()
        self.settings_hook(self.settings)

        # create an in-memory database for this test
        self.engine = create_engine(
            'sqlite:///:memory:',
            connect_args={
                'check_same_thread': False,
            },
            # run a static pool in each test to allow different sessions
            # to be used with an in-memory sqlite database
            poolclass=StaticPool,
        )

        # suppress any maintenance scheduler work
        scheduler_patcher = patch(
            'sphinx_confluence_relay.app.AsyncIOScheduler')
        scheduler_patcher.start()

        # suppress initial confluence validation check
        validate_confluence_patcher = patch(
            'sphinx_confluence_relay.app.validate_confluence')
        validate_confluence_patcher.start()

        # default mock the process and validation calls
        self.mock_process = patch( \
            'sphinx_confluence_relay.process.process_event',
            new=lambda *_a, **_kw: False)
        self.mock_process.start()

        self.mock_validate_page = patch( \
            'sphinx_confluence_relay.routes.validate_page',
            new=AsyncMock(return_value=True))
        self.mock_validate_page.start()

        self.mock_validate_space = patch( \
            'sphinx_confluence_relay.routes.validate_space',
            new=AsyncMock(return_value=True))
        self.mock_validate_space.start()

        # build the application instance for this test
        self.app = create_app(
            engine=self.engine,
            settings=self.settings,
        )

        # restore some instances after application is built

        # bind our test settings and test engine/session over using
        # default/production instances
        def override_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        self.app.dependency_overrides[get_engine] = lambda: self.engine
        self.app.dependency_overrides[get_session] = override_session
        self.app.dependency_overrides[get_settings] = lambda: self.settings

        try:
            # build our test client for web-related requests; note, this also
            # helps trigger the lifespan on the application
            with TestClient(self.app) as client:
                self.client = client

                # run the unit test
                super().run(result)
        finally:
            self.engine.dispose()

            # cleanup mocks
            scheduler_patcher.stop()
            self.mock_process.stop()
            self.mock_validate_page.stop()
            self.mock_validate_space.stop()
            validate_confluence_patcher.stop()

    def settings_hook(self, settings: Settings) -> None:
        """
        hook to allow unit tests to override settings to apply
        """
