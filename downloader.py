import os
import yt_dlp

DOWNLOAD_FOLDER = "downloads"

def ensure_download_folder():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

def download_shorts(url, video_id):
    """
    Скачивает YouTube Shorts с использованием cookies.
    """
    ensure_download_folder()
    
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp4")
    
    if os.path.exists(output_path):
        return output_path
    
    ydl_opts = {
        'format': 'best[height<=1080][ext=mp4]',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        print(f"Ошибка скачивания {url}: {e}")
        return None

def download_video_by_url(url):
    """
    Скачивает любое видео YouTube с использованием cookies.
    """
    ensure_download_folder()
    
    import uuid
    temp_id = str(uuid.uuid4())[:8]
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{temp_id}.mp4")
    
    ydl_opts = {
        'format': 'best[height<=1080][ext=mp4]',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', '')[:500]
            channel = info.get('uploader', '')
            views = info.get('view_count', 0) or 0
            likes = info.get('like_count', 0) or 0
        
        if os.path.exists(output_path):
            return output_path, title, channel, views, likes
        return None, "", "", 0, 0
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        return None, "", "", 0, 0