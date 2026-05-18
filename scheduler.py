import schedule
import time
import threading
from db import (
    get_all_categories, get_all_regions, get_all_keywords,
    get_channel, get_parse_interval, get_post_interval,
    get_next_from_queue, mark_queued_posted, add_to_queue,
    is_posted, mark_posted, get_queue_size
)
from youtube_api import search_popular_shorts, search_by_keyword
from downloader import download_shorts
from telegram_poster import post_video_to_channel

def run_parser():
    """
    Парсит популярные Shorts и добавляет в очередь.
    """
    print("[YouTube Парсер] Запуск...")
    
    categories = get_all_categories()
    regions = get_all_regions()
    keywords = get_all_keywords()
    
    all_shorts = []
    
    # 1. Поиск по ключевым словам
    for kw in keywords:
        print(f"[Парсер] Поиск по ключевому слову: {kw}")
        for region_code, _ in regions:
            shorts = search_by_keyword(kw, region_code=region_code)
            all_shorts.extend(shorts)
    
    # 2. Поиск по популярным в категориях
    for category_id, _ in categories:
        for region_code, _ in regions:
            print(f"[Парсер] Категория {category_id}, регион {region_code}")
            shorts = search_popular_shorts(
                region_code=region_code,
                category_id=category_id
            )
            all_shorts.extend(shorts)
    
    # Убираем дубликаты
    seen = set()
    unique_shorts = []
    for s in all_shorts:
        if s['video_id'] not in seen and not is_posted(s['video_id']):
            seen.add(s['video_id'])
            unique_shorts.append(s)
    
    # Сортируем по просмотрам
    unique_shorts.sort(key=lambda x: x['views'], reverse=True)
    
    print(f"[Парсер] Найдено уникальных Shorts: {len(unique_shorts)}")
    
    # Скачиваем и добавляем в очередь
    downloaded = 0
    for short in unique_shorts[:20]:
        vid = short['video_id']
        if is_posted(vid):
            continue
        
        print(f"[Парсер] Скачиваю: {short['title'][:50]}...")
        path = download_shorts(short['url'], vid)
        
        if path:
            caption = (
                f"🎬 {short['title']}\n"
                f"📺 {short['channel_name']}\n"
                f"👁 {short['views']:,} | 👍 {short['likes']:,} | 💬 {short['comments']:,}"
            )
            add_to_queue(vid, path, short['title'], short['channel_name'], short['views'], short['likes'])
            mark_posted(vid)
            downloaded += 1
            print(f"[Парсер] Добавлен в очередь: {short['title'][:50]}")
    
    print(f"[Парсер] Скачано и добавлено: {downloaded} Shorts")

def run_poster():
    """
    Достаёт из очереди и публикует.
    Вызывается из отдельного потока — не конфликтует с event loop бота.
    """
    channel_id = get_channel()
    if not channel_id:
        print("[Постер] Канал не настроен.")
        return
    
    next_item = get_next_from_queue()
    if not next_item:
        return  # Очередь пуста — без спама в логи
    
    queue_id, video_id, video_path, title, channel_name, views, likes = next_item
    
    caption = (
        f"🎬 {title}\n"
        f"📺 {channel_name}\n"
        f"👁 {views:,} | 👍 {likes:,}"
    )
    
    print(f"[Постер] Публикую: {title[:50]}...")
    success, error = post_video_to_channel(channel_id, video_path, caption)
    
    if success:
        mark_queued_posted(queue_id)
        print(f"[Постер] Опубликовано: {title[:50]}")
    else:
        print(f"[Постер] Ошибка: {error}")

def start_scheduler():
    parse_hours = get_parse_interval()
    post_minutes = get_post_interval()
    
    schedule.every(parse_hours).hours.do(run_parser)
    schedule.every(post_minutes).minutes.do(run_poster)
    
    # Первый запуск парсера через 20 секунд
    schedule.every(20).seconds.do(run_parser).tag('first_parse')
    
    def loop():
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    
    time.sleep(25)
    schedule.clear('first_parse')
    
    print(f"[Планировщик] Парсер: каждые {parse_hours} ч | Постер: каждые {post_minutes} мин")