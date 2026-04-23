
async def youtube_button_handler(update, context):
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

    # TODO: Start Download Video
