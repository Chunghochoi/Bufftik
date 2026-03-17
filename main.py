import os
import time
import threading
import telebot
from telebot import types
from flask import Flask
import re
import random
import requests
import zipfile

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CẤU HÌNH ---
API_TOKEN = '8725772455:AAGVE5UM0qtlES1TWSygwz7flhaaLLbwqlI'
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

PROXY_SCRAPE = [
    "104.207.51.206:3129", "65.111.0.45:3129", "45.3.36.192:3129", "104.207.49.99:3129",
    "216.26.246.0:3129", "104.207.53.210:3129", "216.26.236.43:3129", "151.123.178.209:3129"
]

WEBSHARE = [
    "31.59.20.176:6754:jhxqqqco:39lpkdhlbvzn", "23.95.150.145:6114:jhxqqqco:39lpkdhlbvzn",
    "198.23.239.134:6540:jhxqqqco:39lpkdhlbvzn", "45.38.107.97:6014:jhxqqqco:39lpkdhlbvzn",
    "107.172.163.27:6543:jhxqqqco:39lpkdhlbvzn", "198.105.121.200:6462:jhxqqqco:39lpkdhlbvzn"
]

user_sessions = {}

def get_public_ip():
    try: return requests.get('https://api.ipify.org', timeout=5).text
    except: return "Unknown"

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    manifest_json = '{"version":"1.0.0","manifest_version":2,"name":"Chrome Proxy","permissions":["proxy","tabs","unlimitedStorage","storage","<all_urls>","webRequest","webRequestBlocking"],"background":{"scripts":["background.js"]},"minimum_chrome_version":"22.0.0"}'
    background_js = 'var config={mode:"fixed_servers",rules:{singleProxy:{scheme:"http",host:"%s",port:parseInt(%s)},bypassList:["localhost"]}};chrome.proxy.settings.set({value:config,scope:"regular"},function(){});function callbackFn(details){return{authCredentials:{username:"%s",password:"%s"}}}chrome.webRequest.onAuthRequired.addListener(callbackFn,{urls:["<all_urls>"]},["blocking"]);' % (proxy_host, proxy_port, proxy_user, proxy_pass)
    extension_path = 'proxy_auth_plugin.zip'
    with zipfile.ZipFile(extension_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
    return os.path.abspath(extension_path)

class ZefoyManager:
    def __init__(self, chat_id, video_url, service_id, proxy_source):
        self.chat_id = chat_id
        self.video_url = video_url
        self.service_id = service_id
        self.proxy_source = proxy_source
        self.services = {"2": "t-hearts-button", "3": "t-chearts-button", "4": "t-views-button", "5": "t-shares-button", "6": "t-favorites-button"}
        self.driver = None

    def create_driver(self):
        # Đóng driver cũ nếu tồn tại để giải phóng RAM
        if self.driver:
            try: self.driver.quit()
            except: pass

        options = uc.ChromeOptions()
        options.add_argument('--headless') # Dùng headless tiêu chuẩn để ổn định RAM
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage') # Chạy trên RAM thay vì /dev/shm
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=800,600') # Cửa sổ nhỏ nhất có thể
        
        # --- CẤU HÌNH SIÊU TIẾT KIỆM RAM ---
        options.add_argument('--single-process') # Ép chạy 1 tiến trình (Tiết kiệm ~150MB RAM)
        options.add_argument('--disable-application-cache')
        options.add_argument('--disable-infobars')
        options.add_argument('--no-first-run')
        options.add_argument('--disable-setuid-sandbox')
        
        if self.proxy_source == "scrape":
            p = random.choice(PROXY_SCRAPE)
            options.add_argument(f'--proxy-server=http://{p}')
        else:
            p_str = random.choice(WEBSHARE)
            ip, port, user, pwd = p_str.split(':')
            auth_ext = create_proxy_auth_extension(ip, port, user, pwd)
            options.add_argument(f'--load-extension={auth_ext}')

        # Khởi tạo driver
        self.driver = uc.Chrome(options=options, use_subprocess=True)
        self.wait = WebDriverWait(self.driver, 35)

    def start_process(self):
        try:
            self.create_driver()
            bot.send_message(self.chat_id, "🌐 Đang kết nối Zefoy (Low RAM Mode)...")
            self.driver.get("https://zefoy.com")
            
            time.sleep(15)
            try: self.driver.switch_to.alert.dismiss()
            except: pass

            captcha_img = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
            captcha_img.screenshot("captcha.png")
            with open("captcha.png", "rb") as photo:
                bot.send_photo(self.chat_id, photo, caption="📸 Nhập Captcha:")
            
            user_sessions[self.chat_id]['status'] = 'WAITING_CAPTCHA'
            user_sessions[self.chat_id]['manager'] = self
        except Exception as e:
            bot.send_message(self.chat_id, f"💥 RAM quá tải, bot tự khởi động lại. Vui lòng thử lại sau 1 phút.")
            if self.driver: self.driver.quit()

    def submit_captcha(self, code):
        try:
            try: self.driver.switch_to.alert.dismiss()
            except: pass
            
            self.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']").send_keys(code)
            self.driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
            time.sleep(7)
            
            btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, self.services[self.service_id])))
            btn.click()
            bot.send_message(self.chat_id, "✅ Đã login thành công!")
            self.loop_service()
        except Exception as e:
            bot.send_message(self.chat_id, "❌ Captcha sai hoặc lỗi RAM. Hãy /start lại.")
            if self.driver: self.driver.quit()

    def loop_service(self):
        while True:
            try:
                try: self.driver.switch_to.alert.dismiss()
                except: pass
                
                form = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Video URL']")))
                form.clear()
                form.send_keys(self.video_url)
                self.driver.find_element(By.XPATH, "//button[contains(@class, 'btn-search')] | //form//button").click()
                time.sleep(8)
                
                if "Please wait" in self.driver.page_source:
                    bot.send_message(self.chat_id, "⏳ Đang cooldown...")
                    time.sleep(80)
                    self.driver.refresh()
                    continue
                
                btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'btn-primary')] | //button[contains(@class, 'wbutton')]")
                btn.click()
                bot.send_message(self.chat_id, "🚀 Buff thành công!")
                time.sleep(200) # Nghỉ lâu hơn để tránh spam
                self.driver.refresh()
            except:
                time.sleep(20)
                try: self.driver.refresh()
                except: break

