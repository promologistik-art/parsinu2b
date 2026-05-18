import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from db import (
    init_db, set_channel, get_channel,
    add_category, get_all_categories, remove_category,
    add_region, get_all_regions, remove_region,
    add_keyword, get_all_keywords, remove_keyword,
    set_parse_interval, get_parse_interval,
    set_post_interval, get_post_interval,
    add_subscription, remove_subscription, has_subscription,
    get_all_subscribers, get_queue_size,
    get_next_from_queue, mark_queued_posted
)
from youtube_api import search_by_keyword, CATEGORIES, REGIONS
from downloader import download_video_by_url, download_shorts
from telegram_poster import post_video_to_user, post_video_to_channel, get_chat_info
from scheduler import start_scheduler, run_parser

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_USER_ID'))

# ─── Меню команд ───
async def setup_bot_commands(app: Application):
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("status", "📊 Текущие настройки"),
        BotCommand("add_keyword", "🔑 Добавить ключевое слово"),
        BotCommand("keywords", "📋 Список ключевых слов"),
        BotCommand("add_region", "🌍 Добавить регион"),
        BotCommand("regions", "🗺 Список регионов"),
        BotCommand("add_category", "📂 Добавить категорию"),
        BotCommand("categories", "📁 Список категорий"),
        BotCommand("set_channel", "📢 Указать целевой канал"),
        BotCommand("set_parse", "⏰ Интервал парсинга"),
        BotCommand("set_post", "⏱ Интервал постинга"),
        BotCommand("postnow", "📤 Опубликовать сейчас"),
        BotCommand("catalog", "📚 Справочник категорий и регионов"),
        BotCommand("admin", "🔐 Админ-панель"),
    ]
    await app.bot.set_my_commands(commands)

# ─── Клавиатуры ───
def main_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🔗 Скачать видео по ссылке")], [KeyboardButton("📩 Связь с админом")]],
        resize_keyboard=True
    )

def admin_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔗 Скачать видео по ссылке"), KeyboardButton("📩 Связь с админом")],
            [KeyboardButton("📊 Статус"), KeyboardButton("👥 Подписчики")],
            [KeyboardButton("➕ Выдать подписку"), KeyboardButton("➖ Убрать подписку")],
            [KeyboardButton("🔍 Запустить парсинг Shorts"), KeyboardButton("📤 Опубликовать сейчас")],
        ],
        resize_keyboard=True
    )

def premium_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔗 Скачать видео по ссылке"), KeyboardButton("🔍 Поиск Shorts")],
            [KeyboardButton("📩 Связь с админом")],
        ],
        resize_keyboard=True
    )

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_kb(user_id):
    if is_admin(user_id):
        return admin_keyboard()
    elif has_subscription(user_id):
        return premium_keyboard()
    return main_keyboard()

# ─── /start ───
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    welcome = (
        "👋 Привет! Я бот для скачивания видео с YouTube.\n\n"
        "🚀 Что я умею:\n"
        "• Скачивать любое видео по ссылке (Shorts, ролики, стримы)\n"
        "• Искать популярные Shorts по жанрам и ключевым словам\n"
        "• Автопостинг Shorts в Telegram-канал\n\n"
        "🔗 Просто отправь ссылку на YouTube — и я сразу пришлю видео!\n\n"
        "💎 С премиум-подпиской доступен поиск Shorts по ключевым словам.\n\n"
        "📋 Используй кнопку Меню слева от строки ввода."
    )
    if is_admin(user_id):
        welcome += "\n\n🔐 Режим администратора"
    elif has_subscription(user_id):
        welcome += "\n\n⭐ Премиум-доступ активен"
    await update.message.reply_text(welcome, reply_markup=get_kb(user_id))

# ─── /admin ───
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = (
        "🔐 Админ-панель\n\n"
        "/set_channel — указать целевой канал (пересылкой сообщения)\n"
        "/add_category — добавить категорию для парсинга Shorts\n"
        "/categories — список категорий\n"
        "/remove_category — удалить категорию\n"
        "/add_region — добавить регион\n"
        "/regions — список регионов\n"
        "/remove_region — удалить регион\n"
        "/add_keyword — добавить ключевое слово для поиска Shorts\n"
        "/keywords — список ключевых слов\n"
        "/remove_keyword — удалить ключевое слово\n"
        "/set_parse — интервал парсинга Shorts (часы)\n"
        "/set_post — интервал постинга (минуты)\n"
        "/postnow — опубликовать одно видео из очереди сейчас\n"
        "/status — текущие настройки\n"
        "/subscribers — подписчики\n"
        "/catalog — справочник категорий и регионов"
    )
    await update.message.reply_text(text)

