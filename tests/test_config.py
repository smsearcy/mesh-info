"""Test the configuration module."""

from pymeshmap import config


def test_get_settings(mocker):
    # prevent local .env file from being loaded for tests
    mocker.patch("pymeshmap.config.load_dotenv")

    settings = config.get_settings()

    assert settings["pymeshmap.env"] == config.Environment.PROD
    assert settings["pymeshmap.local_node"] == "localnode.local.mesh"
    # not particularly concerned about the values for these, just that they are set
    assert "pymeshmap.log_level" in settings
    assert "poller.max_connections" in settings
    assert "poller.connect_timeout" in settings
    assert "poller.read_timeout" in settings
    assert "poller.total_timeout" in settings
    assert "database.url" in settings
    assert "aredn.current_firmware" in settings
    assert "aredn.current_api_version" in settings
