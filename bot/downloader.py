import os
import re
import shutil
import logging
import yt_dlp
import httpx

logger = logging.getLogger(__name__)

# Resolve paths relative to the project root, not the cwd
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(_PROJECT_ROOT, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

_default_cookies = os.path.join(_PROJECT_ROOT, "cookies.txt")
YOUTUBE_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE", _default_cookies)
YOUTUBE_COOKIES_BROWSER = os.getenv("YOUTUBE_COOKIES_BROWSER", "chrome")

# Detect node.js for yt-dlp JS challenge solving
_NODE_PATH = shutil.which("node") or "node"

YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)"
    r"[\w\-]+"
)

async def download(source, bot, quality: str = "best") -> str:
    if isinstance(source, str):
        if YOUTUBE_REGEX.match(source):
            logger.info(f"🎬 Detected YouTube URL: {source}")
            return _download_youtube(source, quality=quality)
        else:
            logger.info(f"🌐 Detected direct URL: {source}")
            return await _download_url(source)
    else:
        logger.info(f"📎 Detected Telegram file object: {type(source).__name__}")
        return await _download_telegram_file(source, bot)

QUALITY_FORMATS = {
    "360":  "best[height<=360]/bestvideo[height<=360]+bestaudio/bestvideo[height<=360]/best",
    "480":  "best[height<=480]/bestvideo[height<=480]+bestaudio/bestvideo[height<=480]/best",
    "720":  "best[height<=720]/bestvideo[height<=720]+bestaudio/bestvideo[height<=720]/best",
    "1080": "best[height<=1080]/bestvideo[height<=1080]+bestaudio/bestvideo[height<=1080]/best",
    "best": "bestvideo+bestaudio/best",
}

def _download_youtube(url: str, quality: str = "best") -> str:
    fmt = QUALITY_FORMATS.get(quality, QUALITY_FORMATS["best"])
    logger.info(f"Starting yt-dlp download at quality={quality}, format={fmt}")
    ydl_opts = {
        "format": fmt,
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        "quiet": False,
        "verbose": False,
        # android_testsuite bypasses YouTube bot detection from datacenter IPs
        "extractor_args": {"youtube": {"player_client": ["android_testsuite", "tv_embedded"]}},
        # JS challenge solver
        "js_runtimes": {"node": {}},
        "remote_components": {"ejs:github": {}},
    }
    if os.path.isfile(YOUTUBE_COOKIES_FILE):
        logger.info(f"Using cookies file: {YOUTUBE_COOKIES_FILE}")
        ydl_opts["cookiefile"] = YOUTUBE_COOKIES_FILE
    elif YOUTUBE_COOKIES_BROWSER:
        logger.info(f"Using cookies from browser: {YOUTUBE_COOKIES_BROWSER}")
        ydl_opts["cookiesfrombrowser"] = (YOUTUBE_COOKIES_BROWSER,)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.endswith(".mp4"):
            filename = os.path.splitext(filename)[0] + ".mp4"
    size = os.path.getsize(filename)
    logger.info(f"yt-dlp done → {filename} ({size} bytes)")
    return os.path.abspath(filename)

async def _download_url(url: str) -> str:
    filename = url.split("/")[-1].split("?")[0] or "downloaded_file"
    local_path = os.path.join(DOWNLOAD_DIR, filename)
    logger.info(f"Streaming download → {local_path}")
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            total = 0
            with open(local_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
                    total += len(chunk)
    logger.info(f"URL download done → {local_path} ({total} bytes)")
    return os.path.abspath(local_path)

async def _download_telegram_file(file_obj, bot) -> str:
    logger.info(f"Getting file from Telegram, file_id: {file_obj.file_id}")
    tg_file = await bot.get_file(file_obj.file_id)
    logger.info(f"Telegram file_path: {tg_file.file_path}")
    filename = os.path.basename(tg_file.file_path)
    local_path = os.path.join(DOWNLOAD_DIR, filename)
    logger.info(f"Downloading to: {local_path}")
    await tg_file.download_to_drive(local_path)
    size = os.path.getsize(local_path)
    logger.info(f"Telegram download done → {local_path} ({size} bytes)")
    return os.path.abspath(local_path)