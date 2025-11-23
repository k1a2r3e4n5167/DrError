import os
import telebot
import requests
from telebot import types
import re
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import logging

# ------------------- تنظیمات لاگ‌گیری -------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ------------------- تنظیمات ربات -------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found in environment variables")
    raise ValueError("BOT_TOKEN not found")

bot = telebot.TeleBot(BOT_TOKEN)

# ------------------- API های تعریف شده در همین فایل -------------------
SERVICES = {
    "digikala": {
        "url": "https://api.digikala.com/v1/user/authenticate/",
        "method": "POST",
        "payload": {"username": "{phone}"},
        "headers": {"Content-Type": "application/json"}
    },
    "divar": {
        "url": "https://api.divar.ir/v5/auth/authenticate", 
        "method": "POST",
        "payload": {"phone": "{phone}"},
        "headers": {"Content-Type": "application/json"}
    },
    "banimod": {
        "url": "https://mobapi.banimode.com/api/v2/auth/request",
        "method": "POST", 
        "payload": {"phone": "{phone}"},
        "headers": {"Content-Type": "application/json"}
    }
}

# ------------------- متغیرهای جهانی -------------------
user_sessions = {}
session_lock = threading.Lock()

# ------------------- توابع اصلی -------------------
def send_single_request(service_name, service_config, phone_number):
    """ارسال درخواست به یک سرویس"""
    try:
        # جایگزینی شماره در payload
        formatted_payload = {}
        for key, value in service_config["payload"].items():
            if isinstance(value, str):
                formatted_payload[key] = value.format(phone=phone_number)
            else:
                formatted_payload[key] = value
        
        # ارسال درخواست
        if service_config["method"].upper() == "POST":
            response = requests.post(
                service_config["url"],
                json=formatted_payload,
                headers=service_config.get("headers", {}),
                timeout=15
            )
        else:
            response = requests.get(
                service_config["url"], 
                params=formatted_payload,
                headers=service_config.get("headers", {}),
                timeout=15
            )
        
        response.raise_for_status()
        logger.info(f"✅ {service_name} - Success: {response.status_code}")
        return f"✅ {service_name}"
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"❌ {service_name} - Failed: {str(e)}")
        return f"❌ {service_name}"

def send_bulk_requests(phone_number, rounds=1, delay=1):
    """ارسال درخواست به تمام سرویس ها"""
    all_results = []
    
    for round_num in range(1, rounds + 1):
        round_results = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:  # کاهش worker برای Railway
            futures = []
            for service_name, service_config in SERVICES.items():
                future = executor.submit(send_single_request, service_name, service_config, phone_number)
                futures.append(future)
            
            for future in futures:
                round_results.append(future.result())
        
        all_results.extend(round_results)
        
        if round_num < rounds:
            time.sleep(delay)
    
    return all_results

def cleanup_sessions():
    """تمیز کردن سشن‌های قدیمی"""
    try:
        current_time = time.time()
        with session_lock:
            expired_sessions = []
            for user_id, session_data in user_sessions.items():
                if current_time - session_data.get('timestamp', 0) > 300:  # 5 دقیقه
                    expired_sessions.append(user_id)
            
            for user_id in expired_sessions:
                del user_sessions[user_id]
                logger.info(f"🧹 Cleaned expired session for user {user_id}")
    except Exception as e:
        logger.error(f"Error in cleanup_sessions: {e}")

# ------------------- دستورات ربات -------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
🤖 به ربات OTP خوش آمدید!

📋 دستورات:
/send - ارسال درخواست
/services - نمایش سرویس‌ها
/stats - آمار ربات
/help - راهنما

⚠️ استفاده مسئولانه
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = f"""
📖 راهنمای استفاده:

1. برای ارسال درخواست:
   /send

2. سرویس‌های فعلی: {len(SERVICES)}
   
3. تنظیمات پیش‌فرض:
   - دورها: 1
   - تاخیر: 1 ثانیه
   - ماکسیموم دور: 3
    """
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['services'])
def show_services(message):
    services_text = "📋 سرویس‌های فعال:\n\n"
    for i, service_name in enumerate(SERVICES.keys(), 1):
        services_text += f"{i}. {service_name}\n"
    
    services_text += f"\n🔢 تعداد: {len(SERVICES)} سرویس"
    bot.send_message(message.chat.id, services_text)

@bot.message_handler(commands=['stats'])
def show_stats(message):
    cleanup_sessions()
    stats_text = f"""
📊 آمار ربات:

• سرویس‌های فعال: {len(SERVICES)}
• کاربران فعال: {len(user_sessions)}
• وضعیت: فعال ✅
• محیط: Railway 🚄
    """
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['send'])
def start_send_process(message):
    # محدودیت تعداد سشن
    if len(user_sessions) > 10:
        bot.send_message(message.chat.id, "❌ ظرفیت ربات پر است. لطفا چند دقیقه دیگر تلاش کنید.")
        return
    
    # ذخیره وضعیت کاربر
    with session_lock:
        user_sessions[message.chat.id] = {
            "step": "waiting_phone",
            "timestamp": time.time()
        }
    
    bot.send_message(
        message.chat.id,
        "📱 لطفا شماره موبایل را وارد کنید:\n\n"
        "مثال: 09123456789\n\n"
        "❌ برای لغو: /cancel"
    )

