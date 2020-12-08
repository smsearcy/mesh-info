"""Configuration of SQLAlchemy database, copied from Pyramid Cookiecutter.

(Because the plan is to implement the web portion in Pyramid.)

"""
from __future__ import annotations

import contextlib
from typing import Dict, Iterator

from sqlalchemy import engine_from_config
from sqlalchemy.orm import Session, configure_mappers, sessionmaker

# import or define all models here to ensure they are attached to the
# Base.metadata prior to any initialization routines
from .link import Link  # noqa
from .node import Node  # noqa

# import zope.sqlalchemy


# run configure_mappers after defining all of the models to ensure
# all relationships can be setup
configure_mappers()


def get_engine(settings: Dict, prefix="database."):
    return engine_from_config(settings, prefix)


def get_session_factory(engine) -> sessionmaker:
    factory = sessionmaker()
    factory.configure(bind=engine)
    return factory


@contextlib.contextmanager
def session_scope(factory: sessionmaker, dry_run: bool = False) -> Iterator[Session]:
    """Yields a session wrapped in a context manager."""
    session = factory()
    try:
        yield session
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# def get_tm_session(session_factory, transaction_manager):
#     """
#     Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.
#
#     This function will hook the session to the transaction manager which
#     will take care of committing any changes.
#
#     - When using pyramid_tm it will automatically be committed or aborted
#       depending on whether an exception is raised.
#
#     - When using scripts you should wrap the session in a manager yourself.
#       For example::
#
#           import transaction
#
#           engine = get_engine(settings)
#           session_factory = get_session_factory(engine)
#           with transaction.manager:
#               dbsession = get_tm_session(session_factory, transaction.manager)
#
#     """
#     dbsession = session_factory()
#     zope.sqlalchemy.register(
#         dbsession, transaction_manager=transaction_manager)
#     return dbsession


# def includeme(config):
#     """
#     Initialize the model for a Pyramid app.
#
#     Activate this setup using ``config.include('tutorial.models')``.
#
#     """
#     settings = config.get_settings()
#     settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'
#
#     # use pyramid_tm to hook the transaction lifecycle to the request
#     config.include('pyramid_tm')
#
#     # use pyramid_retry to retry a request when transient exceptions occur
#     config.include('pyramid_retry')
#
#     session_factory = get_session_factory(get_engine(settings))
#     config.registry['dbsession_factory'] = session_factory
#
#     # make request.dbsession available for use in Pyramid
#     config.add_request_method(
#         # r.tm is the transaction manager used by pyramid_tm
#         lambda r: get_tm_session(session_factory, r.tm),
#         'dbsession',
#         reify=True
#     )
