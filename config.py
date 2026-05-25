from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum

from dotenv import load_dotenv

load_dotenv()


class OperatingMode(str, Enum):
    MANUAL = "manual"
    SEMI = "semi"
    FULL = "full"


class Availability(str, Enum):
    ONLINE = "online"
    SLOW = "slow"
    OFFLINE = "offline"


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set. Check your .env file.")
    return value


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass
class Config:
    # Telegram fields kept for backwards-compat but no longer required (replaced by web dashboard)
    telegram_bot_token: str = field(default_factory=lambda: _optional("TELEGRAM_BOT_TOKEN"))
    telegram_user_id: int = field(default_factory=lambda: int(_optional("TELEGRAM_USER_ID", "0")))

    binance_api_key: str = field(default_factory=lambda: _optional("BINANCE_API_KEY"))
    binance_secret_key: str = field(default_factory=lambda: _optional("BINANCE_SECRET_KEY"))

    operating_mode: OperatingMode = field(
        default_factory=lambda: OperatingMode(_optional("OPERATING_MODE", "manual"))
    )
    availability: Availability = field(
        default_factory=lambda: Availability(_optional("AVAILABILITY", "online"))
    )

    p2p_asset: str = field(default_factory=lambda: _optional("P2P_ASSET", "USDT"))
    p2p_fiat: str = field(default_factory=lambda: _optional("P2P_FIAT", "SDG"))
    p2p_spread_alert_high: float = field(
        default_factory=lambda: float(_optional("P2P_SPREAD_ALERT_HIGH", "25"))
    )
    p2p_spread_alert_low: float = field(
        default_factory=lambda: float(_optional("P2P_SPREAD_ALERT_LOW", "10"))
    )
    p2p_premium_buyer_threshold: float = field(
        default_factory=lambda: float(_optional("P2P_PREMIUM_BUYER_THRESHOLD", "30"))
    )
    p2p_watched_merchants: list[str] = field(
        default_factory=lambda: [
            m.strip() for m in _optional("P2P_WATCHED_MERCHANTS", "").split(",")
            if m.strip()
        ]
    )
    p2p_competitor_alert_threshold: float = field(
        default_factory=lambda: float(_optional("P2P_COMPETITOR_ALERT_THRESHOLD", "5"))
    )

    # Rate auto-adjuster (Phase 2)
    p2p_rate_adjuster_enabled: bool = field(
        default_factory=lambda: _optional("P2P_RATE_ADJUSTER_ENABLED", "false").lower() == "true"
    )
    p2p_rate_adjuster_step: float = field(
        default_factory=lambda: float(_optional("P2P_RATE_ADJUSTER_STEP", "1.0"))
    )
    p2p_rate_adjuster_offset: float = field(
        default_factory=lambda: float(_optional("P2P_RATE_ADJUSTER_OFFSET", "0.5"))
    )

    log_level: str = field(default_factory=lambda: _optional("LOG_LEVEL", "INFO"))
    db_path: str = field(default_factory=lambda: _optional("DB_PATH", "data/trading.db"))


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset singleton — used in tests."""
    global _config
    _config = None
