"""
Hybrid AI Router — Telegram Webhook Bot
=========================================
Runs INSIDE the FastAPI server as a webhook endpoint.
No separate process needed — works on HF Spaces, Render, any cloud.

v3.0.0 — Offsite Deployment Edition
"""

import os
import logging
import base64
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters

from src.router import classify_and_route
from src.config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger("bot")

# Simple in-memory conversation history (per-user)
_history: dict[str, list[dict]] = {}
MAX_HISTORY = 10  # Keep last 10 messages per user

# Global reference — initialized at server startup
_bot_app: Application = None


async def handle_message(update: Update, context):
    """Process incoming Telegram messages through the 10-tier cascade."""
    if not update.message:
        return

    user_id = str(update.message.from_user.id)
    user_text = update.message.text or update.message.caption or ""
    image_data = None

    # Handle Photo (Multimodal)
    if update.message.photo:
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_data = base64.b64encode(photo_bytes).decode('utf-8')
            logger.info(f"Image received from {user_id}. Routing to cascade...")
        except Exception as e:
            logger.warning(f"Failed to download photo from {user_id}: {e}")

    if not user_text and not image_data:
        return

    logger.info(f"Telegram Request from {user_id}: {user_text[:50]}...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Build context from in-memory history
    history = _history.get(user_id, [])
    history_context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-5:]])
    full_prompt = f"{history_context}\nuser: {user_text}" if history_context else user_text

    try:
        response, model_used, *_ = classify_and_route(full_prompt, image_data=image_data)

        # Update in-memory history
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": response})
        _history[user_id] = history[-MAX_HISTORY:]

        # Visual Tags
        tag = "\u26a0\ufe0f Error" if "ERROR" in model_used else "\U0001f30a Cascade"
        full_response = f"*{tag}*\n\n{response}"

        # Telegram's 4096 char limit
        if len(full_response) > 4000:
            for i in range(0, len(full_response), 4000):
                await update.message.reply_text(full_response[i:i+4000], parse_mode='Markdown')
        else:
            await update.message.reply_text(full_response, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Bot error: {e}")
        await update.message.reply_text(f"\u26a0\ufe0f Error: {str(e)}")


async def init_webhook_bot(webhook_url: str) -> Application:
    """
    Initialize the Telegram bot in WEBHOOK mode.
    Called from server.py on startup.
    Returns the Application instance for processing updates.
    """
    global _bot_app

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not configured. Telegram bot disabled.")
        return None

    try:
        _bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        _bot_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

        # Initialize the bot (connects to Telegram API)
        await _bot_app.initialize()
        await _bot_app.start()

        # Set the webhook URL with Telegram
        full_webhook_url = f"{webhook_url}/api/telegram/webhook"
        await _bot_app.bot.set_webhook(url=full_webhook_url)

        logger.info(f"[TELEGRAM] Webhook set: {full_webhook_url}")
        return _bot_app

    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to initialize webhook bot: {e}")
        return None


async def process_telegram_update(update_data: dict) -> bool:
    """
    Process a single incoming Telegram update via webhook.
    Called from the FastAPI webhook endpoint.
    """
    global _bot_app

    if _bot_app is None:
        logger.warning("[TELEGRAM] Bot not initialized — dropping update.")
        return False

    try:
        update = Update.de_json(update_data, _bot_app.bot)
        await _bot_app.process_update(update)
        return True
    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to process update: {e}")
        return False


async def shutdown_bot():
    """Graceful shutdown — remove webhook and stop bot."""
    global _bot_app
    if _bot_app:
        try:
            await _bot_app.bot.delete_webhook()
            await _bot_app.stop()
            await _bot_app.shutdown()
            logger.info("[TELEGRAM] Bot shutdown complete.")
        except Exception as e:
            logger.warning(f"[TELEGRAM] Shutdown error: {e}")


# === Legacy polling mode (for local development / docker-compose) ===
def run_bot():
    """Run bot in POLLING mode — for local use only."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN missing in secrets/telegram_bot_token.txt")
        return

    logger.info("Starting Hybrid Telegram Bot (Polling Mode)...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    app.run_polling()


if __name__ == "__main__":
    run_bot()