import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.handlers import ensure_user_allowed, handle_document, handle_video, handle_audio, handle_url, handle_quality_callback

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
)
# Silence noisy httpx/httpcore debug spam
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

START_CAPTION = (
    "🍪 Biscuit is ready!\n\n"
    "Send me a file, video, or YouTube link and "
    "I'll forward it to Bale in 16MB chunks."
)
START_GIF_PATH = Path(__file__).resolve().parent.parent / "Cookie_Chat_Bubble_In_a_charming_animation_style_a_cheerful_round_24177oRz-ezgif.com-optimize.gif"

async def start(update: Update, context):
    if not await ensure_user_allowed(update):
        return

    if START_GIF_PATH.exists():
        with START_GIF_PATH.open("rb") as animation:
            await update.message.reply_animation(animation=animation, caption=START_CAPTION)
        return

    logging.getLogger(__name__).warning("Start GIF not found at %s", START_GIF_PATH)
    await update.message.reply_text(START_CAPTION)

async def error_handler(update: object, context) -> None:
    logging.getLogger(__name__).error("PTB caught an exception:", exc_info=context.error)

async def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN is not set in .env")

    app = (
        ApplicationBuilder()
        .token(token)
        .connection_pool_size(16)
        .pool_timeout(30)
        .build()
    )
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_quality_callback, pattern=r"^yt_quality:"))

    logging.info("🍪 Biscuit is running...")
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logging.info("🍪 Bot is polling. Press Ctrl+C to stop.")
        try:
            await asyncio.Event().wait()  # block until Ctrl+C / cancellation
        finally:
            await app.updater.stop()
            await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Stopped.")