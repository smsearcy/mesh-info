"""Test the configuration module."""

import logging

from meshinfo.config import AppConfig, Environment


def test_default_config():
    """Verify that no configuration works."""
    app_config: AppConfig = AppConfig.from_environ({})

    assert app_config.env == Environment.PROD
    assert app_config.log_level == logging.WARNING
    assert app_config.local_node == "localnode.local.mesh"


def test_config():
    """Verify that the environment variables are working as expected."""
    app_config: AppConfig = AppConfig.from_environ(
        {
            "MESH_INFO_ENV": "development",
            "MESH_INFO_LOG_LEVEL": "DEBUG",
            "MESH_INFO_DB_URL": "foobar",
            "MESH_INFO_POLLER_MAX_CONNECTIONS": "25",
            "MESH_INFO_COLLECTOR_NODE_INACTIVE": "25",
        }
    )

    assert app_config.env == Environment.DEV
    assert app_config.log_level == logging.DEBUG
    assert app_config.db.url == "foobar"
    assert app_config.poller.max_connections == 25
    assert app_config.collector.node_inactive == 25
