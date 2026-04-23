import hashlib
from pathlib import Path
from telegram import Message

base_save_video_dir = Path(__file__).parent.parent / "files" / "download" / "video"


async def download_from_message(message: Message):
    if not message:
        raise ValueError("پیام خالیه")

    attachment = message.video or message.document or message.animation
    if not attachment:
        raise ValueError("پیام فایل قابل دانلود ندارد")

    base_save_video_dir.mkdir(parents=True, exist_ok=True)

    # Name To Hash
    seed = f"{attachment.file_unique_id}-{message.message_id}-{message.date}"
    file_hash = hashlib.sha256(seed.encode()).hexdigest()

    ext = ""
    if getattr(attachment, "file_name", None):
        ext = Path(attachment.file_name).suffix
    if not ext:
        ext = ".mp4"

    filename = f"{file_hash}{ext}"
    file_path = base_save_video_dir / filename

    # Download
    tg_file = await attachment.get_file()
    await tg_file.download_to_drive(custom_path=str(file_path))

    # Disc
    description = message.caption or message.text or ""

    return str(file_path), description, filename
