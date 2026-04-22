from telegram.error import BadRequest, TimedOut, NetworkError
from telegram.request import HTTPXRequest
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pathlib import Path
import logging

from util import check
import setting.ready_messages as mesg


class Youtube_Video():
    logging = None
    def __init__(self, logging):
        self.logging = logging

    async def send_video(self, update, part_size):
        user_id = update.effective_user.id

        user_tag = f"(name: {update.effective_user.full_name}, id: {user_id})"
        file_path = Path(r"C:\Users\CNE\Desktop\p.mp4")
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            file_ok, file_size_err, need_to_split = check.check_file(size_mb)
            if not file_ok:
                logging.info(f"[FILE_IS_LARGE] user={user_tag} file={file_path.name} size={size_mb:.2f}MB err={file_size_err}")
                return



            logging.info(f"[SEND-START] user={user_tag} file={file_path.name} size={size_mb:.2f}MB")
            upload_started_mes = await update.message.reply_text(mesg.UPLOAD_STARTED)

            

            with file_path.open("rb") as f:
                try:
                    await update.message.reply_document(document=f, filename=file_path.name)
                except (BadRequest, TimedOut, NetworkError) as e:
                    logging.error(f"[SEND-FAIL]  user={user_tag} file={file_path.name} error={e.__class__.__name__}")
                    await update.message.reply_text(mesg.UNABLE_TO_UPLOAD)
                except Exception as e:
                    logging.error(f"[SEND-CRASH] user={user_tag} file={file_path.name} error={e.__class__.__name__}")
                    await update.message.reply_text(mesg.UNABLE_TO_UPLOAD)

        else:
            await update.message.reply_text("File not found on server.")

        await upload_started_mes.delete()
        
    def split_file(part_size):