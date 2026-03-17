import os
import time
import threading
import telebot
from telebot import types
from flask import Flask
import re
import random
import requests # Thêm thư viện để lấy IP

# Thư viện Selenium và undetected_chromedriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# --- CẤU HÌNH ---
API_TOKEN = '8725772455:AAGVE5UM0qtlES1TWSygwz7flhaaLLbwqlI'
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# DANH SÁCH PROXY CỦA BẠN
PROXY_LIST = [
    "104.207.51.206:3129", "65.111.0.45:3129", "45.3.36.192:3129", "104.207.49.99:3129",
    "216.26.246.0:3129", "104.207.53.210:3129", "216.26.236.43:3129", "151.123.178.209:3129",
    "209.50.171.176:3129", "216.26.231.249:3129", "216.26.243.221:3129", "45.3.47.247:3129",
    "193.56.28.98:3129", "65.111.12.26:3129", "216.26.242.45:3129", "104.207.47.84:3129",
    "65.111.4.97:3129", "104.207.54.130:3129", "209.50.163.191:3129", "104.207.48.247:3129",
    "216.26.233.6:3129", "45.3.34.23:3129", "216.26.245.141:3129", "45.3.45.104:3129",
    "209.50.172.253:3129", "45.3.43.32:3129", "209.50.186.245:3129", "104.207.55.71:3129",
    "216.26.225.98:3129", "65.111.29.234:3129", "216.26.242.195:3129", "209.50.164.205:3129",
    "65.111.8.100:3129", "209.50.185.68:3129", "216.26.228.78:3129", "65.111.20.156:3129",
    "216.26.225.193:3129", "216.26.239.243:3129", "45.3.41.102:3129", "104.207.47.125:3129",
    "216.26.224.82:3129", "216.26.246.104:3129", "209.50.187.69:3129", "104.207.37.144:3129",
    "104.207.39.232:3129", "209.50.180.227:3129", "151.123.176.148:3129", "104.207.53.43:3129",
    "104.207.38.74:3129", "209.50.180.222:3129", "209.50.189.63:3129", "209.50.188.188:3129",
    "216.26.250.177:3129", "65.111.29.123:3129", "209.50.170.150:3129", "209.50.188.46:3129",
    "45.3.42.150:3129", "104.207.58.1:3129", "104.207.58.129:3129", "209.50.168.218:3129",
    "216.26.254.210:3129", "45.3.62.98:3129", "65.111.7.17:3129", "216.26.247.40:3129",
    "104.167.25.149:3129", "45.3.52.98:3129", "104.207.54.109:3129", "104.207.43.113:3129",
    "209.50.161.33:3129", "104.207.38.226:3129", "65.111.30.220:3129", "65.111.14.112:3129",
    "151.123.176.122:3129", "216.26.241.2:3129", "216.26.227.51:3129", "65.111.8.175:3129",
    "209.50.184.226:3129", "104.207.44.215:3129", "104.207.39.165:3129", "65.111.20.118:3129",
    "216.26.246.37:3129", "209.50.175.151:3129", "209.50.174.7:3129", "216.26.226.173:3129",
    "45.3.54.238:3129", "65.111.2.106:3129", "193.56.28.40:3129", "216.26.227.176:3129",
    "216.26.253.8:3129", "104.207.45.219:3129", "216.26.230.126:3129", "209.50.165.219:3129",
    "45.3.53.170:3129", "65.111.22.17:3129", "216.26.226.235:3129", "65.111.20.32:3129",
    "104.207.54.202:3129", "65.111.12.189:3129", "65.111.25.138:3129", "65.111.15.176:3129"
]

user_sessions = {}

# --- HÀM LẤY IP CỦA RENDER ---
def get_public_ip():
    try:
        # Sử dụng api ipify để lấy IP public của server Render
        response = requests.get('https://api.ipify.org', timeout=10)
        return response.text
    except Exception as e:
        return f"Lỗi: {str(e)}"

@app.route('/')
def home():
    return f"Bot is running. Server IP: {get_public_ip()}"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

