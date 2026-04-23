import logging
import hashlib
from pathlib import Path

from telegram import Update, Message
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from loader import config_loader

# -------------------- Base Setting --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)

SETTING = config_loader.load_config()
TELEGRAM_TOKEN = SETTING["telegram_token"]

# -------------------- Download Function --------------------
base_save_video_dir = Path(__file__).parent.parent / "files" / "download" / "video"

async def download_from_message(message: Message):
    logging.info("download_from_message called")

    if not message:
        logging.error("❌ پیام خالیه")
        raise ValueError("پیام خالیه")

    attachment = message.video or message.document or message.animation
    if not attachment:
        logging.error("❌ پیام فایل قابل دانلود ندارد")
        raise ValueError("پیام فایل قابل دانلود ندارد")

    base_save_video_dir.mkdir(parents=True, exist_ok=True)

    seed = f"{attachment.file_unique_id}-{message.message_id}-{message.date}"
    file_hash = hashlib.sha256(seed.encode()).hexdigest()

    ext = ""
    if getattr(attachment, "file_name", None):
        ext = Path(attachment.file_name).suffix
    if not ext:
        ext = ".mp4"

    filename = f"{file_hash}{ext}"
    file_path = base_save_video_dir / filename

    tg_file = await attachment.get_file()
    await tg_file.download_to_drive(custom_path=str(file_path))

    description = message.caption or message.text or ""
    return str(file_path), description, filename

# -------------------- Telegram Handlers --------------------
async def tg_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message or update.channel_post
    if not message:
        return

    try:
        path, desc, name = await download_from_message(message)
        await message.reply_text(
            f"✅ دانلود شد!\n📁 {path}\n📝 {desc[:200]}"
        )
    except Exception as e:
        logging.error(f"download error: {e}")
        try:
            await message.reply_text(f"❌ خطا: {e}")
        except Exception:
            pass

async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام عشقم")

# -------------------- Main --------------------
def main():
    tg_app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    tg_app.add_handler(CommandHandler("start", tg_start))
    tg_app.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.ALL | filters.ANIMATION | filters.FORWARDED,
            tg_file_handler
        )
    )

    # ✅ خودش لوپ رو هندل می‌کنه
    tg_app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