# ─── /catalog ───
async def catalog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📋 Категории YouTube:\n"
    for cid, cname in CATEGORIES.items():
        text += f"  {cid} — {cname}\n"
    text += "\n🌍 Коды регионов:\n"
    for code, name in REGIONS.items():
        text += f"  {code} — {name}\n"
    await update.message.reply_text(text)

# ─── Команды-запросы ───
async def set_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text(
        "📢 Добавление целевого канала\n\n"
        "1. Добавьте бота в администраторы канала\n"
        "2. Выдайте боту права на публикацию сообщений\n"
        "3. Перешлите сюда любое сообщение из этого канала\n\n"
        "⚠️ Пересылать нужно именно из канала, не из избранного."
    )
    context.user_data['awaiting'] = 'channel'

async def add_category_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("📋 Отправь ID категории (10 — Музыка, 24 — Развлечения и т.д.):\nСправочник: /catalog")
    context.user_data['awaiting'] = 'category'

async def remove_category_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🗑 Отправь ID категории для удаления:")
    context.user_data['awaiting'] = 'remove_category'

async def add_region_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🌍 Отправь код региона (US, DE, FR, GB и т.д.):\nСправочник: /catalog")
    context.user_data['awaiting'] = 'region'

async def remove_region_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🗑 Отправь код региона для удаления:")
    context.user_data['awaiting'] = 'remove_region'

async def add_keyword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🔑 Отправь ключевое слово для поиска Shorts (например, deep house):")
    context.user_data['awaiting'] = 'keyword'

async def remove_keyword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🗑 Отправь ключевое слово для удаления:")
    context.user_data['awaiting'] = 'remove_keyword'

async def set_parse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("⏰ Интервал парсинга Shorts в часах (минимум 1):")
    context.user_data['awaiting'] = 'parse'

async def set_post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("⏰ Интервал постинга в минутах (минимум 5):")
    context.user_data['awaiting'] = 'post'

# ─── /postnow ───
async def postnow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Только админ может публиковать.")
        return

    channel = get_channel()
    if not channel:
        await update.message.reply_text("❌ Целевой канал не настроен. Используй /set_channel")
        return

    next_item = get_next_from_queue()
    if not next_item:
        await update.message.reply_text("📦 Очередь пуста. Запустите парсинг: кнопка «🔍 Запустить парсинг Shorts»")
        return

    queue_id, video_id, video_path, title, channel_name, views, likes = next_item
    caption = f"🎬 {title}\n📺 {channel_name}\n👁 {views:,} | 👍 {likes:,}"

    await update.message.reply_text(f"📤 Публикую: {title[:50]}...")
    success, error = post_video_to_channel(channel, video_path, caption)
    if success:
        mark_queued_posted(queue_id)
        await update.message.reply_text("✅ Опубликовано!")
    else:
        await update.message.reply_text(f"❌ Ошибка: {error}")

# ─── Команды-показыватели ───
async def categories_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats = get_all_categories()
    if cats:
        text = "📋 Выбранные категории:\n" + "\n".join(f"• {cid} — {CATEGORIES.get(cid, cname)}" for cid, cname in cats)
    else:
        text = "Категории не выбраны."
    await update.message.reply_text(text)

async def regions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    regs = get_all_regions()
    if regs:
        text = "🌍 Выбранные регионы:\n" + "\n".join(f"• {code} — {REGIONS.get(code, name)}" for code, name in regs)
    else:
        text = "Регионы не выбраны."
    await update.message.reply_text(text)

async def keywords_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kws = get_all_keywords()
    if kws:
        text = "🔑 Ключевые слова:\n" + "\n".join(f"• {kw}" for kw in kws)
    else:
        text = "Список пуст."
    await update.message.reply_text(text)

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id) and not has_subscription(user_id):
        await update.message.reply_text("⛔ Нужна премиум-подписка.")
        return
    channel = get_channel()
    
    # Получаем название канала
    channel_display = "не настроен"
    if channel:
        title, username = get_chat_info(channel)
        if title:
            channel_display = f"{title} (@{username})" if username else title
        else:
            channel_display = f"{channel} (проверьте права бота)"
    
    cats = get_all_categories()
    regs = get_all_regions()
    kws = get_all_keywords()
    parse_int = get_parse_interval()
    post_int = get_post_interval()
    queue = get_queue_size()
    text = (
        f"📊 Текущие настройки:\n\n"
        f"📢 Канал: {channel_display}\n"
        f"🔍 Парсинг Shorts: каждые {parse_int} ч\n"
        f"📤 Постинг: каждые {post_int} мин\n"
        f"📋 Категорий: {len(cats)}\n"
        f"🌍 Регионов: {len(regs)}\n"
        f"🔑 Ключевых слов: {len(kws)}\n"
        f"📦 В очереди: {queue} видео\n"
    )
    await update.message.reply_text(text)

