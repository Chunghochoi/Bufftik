import os
import time
import threading
import telebot
import re
import random
import requests
from flask import Flask
from datetime import datetime, timezone
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ================= CẤU HÌNH =================
API_TOKEN = '8725772455:AAGVE5UM0qtlES1TWSygwz7flhaaLLbwqlI'
# Đảm bảo Token không dính khoảng trắng
BROWSERLESS_TOKEN = '2UADbr9XrUudNGMb8545fc3940547b391a950eefd007e04ad'.strip()

PROXIES = [
    "31.59.20.176:6754:jhxqqqco:39lpkdhlbvzn", "23.95.150.145:6114:jhxqqqco:39lpkdhlbvzn",
    "198.23.239.134:6540:jhxqqqco:39lpkdhlbvzn", "45.38.107.97:6014:jhxqqqco:39lpkdhlbvzn",
    "107.172.163.27:6543:jhxqqqco:39lpkdhlbvzn", "198.105.121.200:6462:jhxqqqco:39lpkdhlbvzn",
    "64.137.96.74:6641:jhxqqqco:39lpkdhlbvzn", "216.10.27.159:6837:jhxqqqco:39lpkdhlbvzn",
    "142.111.67.146:5611:jhxqqqco:39lpkdhlbvzn", "191.96.254.138:6185:jhxqqqco:39lpkdhlbvzn"
]

SERVICES = {
    "2": {"name": "Hearts ❤️", "btn": "t-hearts-button", "add": 25},
    "3": {"name": "Comments Hearts 💬", "btn": "t-chearts-button", "add": 10},
    "4": {"name": "Views 👁️", "btn": "t-views-button", "add": 500},
    "5": {"name": "Shares ↪️", "btn": "t-shares-button", "add": 100},
    "6": {"name": "Favorites ⭐", "btn": "t-favorites-button", "add": 80}
}

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)
user_data = {}

# ================= TIỆN ÍCH =================
def check_api_status():
    """Kiểm tra token bằng REST API theo tài liệu Browserless"""
    url = f"https://chrome.browserless.io/config?token={BROWSERLESS_TOKEN}"
    try:
        res = requests.get(url, timeout=10)
        return res.status_code == 200
    except:
        return False

def get_now():
    return datetime.now(timezone.utc).strftime("%H:%M:%S")

@app.route('/')
def status():
    return f"Bot Active. Browserless Check: {check_api_status()}"

