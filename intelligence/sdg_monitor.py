"""
SDG Rate Intelligence — trend analysis on Binance P2P snapshots.

Uses the USDT/SDG buy-side best rate as a proxy for the parallel market rate.
Polls every 5 minutes, so 12 slots = 1h, 72 slots = 6h, 288 slots = 24h.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from data.models import MarketSnapshot
from p2p.market_monitor import get_recent_snapshots

Direction = Literal["up", "down", "stable"]

# Thresholds for alerts
_ALERT_1H_MIN_CHANGE = 5.0   # SDG — large 1h move
_ALERT_6H_MIN_CHANGE = 10.0  # SDG — sustained 6h trend


@dataclass
class RateTrend:
    change_abs: float        # absolute SDG change (current − baseline)
    change_pct: float        # percentage change
    direction: Direction
    from_rate: float | None  # baseline rate
    to_rate: float | None    # current rate


def compute_rate_trend(snapshots: list[MarketSnapshot], window_slots: int) -> RateTrend:
    """
    Compare the newest snapshot's buy rate against the snapshot 'window_slots' behind it.
    Snapshots must be ordered newest-first (as returned by get_recent_snapshots).
    """
    if not snapshots:
        return RateTrend(0.0, 0.0, "stable", None, None)

    current = snapshots[0].buy_best_rate
    baseline_idx = min(window_slots - 1, len(snapshots) - 1)
    baseline = snapshots[baseline_idx].buy_best_rate

    if current is None or baseline is None or baseline == 0.0:
        return RateTrend(0.0, 0.0, "stable", baseline, current)

    change_abs = round(current - baseline, 2)
    change_pct = round((change_abs / baseline) * 100, 3)

    if change_abs > 0.5:
        direction: Direction = "up"
    elif change_abs < -0.5:
        direction = "down"
    else:
        direction = "stable"

    return RateTrend(change_abs, change_pct, direction, baseline, current)


def check_rate_movement_alerts(snapshots: list[MarketSnapshot]) -> list[str]:
    """
    Return alert strings if the rate has moved significantly.
    Called after every market poll with the last 6h of snapshots.
    """
    alerts = []
    if len(snapshots) < 2:
        return alerts

    trend_1h = compute_rate_trend(snapshots, window_slots=12)
    trend_6h = compute_rate_trend(snapshots, window_slots=72)

    if abs(trend_1h.change_abs) >= _ALERT_1H_MIN_CHANGE:
        verb = "risen" if trend_1h.direction == "up" else "fallen"
        alerts.append(
            f"📊 SDG rate has {verb} by {abs(trend_1h.change_abs):.1f} SDG in the last hour "
            f"({trend_1h.from_rate:.1f} → {trend_1h.to_rate:.1f}). "
            f"Consider updating your P2P ad rate."
        )

    if trend_6h.direction == "up" and trend_6h.change_abs >= _ALERT_6H_MIN_CHANGE:
        alerts.append(
            f"📈 SDG strengthening for 6h (+{trend_6h.change_abs:.1f} SDG). "
            f"Good time to raise your selling rate."
        )
    elif trend_6h.direction == "down" and abs(trend_6h.change_abs) >= _ALERT_6H_MIN_CHANGE:
        alerts.append(
            f"📉 SDG weakening for 6h ({trend_6h.change_abs:.1f} SDG). "
            f"Consider lowering your rate to stay competitive."
        )

    return alerts


def get_sdg_summary() -> dict:
    """Full trend summary for the /api/p2p/rate-trend endpoint."""
    snapshots = get_recent_snapshots(limit=288)

    if not snapshots:
        return {
            "current_buy_rate": None,
            "current_sell_rate": None,
            "trend_1h": None,
            "trend_6h": None,
            "trend_24h": None,
            "snapshots_available": 0,
        }

    latest = snapshots[0]

    def _as_dict(t: RateTrend) -> dict:
        return {
            "change_abs": t.change_abs,
            "change_pct": t.change_pct,
            "direction": t.direction,
            "from_rate": t.from_rate,
            "to_rate": t.to_rate,
        }

    return {
        "current_buy_rate": latest.buy_best_rate,
        "current_sell_rate": latest.sell_best_rate,
        "trend_1h": _as_dict(compute_rate_trend(snapshots, 12)),
        "trend_6h": _as_dict(compute_rate_trend(snapshots, 72)),
        "trend_24h": _as_dict(compute_rate_trend(snapshots, 288)),
        "snapshots_available": len(snapshots),
    }
