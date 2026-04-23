import logging
from feature.youtube import Youtube_Video


class Youtube_Button_Handler:
    def __init__(self, logger: logging, youtube: Youtube_Video, SETTING):
        self.logger = logger
        self.youtube = youtube
        self.SETTING = SETTING

    async def youtube_button_handler(self, update, context):
        query = update.callback_query
        await query.answer()

        data = query.data

        if not data.startswith("youtube:"):
            return

        try:
            payload = data.split(":", 1)[1]
            format_id, url = payload.split("|", 1)
        except ValueError:
            await query.message.reply_text("خطا در پردازش دکمه")
            return

        await query.message.reply_text(
            f"روی این دکمه کلیک کردی:\n"
            f"format_id: {format_id}"
        )

        await self.youtube.send_video(update, self.SETTING["video_part_size"], url, format_id)
