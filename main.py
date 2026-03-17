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

# ================= CONFIGURATION =================
API_TOKEN = '8725772455:AAGVE5UM0qtlES1TWSygwz7flhaaLLbwqlI'
BROWSERLESS_TOKEN = '2UADbr9XrUudNGMb8545fc3940547b391a950eefd007e04ad'

# Danh sách Proxy Webshare (Xoay vòng tự động)
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

# ================= UTILS =================
def get_now():
    return datetime.now(timezone.utc).strftime("%H:%M:%S")

def get_render_ip():
    try: return requests.get('https://api.ipify.org', timeout=5).text
    except: return "Unknown"

@app.route('/')
def health_check():
    return f"Bot is Active. IP: {get_render_ip()}"

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
        # Chọn Proxy ngẫu nhiên
        p_raw = random.choice(PROXIES)
        host, port, user, pwd = p_raw.split(':')
        
        chrome_options = Options()
        # Cấu hình Browserless Cloud (Xác thực 2 lớp để tránh lỗi API Key)
        bl_config = {
            "token": BROWSERLESS_TOKEN.strip(),
            "stealth": True,
            "headless": True,
            "proxy": f"http://{user}:{pwd}@{host}:{port}",
            "blockAds": True
        }
        chrome_options.set_capability("browserless:options", bl_config)
        
        # Args tiêu chuẩn
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--window-size=1280,720")

        remote_url = f"https://chrome.browserless.io/webdriver?token={BROWSERLESS_TOKEN.strip()}"
        
        self.driver = webdriver.Remote(command_executor=remote_url, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 40)

    def anti_alert(self):
        try: self.driver.switch_to.alert.dismiss()
        except: pass

    def launch(self):
        try:
            self.msg("🛰️ **Khởi tạo trình duyệt Cloud...**\n(RAM Render: 0%)")
            self.build_driver()
            self.driver.get("https://zefoy.com")
            
            # Đợi load và dọn dẹp popup
            time.sleep(12)
            self.anti_alert()

            # Lấy Captcha
            captcha_el = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
            captcha_el.screenshot("captcha.png")
            
            with open("captcha.png", "rb") as photo:
                bot.send_photo(self.chat_id, photo, caption="🔑 **Vui lòng nhập mã Captcha:**")
            
            user_data[self.chat_id]['state'] = 'CAPTCHA'
            user_data[self.chat_id]['engine'] = self
            
        except Exception as e:
            self.msg(f"💥 **Lỗi:** `{str(e)[:100]}`")
            if self.driver: self.driver.quit()

    def process_captcha(self, code):
        try:
            self.anti_alert()
            inp = self.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']")
            inp.send_keys(code)
            self.driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
            time.sleep(6)
            
            # Click service
            svc_info = SERVICES[self.svc_id]
            self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, svc_info['btn']))).click()
            
            self.msg(f"✅ **Đăng nhập thành công!**\nBắt đầu buff: `{svc_info['name']}`")
            self.main_loop()
        except:
            self.msg("❌ **Captcha sai hoặc Proxy lag.** Vui lòng nhấn /start để làm lại.")
            if self.driver: self.driver.quit()

    def main_loop(self):
        svc = SERVICES[self.svc_id]
        while True:
            try:
                self.anti_alert()
                # Submit link video
                inp = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Video URL']")))
                inp.clear()
                inp.send_keys(self.url)
                
                self.driver.find_element(By.XPATH, "//button[contains(text(),'Search')]").click()
                time.sleep(8)
                
                # Xử lý Cooldown
                source = self.driver.page_source
                if "Please wait" in source:
                    wait_find = re.search(r"Please wait (\d+) minutes (\d+) seconds", source)
                    msg = "⏳ **Đang trong thời gian chờ...**"
                    if wait_find: msg = f"⏳ **Cooldown:** {wait_find.group(1)}p {wait_find.group(2)}s."
                    self.msg(msg)
                    time.sleep(75)
                    self.driver.refresh()
                    continue

                # Nhấn nút thực hiện thành công
                success_btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-primary')] | //button[contains(@class, 'wbutton')]")
                for btn in success_btns:
                    if btn.is_displayed():
                        btn.click()
                        self.count += 1
                        self.stats += svc['add']
                        
                        report = f"🚀 **BUFF THÀNH CÔNG**\n"
                        report += f"📊 Lần thứ: `{self.count}`\n"
                        report += f"🔥 Tổng cộng: `+{self.stats} {svc['name']}`\n"
                        report += f"🕒 Lúc: `{get_now()}`"
                        self.msg(report)
                        break
                
                # Nghỉ 3 phút rưỡi để an toàn
                time.sleep(210)
                self.driver.refresh()
                
            except Exception:
                time.sleep(20)
                try: self.driver.refresh()
                except: break

# ================= TG HANDLERS =================
@bot.message_handler(commands=['start'])
def start(message):
    welcome = f"🤖 **ZEFOY REMOTE BOT v4.0**\n"
    welcome += f"📍 Server IP: `{get_render_ip()}`\n"
    welcome += f"🚀 Mode: `Cloud Browserless`\n\n"
    welcome += "👉 **Gửi Link TikTok để bắt đầu:**"
    bot.reply_to(message, welcome, parse_mode="Markdown")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def handle_link(message):
    user_data[message.chat.id] = {'url': message.text}
    markup = types.InlineKeyboardMarkup(row_width=2)
    for k, v in SERVICES.items():
        markup.add(types.InlineKeyboardButton(v['name'], callback_data=f"svc_{k}"))
    bot.send_message(message.chat.id, "✨ **Chọn loại dịch vụ:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("svc_"))
def handle_svc(call):
    chat_id = call.message.chat.id
    svc_id = call.data.replace("svc_", "")
    url = user_data[chat_id]['url']
    
    engine = ZefoyEngine(chat_id, url, svc_id)
    threading.Thread(target=engine.launch).start()
    bot.answer_callback_query(call.id, "Đang khởi tạo phiên làm việc...")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('state') == 'CAPTCHA')
def handle_captcha(message):
    chat_id = message.chat.id
    engine = user_data[chat_id]['engine']
    user_data[chat_id]['state'] = 'RUNNING'
    threading.Thread(target=engine.process_captcha, args=(message.text,)).start()

# ================= RUN =================
if __name__ == '__main__':
    # Chạy Web Server cho Render (Keep-alive)
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    print("Bot is ready!")
    bot.infinity_polling()
