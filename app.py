import os
import telebot
import requests
from telebot import types
import random
import re
from concurrent.futures import ThreadPoolExecutor

# ------------------- خواندن توکن از Environment Variable -------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # توکن باید در Railway به عنوان Environment Variable تعریف شود
if not BOT_TOKEN:
    raise ValueError("توکن BOT_TOKEN در متغیرهای محیطی تنظیم نشده است!")

bot = telebot.TeleBot(BOT_TOKEN)

# ------------------- لیست APIها -------------------
APIS = {
    "digikala": {
        "url": "https://api.digikala.com/v1/user/authenticate/",
        "payload_key": "username",
        "headers": {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    },
    "divar": {
        "url": "https://api.divar.ir/v5/auth/authenticate",
        "payload_key": "phone",
        "headers": {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    },
    "banimod": {
        "url": "https://mobapi.banimode.com/api/v2/auth/request",
        "payload_key": "phone",
        "headers": {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    },
    "otaghak": {
        "url": "https://core.otaghak.com/odata/Otaghak/Users/SendVerificationCode",
        "payload_key": "userName",
        "headers": {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    }
}

# ------------------- توابع OTP -------------------
def send_otp(api_name, api, phone_number):
    try:
        response = requests.post(api["url"],
                                 json={api["payload_key"]: phone_number},
                                 headers=api["headers"],
                                 timeout=10)
        response.raise_for_status()
        try:
            data = response.json()
        except:
            data = response.text
        return f"✅ پاسخ {api_name}: {data}"
    except requests.exceptions.RequestException as e:
        return f"❌ خطا در {api_name}: {e}"

def send_otp_to_all(phone_number):
    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(send_otp, name, api, phone_number) for name, api in APIS.items()]
        for future in futures:
            results.append(future.result())
    return results

# ------------------- دستور /api -------------------
@bot.message_handler(commands=['api'])
def ask_phone(message):
    bot.send_message(message.chat.id, "لطفا شماره موبایل خود را وارد کنید:")
    bot.register_next_step_handler(message, process_phone)

def process_phone(message):
    phone = message.text.strip()
    if not re.match(r"^09\d{9}$", phone):
        bot.send_message(message.chat.id, "شماره موبایل نامعتبر است. لطفا دوباره وارد کنید:")
        bot.register_next_step_handler(message, process_phone)
        return

    bot.send_message(message.chat.id, "در حال ارسال درخواست‌ها به APIها ...")
    results = send_otp_to_all(phone)
    for res in results:
        bot.send_message(message.chat.id, res)

# ------------------- دستورات اصلی ربات -------------------

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, 'به ربات خوش آمدید!')
    bot.reply_to(message, 'لطفا از این ربات توقع زیادی نداشته باشید!')
    bot.reply_to(message, 'با زدن /help کارهای این ربات را می‌بینید')

@bot.message_handler(commands=['hello'])
def ask_name(message):
    bot.send_message(message.chat.id, 'اسم خود را وارد کنید:')
    bot.register_next_step_handler(message, name_handler)

def name_handler(message):
    name = message.text
    if re.match(r"^[a-zA-Z\sآ-ی]*$", name):
        bot.send_message(message.chat.id, f'سلام {name} چند سالته؟')
        bot.register_next_step_handler(message, age_handler)
    else:
        bot.send_message(message.chat.id, 'اسم خود را درست وارد کنید')
        bot.register_next_step_handler(message, name_handler)

def age_handler(message):
    age = message.text
    if age.isdigit():
        bot.send_message(message.chat.id, f'موفق باشی')
    else:
        bot.send_message(message.chat.id, 'سن خود را درست وارد کنید')
        bot.register_next_step_handler(message, age_handler)

@bot.message_handler(func=lambda message: any(word in message.text.lower() for word in ['kir', 'koz', 'kos', 'kos nanat', 'kiri', 'koni', 'mamano', 'کیر','کص']))
def filter_bad_words(message):
    bot.send_message(message.chat.id, 'برو بچه کونی')

# ------------------- لینک‌ها -------------------
button1 = types.InlineKeyboardButton(text='Porn_Hub', url='https://www.pornhub.com/')
button2 = types.InlineKeyboardButton(text='Xvideos', url='https://www.xvideos.com/')
button3 = types.InlineKeyboardButton(text='Xnxx', url='https://www.xnxx.com/')
Inline_Keyboard = types.InlineKeyboardMarkup(row_width=1)
Inline_Keyboard.add(button1, button2, button3)

@bot.message_handler(commands=['jagh'])
def send_links(message):
    bot.reply_to(message, 'ای جقی 😂', reply_markup=Inline_Keyboard)

# ------------------- بازی سنگ کاغذ قیچی -------------------
@bot.message_handler(commands=['bazi'])
def start_game(message):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("سنگ", callback_data="rock")
    button2 = types.InlineKeyboardButton("کاغذ", callback_data="paper")
    button3 = types.InlineKeyboardButton("قیچی", callback_data="scissors")
    markup.add(button1, button2, button3)
    restart_button = types.InlineKeyboardButton("شروع مجدد", callback_data="restart")
    markup.add(restart_button)
    bot.send_message(message.chat.id, "سلام! بازی سنگ، کاغذ، قیچی شروع شد. لطفا یکی از گزینه‌ها را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_game_choice(call):
    if call.data == "restart":
        start_game(call.message)
    else:
        user_choice = call.data
        bot_choice = random.choice(["rock", "paper", "scissors"])
        result = determine_winner(user_choice, bot_choice)
        bot.send_message(call.message.chat.id, f"انتخاب شما: {user_choice}\nانتخاب من: {bot_choice}\nنتیجه: {result}")

def determine_winner(user_choice, bot_choice):
    if user_choice == bot_choice:
        return "مساوی شدیم"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        return "تو بردی"
    else:
        return "من بردم"

# ------------------- کمک‌ها -------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, 'با زدن /hello میتوانید با من مکالمه کوتاهی داشته باشید')
    bot.reply_to(message, 'با زدن /bazi با من سنگ کاغذ قیچی بازی کنیم')
    bot.reply_to(message, 'برای گزینه بعدی به User https://t.me/KarenKH1 در تلگرام پیام دهید')

# ------------------- شروع ربات -------------------
if __name__ == "__main__":
    bot.polling()
