import logging

from telegram import Update
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from loader import access_loader, config_loader
import setting.ready_messages as mesg
from feature.youtube import Youtube_Video
from handler.youtube_button_handler import Youtube_Button_Handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)

ADMINS, USERS = access_loader.load_access()
SETTING = config_loader.load_config()
BALE_TOKEN = SETTING["bale_token"]

youtube = Youtube_Video(logging)
yt_but_handler = Youtube_Button_Handler(logging, youtube, SETTING)

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

def main():
    request = HTTPXRequest(
        connect_timeout=60,
        read_timeout=60,
        write_timeout=180,
        pool_timeout=60
    )

    bale_app = (
        Application.builder()
        .token(BALE_TOKEN)
        .base_url("https://tapi.bale.ai/bot")
        .request(request)
        .build()
    )

    bale_app.add_handler(CommandHandler("start", start))
    bale_app.add_handler(CommandHandler("dy", dy))

    # ✅ اینجا خودش لوپ رو هندل می‌کنه
    bale_app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
