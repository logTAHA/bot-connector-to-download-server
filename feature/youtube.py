from telegram.error import BadRequest, TimedOut, NetworkError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pathlib import Path
import random
import string
import subprocess
import shutil

from util import check
import setting.ready_messages as mesg
from . import yt_download

base_save_dir = Path(__file__).parent.parent / "files" / "user"
base_read_video_dir = Path(__file__).parent.parent / "files" / "download" / "video"
base_read_thumb_dir = Path(__file__).parent.parent / "files" / "download" / "thumb"

class Youtube_Video():
    def __init__(self, logging):
        self.logging = logging

    async def send_video_details(self, update, url):

        video_found, thumb_name, title, description, formats = await yt_download.fetch_video_data_and_save_thumb(url, self.logging)

        if video_found:
            thumb_path = base_read_thumb_dir / thumb_name

            filtered_formats = []
            for fmt in formats:
                w, h = map(int, fmt["resolution"].split("x"))

                if w > 2000 or h > 1200:
                    continue

                filtered_formats.append(fmt)


            formats_sorted = sorted(filtered_formats, key=resolution_area)
            if len(formats_sorted) <= 6:
                keyboard = [
                    [
                        InlineKeyboardButton(
                            text=f"{f['resolution']} | {f['filesize']}",
                            callback_data=f"youtube:{f['format_id']}|{url}"
                        )
                    ]
                    for f in formats_sorted
                ]
            else:
                n = len(formats_sorted)
                mid = n // 2

                selected_formats = []
                # 2 smallest
                selected_formats.extend(formats_sorted[:2])
                # 2 middle
                selected_formats.extend(formats_sorted[mid - 1: mid + 1])
                # 2 largest
                selected_formats.extend(formats_sorted[-2:])

                keyboard = [
                    [
                        InlineKeyboardButton(
                            text=f"{f['resolution']} | {f['filesize']}",
                            callback_data=f"youtube:{f['format_id']}|{url}",
                        )
                    ]
                    for f in selected_formats
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


    async def send_video(self, update, part_size, url, format_id):
        msg = update.effective_message  # or msg = update.callback_query.message

        user_id = update.effective_user.id
        user_tag = f"(name: {update.effective_user.full_name}, id: {user_id})"

        temp_dir = None
        upload_started_mes = None
        file_path = None

        try:
            self.logging.info(
                f"[DOWNLOAD-START] user={user_tag} url={url} format={format_id}"
            )

            file_ok, reject_res, video_name = await yt_download.download_video(
                url, format_id, self.logging
            )
            if not file_ok:
                self.logging.info(
                    f"[FILE-REJECT] user={user_tag} file={'-' if not video_name else video_name} reason={reject_res}"
                )
                await msg.reply_text(reject_res)
                return


            file_path = Path(base_read_video_dir / video_name)

            if not file_path.exists():
                await msg.reply_text("فایل روی سرور پیدا نشد")
                self.logging.info(
                    f"[FILE-MISS] user={user_tag} file={file_path.name}"
                )
                return

            size_mb = file_path.stat().st_size / (1024 * 1024)
            self.logging.info(
                f"[FILE-FOUND] user={user_tag} file={file_path.name} size={size_mb:.2f}MB"
            )

            _, _, need_to_split = check.check_file(size_mb)

            send_session = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
            self.logging.info(
                f"[SEND-START] user={user_tag} file={file_path.name} size={size_mb:.2f}MB session={send_session}"
            )

            await msg.reply_text("شروع دانلود:" + "\n" + f"سشن آپلود: {send_session}")
            upload_started_mes = await msg.reply_text(mesg.UPLOAD_STARTED)

            if need_to_split:
                temp_dir = self.split_file(part_size, video_name)
                for part_file in sorted(temp_dir.glob("*")):
                    self.logging.info(f"[SENDING-PART] user={user_tag} session={send_session} part={part_file.name}")
                    temp_size = part_file.stat().st_size / (1024 * 1024)

                    sent = False
                    for i in range(5):
                        try:
                            with part_file.open("rb") as part_f:
                                await msg.reply_document(
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
                        await msg.reply_text(mesg.UNABLE_TO_UPLOAD + "\nبعد از 5 بار تلاش آخرین فایل ارسال نشد...")
                self.logging.info(
                    f"[SEND-DONE] user={user_tag} file={file_path.name} session={send_session} mode=split"
                )
            else:
                with file_path.open("rb") as f:
                    await msg.reply_document(
                        document=f,
                        filename=file_path.name,
                        read_timeout=300,
                        write_timeout=300,
                        connect_timeout=60,
                        pool_timeout=60,
                    )
                self.logging.info(
                    f"[SEND-DONE] user={user_tag} file={file_path.name} session={send_session} mode=single"
                )

        except (BadRequest, TimedOut, NetworkError) as e:
            self.logging.info(
                f"[SEND-FAIL] user={user_tag} session=? file={file_path.name if file_path else '-'} error={e.__class__.__name__}: {e}"
            )
            await msg.reply_text(mesg.UNABLE_TO_UPLOAD)

        except Exception as e:
            self.logging.error(
                f"[SEND-CRASH] user={user_tag} session=? file={file_path.name if file_path else '-'} error={e.__class__.__name__}: {e}"
            )
            await msg.reply_text(mesg.UNABLE_TO_UPLOAD)

        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
                self.logging.info(f"[CLEANUP] temp_dir removed={temp_dir}")

            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                    self.logging.info(f"[CLEANUP] source video removed={file_path.name}")
                except Exception as e:
                    self.logging.error(f"[CLEANUP-FAIL] source video remove error={e.__class__.__name__}: {e}")

            if upload_started_mes:
                await upload_started_mes.delete()


    def split_file(self, part_size, video_name):
        while True:
            folder_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
            temp_dir = base_save_dir / folder_name
            if not temp_dir.exists():
                break
        temp_dir.mkdir(parents=True, exist_ok=False)

        input_file = base_read_video_dir / video_name

        # on linux / change if need
        # seven_zip = r"C:\Program Files\7-Zip\7z.exe"
        seven_zip = "/usr/bin/7z"


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

def resolution_area(fmt: dict) -> int:
    w, h = fmt["resolution"].split("x")
    return int(w) * int(h)
