import asyncio
import logging
import hashlib
from pathlib import Path

from telegram import Update, Message
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from loader import access_loader, config_loader
import setting.ready_messages as mesg
from feature.youtube import Youtube_Video
from handler.youtube_button_handler import Youtube_Button_Handler

# -------------------- Base Setting --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Cache
ADMINS, USERS = access_loader.load_access()
SETTING = config_loader.load_config()
BALE_TOKEN = SETTING["bale_token"]
TELEGRAM_TOKEN = SETTING["telegram_token"]

# Initialize Class
youtube = Youtube_Video(logging)
yt_but_handler = Youtube_Button_Handler(logging, youtube, SETTING)

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
    logging.info(f"📂 save_dir: {base_save_video_dir}")

    seed = f"{attachment.file_unique_id}-{message.message_id}-{message.date}"
    file_hash = hashlib.sha256(seed.encode()).hexdigest()
    logging.info(f"🔐 hash_seed: {seed}")
    logging.info(f"🔑 file_hash: {file_hash}")

    ext = ""
    if getattr(attachment, "file_name", None):
        ext = Path(attachment.file_name).suffix
        logging.info(f"📎 original_filename: {attachment.file_name}")
    if not ext:
        ext = ".mp4"
        logging.info("🎯 extension not found, defaulting to .mp4")

    filename = f"{file_hash}{ext}"
    file_path = base_save_video_dir / filename
    logging.info(f"📝 final_filename: {filename}")
    logging.info(f"📦 file_path: {file_path}")

    tg_file = await attachment.get_file()
    logging.info("⬇️ downloading file...")
    await tg_file.download_to_drive(custom_path=str(file_path))
    logging.info("✅ download complete")

    description = message.caption or message.text or ""
    logging.info(f"🗒️ description length: {len(description)}")

    return str(file_path), description, filename

# -------------------- Bale Handlers --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("سلام! برای دانلود: /dy لینک")

async def dy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USERS:
        logging.warning(f"User: {user_id} try tried to access a part he doesn’t have access to")
        await update.effective_message.reply_text(mesg.NO_ACCESS)
        return

    if not context.args:
        await update.effective_message.reply_text("❌ لینک ندادی!\nمثال: /dy https://youtube.com/...")
        return

    url = context.args[0]
    await youtube.send_video_details(update, url)

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
async def main():
    request = HTTPXRequest(
        connect_timeout=60,
        read_timeout=60,
        write_timeout=180,
        pool_timeout=60
    )

    # Bale bot
    bale_app = (
        Application.builder()
        .token(BALE_TOKEN)
        .base_url("https://tapi.bale.ai/bot")
        .request(request)
        .build()
    )

    bale_app.add_handler(CommandHandler("start", start))
    bale_app.add_handler(CommandHandler("dy", dy))
    bale_app.add_handler(
        CallbackQueryHandler(yt_but_handler.youtube_button_handler, pattern="^youtube:")
    )

    # Telegram bot
    tg_app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    tg_app.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.ALL | filters.ANIMATION | filters.FORWARDED,
            tg_file_handler
        )
    )
    tg_app.add_handler(CommandHandler("start", tg_start))

    # initialize
    await bale_app.initialize()
    await tg_app.initialize()

    # start
    await bale_app.start()
    await tg_app.start()

    # polling
    await asyncio.gather(
        bale_app.run_polling(stop_signals=None),
        tg_app.run_polling(stop_signals=None)
    )


if __name__ == "__main__":
    asyncio.run(main())