# ================= CORE LOGIC =================
class ZefoyEngine:
    def __init__(self, chat_id, tiktok_url, svc_id):
        self.chat_id = chat_id
        self.url = tiktok_url
        self.svc_id = svc_id
        self.driver = None
        self.stats = 0
        self.count = 0

    def msg(self, text):
        bot.send_message(self.chat_id, text, parse_mode="Markdown")

    def build_driver(self):
        # Kiểm tra API trước khi chạy Selenium
        if not check_api_status():
            raise Exception("Invalid API Key (REST Check Failed). Hãy Verify Email hoặc đổi Token.")

        # Lấy Proxy ngẫu nhiên và định dạng chuẩn Browserless
        p_raw = random.choice(PROXIES)
        host, port, user, pwd = p_raw.split(':')
        proxy_url = f"http://{user}:{pwd}@{host}:{port}"
        
        chrome_options = Options()
        # Cấu hình Vendor Capabilities chuẩn Browserless
        chrome_options.set_capability('browserless:options', {
            'token': BROWSERLESS_TOKEN,
            'stealth': True,
            'proxy': proxy_url,
            'headless': True
        })
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")

        # Endpoint Selenium WebDriver theo tài liệu Browserless
        remote_url = f"https://chrome.browserless.io/webdriver?token={BROWSERLESS_TOKEN}"
        
        self.driver = webdriver.Remote(
            command_executor=remote_url,
            options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 40)

    def anti_alert(self):
        try: self.driver.switch_to.alert.dismiss()
        except: pass

    def launch(self):
        try:
            self.msg("🌐 **Đang khởi tạo trình duyệt Cloud...**")
            self.build_driver()
            
            # Truy cập Zefoy
            self.driver.get("https://zefoy.com")
            time.sleep(15)
            self.anti_alert()

            # Screenshot Captcha
            img = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
            img.screenshot("captcha.png")
            
            with open("captcha.png", "rb") as f:
                bot.send_photo(self.chat_id, f, caption="🔑 **Vui lòng nhập mã Captcha:**")
            
            user_data[self.chat_id]['state'] = 'CAPTCHA'
            user_data[self.chat_id]['engine'] = self
            
        except Exception as e:
            self.msg(f"❌ **Lỗi kết nối:** `{str(e)[:150]}`")
            if self.driver: self.driver.quit()

    def submit(self, code):
        try:
            self.anti_alert()
            self.driver.find_element(By.XPATH, "//input").send_keys(code)
            self.driver.find_element(By.XPATH, "//button").click()
            time.sleep(7)
            
            # Chọn dịch vụ
            svc = SERVICES[self.svc_id]
            self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, svc['btn']))).click()
            
            self.msg(f"✅ **Đã vào thành công!** Đang buff `{svc['name']}`")
            self.loop()
        except:
            self.msg("❌ **Lỗi:** Sai mã hoặc Proxy lag. Hãy gõ /start để thử lại.")
            if self.driver: self.driver.quit()

    def loop(self):
        svc = SERVICES[self.svc_id]
        while True:
            try:
                self.anti_alert()
                inp = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Video URL']")))
                inp.clear()
                inp.send_keys(self.url)
                
                self.driver.find_element(By.XPATH, "//button[contains(text(),'Search')]").click()
                time.sleep(8)
                
                # Xử lý Cooldown
                if "Please wait" in self.driver.page_source:
                    wait_find = re.search(r"Please wait (\d+) minutes (\d+) seconds", self.driver.page_source)
                    txt = f"⏳ **Cooldown:** {wait_find.group(1)}p {wait_find.group(2)}s." if wait_find else "⏳ **Đang đợi...**"
                    self.msg(txt)
                    time.sleep(75)
                    self.driver.refresh()
                    continue

                # Nhấn nút buff
                btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-primary')] | //button[contains(@class, 'wbutton')]")
                for b in btns:
                    if b.is_displayed():
                        b.click()
                        self.count += 1
                        self.stats += svc['add']
                        self.msg(f"🚀 **THÀNH CÔNG**\n📊 Lần: `{self.count}`\n🔥 Tổng: `+{self.stats} {svc['name']}`")
                        break
                
                time.sleep(200)
                self.driver.refresh()
            except:
                time.sleep(20)
                try: self.driver.refresh()
                except: break

# ================= BOT HANDLERS =================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, f"🤖 **ZEFOY CLOUD v5.0**\n📍 IP: `{get_render_ip()}`\n👉 Gửi link TikTok để bắt đầu.")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def link_handler(message):
    user_data[message.chat.id] = {'url': message.text}
    markup = types.InlineKeyboardMarkup()
    for k, v in SERVICES.items():
        markup.add(types.InlineKeyboardButton(v['name'], callback_data=f"svc_{k}"))
    bot.send_message(message.chat.id, "✨ **Chọn dịch vụ:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("svc_"))
def svc_handler(call):
    chat_id = call.message.chat.id
    engine = ZefoyEngine(chat_id, user_data[chat_id]['url'], call.data.replace("svc_", ""))
    threading.Thread(target=engine.launch).start()

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('state') == 'CAPTCHA')
def captcha_handler(message):
    chat_id = message.chat.id
    engine = user_data[chat_id]['engine']
    user_data[chat_id]['state'] = 'RUNNING'
    threading.Thread(target=engine.submit, args=(message.text,)).start()

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
