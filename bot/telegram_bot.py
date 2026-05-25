"""
Telegram bot setup — registers all command handlers and starts polling.
"""
from __future__ import annotations

from loguru import logger
from telegram.ext import Application, CommandHandler

from config import get_config
from bot.commands import (
    cmd_start,
    cmd_help,
    cmd_status,
    cmd_mode,
    cmd_online,
    cmd_slow,
    cmd_pause,
    cmd_p2p,
    cmd_score,
    cmd_trades,
    cmd_risk,
)


def build_application() -> Application:
    cfg = get_config()
    app = Application.builder().token(cfg.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("mode", cmd_mode))
    app.add_handler(CommandHandler("online", cmd_online))
    app.add_handler(CommandHandler("slow", cmd_slow))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("p2p", cmd_p2p))
    app.add_handler(CommandHandler("score", cmd_score))
    app.add_handler(CommandHandler("trades", cmd_trades))
    app.add_handler(CommandHandler("risk", cmd_risk))

    logger.info("Telegram bot application built — all handlers registered.")
    return app


async def send_message(app: Application, text: str) -> None:
    """Send a message to the configured owner user."""
    cfg = get_config()
    await app.bot.send_message(
        chat_id=cfg.telegram_user_id,
        text=text,
        parse_mode="Markdown",
    )
