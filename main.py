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

# Danh sách Webshare (IP:Port:User:Pass)
WEBSHARE = [
    "31.59.20.176:6754:jhxqqqco:39lpkdhlbvzn", "23.95.150.145:6114:jhxqqqco:39lpkdhlbvzn",
    "198.23.239.134:6540:jhxqqqco:39lpkdhlbvzn", "45.38.107.97:6014:jhxqqqco:39lpkdhlbvzn",
    "107.172.163.27:6543:jhxqqqco:39lpkdhlbvzn", "198.105.121.200:6462:jhxqqqco:39lpkdhlbvzn",
    "64.137.96.74:6641:jhxqqqco:39lpkdhlbvzn", "216.10.27.159:6837:jhxqqqco:39lpkdhlbvzn",
    "142.111.67.146:5611:jhxqqqco:39lpkdhlbvzn", "191.96.254.138:6185:jhxqqqco:39lpkdhlbvzn"
]

user_sessions = {}

def get_public_ip():
    try: return requests.get('https://api.ipify.org', timeout=5).text
    except: return "Unknown"

# Hàm tạo Extension để vượt qua Username/Password Proxy (Tiết kiệm RAM hơn selenium-wire)
def create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": ["proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version":"22.0.0"
    }
    """
    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
          singleProxy: {
            scheme: "http",
            host: "%s",
            port: parseInt(%s)
          },
          bypassList: ["localhost"]
        }
      };
    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }
    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (proxy_host, proxy_port, proxy_user, proxy_pass)
    
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
        options = uc.ChromeOptions()
        options.add_argument('--headless=new') # Headless mới lách tốt hơn
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1280,720')
        
        # Cấu hình Proxy
        if self.proxy_source == "scrape":
            p = random.choice(PROXY_SCRAPE)
            options.add_argument(f'--proxy-server=http://{p}')
            bot.send_message(self.chat_id, f"🛰 ProxyScrape: `{p}`")
        else:
            p_str = random.choice(WEBSHARE)
            ip, port, user, pwd = p_str.split(':')
            auth_ext = create_proxy_auth_extension(ip, port, user, pwd)
            options.add_argument(f'--load-extension={auth_ext}')
            bot.send_message(self.chat_id, f"🛰 Webshare: `{ip}:{port}`")

        # Khởi tạo driver (Tắt use_subprocess để tiết kiệm RAM)
        self.driver = uc.Chrome(options=options, use_subprocess=False)
        self.wait = WebDriverWait(self.driver, 35)

    def start_process(self):
        try:
            self.create_driver()
            bot.send_message(self.chat_id, "🌐 Đang truy cập Zefoy...")
            self.driver.get("https://zefoy.com")
            
            time.sleep(15)
            # Tự động đóng Alert nếu có
            try: self.driver.switch_to.alert.dismiss()
            except: pass

            captcha_img = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
            captcha_img.screenshot("captcha.png")
            with open("captcha.png", "rb") as photo:
                bot.send_photo(self.chat_id, photo, caption="📸 Nhập Captcha:")
            
            user_sessions[self.chat_id]['status'] = 'WAITING_CAPTCHA'
            user_sessions[self.chat_id]['manager'] = self
        except Exception as e:
            bot.send_message(self.chat_id, f"💥 Lỗi Stacktrace (RAM yếu): {str(e)[:100]}")
            if self.driver: self.driver.quit()

    def submit_captcha(self, code):
        try:
            try: self.driver.switch_to.alert.dismiss()
            except: pass
            
            self.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']").send_keys(code)
            self.driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
            time.sleep(5)
            
            btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, self.services[self.service_id])))
            btn.click()
            bot.send_message(self.chat_id, "✅ OK! Đang chạy...")
            self.loop_service()
        except Exception as e:
            bot.send_message(self.chat_id, f"❌ Lỗi: {str(e)[:50]}")
            self.driver.quit()

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
                    time.sleep(75)
                    self.driver.refresh()
                    continue
                
                btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'btn-primary')] | //button[contains(@class, 'wbutton')]")
                btn.click()
                bot.send_message(self.chat_id, "🚀 Thành công!")
                time.sleep(180)
                self.driver.refresh()
            except:
                time.sleep(15)
                self.driver.refresh()

@app.route('/')
def home(): return f"Bot IP: {get_public_ip()}"

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, f"🤖 **Zefoy Lite v3**\nIP: `{get_public_ip()}`\nGửi link TikTok để bắt đầu.")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def handle_link(message):
    user_sessions[message.chat.id] = {'url': message.text}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("1️⃣ ProxyScrape", callback_data="src_scrape"),
               types.InlineKeyboardButton("2️⃣ Webshare", callback_data="src_webshare"))
    bot.send_message(message.chat.id, "Chọn Proxy:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("src_"))
def handle_src(call):
    chat_id = call.message.chat.id
    user_sessions[chat_id]['src'] = call.data.replace("src_", "")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👁 Views", callback_data="svc_4"), types.InlineKeyboardButton("❤️ Hearts", callback_data="svc_2"))
    markup.add(types.InlineKeyboardButton("↪️ Shares", callback_data="svc_5"), types.InlineKeyboardButton("⭐ Favorites", callback_data="svc_6"))
    bot.edit_message_text("Chọn dịch vụ:", chat_id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("svc_"))
def handle_svc(call):
    chat_id = call.message.chat.id
    data = user_sessions[chat_id]
    manager = ZefoyManager(chat_id, data['url'], call.data.replace("svc_", ""), data['src'])
    threading.Thread(target=manager.start_process).start()

@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get('status') == 'WAITING_CAPTCHA')
def handle_captcha(message):
    manager = user_sessions[message.chat.id]['manager']
    user_sessions[message.chat.id]['status'] = 'RUNNING'
    threading.Thread(target=manager.submit_captcha, args=(message.text,)).start()

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
