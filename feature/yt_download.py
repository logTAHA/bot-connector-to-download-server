import os
import uuid
import aiohttp
from yt_dlp import YoutubeDL
from pathlib import Path



base_save_dir = Path(__file__).parent.parent / "files" / "download"


def _format_size(size):
    if not size:
        return "نامشخص"
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} WHAT UNTI BROOOO!!!!"

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

    # Image
    thumb_url = info.get("thumbnail")
    filename = ""
    if thumb_url:
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(base_save_dir / "thumb", filename)

        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as resp:
                content = await resp.read()

        with open(filepath, "wb") as f:
            f.write(content)

    # formats
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
