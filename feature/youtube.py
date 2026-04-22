from telegram.error import BadRequest, TimedOut, NetworkError
from pathlib import Path
import random
import string
import subprocess
import shutil


from util import check
import setting.ready_messages as mesg

base_save_dir = Path(__file__).parent.parent / "files" / "user"
base_read_dir = Path(__file__).parent.parent / "files" / "download"

class Youtube_Video():
    def __init__(self, logging):
        self.logging = logging

    async def send_video(self, update, part_size, video_name):
        user_id = update.effective_user.id
        user_tag = f"(name: {update.effective_user.full_name}, id: {user_id})"
        file_path = Path(base_read_dir / video_name)

        upload_started_mes = None

        if not file_path.exists():
            await update.message.reply_text("File not found on server.")
            return

        size_mb = file_path.stat().st_size / (1024 * 1024)
        file_ok, file_size_err, need_to_split = check.check_file(size_mb)

        if not file_ok:
            self.logging.info(
                f"[FILE_IS_LARGE] user={user_tag} file={file_path.name} size={size_mb:.2f}MB err={file_size_err}"
            )
            return

        self.logging.info(
            f"[SEND-START] user={user_tag} file={file_path.name} size={size_mb:.2f}MB"
        )

        upload_started_mes = await update.message.reply_text(mesg.UPLOAD_STARTED)

        temp_dir = None

        try:
            if need_to_split:
                temp_dir = self.split_file(part_size, video_name)

                for part_file in sorted(temp_dir.glob("*")):
                    self.logging.info(
                        f"[SENDING-PART] user={user_tag} part={part_file.name}"
                    )
                    with part_file.open("rb") as part_f:
                        await update.message.reply_document(
                            document=part_f,
                            filename=part_file.name,
                            read_timeout=300,
                            write_timeout=300,
                            connect_timeout=60,
                            pool_timeout=60,
                        )
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
            self.logging.error(
                f"[SEND-FAIL] user={user_tag} file={file_path.name} error={e.__class__.__name__}: {e}"
            )
            await update.message.reply_text(mesg.UNABLE_TO_UPLOAD)

        except Exception as e:
            self.logging.error(
                f"[SEND-CRASH] user={user_tag} file={file_path.name} error={e.__class__.__name__}: {e}"
            )
            await update.message.reply_text(mesg.UNABLE_TO_UPLOAD)

        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

            if upload_started_mes:
                await upload_started_mes.delete()
    def split_file(self, part_size, video_name):
        while True:
            folder_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
            temp_dir = base_save_dir / folder_name
            if not temp_dir.exists():
                break
        temp_dir.mkdir(parents=True, exist_ok=False)

        input_file = base_read_dir / video_name

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
