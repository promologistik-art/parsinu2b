import sqlite3

DB_PATH = "youtube_bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Целевой канал
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS target_channel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Категории для поиска
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id TEXT NOT NULL UNIQUE,
            category_name TEXT
        )
    ''')
    
    # Регионы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_code TEXT NOT NULL UNIQUE,
            region_name TEXT
        )
    ''')
    
    # Дополнительные ключевые слова
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Расписание парсинга (часы)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parse_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interval_hours INTEGER NOT NULL DEFAULT 6
        )
    ''')
    
    # Расписание постинга (минуты)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interval_minutes INTEGER NOT NULL DEFAULT 30
        )
    ''')
    
    # Опубликованные видео
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posted_videos (
            video_id TEXT PRIMARY KEY,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Очередь на публикацию
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            video_path TEXT NOT NULL,
            title TEXT,
            channel_name TEXT,
            views INTEGER,
            likes INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    # Подписки пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_active INTEGER DEFAULT 1,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# ─── Канал ───
def set_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM target_channel")
    cursor.execute("INSERT INTO target_channel (channel_id) VALUES (?)", (channel_id,))
    conn.commit()
    conn.close()

def get_channel():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM target_channel LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# ─── Категории ───
def add_category(category_id, category_name=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (category_id, category_name) VALUES (?, ?)", (category_id, category_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_categories():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT category_id, category_name FROM categories")
    rows = cursor.fetchall()
    conn.close()
    return rows

def remove_category(category_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
    conn.commit()
    conn.close()

# ─── Регионы ───
def add_region(region_code, region_name=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO regions (region_code, region_name) VALUES (?, ?)", (region_code, region_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_regions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT region_code, region_name FROM regions")
    rows = cursor.fetchall()
    conn.close()
    return rows

def remove_region(region_code):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM regions WHERE region_code = ?", (region_code,))
    conn.commit()
    conn.close()

# ─── Ключевые слова ───
def add_keyword(keyword):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO keywords (keyword) VALUES (?)", (keyword.lower(),))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_keywords():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT keyword FROM keywords")
    rows = [row[0] for row in cursor.fetchall()]
    conn.close()
    return rows

def remove_keyword(keyword):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM keywords WHERE keyword = ?", (keyword.lower(),))
    conn.commit()
    conn.close()

# ─── Расписания ───
def set_parse_interval(hours):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM parse_schedule")
    cursor.execute("INSERT INTO parse_schedule (interval_hours) VALUES (?)", (hours,))
    conn.commit()
    conn.close()

def get_parse_interval():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT interval_hours FROM parse_schedule LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 6

def set_post_interval(minutes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM post_schedule")
    cursor.execute("INSERT INTO post_schedule (interval_minutes) VALUES (?)", (minutes,))
    conn.commit()
    conn.close()

def get_post_interval():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT interval_minutes FROM post_schedule LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 30

# ─── Опубликованные ───
def is_posted(video_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM posted_videos WHERE video_id = ?", (video_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def mark_posted(video_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO posted_videos (video_id) VALUES (?)", (video_id,))
    conn.commit()
    conn.close()

# ─── Очередь ───
def add_to_queue(video_id, video_path, title="", channel_name="", views=0, likes=0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO post_queue (video_id, video_path, title, channel_name, views, likes) VALUES (?, ?, ?, ?, ?, ?)",
        (video_id, video_path, title, channel_name, views, likes)
    )
    conn.commit()
    conn.close()

def get_next_from_queue():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, video_id, video_path, title, channel_name, views, likes FROM post_queue WHERE status = 'pending' ORDER BY added_at ASC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row

def mark_queued_posted(queue_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE post_queue SET status = 'posted' WHERE id = ?", (queue_id,))
    conn.commit()
    conn.close()

def get_queue_size():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM post_queue WHERE status = 'pending'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ─── Подписки ───
def add_subscription(user_id, username=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO subscriptions (user_id, username, is_active) VALUES (?, ?, 1)", (user_id, username))
    conn.commit()
    conn.close()

def remove_subscription(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE subscriptions SET is_active = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def has_subscription(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM subscriptions WHERE user_id = ? AND is_active = 1", (user_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def get_all_subscribers():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username FROM subscriptions WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    return rows