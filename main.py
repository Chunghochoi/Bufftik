import os
import time
import threading
import telebot
from telebot import types
from flask import Flask
import re
import requests
import random
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# --- CẤU HÌNH ---
API_TOKEN = '8725772455:AAGVE5UM0qtlES1TWSygwz7flhaaLLbwqlI'
# API Browserless của bạn
BROWSERLESS_TOKEN = '2UADbr9XrUudNGMb8545fc3940547b391a950eefd007e04ad' 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- DANH SÁCH PROXY (Khôi phục từ bản trước) ---
WEBSHARE = [
    "31.59.20.176:6754:jhxqqqco:39lpkdhlbvzn", "23.95.150.145:6114:jhxqqqco:39lpkdhlbvzn",
    "198.23.239.134:6540:jhxqqqco:39lpkdhlbvzn", "45.38.107.97:6014:jhxqqqco:39lpkdhlbvzn"
]

user_sessions = {}

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

class ZefoyBotRemote:
    def __init__(self, chat_id, video_url, service_id):
        self.chat_id = chat_id
        self.video_url = video_url
        self.service_id = service_id
        self.success_count = 0
        self.total_added = 0
        self.driver = None
        
        # Khôi phục danh sách dịch vụ từ bản gốc
        self.services = {
            "2": {"name": "Hearts", "button": "t-hearts-button", "increment": 30},
            "3": {"name": "Comments Hearts", "button": "t-chearts-button", "increment": 10},
            "4": {"name": "Views", "button": "t-views-button", "increment": 500},
            "5": {"name": "Shares", "button": "t-shares-button", "increment": 150},
            "6": {"name": "Favorites", "button": "t-favorites-button", "increment": 90}
        }

    def create_driver(self):
        chrome_options = Options()
        # Chạy Proxy qua Browserless nếu cần (Webshare)
        proxy_str = random.choice(WEBSHARE)
        ip, port, user, pwd = proxy_str.split(':')
        
        # Cấu hình Remote WebDriver kết nối tới Browserless
        remote_url = f"https://chrome.browserless.io/webdriver?token={BROWSERLESS_TOKEN}"
        
        capabilities = {
            "browserName": "chrome",
            "goog:chromeOptions": {
                "args": [
                    "--no-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-notifications",
                    "--disable-popup-blocking"
                ]
            },
            "browserless:options": {
                "stealth": True,
                "headless": True,
                "proxy": f"http://{user}:{pwd}@{ip}:{port}" # Tích hợp thẳng proxy vào cloud
            }
        }

        self.driver = webdriver.Remote(
            command_executor=remote_url,
            options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 40)

    def send_tg(self, text):
        bot.send_message(self.chat_id, text, parse_mode="Markdown")

    def handle_alert(self):
        try: self.driver.switch_to.alert.dismiss()
        except: pass

    def wait_for_ad(self):
        self.send_tg("⏳ Đang lách quảng cáo Zefoy (30s)...")
        time.sleep(30)
        try:
            # Logic lách quảng cáo từ file gốc
            ad_btn = self.driver.find_element(By.CLASS_NAME, "fc-rewarded-ad-button")
            if ad_btn:
                ad_btn.click()
                time.sleep(10)
                self.driver.refresh()
                time.sleep(10)
        except:
            pass

    def start(self):
        try:
            self.send_tg("🌐 Đang khởi tạo trình duyệt Cloud (RAM Usage: 0%)...")
            self.create_driver()
            self.driver.get("https://zefoy.com")
            
            self.wait_for_ad()
            self.handle_alert()

            # Chụp captcha gửi về Telegram
            captcha_img = self.wait.until(EC.presence_of_element_located((By.XPATH, "//img")))
            captcha_img.screenshot("captcha.png")
            
            with open("captcha.png", "rb") as photo:
                bot.send_photo(self.chat_id, photo, caption="🔑 **Nhập mã Captcha để bắt đầu:**")
            
            user_sessions[self.chat_id]['status'] = 'WAITING_CAPTCHA'
            user_sessions[self.chat_id]['manager'] = self
            
        except Exception as e:
            self.send_tg(f"❌ Lỗi khởi tạo: `{str(e)[:100]}`")
            if self.driver: self.driver.quit()

    def solve_and_run(self, captcha_text):
        try:
            self.handle_alert()
            # Điền captcha
            self.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']").send_keys(captcha_text)
            self.driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
            time.sleep(5)
            
            # Chọn dịch vụ đã lưu
            service = self.services[self.service_id]
            self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, service["button"]))).click()
            
            self.send_tg(f"✅ Đăng nhập thành công! Bắt đầu buff **{service['name']}**...")
            self.loop_process()
        except Exception as e:
            self.send_tg(f"❌ Lỗi đăng nhập: Captcha sai hoặc Zefoy lag.")
            self.driver.quit()

    def loop_process(self):
        service = self.services[self.service_id]
        while True:
            try:
                self.handle_alert()
                # Gửi link
                inp = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Video URL']")))
                inp.clear()
                inp.send_keys(self.video_url)
                
                self.driver.find_element(By.XPATH, "//button[contains(text(),'Search')]").click()
                time.sleep(8)
                
                source = self.driver.page_source
                if "Please wait" in source:
                    wait_match = re.search(r"Please wait (\d+) minutes (\d+) seconds", source)
                    msg = "⏳ Đang cooldown..."
                    if wait_match: msg = f"⏳ Đợi: {wait_match.group(1)}p {wait_match.group(2)}s."
                    self.send_tg(msg)
                    time.sleep(75)
                    self.driver.refresh()
                    continue

                # Nhấn nút buff cuối cùng
                final_btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-primary')] | //button[contains(@class, 'wbutton')]")
                for btn in final_btns:
                    if btn.is_displayed():
                        btn.click()
                        self.success_count += 1
                        self.total_added += service['increment']
                        
                        success_msg = f"✨ **THÀNH CÔNG** ✨\n"
                        success_msg += f"🔥 Lượt buff: {self.success_count}\n"
                        success_msg += f"📊 Tổng cộng: +{self.total_added} {service['name']}"
                        self.send_tg(success_msg)
                        break
                
                time.sleep(180) # Nghỉ 3 phút
                self.driver.refresh()
            except Exception:
                time.sleep(20)
                self.driver.refresh()

