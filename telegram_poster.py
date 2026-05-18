import os
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

def _get_bot():
    return Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))

async def get_chat_info(channel_id):
    """Получает название канала по ID (асинхронно)."""
    try:
        bot = _get_bot()
        chat = await bot.get_chat(chat_id=channel_id)
        return chat.title, chat.username
    except TelegramError as e:
        print(f"Ошибка получения инфо о канале: {e}")
        return None, None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None, None

def post_video_to_channel(channel_id, video_path, caption=""):
    """
    Отправляет видео в Telegram-канал (синхронно, для scheduler).
    Возвращает (True, None) если успешно, (False, error_msg) если ошибка.
    """
    bot = _get_bot()
    try:
        with open(video_path, 'rb') as video:
            msg = bot.send_video(
                chat_id=channel_id,
                video=video,
                caption=caption[:1024],
                supports_streaming=True,
                read_timeout=60,
                write_timeout=60,
            )
        if os.path.exists(video_path):
            os.remove(video_path)
        if msg and msg.video:
            return True, None
        return False, "Видео не отобразилось в сообщении"
    except TelegramError as e:
        error_msg = str(e)
        if "not enough rights" in error_msg.lower() or "forbidden" in error_msg.lower():
            return False, "Нет прав на публикацию. Сделайте бота админом канала."
        elif "chat not found" in error_msg.lower():
            return False, "Канал не найден. Проверьте ID."
        else:
            return False, error_msg
    except Exception as e:
        return False, str(e)

async def post_video_to_user(user_id, video_path, caption=""):
    """Асинхронная версия для отправки пользователю."""
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
        print(f"Ошибка отправки пользователю: {e}")
        return False