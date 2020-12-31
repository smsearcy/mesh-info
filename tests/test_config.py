"""Test the configuration module."""

from pymeshmap.config import AppConfig, Environment


def test_default_config():
    """Verify that no configuration works."""
    app_config: AppConfig = AppConfig.from_environ({})

    assert app_config.env == Environment.PROD
    assert app_config.log_level == "SUCCESS"
    assert app_config.poller.node == "localnode.local.mesh"


def test_config():
    """Verify that the environment variables are working as expected."""
    app_config: AppConfig = AppConfig.from_environ(
        {
            "MESHMAP_ENV": "development",
            "MESHMAP_LOG_LEVEL": "DEBUG",
            "MESHMAP_DB_URL": "foobar",
            "MESHMAP_POLLER_MAX_CONNECTIONS": "25",
            "MESHMAP_COLLECTOR_NODE_INACTIVE": "25",
        }
    )

    assert app_config.env == Environment.DEV
    assert app_config.log_level == "DEBUG"
    assert app_config.db_url == "foobar"
    assert app_config.poller.max_connections == 25
    assert app_config.collector.node_inactive == 25
