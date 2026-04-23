import hashlib
import uuid
import aiohttp
from yt_dlp import YoutubeDL
from pathlib import Path

# Base save directory (download folder)
base_save_dir = Path(__file__).parent.parent / "files" / "download"


def _format_size(size):
    if not size:
        return "نامشخص"
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} WHAT UNIT BROOOO!!!!"


async def fetch_video_data_and_save_thumb(url: str, logger):
    try:
        with YoutubeDL({"quiet": True, "skip_download": True, "noplaylist": True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        logger.error(
            f"[ERROR_TO_CATCH_VIDEO] link={url} error={e.__class__.__name__}: {e}"
        )
        return False, "", "", "❌ لینک نامعتبره یا دسترسی ندارم", []

    if not info:
        return False, "", "", "❌ ویدیو پیدا نشد", []

    title = info.get("title", "بدون عنوان")
    description = info.get("description", "بدون توضیحات")

    thumb_url = info.get("thumbnail")
    filename = ""

    if thumb_url:
        thumb_dir = base_save_dir / "thumb"
        thumb_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = thumb_dir / filename

        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as resp:
                content = await resp.read()

        with open(filepath, "wb") as f:
            f.write(content)

    # ---------------------------------------------
    # Formats
    # ---------------------------------------------
    formats = []
    for f in info.get("formats", []):
        if f.get("vcodec") == "none":  
            continue

        fmt = {
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "resolution": f.get("resolution") or f"{f.get('width')}x{f.get('height')}",
            "filesize": _format_size(f.get("filesize") or f.get("filesize_approx")),
        }
        formats.append(fmt)

    formats.sort(key=lambda x: x["resolution"] or "", reverse=True)

    return True, filename, title, description, formats


async def download_video(url: str, format_id, logger) -> str:
    """
    Download video with selected format_id and return only filename.
    Returns empty string on failure.
    """
    try:
        video_dir = base_save_dir / "video"
        video_dir.mkdir(parents=True, exist_ok=True)

        hash_src = f"{format_id}|{url}"
        hash_name = hashlib.sha256(hash_src.encode("utf-8")).hexdigest()

        filename_tmpl = f"{hash_name}.%(ext)s"
        
        outtmpl = str(video_dir / filename_tmpl)

        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "format": format_id,
            "outtmpl": outtmpl,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

        return Path(filepath).name # File name

    except Exception as e:
        logger.error(f"[ERROR_DOWNLOAD_VIDEO] link={url} format_id={format_id} error={e.__class__.__name__}: {e}")
        return ""