class ZefoyManager:
    def __init__(self, chat_id, video_url, service_id):
        self.chat_id = chat_id
        self.video_url = video_url
        self.service_id = service_id
        self.services = {"2": "t-hearts-button", "3": "t-chearts-button", "4": "t-views-button", "5": "t-shares-button", "6": "t-favorites-button"}
        self.driver = None

    def create_driver(self):
        proxy = random.choice(PROXY_LIST)
        bot.send_message(self.chat_id, f"🛰️ Đang dùng Proxy: `{proxy}`")

        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument(f'--proxy-server=http://{proxy}')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        options.add_argument('--disable-blink-features=AutomationControlled')

        self.driver = uc.Chrome(options=options, use_subprocess=True)
        self.wait = WebDriverWait(self.driver, 30)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def start_process(self):
        try:
            self.create_driver()
            bot.send_message(self.chat_id, "🔗 Đang kết nối Zefoy...")
            self.driver.get("https://zefoy.com")
            time.sleep(15) 
            
            try:
                captcha_img = self.wait.until(EC.presence_of_element_located((By.XPATH, "//img[contains(@class, 'img-thumbnail')] | //img")))
                captcha_img.screenshot("captcha.png")
                with open("captcha.png", "rb") as photo:
                    bot.send_photo(self.chat_id, photo, caption="📸 Nhập Captcha:")
                user_sessions[self.chat_id]['status'] = 'WAITING_CAPTCHA'
                user_sessions[self.chat_id]['manager'] = self
            except:
                bot.send_message(self.chat_id, "❌ Proxy lag hoặc bị chặn IP Render. Thử lại với Proxy khác...")
                self.driver.quit()
                self.start_process()

        except Exception as e:
            bot.send_message(self.chat_id, f"💥 Lỗi: {str(e)}")
            if self.driver: self.driver.quit()

    def submit_captcha(self, code):
        try:
            input_box = self.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']")
            input_box.send_keys(code)
            self.driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
            time.sleep(7)
            service_btn_class = self.services.get(self.service_id)
            btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, service_btn_class)))
            btn.click()
            bot.send_message(self.chat_id, "✅ OK! Đang chạy...")
            self.loop_service()
        except:
            bot.send_message(self.chat_id, "❌ Lỗi captcha/login. Thử lại /start")
            self.driver.quit()

    def loop_service(self):
        while True:
            try:
                form = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Video URL']")))
                form.clear()
                form.send_keys(self.video_url)
                self.driver.find_element(By.XPATH, "//button[contains(@class, 'btn-search')] | //form//button").click()
                time.sleep(6)
                if "Please wait" in self.driver.page_source:
                    time.sleep(70)
                    self.driver.refresh()
                    continue
                buff_btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-primary')] | //button[contains(@class, 'wbutton')]")
                for b in buff_btns:
                    if b.is_displayed():
                        b.click()
                        bot.send_message(self.chat_id, "🚀 Thành công!")
                        time.sleep(180)
                        self.driver.refresh()
                        break
            except:
                self.driver.refresh()
                time.sleep(10)

# --- TELEGRAM HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(message):
    current_ip = get_public_ip()
    msg = f"🤖 **Zefoy Bot Proxy**\n\n"
    msg += f"📍 **IP Render hiện tại:** `{current_ip}`\n"
    msg += f"⚠️ *Hãy add IP trên vào Whitelist của ProxyScrape nếu cần!*\n\n"
    msg += f"Gửi Link TikTok để bắt đầu."
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def handle_link(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {'url': message.text, 'status': 'SELECT_SERVICE'}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👁️ Views", callback_data="4"), types.InlineKeyboardButton("❤️ Hearts", callback_data="2"))
    markup.add(types.InlineKeyboardButton("↪️ Shares", callback_data="5"), types.InlineKeyboardButton("⭐ Favorites", callback_data="6"))
    bot.send_message(chat_id, "Chọn dịch vụ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    if chat_id in user_sessions:
        manager = ZefoyManager(chat_id, user_sessions[chat_id]['url'], call.data)
        threading.Thread(target=manager.start_process).start()
        bot.answer_callback_query(call.id, "Đang khởi động...")

@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get('status') == 'WAITING_CAPTCHA')
def handle_captcha(message):
    chat_id = message.chat.id
    if 'manager' in user_sessions[chat_id]:
        user_sessions[chat_id]['status'] = 'RUNNING'
        threading.Thread(target=user_sessions[chat_id]['manager'].submit_captcha, args=(message.text,)).start()

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling()