@bot.message_handler(commands=['cancel'])
def cancel_operation(message):
    with session_lock:
        if message.chat.id in user_sessions:
            del user_sessions[message.chat.id]
    bot.send_message(message.chat.id, "❌ عملیات لغو شد.")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.chat.id
    
    with session_lock:
        if user_id not in user_sessions:
            return
        user_data = user_sessions[user_id]
    
    # آپدیت تایم‌استمپ
    user_data['timestamp'] = time.time()
    
    if user_data.get("step") == "waiting_phone":
        # پردازش شماره تلفن
        phone = message.text.strip()
        
        if not re.match(r"^09\d{9}$", phone):
            bot.send_message(
                user_id,
                "❌ شماره موبایل نامعتبر است!\n"
                "لطفا شماره را به فرمت صحیح وارد کنید:\n"
                "مثال: 09123456789\n\n"
                "❌ برای لغو: /cancel"
            )
            return
        
        user_data["step"] = "waiting_rounds"
        user_data["phone"] = phone
        
        bot.send_message(
            user_id,
            "🔄 تعداد دورهای ارسال را وارد کنید (1-3):\n\n"
            "مثال: 1\n\n"
            "❌ برای لغو: /cancel"
        )
    
    elif user_data.get("step") == "waiting_rounds":
        # پردازش تعداد دورها
        try:
            rounds = int(message.text.strip())
            if rounds < 1 or rounds > 3:  # محدودیت برای Railway
                bot.send_message(
                    user_id,
                    "❌ تعداد دور باید بین 1 تا 3 باشد!\n"
                    "لطفا عدد معتبر وارد کنید:\n\n"
                    "❌ برای لغو: /cancel"
                )
                return
            
            user_data["step"] = "waiting_delay"
            user_data["rounds"] = rounds
            
            bot.send_message(
                user_id,
                "⏰ تاخیر بین دورها (1-5 ثانیه):\n\n"
                "مثال: 1\n\n"
                "❌ برای لغو: /cancel"
            )
            
        except ValueError:
            bot.send_message(
                user_id,
                "❌ تعداد دور نامعتبر است!\n"
                "لطفا عدد وارد کنید:\n\n"
                "❌ برای لغو: /cancel"
            )
    
    elif user_data.get("step") == "waiting_delay":
        # پردازش تاخیر
        try:
            delay = float(message.text.strip())
            if delay < 1 or delay > 5:  # محدودیت برای Railway
                bot.send_message(
                    user_id,
                    "❌ تاخیر باید بین 1 تا 5 ثانیه باشد!\n"
                    "لطفا عدد معتبر وارد کنید:\n\n"
                    "❌ برای لغو: /cancel"
                )
                return
            
            # شروع ارسال
            phone = user_data["phone"]
            rounds = user_data["rounds"]
            
            progress_msg = bot.send_message(
                user_id,
                f"🚀 شروع ارسال درخواست‌ها...\n\n"
                f"📞 شماره: {phone}\n"
                f"🔁 دورها: {rounds}\n"
                f"⏰ تاخیر: {delay} ثانیه\n"
                f"📡 سرویس‌ها: {len(SERVICES)}\n\n"
                f"⏳ لطفا صبر کنید..."
            )
            
            # ارسال در پس‌زمینه
            def send_requests():
                try:
                    results = send_bulk_requests(phone, rounds, delay)
                    
                    # نمایش نتایج
                    successful = sum(1 for r in results if "✅" in r)
                    failed = sum(1 for r in results if "❌" in r)
                    
                    result_text = f"📊 نتایج ارسال برای {phone}:\n\n"
                    result_text += f"✅ موفق: {successful}\n"
                    result_text += f"❌ ناموفق: {failed}\n"
                    result_text += f"📈 مجموع: {len(results)} درخواست"
                    
                    bot.edit_message_text(
                        result_text,
                        chat_id=user_id,
                        message_id=progress_msg.message_id
                    )
                    
                except Exception as e:
                    logger.error(f"Error in send_requests: {e}")
                    bot.edit_message_text(
                        f"❌ خطا در ارسال: {str(e)}",
                        chat_id=user_id,
                        message_id=progress_msg.message_id
                    )
                
                finally:
                    # پاک کردن session
                    with session_lock:
                        if user_id in user_sessions:
                            del user_sessions[user_id]
            
            # اجرا در thread جداگانه
            thread = threading.Thread(target=send_requests)
            thread.daemon = True
            thread.start()
            
        except ValueError:
            bot.send_message(
                user_id,
                "❌ تاخیر نامعتبر است!\n"
                "لطفا عدد وارد کنید:\n\n"
                "❌ برای لغو: /cancel"
            )

# ------------------- health check برای Railway -------------------
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot is running!"

@app.route('/health')
def health():
    return {"status": "healthy", "services": len(SERVICES)}

def run_flask():
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))

# ------------------- راه‌اندازی ربات -------------------
if __name__ == "__main__":
    logger.info("🤖 ربات OTP راه‌اندازی شد!")
    logger.info(f"📡 تعداد سرویس‌ها: {len(SERVICES)}")
    
    # راه‌اندازی همزمان Flask و Telegram Bot
    import threading
    
    # اجرای Flask در thread جداگانه
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # اجرای ربات تلگرام
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"❌ خطا در ربات: {e}")
