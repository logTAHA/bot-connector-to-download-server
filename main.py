from telegram.request import HTTPXRequest
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pathlib import Path
import logging

from loader import access_loader, config_loader
import setting.ready_messages as mesg
from util import check
from feature import youtube


# Base Setting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Cache
ADMINS, USERS = access_loader.load_access()
SETTING = config_loader.load_config()
TOKEN = SETTING["token"]

# Initialize Class
youtube = youtube.Youtube_Video(logging)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USERS:
            logging.warning(f"User: {user_id} try tried to access a part he doesn’t have access to")
            await update.message.reply_text(mesg.NO_ACCESS)
            return
    await youtube.send_video(update, SETTING["video_part_size"], "p.mp4")

def main():
    request = HTTPXRequest(
        connect_timeout=60,
        read_timeout=60,
        write_timeout=180, # Uploading
        pool_timeout=60
    )

    app = (
        Application.builder()
        .token(TOKEN)
        .base_url("https://tapi.bale.ai/bot")
        .request(request)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
