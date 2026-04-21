import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

BALE_TOKEN = os.getenv("BALE_TOKEN")
BALE_CHAT_ID = os.getenv("BALE_CHAT_ID")
BALE_BASE_URL = "https://tapi.bale.ai"
DEFAULT_ARCHIVE_MODE = os.getenv("ARCHIVE_MODE", "zip").strip().lower()


def _resolve_archive_mode(archive_mode: str | None) -> str:
    mode = (archive_mode or DEFAULT_ARCHIVE_MODE).strip().lower()
    if mode not in {"zip", "7z"}:
        logger.warning(f"Unknown archive mode {mode!r}; falling back to zip mode")
        return "zip"
    return mode


def _build_multipart_caption(original_name: str, total: int, archive_mode: str) -> str:
    if archive_mode == "7z":
        return (
            f"🍪 Biscuit — Part 1 of {total}\n\n"
            f"📦 Download all {total} parts. This is a multi-volume 7z archive.\n\n"
            f"📱 Mobile\n"
            f"Open {original_name}.0001 in an archive app that supports multi-part 7z files, such as ZArchiver or RAR.\n\n"
            f"🖥️ Desktop\n"
            f"Open {original_name}.0001 with 7-Zip, WinRAR, or p7zip and extract normally."
        )

    return (
        f"🍪 Biscuit — Part 1 of {total}\n\n"
        f"📦 Download all {total} parts, reassemble the zip, then extract it:\n\n"
        f"🖥️ Windows\n"
        f"copy /b \"{original_name}.part*\" \"{original_name}\"\n\n"
        f"🐧 Linux\n"
        f"cat {original_name}.part* > {original_name}\n\n"
        f"🍎 macOS\n"
        f"cat {original_name}.part* > {original_name}\n\n"
        f"Then extract {original_name} to recover your original file.\n\n"
        f"📱 Mobile\n"
        f"Join the parts into {original_name} first, then open that zip in your archive app."
    )

async def send_to_bale(parts: list, status_callback, archive_mode: str | None = None) -> None:
    resolved_mode = _resolve_archive_mode(archive_mode)
    total = len(parts)
    logger.info(f"Sending {total} part(s) to Bale chat_id={BALE_CHAT_ID}")
    logger.info(f"Using Bale base URL: {BALE_BASE_URL}")
    logger.info(f"Token starts with: {BALE_TOKEN[:8] if BALE_TOKEN else 'NOT SET'}...")

    if not BALE_TOKEN:
        raise Exception("BALE_TOKEN is not set in .env")
    if not BALE_CHAT_ID:
        raise Exception("BALE_CHAT_ID is not set in .env")

    async with httpx.AsyncClient(timeout=120) as client:
        for i, part_path in enumerate(parts):
            await status_callback(f"📤 Sending part {i+1}/{total} to Bale...")
            logger.info(f"Opening file: {part_path} ({os.path.getsize(part_path)} bytes)")

            with open(part_path, "rb") as f:
                url = f"{BALE_BASE_URL}/bot{BALE_TOKEN}/sendDocument"
                logger.info(f"POST → {BALE_BASE_URL}/bot<token>/sendDocument")

                if total == 1:
                    if resolved_mode == "7z" and part_path.endswith(".7z.0001"):
                        caption = "🍪 Biscuit — Your archive is ready! Open the .7z.0001 file in a compatible archive app to extract it."
                    else:
                        caption = "🍪 Biscuit — Your file is ready! Extract the zip to get started."
                elif i == 0:
                    filename = os.path.basename(part_path)
                    if resolved_mode == "7z" and filename.endswith(".0001"):
                        original_name = filename[:-5]
                    else:
                        original_name = filename.rsplit(".part", 1)[0]
                    caption = _build_multipart_caption(original_name, total, resolved_mode)
                else:
                    caption = f"🍪 Biscuit — Part {i+1} of {total}"

                response = await client.post(
                    url,
                    data={
                        "chat_id": BALE_CHAT_ID,
                        "caption": caption
                    },
                    files={"document": (os.path.basename(part_path), f, "application/octet-stream")}
                )

            logger.info(f"Bale response status: {response.status_code}")
            logger.info(f"Bale response body: {response.text}")

            result = response.json()
            if not result.get("ok"):
                raise Exception(f"Bale API error on part {i+1}: {result.get('description')} (error_code: {result.get('error_code')})")

            os.remove(part_path)
            logger.info(f"✅ Part {i+1}/{total} sent and cleaned up")