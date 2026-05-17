import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ID популярных категорий
CATEGORIES = {
    "0": "Все",
    "1": "Фильмы и анимация",
    "2": "Авто и транспорт",
    "10": "Музыка",
    "15": "Животные",
    "17": "Спорт",
    "19": "Путешествия",
    "20": "Игры",
    "22": "Люди и блоги",
    "23": "Комедия",
    "24": "Развлечения",
    "25": "Новости и политика",
    "26": "Хобби и стиль",
    "27": "Образование",
    "28": "Наука и техника",
}

# Коды стран
REGIONS = {
    "US": "США",
    "GB": "Великобритания",
    "DE": "Германия",
    "FR": "Франция",
    "IT": "Италия",
    "ES": "Испания",
    "NL": "Нидерланды",
    "SE": "Швеция",
    "CA": "Канада",
    "AU": "Австралия",
    "JP": "Япония",
    "KR": "Южная Корея",
    "BR": "Бразилия",
    "RU": "Россия",
}

def get_youtube_client():
    api_key = os.getenv('YOUTUBE_API_KEY')
    return build('youtube', 'v3', developerKey=api_key)

def search_popular_shorts(region_code="US", category_id=None, max_results=10):
    """
    Ищет популярные Shorts в указанном регионе и категории.
    """
    youtube = get_youtube_client()
    
    try:
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            chart="mostPopular",
            regionCode=region_code,
            videoCategoryId=category_id if category_id else None,
            maxResults=max_results,
        )
        response = request.execute()
        
        shorts = []
        for item in response.get('items', []):
            duration = item['contentDetails']['duration']
            
            # Проверяем, что это короткое видео (до 60 секунд)
            if _is_short(duration):
                video_id = item['id']
                snippet = item['snippet']
                stats = item['statistics']
                
                shorts.append({
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/shorts/{video_id}",
                    'title': snippet.get('title', ''),
                    'channel_name': snippet.get('channelTitle', ''),
                    'description': snippet.get('description', '')[:200],
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0)),
                    'published_at': snippet.get('publishedAt', ''),
                    'category_id': snippet.get('categoryId', ''),
                })
        
        return shorts
    
    except HttpError as e:
        print(f"YouTube API ошибка: {e}")
        return []

def search_by_keyword(keyword, region_code="US", max_results=10):
    """
    Ищет видео по ключевому слову и отбирает Shorts.
    """
    youtube = get_youtube_client()
    
    try:
        # Сначала ищем по ключевому слову
        search_request = youtube.search().list(
            part="id",
            q=keyword,
            type="video",
            videoDuration="short",
            regionCode=region_code,
            maxResults=max_results,
            relevanceLanguage="en",
        )
        search_response = search_request.execute()
        
        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        
        if not video_ids:
            return []
        
        # Получаем детальную информацию
        details_request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids),
            maxResults=max_results,
        )
        details_response = details_request.execute()
        
        shorts = []
        for item in details_response.get('items', []):
            duration = item['contentDetails']['duration']
            if _is_short(duration):
                video_id = item['id']
                snippet = item['snippet']
                stats = item['statistics']
                
                shorts.append({
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/shorts/{video_id}",
                    'title': snippet.get('title', ''),
                    'channel_name': snippet.get('channelTitle', ''),
                    'description': snippet.get('description', '')[:200],
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0)),
                    'published_at': snippet.get('publishedAt', ''),
                })
        
        # Сортируем по просмотрам
        shorts.sort(key=lambda x: x['views'], reverse=True)
        return shorts
    
    except HttpError as e:
        print(f"YouTube API ошибка: {e}")
        return []

def _is_short(duration_str):
    """
    Проверяет, является ли видео Shorts (до 60 секунд, вертикальное).
    YouTube Shorts обычно длятся до 60 секунд.
    """
    import re
    
    # Парсим ISO 8601 duration: PT#M#S или PT#S
    match = re.match(r'PT(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return False
    
    minutes = int(match.group(1)) if match.group(1) else 0
    seconds = int(match.group(2)) if match.group(2) else 0
    
    total_seconds = minutes * 60 + seconds
    
    # Shorts должны быть до 60 секунд
    return total_seconds <= 60