async def subscribers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    subs = get_all_subscribers()
    if subs:
        text = "👥 Подписчики:\n" + "\n".join(f"• {uid} (@{uname})" for uid, uname in subs)
    else:
        text = "Подписчиков нет."
    await update.message.reply_text(text)

# ─── Кнопка «Запустить парсинг» ───
async def run_parser_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return False
    kb = get_kb(user_id)
    await update.message.reply_text("🔄 Запускаю парсинг Shorts...", reply_markup=kb)

    before = get_queue_size()
    run_parser()
    after = get_queue_size()
    added = after - before

    if added > 0:
        await update.message.reply_text(
            f"✅ Парсинг завершён!\n\n📦 Добавлено в очередь: {added} Shorts\n📤 Опубликую по расписанию или через /postnow.",
            reply_markup=kb
        )
    else:
        await update.message.reply_text(
            "⚠️ Новые Shorts не найдены.\nПроверь регионы, категории и ключевые слова через /status.",
            reply_markup=kb
        )
    return True

# ─── Кнопка «Опубликовать сейчас» ───
async def postnow_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await postnow_cmd(update, context)
    return True

# ─── Обработчик кнопок ───
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    kb = get_kb(user_id)

    if text == "📩 Связь с админом":
        await update.message.reply_text("📩 Напиши админу: @твой_ник", reply_markup=kb)
        return True
    if text == "🔗 Скачать видео по ссылке":
        await update.message.reply_text("🔗 Отправь ссылку на любое видео с YouTube:", reply_markup=kb)
        return True
    if text == "📊 Статус":
        await status_cmd(update, context)
        return True
    if text == "👥 Подписчики" and is_admin(user_id):
        await subscribers_cmd(update, context)
        return True
    if text == "➕ Выдать подписку" and is_admin(user_id):
        await update.message.reply_text("Отправь Telegram ID пользователя:", reply_markup=kb)
        context.user_data['awaiting'] = 'add_sub'
        return True
    if text == "➖ Убрать подписку" and is_admin(user_id):
        await update.message.reply_text("Отправь Telegram ID пользователя:", reply_markup=kb)
        context.user_data['awaiting'] = 'remove_sub'
        return True
    if text == "🔍 Запустить парсинг Shorts" and is_admin(user_id):
        return await run_parser_button(update, context)
    if text == "📤 Опубликовать сейчас" and is_admin(user_id):
        return await postnow_button(update, context)
    if text == "🔍 Поиск Shorts" and (is_admin(user_id) or has_subscription(user_id)):
        await update.message.reply_text("🔑 Отправь ключевое слово для поиска Shorts:", reply_markup=kb)
        context.user_data['awaiting'] = 'search'
        return True
    return False

