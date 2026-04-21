import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.downloader import download, YOUTUBE_REGEX
from bot.zipper import split_into_parts
from bot.sender import send_to_bale

logger = logging.getLogger(__name__)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    logger.info(f"📥 Received document: {doc.file_name}, size: {doc.file_size} bytes, file_id: {doc.file_id}")
    await _process(update, context, source=doc)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    logger.info(f"📥 Received video: {video.file_name}, size: {video.file_size} bytes, file_id: {video.file_id}")
    await _process(update, context, source=video)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio = update.message.audio
    logger.info(f"📥 Received audio: {audio.file_name}, size: {audio.file_size} bytes, file_id: {audio.file_id}")
    await _process(update, context, source=audio)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.startswith("http://") and not text.startswith("https://"):
        await update.message.reply_text("Please send a file, video, or a URL.")
        return
    logger.info(f"🔗 Received URL: {text}")

    if YOUTUBE_REGEX.match(text):
        context.user_data["yt_url"] = text
        keyboard = [
            [
                InlineKeyboardButton("📱 360p", callback_data="yt_quality:360"),
                InlineKeyboardButton("📺 480p", callback_data="yt_quality:480"),
            ],
            [
                InlineKeyboardButton("🖥️ 720p", callback_data="yt_quality:720"),
                InlineKeyboardButton("🎬 1080p", callback_data="yt_quality:1080"),
            ],
            [
                InlineKeyboardButton("⭐ Best quality", callback_data="yt_quality:best"),
            ],
        ]
        await update.message.reply_text(
            "🎬 YouTube link detected! Choose download quality:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    await _process(update, context, source=text)

async def handle_quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, quality = query.data.split(":")
    url = context.user_data.get("yt_url")
    if not url:
        await query.edit_message_text("❌ Session expired. Please send the YouTube link again.")
        return

    quality_labels = {
        "360": "360p", "480": "480p",
        "720": "720p", "1080": "1080p", "best": "Best"
    }
    await query.edit_message_text(f"⏳ Starting download at {quality_labels.get(quality, quality)}...")
    await _process(update, context, source=url, quality=quality, status_msg_override=query.message)

async def _process(update: Update, context: ContextTypes.DEFAULT_TYPE, source, quality: str = "best", status_msg_override=None):
    if status_msg_override:
        status_msg = status_msg_override
    else:
        status_msg = await update.message.reply_text("⏳ Starting Biscuit pipeline...")
    logger.info("🚀 Pipeline started")

    async def status(text: str):
        logger.info(f"STATUS → {text}")
        try:
            await status_msg.edit_text(text)
        except Exception as e:
            logger.warning(f"Could not edit status message: {e}")

    try:
        await status("⬇️ Step 1/4 — Downloading file...")
        logger.info("Calling downloader...")
        local_path = await download(source, context.bot, quality=quality)
        logger.info(f"✅ Download complete: {local_path}")

        await status(f"🗜️ Step 2/4 — Zipping {local_path}...")
        logger.info("Calling zipper...")
        parts = split_into_parts(local_path)
        logger.info(f"✅ Zip complete: {len(parts)} part(s) → {parts}")

        await status(f"📤 Step 3/4 — Sending {len(parts)} part(s) to Bale...")
        logger.info("Calling sender...")
        await send_to_bale(parts, status)
        logger.info("✅ All parts sent to Bale")

        await status(f"✅ Step 4/4 — Done! {len(parts)} part(s) delivered to Bale 🍪")
        logger.info("🍪 Pipeline complete!")

    except Exception as e:
        logger.exception(f"❌ Pipeline failed: {e}")
        # Strip ANSI escape codes before sending to Telegram
        import re as _re
        clean = _re.sub(r"\x1b\[[0-9;]*m", "", str(e))
        await status(f"❌ Error: {clean}")