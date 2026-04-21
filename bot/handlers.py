import logging
import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.downloader import download, YOUTUBE_REGEX
from bot.zipper import split_into_parts
from bot.sender import send_to_bale

logger = logging.getLogger(__name__)

DEFAULT_ARCHIVE_MODE = os.getenv("ARCHIVE_MODE", "zip").strip().lower()
PENDING_PACKAGING_KEY = "pending_packaging"
ARCHIVE_LABELS = {
    "zip": "🖥️ PC-safe ZIP",
    "7z": "📱 Mobile 7Z",
}
ARCHIVE_HINTS = {
    "zip": "Best if you will join parts on PC before extracting.",
    "7z": "Best if you want mobile archive apps to open the first part directly.",
}


def _ordered_archive_modes() -> list[str]:
    if DEFAULT_ARCHIVE_MODE == "7z":
        return ["7z", "zip"]
    return ["zip", "7z"]


def _build_archive_prompt(file_name: str) -> str:
    recommended_mode = _ordered_archive_modes()[0]
    recommended_label = ARCHIVE_LABELS[recommended_mode]
    return (
        f"✅ Download complete: {file_name}\n\n"
        f"Choose how Biscuit should pack it before sending to Bale:\n\n"
        f"{ARCHIVE_LABELS['zip']}\n"
        f"{ARCHIVE_HINTS['zip']}\n\n"
        f"{ARCHIVE_LABELS['7z']}\n"
        f"{ARCHIVE_HINTS['7z']}\n\n"
        f"Tip: If you're unsure, choose {recommended_label}."
    )


def _build_archive_keyboard(job_id: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(ARCHIVE_LABELS[mode], callback_data=f"pack:{job_id}:{mode}")
        for mode in _ordered_archive_modes()
    ]
    return InlineKeyboardMarkup([buttons])


async def _prompt_for_archive_mode(status_msg, context: ContextTypes.DEFAULT_TYPE, local_path: str):
    job_id = uuid.uuid4().hex[:12]
    pending = context.user_data.setdefault(PENDING_PACKAGING_KEY, {})
    pending[job_id] = {
        "local_path": local_path,
        "file_name": os.path.basename(local_path),
    }
    await status_msg.edit_text(
        _build_archive_prompt(os.path.basename(local_path)),
        reply_markup=_build_archive_keyboard(job_id),
    )


async def _package_and_send(status_msg, local_path: str, archive_mode: str):
    archive_label = ARCHIVE_LABELS.get(archive_mode, archive_mode.upper())

    async def status(text: str):
        logger.info(f"STATUS → {text}")
        try:
            await status_msg.edit_text(text)
        except Exception as e:
            logger.warning(f"Could not edit status message: {e}")

    try:
        await status(f"🗜️ Step 2/4 — Packaging {os.path.basename(local_path)} as {archive_label}...")
        logger.info(f"Calling zipper with archive_mode={archive_mode}...")
        parts = split_into_parts(local_path, archive_mode=archive_mode)
        logger.info(f"✅ Packaging complete: {len(parts)} part(s) → {parts}")

        await status(f"📤 Step 3/4 — Sending {len(parts)} part(s) to Bale...")
        logger.info(f"Calling sender with archive_mode={archive_mode}...")
        await send_to_bale(parts, status, archive_mode=archive_mode)
        logger.info("✅ All parts sent to Bale")

        await status(f"✅ Step 4/4 — Done! {len(parts)} part(s) delivered to Bale as {archive_label} 🍪")
        logger.info("🍪 Pipeline complete!")

    except Exception as e:
        logger.exception(f"❌ Pipeline failed: {e}")
        import re as _re
        clean = _re.sub(r"\x1b\[[0-9;]*m", "", str(e))
        await status(f"❌ Error: {clean}")

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


async def handle_packaging_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, job_id, archive_mode = query.data.split(":", 2)
    pending = context.user_data.get(PENDING_PACKAGING_KEY, {})
    job = pending.pop(job_id, None)
    if not job:
        await query.edit_message_text("❌ Packaging session expired. Please send the file again.")
        return

    await _package_and_send(query.message, job["local_path"], archive_mode)

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
        await _prompt_for_archive_mode(status_msg, context, local_path)

    except Exception as e:
        logger.exception(f"❌ Pipeline failed: {e}")
        # Strip ANSI escape codes before sending to Telegram
        import re as _re
        clean = _re.sub(r"\x1b\[[0-9;]*m", "", str(e))
        await status(f"❌ Error: {clean}")