import os
import zipfile
import logging

logger = logging.getLogger(__name__)

DEFAULT_ARCHIVE_MODE = os.getenv("ARCHIVE_MODE", "zip").strip().lower()
SUPPORTED_ARCHIVE_MODES = {"zip", "7z"}


def _resolve_archive_mode(archive_mode: str | None) -> str:
    mode = (archive_mode or DEFAULT_ARCHIVE_MODE).strip().lower()
    if mode not in SUPPORTED_ARCHIVE_MODES:
        logger.warning(f"Unknown archive mode {mode!r}; falling back to zip mode")
        return "zip"
    return mode


def _build_archive(file_path: str) -> str:
    base_name = os.path.basename(file_path)
    archive_path = file_path + ".zip"

    logger.info(f"Creating archive → {archive_path}")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(file_path, base_name)

    archive_size = os.path.getsize(archive_path)
    logger.info(f"Archive ready → {archive_path} ({archive_size} bytes)")
    return archive_path


def _build_multivolume_7z(file_path: str, chunk_size: int) -> list[str]:
    try:
        import multivolumefile
        import py7zr
    except ImportError as exc:
        raise RuntimeError(
            "ARCHIVE_MODE=7z requires py7zr and multivolumefile to be installed."
        ) from exc

    base_name = os.path.basename(file_path)
    archive_path = file_path + ".7z"

    logger.info(f"Creating multi-volume 7z archive → {archive_path}")
    with multivolumefile.MultiVolume(archive_path, mode="wb", volume=chunk_size, ext_digits=4) as mvf:
        with py7zr.SevenZipFile(mvf, "w") as archive:
            archive.write(file_path, base_name)

    part_paths = []
    part_num = 1
    while True:
        part_path = f"{archive_path}.{part_num:04d}"
        if not os.path.exists(part_path):
            break
        logger.info(f"  Written part {part_num}: {part_path} ({os.path.getsize(part_path)} bytes)")
        part_paths.append(part_path)
        part_num += 1

    if not part_paths:
        raise RuntimeError(f"Failed to create multi-volume 7z archive for {file_path}")

    logger.info(f"Multi-volume 7z complete: {len(part_paths)} parts")
    return part_paths


def _build_zip_parts(file_path: str, chunk_size: int) -> list[str]:
    archive_path = _build_archive(file_path)
    archive_name = os.path.basename(archive_path)
    dir_path = os.path.dirname(archive_path)
    archive_size = os.path.getsize(archive_path)

    if archive_size <= chunk_size:
        logger.info(f"Archive fits in one part → {archive_path}")
        return [archive_path]

    logger.info(f"Archive too large ({archive_size} bytes), splitting into {chunk_size // (1024 * 1024)}MB parts...")
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

def split_into_parts(file_path: str, chunk_mb: int = 16, archive_mode: str | None = None) -> list:
    chunk_size = chunk_mb * 1024 * 1024
    resolved_mode = _resolve_archive_mode(archive_mode)

    if resolved_mode == "7z":
        parts = _build_multivolume_7z(file_path, chunk_size)
    else:
        parts = _build_zip_parts(file_path, chunk_size)

    os.remove(file_path)
    logger.info(f"Deleted original file: {file_path}")
    return parts