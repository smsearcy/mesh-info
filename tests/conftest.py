import os
from pathlib import Path

import alembic.command
import alembic.config
import pytest
import transaction
import webtest
from pyramid.scripting import prepare
from pyramid.testing import DummyRequest, testConfig
from pytest_postgresql import factories
from sqlalchemy import create_engine

from meshinfo import models
from meshinfo.config import AppConfig, configure
from meshinfo.models.meta import Base

if os.environ.get("CI"):
    postgresql_ci = factories.postgresql_noproc(
        # needs to match service in .gitlab-ci.yml
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        dbname=os.environ.get("POSTGRES_DB", "postgres"),
    )
else:
    postgresql_local = factories.postgresql("postgresql_proc")


@pytest.fixture(scope="module")
def data_folder() -> Path:
    """Fixture to simplify accessing test data files."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def app_config():
    # need to get environment variables from CI
    env = os.environ.copy()
    env["MESHMAP_POLLER_NODE"] = "127.0.0.1"
    return AppConfig.from_environ(env)


@pytest.fixture(params=("sqlite", "postgres"))
def dbengine(request, tmp_path):

    if request.param == "sqlite":
        sqlite_file = tmp_path / "testing.sqlite"
        db_url = f"sqlite:///{sqlite_file!s}"
    elif request.param == "postgres":
        if os.environ.get("CI"):
            dbinfo = request.getfixturevalue("postgresql_ci")
        else:
            postgresql = request.getfixturevalue("postgresql_local")
            dbinfo = postgresql.info
        user = dbinfo.user
        password = dbinfo.password
        host = dbinfo.host
        port = dbinfo.port
        dbname = dbinfo.dbname
        db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    else:
        raise ValueError(f"Unknown param: {request.param!r}")

    alembic_cfg = alembic.config.Config("alembic.ini")
    engine = create_engine(db_url)
    alembic_cfg.attributes["connection"] = engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    alembic.command.stamp(alembic_cfg, "head")

    yield engine

    Base.metadata.drop_all(bind=engine)
    alembic.command.stamp(alembic_cfg, None, purge=True)


@pytest.fixture
def app(app_config, dbengine):
    config = configure({"dbengine": dbengine}, app_config=app_config)
    return config.make_wsgi_app()


@pytest.fixture
def tm():
    tm = transaction.TransactionManager(explicit=True)
    tm.begin()
    tm.doom()

    yield tm

    tm.abort()


@pytest.fixture
def dbsession(app, tm):
    session_factory = app.registry["dbsession_factory"]
    return models.get_tm_session(session_factory, tm)


@pytest.fixture
def testapp(app, tm, dbsession):
    # override request.dbsession and request.tm with our own
    # externally-controlled values that are shared across requests but aborted
    # at the end
    testapp = webtest.TestApp(
        app,
        extra_environ={
            "HTTP_HOST": "example.com",
            "tm.active": True,
            "tm.manager": tm,
            "app.dbsession": dbsession,
        },
    )

    return testapp


@pytest.fixture
def app_request(app, tm, dbsession):
    """A real request.

    This request is almost identical to a real request but it has some
    drawbacks in tests as it's harder to mock data and is heavier.

    """
    with prepare(registry=app.registry) as env:
        request = env["request"]
        request.host = "example.com"

        # without this, request.dbsession will be joined to the same transaction
        # manager but it will be using a different sqlalchemy.orm.Session using
        # a separate database transaction
        request.dbsession = dbsession
        request.tm = tm

        yield request


@pytest.fixture
def dummy_request(tm, dbsession):
    """A lightweight dummy request.

    This request is ultra-lightweight and should be used only when the request
    itself is not a large focus in the call-stack.  It is much easier to mock
    and control side-effects using this object, however:

    - It does not have request extensions applied.
    - Threadlocals are not properly pushed.

    """
    request = DummyRequest()
    request.host = "example.com"
    request.dbsession = dbsession
    request.tm = tm

    return request


@pytest.fixture
def dummy_config(dummy_request):
    """A dummy :class:`pyramid.config.Configurator` object.

    This allows for mock configuration, including configuration for ``dummy_request``,
    as well as pushing the appropriate threadlocals.

    """
    with testConfig(request=dummy_request) as config:
        yield config
