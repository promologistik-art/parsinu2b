import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from db import (
    init_db, set_channel, get_channel,
    add_category, get_all_categories, remove_category,
    add_region, get_all_regions, remove_region,
    add_keyword, get_all_keywords, remove_keyword,
    set_parse_interval, get_parse_interval,
    set_post_interval, get_post_interval,
    add_subscription, remove_subscription, has_subscription,
    get_all_subscribers, get_queue_size
)
from youtube_api import search_by_keyword, CATEGORIES, REGIONS
from downloader import download_video_by_url, download_shorts
from telegram_poster import post_video_to_user
from scheduler import start_scheduler, run_parser

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_USER_ID'))

# ─── Клавиатуры ───
def main_keyboard():
    keyboard = [
        [KeyboardButton("🔗 Скачать по ссылке")],
        [KeyboardButton("📩 Связь с админом")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_keyboard():
    keyboard = [
        [KeyboardButton("🔗 Скачать по ссылке"), KeyboardButton("📩 Связь с админом")],
        [KeyboardButton("📊 Статус"), KeyboardButton("👥 Подписчики")],
        [KeyboardButton("➕ Выдать подписку"), KeyboardButton("➖ Убрать подписку")],
        [KeyboardButton("🔍 Запустить парсинг")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def premium_keyboard():
    keyboard = [
        [KeyboardButton("🔗 Скачать по ссылке"), KeyboardButton("🔍 Поиск Shorts")],
        [KeyboardButton("📩 Связь с админом")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def is_admin(user_id):
    return user_id == ADMIN_ID

# ─── Старт ───
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    welcome = (
        "👋 Привет! Я бот для скачивания YouTube Shorts.\n\n"
        "🚀 **Что я умею:**\n"
        "• Скачивать Shorts по ссылке\n"
        "• Искать популярные Shorts по жанрам\n"
        "• Автопостинг в Telegram-канал\n\n"
        "🔗 Отправь ссылку на YouTube Shorts — и я сразу пришлю видео!\n\n"
        "💎 С премиум-подпиской доступен поиск по ключевым словам."
    )
    
    if is_admin(user_id):
        await update.message.reply_text(welcome + "\n\n🔐 *Режим администратора*", parse_mode='Markdown', reply_markup=admin_keyboard())
    elif has_subscription(user_id):
        await update.message.reply_text(welcome + "\n\n⭐ *Премиум-доступ активен*", parse_mode='Markdown', reply_markup=premium_keyboard())
    else:
        await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=main_keyboard())

# ─── Админ-панель ───
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    text = (
        "🔐 **Админ-панель**\n\n"
        "*/set_channel* — целевой канал\n"
        "*/add_category* — добавить категорию (ID)\n"
        "*/categories* — список категорий\n"
        "*/remove_category* — удалить категорию\n"
        "*/add_region* — добавить регион (код)\n"
        "*/regions* — список регионов\n"
        "*/remove_region* — удалить регион\n"
        "*/add_keyword* — добавить ключевое слово\n"
        "*/keywords* — список ключевых слов\n"
        "*/remove_keyword* — удалить ключевое слово\n"
        "*/set_parse* — интервал парсинга (часы)\n"
        "*/set_post* — интервал постинга (минуты)\n"
        "*/status* — текущие настройки\n"
        "*/subscribers* — подписчики\n"
        "*/catalog* — справочник категорий и регионов"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

# ─── Команды ───
async def catalog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📋 **Категории:**\n"
    for cid, cname in CATEGORIES.items():
        text += f"  `{cid}` — {cname}\n"
    
    text += "\n🌍 **Регионы:**\n"
    for code, name in REGIONS.items():
        text += f"  `{code}` — {name}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def set_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только админ.")
        return
    await update.message.reply_text("📢 Отправь username канала:\n`@мой_канал`", parse_mode='Markdown')
    context.user_data['awaiting_channel'] = True

async def add_category_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("📋 Отправь ID категории:\n`10` (Музыка), `24` (Развлечения) и т.д.\nСправочник: /catalog", parse_mode='Markdown')
    context.user_data['awaiting_category'] = True

async def categories_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats = get_all_categories()
    if cats:
        text = "📋 **Выбранные категории:**\n" + "\n".join(f"• `{cid}` — {CATEGORIES.get(cid, cname)}" for cid, cname in cats)
    else:
        text = "Категории не выбраны."
    await update.message.reply_text(text, parse_mode='Markdown')

async def remove_category_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("🗑 Отправь ID категории для удаления:")
    context.user_data['awaiting_remove_category'] = True

async def add_region_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("🌍 Отправь код региона:\n`US`, `DE`, `FR`, `GB` и т.д.\nСправочник: /catalog", parse_mode='Markdown')
    context.user_data['awaiting_region'] = True

async def regions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    regs = get_all_regions()
    if regs:
        text = "🌍 **Выбранные регионы:**\n" + "\n".join(f"• `{code}` — {REGIONS.get(code, name)}" for code, name in regs)
    else:
        text = "Регионы не выбраны."
    await update.message.reply_text(text, parse_mode='Markdown')

async def remove_region_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("🗑 Отправь код региона для удаления:")
    context.user_data['awaiting_remove_region'] = True

async def add_keyword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("🔑 Отправь ключевое слово:\n`deep house`, `jazz`, `techno`")
    context.user_data['awaiting_keyword'] = True

async def keywords_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kws = get_all_keywords()
    text = "🔑 **Ключевые слова:**\n" + "\n".join(f"• {kw}" for kw in kws) if kws else "Список пуст."
    await update.message.reply_text(text)

async def remove_keyword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("🗑 Отправь ключевое слово для удаления:")
    context.user_data['awaiting_remove_keyword'] = True

async def set_parse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("⏰ Интервал парсинга в часах (минимум 1):")
    context.user_data['awaiting_parse'] = True

async def set_post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("⏰ Интервал постинга в минутах (минимум 5):")
    context.user_data['awaiting_post'] = True

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) and not has_subscription(update.effective_user.id):
        return
    
    channel = get_channel()
    cats = get_all_categories()
    regs = get_all_regions()
    kws = get_all_keywords()
    parse_int = get_parse_interval()
    post_int = get_post_interval()
    queue = get_queue_size()
    
    text = (
        "📊 **Настройки:**\n\n"
        f"📢 Канал: {channel or 'не настроен'}\n"
        f"🔍 Парсинг: каждые {parse_int} ч\n"
        f"📤 Постинг: каждые {post_int} мин\n"
        f"📋 Категорий: {len(cats)}\n"
        f"🌍 Регионов: {len(regs)}\n"
        f"🔑 Ключевых слов: {len(kws)}\n"
        f"📦 В очереди: {queue} видео\n"
    )
    await update.message.reply_text(text)

async def subscribers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    subs = get_all_subscribers()
    if subs:
        text = "👥 **Подписчики:**\n" + "\n".join(f"• `{uid}` (@{uname})" for uid, uname in subs)
    else:
        text = "Подписчиков нет."
    await update.message.reply_text(text, parse_mode='Markdown')

# ─── Обработка кнопок ───
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    kb = main_keyboard()
    if is_admin(user_id):
        kb = admin_keyboard()
    elif has_subscription(user_id):
        kb = premium_keyboard()
    
    if text == "📩 Связь с админом":
        await update.message.reply_text("📩 Напиши админу: @твой_ник", reply_markup=kb)
        return True
    
    if text == "🔗 Скачать по ссылке":
        await update.message.reply_text("🔗 Отправь ссылку на YouTube Shorts:", reply_markup=kb)
        return True
    
    if text == "📊 Статус" and (is_admin(user_id) or has_subscription(user_id)):
        await status_cmd(update, context)
        return True
    
    if text == "👥 Подписчики" and is_admin(user_id):
        await subscribers_cmd(update, context)
        return True
    
    if text == "➕ Выдать подписку" and is_admin(user_id):
        await update.message.reply_text("Отправь Telegram ID пользователя:", reply_markup=kb)
        context.user_data['awaiting_add_sub'] = True
        return True
    
    if text == "➖ Убрать подписку" and is_admin(user_id):
        await update.message.reply_text("Отправь Telegram ID пользователя:", reply_markup=kb)
        context.user_data['awaiting_remove_sub'] = True
        return True
    
    if text == "🔍 Запустить парсинг" and is_admin(user_id):
        await update.message.reply_text("🔄 Запускаю парсинг...", reply_markup=kb)
        run_parser()
        await update.message.reply_text("✅ Парсинг завершён!", reply_markup=kb)
        return True
    
    if text == "🔍 Поиск Shorts" and (is_admin(user_id) or has_subscription(user_id)):
        await update.message.reply_text("🔑 Отправь ключевое слово для поиска Shorts:", reply_markup=kb)
        context.user_data['awaiting_search'] = True
        return True
    
    return False

# ─── Обработка текста ───
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    kb = main_keyboard()
    if is_admin(user_id):
        kb = admin_keyboard()
    elif has_subscription(user_id):
        kb = premium_keyboard()
    
    # Админские вводы
    if is_admin(user_id):
        if context.user_data.get('awaiting_channel'):
            ch = text if text.startswith('@') else f"@{text}"
            set_channel(ch)
            await update.message.reply_text(f"✅ Канал `{ch}` сохранён!", parse_mode='Markdown', reply_markup=kb)
            context.user_data['awaiting_channel'] = False
            return
        
        if context.user_data.get('awaiting_category'):
            cid = text.strip()
            cname = CATEGORIES.get(cid, "")
            if add_category(cid, cname):
                await update.message.reply_text(f"✅ Категория `{cid}` ({cname}) добавлена!", reply_markup=kb)
            else:
                await update.message.reply_text(f"⚠️ Категория `{cid}` уже есть.", reply_markup=kb)
            context.user_data['awaiting_category'] = False
            return
        
        if context.user_data.get('awaiting_remove_category'):
            remove_category(text.strip())
            await update.message.reply_text(f"🗑 Категория `{text}` удалена.", reply_markup=kb)
            context.user_data['awaiting_remove_category'] = False
            return
        
        if context.user_data.get('awaiting_region'):
            code = text.strip().upper()
            rname = REGIONS.get(code, "")
            if add_region(code, rname):
                await update.message.reply_text(f"✅ Регион `{code}` ({rname}) добавлен!", reply_markup=kb)
            else:
                await update.message.reply_text(f"⚠️ Регион `{code}` уже есть.", reply_markup=kb)
            context.user_data['awaiting_region'] = False
            return
        
        if context.user_data.get('awaiting_remove_region'):
            remove_region(text.strip().upper())
            await update.message.reply_text(f"🗑 Регион `{text}` удалён.", reply_markup=kb)
            context.user_data['awaiting_remove_region'] = False
            return
        
        if context.user_data.get('awaiting_keyword'):
            kw = text.strip().lower()
            if add_keyword(kw):
                await update.message.reply_text(f"✅ `{kw}` добавлено!", reply_markup=kb)
            else:
                await update.message.reply_text(f"⚠️ `{kw}` уже есть.", reply_markup=kb)
            context.user_data['awaiting_keyword'] = False
            return
        
        if context.user_data.get('awaiting_remove_keyword'):
            remove_keyword(text.strip().lower())
            await update.message.reply_text(f"🗑 `{text}` удалено.", reply_markup=kb)
            context.user_data['awaiting_remove_keyword'] = False
            return
        
        if context.user_data.get('awaiting_parse'):
            try:
                h = max(1, int(text))
                set_parse_interval(h)
                await update.message.reply_text(f"✅ Парсинг: каждые {h} ч", reply_markup=kb)
            except:
                await update.message.reply_text("❌ Отправь число.", reply_markup=kb)
            context.user_data['awaiting_parse'] = False
            return
        
        if context.user_data.get('awaiting_post'):
            try:
                m = max(5, int(text))
                set_post_interval(m)
                await update.message.reply_text(f"✅ Постинг: каждые {m} мин", reply_markup=kb)
            except:
                await update.message.reply_text("❌ Отправь число.", reply_markup=kb)
            context.user_data['awaiting_post'] = False
            return
        
        if context.user_data.get('awaiting_add_sub'):
            try:
                sub_id = int(text)
                add_subscription(sub_id)
                await update.message.reply_text(f"✅ Подписка выдана `{sub_id}`", parse_mode='Markdown', reply_markup=kb)
            except:
                await update.message.reply_text("❌ Отправь числовой ID.", reply_markup=kb)
            context.user_data['awaiting_add_sub'] = False
            return
        
        if context.user_data.get('awaiting_remove_sub'):
            try:
                sub_id = int(text)
                remove_subscription(sub_id)
                await update.message.reply_text(f"✅ Подписка у `{sub_id}` отключена", parse_mode='Markdown', reply_markup=kb)
            except:
                await update.message.reply_text("❌ Отправь числовой ID.", reply_markup=kb)
            context.user_data['awaiting_remove_sub'] = False
            return
    
    # Поиск Shorts (премиум + админ)
    if context.user_data.get('awaiting_search') and (is_admin(user_id) or has_subscription(user_id)):
        await update.message.reply_text(f"🔍 Ищу Shorts: `{text}`...", parse_mode='Markdown')
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
                    await update.message.reply_video(video=open(path, 'rb'), caption=cap[:1024]) if False else None
                else:
                    await update.message.reply_text(f"❌ Не удалось скачать: {s['url']}")
        
        context.user_data['awaiting_search'] = False
        return
    
    # Ссылка на YouTube
    if 'youtube.com' in text or 'youtu.be' in text:
        await update.message.reply_text("⏳ Скачиваю видео, подожди...")
        
        path, title, channel, views, likes = download_video_by_url(text)
        
        if path:
            cap = f"🎬 {title}\n📺 {channel}\n👁 {views:,} | 👍 {likes:,}"
            await post_video_to_user(user_id, path, cap)
        else:
            await update.message.reply_text("❌ Не удалось скачать видео. Проверь ссылку.", reply_markup=kb)
        return
    
    # Ничего не подошло
    await update.message.reply_text("Используй кнопки или отправь ссылку на YouTube.", reply_markup=kb)

# ─── Главный обработчик ───
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button_handled = await handle_buttons(update, context)
    if not button_handled:
        await handle_text(update, context)

# ─── main ───
def main():
    init_db()
    
    app = Application.builder().token(TOKEN).build()
    
    # Команды
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
    app.add_handler(CommandHandler('status', status_cmd))
    app.add_handler(CommandHandler('subscribers', subscribers_cmd))
    
    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Планировщик
    start_scheduler()
    
    print("🤖 YouTube Shorts Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()