@app.route('/')
def home(): return f"IP: {get_public_ip()}"

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, f"🤖 **Zefoy Render-Ultra-Lite**\nIP: `{get_public_ip()}`\nGửi link TikTok.")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def handle_link(message):
    user_sessions[message.chat.id] = {'url': message.text}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("1️⃣ Scrape", callback_data="src_scrape"),
               types.InlineKeyboardButton("2️⃣ Webshare", callback_data="src_webshare"))
    bot.send_message(message.chat.id, "Chọn Proxy:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("src_"))
def handle_src(call):
    chat_id = call.message.chat.id
    user_sessions[chat_id]['src'] = call.data.replace("src_", "")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👁 Views", callback_data="svc_4"), types.InlineKeyboardButton("❤️ Hearts", callback_data="svc_2"))
    markup.add(types.InlineKeyboardButton("⭐ Favorites", callback_data="svc_6"))
    bot.edit_message_text("Chọn dịch vụ:", chat_id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("svc_"))
def handle_svc(call):
    chat_id = call.message.chat.id
    data = user_sessions[chat_id]
    manager = ZefoyManager(chat_id, data['url'], call.data.replace("svc_", ""), data['src'])
    threading.Thread(target=manager.start_process).start()

@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get('status') == 'WAITING_CAPTCHA')
def handle_captcha(message):
    if message.chat.id in user_sessions and 'manager' in user_sessions[message.chat.id]:
        manager = user_sessions[message.chat.id]['manager']
        user_sessions[message.chat.id]['status'] = 'RUNNING'
        threading.Thread(target=manager.submit_captcha, args=(message.text,)).start()

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
