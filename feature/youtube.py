from telegram.error import BadRequest, TimedOut, NetworkError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pathlib import Path
import random
import string
import subprocess
import shutil
import yt_dlp
import os

from util import check
import setting.ready_messages as mesg
from . import yt_download

base_save_dir = Path(__file__).parent.parent / "files" / "user"
base_read_video_dir = Path(__file__).parent.parent / "files" / "download" / "video"
base_read_thumb_dir = Path(__file__).parent.parent / "files" / "download" / "thumb"

class Youtube_Video():
    def __init__(self, logging):
        self.logging = logging

    async def send_video(self, update, part_size, url):
        user_id = update.effective_user.id
        user_tag = f"(name: {update.effective_user.full_name}, id: {user_id})"



        video_found, thumb_name, title, description, formats = await yt_download.fetch_video_data_and_save_thumb(url, self.logging)
        if video_found:
            thumb_path = base_read_thumb_dir / thumb_name
            keyboard = [
                [InlineKeyboardButton(
                    text=f"{f['resolution']} | {f['filesize']}",
                    callback_data=f"dl:{f['format_id']}"
                )]
                for f in formats[:10]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            caption = f"🎬 {title}\n\n📝 {description[:900]}"

            try:
                with open(thumb_path, "rb") as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=caption,
                        reply_markup=reply_markup
                    )
            finally:
                if thumb_path.exists():
                    thumb_path.unlink()
        else:
            await update.message.reply_text(description)
            return

        video_name = self.download_video(url)





        file_path = Path(base_read_video_dir / video_name)

        upload_started_mes = None

        if not file_path.exists():
            await update.message.reply_text("فایل روی سرور پیدا نشد")
            return

        size_mb = file_path.stat().st_size / (1024 * 1024)
        file_ok, file_size_err, need_to_split = check.check_file(size_mb)

        if not file_ok:
            self.logging.info(
                f"[FILE_IS_LARGE] user={user_tag} file={file_path.name} size={size_mb:.2f}MB err={file_size_err}"
            )
            return




        send_session = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
        self.logging.info(
            f"[SEND-START] user={user_tag} file={file_path.name} size={size_mb:.2f}MB session={send_session}"
        )

        await update.message.reply_text("شروع دانلود:" + "\n" + f"سشن آپلود: {send_session}")

        upload_started_mes = await update.message.reply_text(mesg.UPLOAD_STARTED)

        temp_dir = None

        try:
            if need_to_split:
                temp_dir = self.split_file(part_size, video_name)

                for part_file in sorted(temp_dir.glob("*")):
                    self.logging.info(f"[SENDING-PART] user={user_tag} session={send_session} part={part_file.name}")
                    temp_size = part_file.stat().st_size / (1024 * 1024)

                    sent = False
                    for i in range(5):
                        try:
                            with part_file.open("rb") as part_f:
                                await update.message.reply_document(
                                    document=part_f,
                                    filename=part_file.name,
                                    read_timeout=300,
                                    write_timeout=300,
                                    connect_timeout=60,
                                    pool_timeout=60,
                                )
                            sent = True
                            break
                        except (BadRequest, TimedOut, NetworkError) as e:
                            self.logging.info(
                                f"[SEND-FAIL] try={i+1} user={user_tag} session={send_session} part={part_file.name} error={e.__class__.__name__}: {e} size={temp_size:.2f}MB"
                            )

                    if sent:
                        self.logging.info(
                            f"[SEND-SUCCESS] user={user_tag} session={send_session} part={part_file.name} size={temp_size:.2f}MB"
                        )
                    else:
                        self.logging.info(
                            f"[SEND-FAIL] user={user_tag} session={send_session} part={part_file.name} size={temp_size:.2f}MB after 5 tries"
                        )
                        await update.message.reply_text(mesg.UNABLE_TO_UPLOAD + "\nبعد از 5 بار تلاش آخرین فایل ارسال نشد...")
            else:
                with file_path.open("rb") as f:
                    await update.message.reply_document(
                        document=f,
                        filename=file_path.name,
                        read_timeout=300,
                        write_timeout=300,
                        connect_timeout=60,
                        pool_timeout=60,
                    )

        except (BadRequest, TimedOut, NetworkError) as e:
            self.logging.info(
                f"[SEND-FAIL] user={user_tag} session={send_session} file={file_path.name} error={e.__class__.__name__}: {e}"
            )
            await update.message.reply_text(mesg.UNABLE_TO_UPLOAD)
        except Exception as e:
            self.logging.error(
                f"[SEND-CRASH] user={user_tag} session={send_session} file={file_path.name} error={e.__class__.__name__}: {e}"
            )
            await update.message.reply_text(mesg.UNABLE_TO_UPLOAD)
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

            if upload_started_mes:
                await upload_started_mes.delete()
    

    def video_formats(url):
        return []
    
    def download_video(url):
        video_name = ""
        return video_name
    
    def split_file(self, part_size, video_name):
        while True:
            folder_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
            temp_dir = base_save_dir / folder_name
            if not temp_dir.exists():
                break
        temp_dir.mkdir(parents=True, exist_ok=False)

        input_file = base_read_video_dir / video_name

        # on windows / change if need
        seven_zip = r"C:\Program Files\7-Zip\7z.exe"

        out_archive = temp_dir / f"{input_file.stem}.zip"

        cmd = [
            seven_zip,
            "a",              # add
            "-tzip",          # zip format
            str(out_archive),
            str(input_file),
            f"-v{part_size}m"
        ]

        subprocess.run(cmd, check=True)
        return temp_dir

