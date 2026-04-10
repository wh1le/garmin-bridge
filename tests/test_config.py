import pytest

from src.config import CONFIG_PATH, Config


@pytest.fixture
def config(tmp_path):
    yml = tmp_path / CONFIG_PATH
    yml.write_text("watch:\n  address: 'AA:BB:CC:DD:EE:FF'\n")
    return Config(str(yml))


@pytest.fixture
def config_with_file(tmp_path):
    yml = tmp_path / CONFIG_PATH 
    yml.write_text("watch:\n  address: 'AA:BB:CC:DD:EE:FF'\n")
    return Config(str(yml)), yml


def test_get_existing_key(config):
    assert config.get("watch.address") == "AA:BB:CC:DD:EE:FF"


def test_get_missing_returns_default(config):
    assert config.get("watch.missing", "fallback") == "fallback"


def test_get_missing_returns_none(config):
    assert config.get("nonexistent") is None


def test_set_persists(config_with_file):
    config, yml = config_with_file
    config.set("watch.address", "11:22:33:44:55:66")
    assert "11:22:33:44:55:66" in yml.read_text()


def test_get_after_set(config):
    config.set("watch.address", "11:22:33:44:55:66")
    assert config.get("watch.address") == "11:22:33:44:55:66"
