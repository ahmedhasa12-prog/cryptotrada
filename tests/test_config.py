import os
import pytest

import config as cfg


def setup_function():
    cfg.reset_config()


def teardown_function():
    cfg.reset_config()


def test_config_loads_optional_telegram_fields(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("TELEGRAM_USER_ID", "123456789")
    monkeypatch.setenv("OPERATING_MODE", "manual")
    monkeypatch.setenv("AVAILABILITY", "online")
    cfg.reset_config()

    c = cfg.get_config()
    assert c.telegram_bot_token == "test_token"
    assert c.telegram_user_id == 123456789
    assert c.operating_mode == cfg.OperatingMode.MANUAL
    assert c.availability == cfg.Availability.ONLINE


def test_config_works_without_telegram(monkeypatch):
    # Telegram is optional — web dashboard replaces it
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_USER_ID", raising=False)
    cfg.reset_config()

    c = cfg.get_config()
    assert c.telegram_bot_token == ""
    assert c.telegram_user_id == 0


def test_config_defaults(monkeypatch):
    for key in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_USER_ID", "OPERATING_MODE", "AVAILABILITY",
                "P2P_ASSET", "P2P_FIAT", "P2P_SPREAD_ALERT_HIGH", "P2P_SPREAD_ALERT_LOW", "LOG_LEVEL"]:
        monkeypatch.delenv(key, raising=False)
    cfg.reset_config()

    c = cfg.get_config()
    assert c.operating_mode == cfg.OperatingMode.MANUAL
    assert c.availability == cfg.Availability.ONLINE
    assert c.p2p_asset == "USDT"
    assert c.p2p_fiat == "SDG"
    assert c.p2p_spread_alert_high == 25.0
    assert c.p2p_spread_alert_low == 10.0
    assert c.log_level == "INFO"


def test_config_singleton(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    cfg.reset_config()

    c1 = cfg.get_config()
    c2 = cfg.get_config()
    assert c1 is c2


def test_operating_mode_enum_values():
    assert cfg.OperatingMode.MANUAL.value == "manual"
    assert cfg.OperatingMode.SEMI.value == "semi"
    assert cfg.OperatingMode.FULL.value == "full"


def test_availability_enum_values():
    assert cfg.Availability.ONLINE.value == "online"
    assert cfg.Availability.SLOW.value == "slow"
    assert cfg.Availability.OFFLINE.value == "offline"