# --- TELEGRAM INTERFACE ---

@bot.message_handler(commands=['start'])
def welcome(message):
    banner = f"🤖 **ZEFOY CLOUD BOT V3.0**\n"
    banner += f"⏰ {get_current_time()}\n"
    banner += f"🚀 Chế độ: **Remote Browser (Browserless)**\n"
    banner += f"💎 RAM Render tiêu thụ: **~40MB**\n\n"
    banner += "👉 Hãy gửi Link video TikTok của bạn."
    bot.reply_to(message, banner, parse_mode="Markdown")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def handle_link(message):
    user_sessions[message.chat.id] = {'url': message.text}
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👁 Views", callback_data="svc_4"),
        types.InlineKeyboardButton("❤️ Hearts", callback_data="svc_2"),
        types.InlineKeyboardButton("💬 Comm. Hearts", callback_data="svc_3"),
        types.InlineKeyboardButton("↪️ Shares", callback_data="svc_5"),
        types.InlineKeyboardButton("⭐ Favorites", callback_data="svc_6")
    )
    bot.send_message(message.chat.id, "✨ Chọn dịch vụ bạn muốn buff:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("svc_"))
def handle_service(call):
    chat_id = call.message.chat.id
    service_id = call.data.replace("svc_", "")
    url = user_sessions[chat_id]['url']
    
    manager = ZefoyBotRemote(chat_id, url, service_id)
    threading.Thread(target=manager.start).start()
    bot.answer_callback_query(call.id, "Đang kết nối tới trình duyệt Cloud...")

@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get('status') == 'WAITING_CAPTCHA')
def handle_captcha_input(message):
    chat_id = message.chat.id
    manager = user_sessions[chat_id]['manager']
    user_sessions[chat_id]['status'] = 'RUNNING'
    threading.Thread(target=manager.solve_and_run, args=(message.text,)).start()

# --- WEB SERVER GIỮ CHỖ ---
@app.route('/')
def home():
    return "Bot is running on Cloud Browserless!"

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    print("Zefoy Bot is Online...")
    bot.infinity_polling()
