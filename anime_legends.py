import logging
import sqlite3
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8427386492:AAEIgcnOcvOqf-GtMlf_pGWPBMdEaRwAJVY"
DB_NAME = "anime_legends.db"
ADMIN_ID = 6267038708
MESSAGE_THRESHOLD = 100

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

RARITY_REWARD = {"Common": 50, "Rare": 150, "Epic": 400, "Legendary": 1000, "Mythic": 2500}
RARITY_EMOJI = {"Common": "⚪", "Rare": "🔵", "Epic": "🟣", "Legendary": "🟡", "Mythic": "🔴"}
RARITY_WEIGHTS = {"Common": 50, "Rare": 30, "Epic": 15, "Legendary": 4, "Mythic": 1}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        coins INTEGER DEFAULT 100,
        total_catches INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS characters (
        code INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        anime TEXT,
        rarity TEXT,
        video_id TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS harem (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        char_code INTEGER,
        count INTEGER DEFAULT 1,
        caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS active_char (
        chat_id INTEGER PRIMARY KEY,
        char_code INTEGER,
        active INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_stats (
        chat_id INTEGER PRIMARY KEY,
        message_count INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user.id, user.username or user.first_name))
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"سلام {user.first_name}! 🎮\n\n"
        "به **Anime Legends** خوش اومدی! 🏆\n\n"
        "📋 **دستورات:**\n"
        "/start - شروع\n"
        "/profile - پروفایل\n"
        "/harem - کلکسیون من\n"
        "/top - ۱۰ نفر برتر\n"
        "/gtop - ۱۰ نفر برتر جهانی\n"
        "/s <کد> - نمایش کاراکتر\n"
        "/lb - لوت‌باکس (۱۰۰۰ سکه)\n\n"
        "💡 هر ۱۰۰ پیام توی گروه، یه کاراکتر ظاهر میشه!",
        parse_mode="Markdown"
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT coins, total_catches, xp, level FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    if not row:
        conn.close()
        await update.message.reply_text("اول /start رو بزن!")
        return
    coins, catches, xp, level = row
    c.execute("SELECT COUNT(DISTINCT char_code) FROM harem WHERE user_id = ?", (user.id,))
    unique_count = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(
        f"👤 **پروفایل {user.first_name}**\n\n"
        f"💰 سکه: **{coins}**\n"
        f"🎯 شکار: **{catches}**\n"
        f"📚 کاراکتر یکتا: **{unique_count}**\n"
        f"⭐ سطح: **{level}** (XP: {xp})",
        parse_mode="Markdown"
    )

async def harem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""SELECT ch.code, ch.name, ch.anime, ch.rarity, h.count 
                 FROM harem h 
                 JOIN characters ch ON h.char_code = ch.code 
                 WHERE h.user_id = ? 
                 ORDER BY ch.rarity DESC, ch.name""", (user.id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("هنوز هیچ کاراکتری شکار نکردی! 😢")
        return
    text = f"📚 **حرم‌سرای {user.first_name}**\n\n"
    for code, name, anime, rarity, count in rows:
        emoji = RARITY_EMOJI.get(rarity, "⚪")
        text += f"{emoji} `#{code}` {name} ({anime}) ×{count}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT username, total_catches FROM users ORDER BY total_catches DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    text = "🏆 **۱۰ شکارچی برتر گروه**\n\n"
    for i, (name, catches) in enumerate(rows, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        text += f"{medal} {name} - {catches}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def gtop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT username, total_catches FROM users ORDER BY total_catches DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    text = "🌍 **۱۰ شکارچی برتر جهانی**\n\n"
    for i, (name, catches) in enumerate(rows, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        text += f"{medal} {name} - {catches}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def lootbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    if not row or row[0] < 1000:
        conn.close()
        await update.message.reply_text("❌ سکه کافی نداری! (نیاز: ۱۰۰۰ سکه)")
        return
    c.execute("UPDATE users SET coins = coins - 1000 WHERE user_id = ?", (user.id,))
    c.execute("SELECT code, name, rarity FROM characters ORDER BY RANDOM() LIMIT 1")
    char = c.fetchone()
    if not char:
        conn.close()
        await update.message.reply_text("⚠️ هیچ کاراکتری توی دیتابیس نیست!")
        return
    code, name, rarity = char
    c.execute("INSERT INTO harem (user_id, char_code) VALUES (?, ?)", (user.id, code))
    conn.commit()
    conn.close()
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    await update.message.reply_text(
        f"🎁 **لوت‌باکس باز شد!**\n\n"
        f"{emoji} {name} ({rarity}) به حرم‌سرات اضافه شد! 🎉",
        parse_mode="Markdown"
    )

async def show_char(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("مثال: `/s 9`", parse_mode="Markdown")
        return
    try:
        code = int(context.args[0])
    except:
        await update.message.reply_text("❌ کد باید عدد باشه!")
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT code, name, anime, rarity, video_id FROM characters WHERE code = ?", (code,))
    char = c.fetchone()
    if not char:
        conn.close()
        await update.message.reply_text(f"❌ کاراکتری با کد `{code}` نیست!", parse_mode="Markdown")
        return
    c.execute("SELECT COUNT(DISTINCT user_id) FROM harem WHERE char_code = ?", (code,))
    owners = c.fetchone()[0]
    conn.close()
    ch_code, name, anime, rarity, video_id = char
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    caption = f"{emoji} **{name}**\n\n📺 انیمه: {anime}\n🔢 کد: `#{ch_code}`\n📊 سطح: {rarity}\n👥 صاحبان: **{owners}**"
    try:
        await update.message.reply_video(video=video_id, caption=caption, parse_mode="Markdown")
    except:
        await update.message.reply_text(caption, parse_mode="Markdown")

async def addchar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "📤 **راهنما:**\n\nیه ویدیو بفرست با کپشن:\n"
        "`اسم | انیمه | سطح`\n\n"
        "مثال:\n`Naruto | Naruto Shippuden | Legendary`\n\n"
        "سطوح: Common, Rare, Epic, Legendary, Mythic",
        parse_mode="Markdown"
    )

async def listchars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT code, name, anime, rarity FROM characters ORDER BY code")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("هیچ کاراکتری نیست!")
        return
    text = f"📋 **لیست ({len(rows)} تا):**\n\n"
    for code, name, anime, rarity in rows:
        emoji = RARITY_EMOJI.get(rarity, "⚪")
        text += f"`#{code}` {emoji} {name} ({anime})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    video = update.message.video or update.message.animation
    caption = update.message.caption
    if not video:
        return
    if not caption or "|" not in caption:
        await update.message.reply_text("❌ کپشن باید این شکل باشه: `اسم | انیمه | سطح`", parse_mode="Markdown")
        return
    parts = [p.strip() for p in caption.split("|")]
    if len(parts) != 3:
        await update.message.reply_text("❌ کپشن باید ۳ بخش داشته باشه: اسم | انیمه | سطح")
        return
    name, anime, rarity = parts
    if rarity not in RARITY_REWARD:
        await update.message.reply_text(f"❌ سطح نامعتبر! باید یکی از اینا باشه:\n{', '.join(RARITY_REWARD.keys())}")
        return
    file_id = video.file_id
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO characters (name, anime, rarity, video_id) VALUES (?, ?, ?, ?)",
                  (name, anime, rarity, file_id))
        conn.commit()
        c.execute("SELECT code FROM characters WHERE name = ?", (name,))
        code = c.fetchone()[0]
        emoji = RARITY_EMOJI.get(rarity, "⚪")
        await update.message.reply_text(
            f"✅ کاراکتر اضافه شد!\n\n"
            f"🔢 کد: `#{code}`\n"
            f"📛 نام: **{name}**\n"
            f"📺 انیمه: {anime}\n"
            f"{emoji} سطح: {rarity}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")
    finally:
        conn.close()

async def spawn_char(context, chat_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT active FROM active_char WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    if row and row[0] == 1:
        conn.close()
        return
    c.execute("SELECT code, name, rarity, video_id FROM characters")
    all_chars = c.fetchall()
    if not all_chars:
        conn.close()
        await context.bot.send_message(chat_id=chat_id, text="⚠️ هیچ کاراکتری نیست! ادمین باید اضافه کنه.")
        return
    weighted_chars = []
    for ch in all_chars:
        weight = RARITY_WEIGHTS.get(ch[2], 1)
        weighted_chars.extend([ch] * weight)
    char = random.choice(weighted_chars)
    ch_code, name, rarity, video_id = char
    c.execute("REPLACE INTO active_char (chat_id, char_code, active) VALUES (?, ?, 1)", (chat_id, ch_code))
    conn.commit()
    conn.close()
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    caption = (
        f"🎬 یه کاراکتر ظاهر شد!\n\n"
        f"{emoji} سطح: {rarity}\n\n"
        "⏰ ۶۰ ثانیه وقت داری اسمش رو حدس بزنی!\n"
        "✍️ فقط اسم کاراکتر رو توی چت بنویس!"
    )
    try:
        await context.bot.send_video(chat_id=chat_id, video=video_id, caption=caption)
    except Exception as e:
        print(f"خطا: {e}")
        await context.bot.send_message(chat_id=chat_id, text=caption)

async def spawn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await spawn_char(context, update.effective_chat.id)

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = update.message.text.strip()
    if text.startswith("/"):
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO chat_stats (chat_id, message_count) VALUES (?, 0)", (chat_id,))
    c.execute("UPDATE chat_stats SET message_count = message_count + 1 WHERE chat_id = ?", (chat_id,))
    c.execute("SELECT message_count FROM chat_stats WHERE chat_id = ?", (chat_id,))
    count = c.fetchone()[0]
    if count >= MESSAGE_THRESHOLD:
        c.execute("UPDATE chat_stats SET message_count = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        await spawn_char(context, chat_id)
        return
    c.execute("""SELECT ch.code, ch.name, ch.rarity 
                 FROM active_char ac 
                 JOIN characters ch ON ac.char_code = ch.code 
                 WHERE ac.chat_id = ? AND ac.active = 1""", (chat_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    ch_code, char_name, rarity = row
    if text.lower() == char_name.lower():
        c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                  (user.id, user.username or user.first_name))
        reward = RARITY_REWARD.get(rarity, 50)
        c.execute("UPDATE users SET coins = coins + ?, total_catches = total_catches + 1, xp = xp + 10 WHERE user_id = ?",
                  (reward, user.id))
        c.execute("INSERT INTO harem (user_id, char_code) VALUES (?, ?)", (user.id, ch_code))
        c.execute("UPDATE active_char SET active = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        emoji = RARITY_EMOJI.get(rarity, "⚪")
        await update.message.reply_text(
            f"🎉 **شکار موفق!**\n\n"
            f"{emoji} {user.first_name} کاراکتر **{char_name}** (`#{ch_code}`) رو شکار کرد!\n"
            f"💰 +{reward} سکه",
            parse_mode="Markdown"
        )
    else:
        conn.close()

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("me", profile))
    app.add_handler(CommandHandler("harem", harem))
    app.add_handler(CommandHandler("collection", harem))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("gtop", gtop))
    app.add_handler(CommandHandler("lb", lootbox))
    app.add_handler(CommandHandler("lootbox", lootbox))
    app.add_handler(CommandHandler("s", show_char))
    app.add_handler(CommandHandler("info", show_char))
    app.add_handler(CommandHandler("spawn", spawn))
    app.add_handler(CommandHandler("addchar", addchar))
    app.add_handler(CommandHandler("listchars", listchars))
    app.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess))
    print("Anime Legends Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
