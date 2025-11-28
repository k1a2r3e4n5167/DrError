import os
import telebot
import sqlite3

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# -----------------------------
# ایجاد دیتابیس (فقط یک بار)
# -----------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        age INTEGER,
        role TEXT
    )
    """)

    conn.commit()
    conn.close()

# -----------------------------
# چک کردن وجود کاربر
# -----------------------------
def get_user(chat_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    user = cursor.fetchone()

    conn.close()
    return user

# -----------------------------
# ذخیره کاربر جدید
# -----------------------------
def save_user(chat_id, first_name, last_name, age):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (chat_id, first_name, last_name, age, role) VALUES (?, ?, ?, ?, ?)",
        (chat_id, first_name, last_name, age, "member")
    )

    conn.commit()
    conn.close()

# -----------------------------
# سیستم پرسش مرحله‌ای
# -----------------------------
user_steps = {}   # مرحله ثبت‌نام
user_temp = {}    # داده‌های موقت

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user = get_user(chat_id)

    # اگر کاربر قبلاً ثبت‌نام کرده بود
    if user:
        bot.send_message(chat_id, f"🤝 خوش برگشتی {user[1]} عزیز!")
        return

    # کاربر جدید → شروع فرم ثبت‌نام
    user_steps[chat_id] = "ask_firstname"
    bot.send_message(chat_id, "🌟 سلام! خوش اومدی.\nبرای ساخت اکانت، لطفاً اسم خود را وارد کن:")

@bot.message_handler(func=lambda msg: True)
def register_system(message):
    chat_id = message.chat.id

    # اگر در حالت ثبت‌نام نیست، بی‌خیال
    if chat_id not in user_steps:
        return

    step = user_steps[chat_id]
    text = message.text.strip()

    # -------- مرحله 1: اسم --------
    if step == "ask_firstname":
        user_temp[chat_id] = {}
        user_temp[chat_id]["first_name"] = text
        user_steps[chat_id] = "ask_lastname"
        bot.send_message(chat_id, "فامیلی شما:")

    # -------- مرحله 2: فامیلی --------
    elif step == "ask_lastname":
        user_temp[chat_id]["last_name"] = text
        user_steps[chat_id] = "ask_age"
        bot.send_message(chat_id, "سن:")

    # -------- مرحله 3: سن --------
    elif step == "ask_age":
        if not text.isdigit():
            bot.send_message(chat_id, "❗ لطفاً سن را به صورت عدد وارد کنید:")
            return

        user_temp[chat_id]["age"] = int(text)

        # ذخیره در دیتابیس
        save_user(
            chat_id,
            user_temp[chat_id]["first_name"],
            user_temp[chat_id]["last_name"],
            user_temp[chat_id]["age"]
        )

        # پایان ثبت‌نام
        bot.send_message(
            chat_id,
            "🎉 اکانت شما با موفقیت ساخته شد!\n"
            f"نام: {user_temp[chat_id]['first_name']}\n"
            f"فامیلی: {user_temp[chat_id]['last_name']}\n"
            f"سن: {user_temp[chat_id]['age']}\n"
            "نقش: member"
        )

        del user_steps[chat_id]
        del user_temp[chat_id]


# -----------------------------
# اجرای ربات
# -----------------------------
init_db()
bot.infinity_polling()
