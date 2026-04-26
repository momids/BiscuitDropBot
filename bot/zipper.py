import os
import zipfile
import logging

logger = logging.getLogger(__name__)

CHUNK_SIZE_MB = int(os.getenv("CHUNK_SIZE_MB", "10"))


def _build_archive(file_path: str) -> str:
    base_name = os.path.basename(file_path)
    archive_path = file_path + ".zip"

    logger.info(f"Creating archive → {archive_path}")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(file_path, base_name)

    archive_size = os.path.getsize(archive_path)
    logger.info(f"Archive ready → {archive_path} ({archive_size} bytes)")
    return archive_path

def split_into_parts(file_path: str, chunk_mb: int = CHUNK_SIZE_MB) -> list:
    chunk_size = chunk_mb * 1024 * 1024
    archive_path = _build_archive(file_path)
    archive_name = os.path.basename(archive_path)
    dir_path = os.path.dirname(archive_path)
    archive_size = os.path.getsize(archive_path)

    os.remove(file_path)
    logger.info(f"Deleted original file: {file_path}")

    if archive_size <= chunk_size:
        logger.info(f"Archive fits in one part → {archive_path}")
        return [archive_path]

    logger.info(f"Archive too large ({archive_size} bytes), splitting into {chunk_mb}MB parts...")
    parts = []
    part_num = 0
    with open(archive_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            part_num += 1
            part_path = os.path.join(dir_path, f"{archive_name}.part{part_num:03d}")
            with open(part_path, "wb") as pf:
                pf.write(chunk)
            logger.info(f"  Written part {part_num}: {part_path} ({len(chunk)} bytes)")
            parts.append(part_path)

    os.remove(archive_path)
    logger.info(f"Deleted temporary archive: {archive_path}")
    logger.info(f"Split complete: {part_num} parts")
    return parts