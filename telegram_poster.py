import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))

def post_video_to_channel(channel_id, video_path, caption=""):
    try:
        with open(video_path, 'rb') as video:
            bot.send_video(
                chat_id=channel_id,
                video=video,
                caption=caption[:1024],
                supports_streaming=True
            )
        if os.path.exists(video_path):
            os.remove(video_path)
        return True
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False

def post_video_to_user(user_id, video_path, caption=""):
    try:
        with open(video_path, 'rb') as video:
            bot.send_video(
                chat_id=user_id,
                video=video,
                caption=caption[:1024],
                supports_streaming=True
            )
        if os.path.exists(video_path):
            os.remove(video_path)
        return True
    except Exception as e:
        print(f"Ошибка отправки пользователю: {e}")
        return False