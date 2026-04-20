import os
import zipfile
import logging

logger = logging.getLogger(__name__)

def split_into_parts(file_path: str, chunk_mb: int = 16) -> list:
    chunk_size = chunk_mb * 1024 * 1024
    base_name = os.path.basename(file_path)    # e.g. video.mp4
    dir_path = os.path.dirname(file_path)
    base_no_ext = os.path.splitext(file_path)[0]  # for .zip path only
    file_size = os.path.getsize(file_path)

    # Single part: compress into one zip and send
    if file_size <= chunk_size:
        zip_path = base_no_ext + ".zip"
        logger.info(f"File fits in one part, zipping → {zip_path}")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, base_name)
        os.remove(file_path)
        logger.info(f"Deleted original file: {file_path}")
        return [zip_path]

    # Multiple parts: split the raw file into named chunks — no zipping.
    # The receiver downloads all parts and concatenates them to get the original file.
    logger.info(f"File too large ({file_size} bytes), splitting into {chunk_mb}MB raw parts...")
    parts = []
    part_num = 0
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            part_num += 1
            # Use full filename (with extension) as prefix so parts are e.g. video.mp4.part001
            # When concatenated, output must be named video.mp4
            part_path = os.path.join(dir_path, f"{base_name}.part{part_num:03d}")
            with open(part_path, "wb") as pf:
                pf.write(chunk)
            logger.info(f"  Written part {part_num}: {part_path} ({len(chunk)} bytes)")
            parts.append(part_path)

    os.remove(file_path)
    logger.info(f"Deleted original file: {file_path}")
    logger.info(f"Split complete: {part_num} parts")
    return parts