# ─── Обработчик текста и пересылаемых сообщений ───
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kb = get_kb(user_id)
    awaiting = context.user_data.get('awaiting')

    # Пересланное сообщение для канала
    if awaiting == 'channel' and update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        if chat.type == 'channel':
            channel_id = f"@{chat.username}" if chat.username else str(chat.id)
            set_channel(channel_id)
            await update.message.reply_text(f"✅ Целевой канал сохранён: {channel_id}", reply_markup=kb)
        else:
            await update.message.reply_text("⚠️ Это не канал. Перешли сообщение именно из канала.", reply_markup=kb)
        context.user_data.pop('awaiting', None)
        return

    if awaiting == 'channel' and not update.message.forward_from_chat:
        await update.message.reply_text("⚠️ Нужно переслать сообщение из канала, а не просто текст.", reply_markup=kb)
        return

    text = update.message.text.strip() if update.message.text else ""

    # Админские флаги
    if is_admin(user_id):
        if awaiting == 'category':
            cname = CATEGORIES.get(text, "")
            if add_category(text, cname):
                await update.message.reply_text(f"✅ Категория {text} ({cname}) добавлена!", reply_markup=kb)
            else:
                await update.message.reply_text(f"⚠️ Категория {text} уже есть.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return
        if awaiting == 'remove_category':
            remove_category(text)
            await update.message.reply_text(f"🗑 Категория {text} удалена.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return
        if awaiting == 'region':
            code = text.upper()
            rname = REGIONS.get(code, "")
            if add_region(code, rname):
                await update.message.reply_text(f"✅ Регион {code} ({rname}) добавлен!", reply_markup=kb)
            else:
                await update.message.reply_text(f"⚠️ Регион {code} уже есть.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return
        if awaiting == 'remove_region':
            remove_region(text.upper())
            await update.message.reply_text(f"🗑 Регион {text} удалён.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return
        if awaiting == 'keyword':
            kw = text.lower()
            if add_keyword(kw):
                await update.message.reply_text(f"✅ Ключевое слово {kw} добавлено!", reply_markup=kb)
            else:
                await update.message.reply_text(f"⚠️ Ключевое слово {kw} уже есть.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return
        if awaiting == 'remove_keyword':
            remove_keyword(text.lower())
            await update.message.reply_text(f"🗑 Ключевое слово {text} удалено.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return
        if awaiting == 'parse':
            try:
                h = max(1, int(text))
                set_parse_interval(h)
                await update.message.reply_text(f"✅ Парсинг: каждые {h} ч", reply_markup=kb)
            except:
                await update.message.reply_text("❌ Отправь число.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return
        if awaiting == 'post':
            try:
                m = max(5, int(text))
                set_post_interval(m)
                await update.message.reply_text(f"✅ Постинг: каждые {m} мин", reply_markup=kb)
            except:
                await update.message.reply_text("❌ Отправь число.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return
        if awaiting == 'add_sub':
            try:
                sub_id = int(text)
                add_subscription(sub_id)
                await update.message.reply_text(f"✅ Подписка выдана пользователю {sub_id}", reply_markup=kb)
            except:
                await update.message.reply_text("❌ Отправь числовой ID.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return
        if awaiting == 'remove_sub':
            try:
                sub_id = int(text)
                remove_subscription(sub_id)
                await update.message.reply_text(f"✅ Подписка у пользователя {sub_id} отключена", reply_markup=kb)
            except:
                await update.message.reply_text("❌ Отправь числовой ID.", reply_markup=kb)
            context.user_data.pop('awaiting', None)
            return

    # Поиск Shorts (премиум + админ)
    if awaiting == 'search' and (is_admin(user_id) or has_subscription(user_id)):
        await update.message.reply_text(f"🔍 Ищу Shorts: {text}...")
        shorts = search_by_keyword(text, region_code="US", max_results=5)
        if not shorts:
            await update.message.reply_text("😕 Ничего не найдено.", reply_markup=kb)
        else:
            for s in shorts[:3]:
                await update.message.reply_text(f"⏳ Скачиваю: {s['title'][:50]}...")
                path = download_shorts(s['url'], s['video_id'])
                if path:
                    cap = f"🎬 {s['title']}\n📺 {s['channel_name']}\n👁 {s['views']:,} | 👍 {s['likes']:,}"
                    await post_video_to_user(user_id, path, cap)
                else:
                    await update.message.reply_text(f"❌ Не удалось скачать: {s['url']}")
        context.user_data.pop('awaiting', None)
        return

    # Ссылка на YouTube (любое видео)
    if 'youtube.com' in text or 'youtu.be' in text:
        await update.message.reply_text("⏳ Скачиваю видео, подожди...")
        path, title, channel, views, likes = download_video_by_url(text)
        if path:
            cap = f"🎬 {title}\n📺 {channel}\n👁 {views:,} | 👍 {likes:,}"
            await post_video_to_user(user_id, path, cap)
        else:
            await update.message.reply_text("❌ Не удалось скачать видео.", reply_markup=kb)
        return

    await update.message.reply_text("Используй кнопки или отправь ссылку на YouTube.", reply_markup=kb)

# ─── Главный обработчик ───
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button_handled = await handle_buttons(update, context)
    if not button_handled:
        await handle_text(update, context)

# ─── MAIN ───
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.post_init = lambda app: setup_bot_commands(app)

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('admin', admin_cmd))
    app.add_handler(CommandHandler('catalog', catalog_cmd))
    app.add_handler(CommandHandler('set_channel', set_channel_cmd))
    app.add_handler(CommandHandler('add_category', add_category_cmd))
    app.add_handler(CommandHandler('categories', categories_cmd))
    app.add_handler(CommandHandler('remove_category', remove_category_cmd))
    app.add_handler(CommandHandler('add_region', add_region_cmd))
    app.add_handler(CommandHandler('regions', regions_cmd))
    app.add_handler(CommandHandler('remove_region', remove_region_cmd))
    app.add_handler(CommandHandler('add_keyword', add_keyword_cmd))
    app.add_handler(CommandHandler('keywords', keywords_cmd))
    app.add_handler(CommandHandler('remove_keyword', remove_keyword_cmd))
    app.add_handler(CommandHandler('set_parse', set_parse_cmd))
    app.add_handler(CommandHandler('set_post', set_post_cmd))
    app.add_handler(CommandHandler('postnow', postnow_cmd))
    app.add_handler(CommandHandler('status', status_cmd))
    app.add_handler(CommandHandler('subscribers', subscribers_cmd))

    app.add_handler(MessageHandler(filters.TEXT | filters.FORWARDED, message_handler))

    start_scheduler()

    print("🤖 YouTube Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()