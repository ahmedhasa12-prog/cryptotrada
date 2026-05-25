"""
Message formatters — all Telegram message text is built here.
No business logic, only presentation.
"""
from __future__ import annotations

from datetime import datetime

from config import OperatingMode, Availability
from p2p.market_monitor import MarketData, Offer
from p2p.trader_scorer import ScoreResult, RiskColor, color_emoji


def _mode_label(mode: OperatingMode) -> str:
    return {
        OperatingMode.MANUAL: "🟢 MANUAL + INSIGHTS",
        OperatingMode.SEMI: "🟡 SEMI-AUTO",
        OperatingMode.FULL: "🔴 FULL AUTO",
    }[mode]


def _availability_label(avail: Availability) -> str:
    return {
        Availability.ONLINE: "🟢 ONLINE",
        Availability.SLOW: "🟡 SLOW",
        Availability.OFFLINE: "🔴 OFFLINE",
    }[avail]


def format_status(mode: OperatingMode, availability: Availability) -> str:
    return (
        f"📊 *Platform Status*\n"
        f"──────────────────\n"
        f"Mode:         {_mode_label(mode)}\n"
        f"Availability: {_availability_label(availability)}\n"
    )


def format_p2p_snapshot(data: MarketData, avg_spread_1h: float | None = None) -> str:
    buy = f"{data.buy_best_rate:.2f}" if data.buy_best_rate else "—"
    sell = f"{data.sell_best_rate:.2f}" if data.sell_best_rate else "—"
    spread = f"{data.spread:.2f}" if data.spread is not None else "—"
    avg = f"{avg_spread_1h:.2f}" if avg_spread_1h is not None else "—"
    ts = data.timestamp.strftime("%H:%M UTC")

    lines = [
        "📉 *P2P Market Snapshot*",
        "──────────────────────",
        f"Time:           {ts}",
        f"Best sell rate: {buy} SDG  (cheapest USDT)",
        f"Best buy rate:  {sell} SDG  (highest bid)",
        f"Spread:         {spread} SDG  (1h avg: {avg})",
        "",
        "*Top sellers (merchants selling USDT):*",
    ]
    for i, o in enumerate(data.buy_offers[:5], 1):
        lines.append(f"  {i}. {o.merchant_name} — {o.price:.2f} SDG")

    return "\n".join(lines)


def format_trade_alert(
    order_id: str,
    profile_data: dict,
    score_result: ScoreResult,
    market: MarketData,
    our_rate: float | None,
    avg_spread_24h: float | None,
) -> str:
    emoji = color_emoji(score_result.color)
    spread = f"{market.spread:.1f}" if market.spread else "—"
    avg24 = f"{avg_spread_24h:.1f}" if avg_spread_24h else "—"
    our = f"{our_rate:.2f}" if our_rate else "—"
    best_comp = f"{market.buy_best_rate:.2f}" if market.buy_best_rate else "—"

    amount_usdt = profile_data.get("amount_usdt", "?")
    total_sdg = profile_data.get("total_sdg", "?")
    username = profile_data.get("username", "unknown")
    trader_trades = profile_data.get("total_trades", "?")
    completion = profile_data.get("completion_rate", "?")
    age_days = profile_data.get("account_age_days", "?")
    payment = profile_data.get("payment_method", "—")

    est_profit = "—"
    if our_rate and market.sell_best_rate and isinstance(amount_usdt, (int, float)):
        est_profit = f"{(our_rate - market.sell_best_rate) * amount_usdt:.1f} SDG"

    return (
        f"🔔 *NEW TRADE ORDER — P2P*\n\n"
        f"👤 Trader: `{username}`\n"
        f"⭐ Score: {score_result.score}/100 {emoji}\n"
        f"📊 Trades: {trader_trades} | ✅ {completion}% completion\n"
        f"📅 Account: {age_days} days old\n"
        f"💰 Order: {amount_usdt} USDT ({total_sdg} SDG)\n"
        f"🏦 Payment: {payment}\n\n"
        f"📉 *MARKET NOW*\n"
        f"Spread: {spread} SDG (avg 24h: {avg24})\n"
        f"Your rate: {our} | Best competitor: {best_comp}\n"
        f"Est. profit this trade: {est_profit}\n\n"
        f"💡 *RECOMMENDATION: {score_result.recommendation}*\n\n"
        f"Reply: /accept {order_id} | /decline {order_id}"
    )


def format_daily_summary(
    date: str,
    p2p_trades: int,
    p2p_volume_usdt: float,
    p2p_profit_sdg: float,
    avg_release_min: float | None,
    mode: OperatingMode,
) -> str:
    profit_usd = p2p_profit_sdg / 600  # rough SDG→USD; replace with live rate later
    avg_rel = f"{avg_release_min:.1f} min" if avg_release_min else "—"

    return (
        f"📊 *DAILY SUMMARY — {date}*\n\n"
        f"*P2P TRADING:*\n"
        f"  Trades:          {p2p_trades} completed\n"
        f"  Volume:          {p2p_volume_usdt:.1f} USDT\n"
        f"  Profit:          {p2p_profit_sdg:.1f} SDG (~${profit_usd:.1f})\n"
        f"  Avg release:     {avg_rel}\n\n"
        f"*SPOT TRADING:*\n"
        f"  Paper trading active — signals in /signals\n\n"
        f"Mode: {_mode_label(mode)}"
    )


def format_help() -> str:
    return (
        "🤖 *Trading Platform Commands*\n\n"
        "/status              — Platform status\n"
        "/p2p                 — P2P market snapshot\n"
        "/mode manual|semi|full — Switch mode\n"
        "/online              — Set availability ONLINE\n"
        "/slow                — Set availability SLOW\n"
        "/pause               — Set availability OFFLINE\n"
        "/trades today|week   — Trade history\n"
        "/score \\[username\\]   — Score a trader\n"
        "/risk                — Risk limits\n"
        "/help                — This message"
    )
