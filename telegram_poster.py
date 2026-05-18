import os
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

def _get_bot():
    return Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))

async def get_chat_info(channel_id):
    """Асинхронно получает название канала."""
    try:
        bot = _get_bot()
        chat = await bot.get_chat(chat_id=channel_id)
        return chat.title, chat.username
    except TelegramError as e:
        print(f"Ошибка получения инфо о канале: {e}")
        return None, None

def post_video_to_channel(channel_id, video_path, caption=""):
    """Синхронно отправляет видео в канал (для scheduler и /postnow)."""
    bot = _get_bot()
    try:
        with open(video_path, 'rb') as video:
            msg = asyncio.run(bot.send_video(
                chat_id=channel_id,
                video=video,
                caption=caption[:1024],
                supports_streaming=True,
                read_timeout=60,
                write_timeout=60,
            ))
        if os.path.exists(video_path):
            os.remove(video_path)
        if msg and msg.video:
            return True, None
        return False, "Видео не отобразилось"
    except TelegramError as e:
        msg_text = str(e)
        if "not enough rights" in msg_text.lower() or "forbidden" in msg_text.lower():
            return False, "Нет прав на публикацию"
        elif "chat not found" in msg_text.lower():
            return False, "Канал не найден"
        return False, msg_text
    except Exception as e:
        return False, str(e)

async def post_video_to_user(user_id, video_path, caption=""):
    """Асинхронно отправляет видео пользователю."""
    bot = _get_bot()
    try:
        with open(video_path, 'rb') as video:
            await bot.send_video(
                chat_id=user_id,
                video=video,
                caption=caption[:1024],
                supports_streaming=True,
                read_timeout=60,
                write_timeout=60,
            )
        if os.path.exists(video_path):
            os.remove(video_path)
        return True
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return False