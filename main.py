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
# Token Bot Telegram của bạn
API_TOKEN = '8725772455:AAGVE5UM0qtlES1TWSygwz7flhaaLLbwqlI'

# Token Browserless (Đã thêm .strip() để tránh lỗi khoảng trắng)
BROWSERLESS_TOKEN = '2UADbr9XrUudNGMb8545fc3940547b391a950eefd007e04ad'.strip()

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# DANH SÁCH PROXY WEBSHARE (IP:Port:User:Pass)
WEBSHARE = [
    "31.59.20.176:6754:jhxqqqco:39lpkdhlbvzn", "23.95.150.145:6114:jhxqqqco:39lpkdhlbvzn",
    "198.23.239.134:6540:jhxqqqco:39lpkdhlbvzn", "45.38.107.97:6014:jhxqqqco:39lpkdhlbvzn",
    "107.172.163.27:6543:jhxqqqco:39lpkdhlbvzn", "198.105.121.200:6462:jhxqqqco:39lpkdhlbvzn",
    "64.137.96.74:6641:jhxqqqco:39lpkdhlbvzn", "216.10.27.159:6837:jhxqqqco:39lpkdhlbvzn",
    "142.111.67.146:5611:jhxqqqco:39lpkdhlbvzn", "191.96.254.138:6185:jhxqqqco:39lpkdhlbvzn"
]

user_sessions = {}

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

class ZefoyManagerRemote:
    def __init__(self, chat_id, video_url, service_id):
        self.chat_id = chat_id
        self.video_url = video_url
        self.service_id = service_id
        self.driver = None
        self.success_count = 0
        self.total_stats = 0
        # Thông số dịch vụ từ bản gốc
        self.services = {
            "2": {"name": "Hearts", "button": "t-hearts-button", "inc": 30},
            "3": {"name": "Comments Hearts", "button": "t-chearts-button", "inc": 10},
            "4": {"name": "Views", "button": "t-views-button", "inc": 500},
            "5": {"name": "Shares", "button": "t-shares-button", "inc": 150},
            "6": {"name": "Favorites", "button": "t-favorites-button", "inc": 90}
        }

    def create_driver(self):
        # Chọn proxy ngẫu nhiên
        p_str = random.choice(WEBSHARE)
        ip, port, user, pwd = p_str.split(':')
        
        chrome_options = Options()
        
        # --- KHẮC PHỤC LỖI INVALID API KEY ---
        # 1. Đưa Token vào Browserless Options (Xác thực nội bộ)
        browserless_config = {
            "token": BROWSERLESS_TOKEN,
            "stealth": True,
            "headless": True,
            "proxy": f"http://{user}:{pwd}@{ip}:{port}"
        }
        chrome_options.set_capability("browserless:options", browserless_config)
        
        # 2. Các tham số Chrome tiêu chuẩn
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")

        # 3. URL kết nối (Xác thực qua URL)
        remote_url = f"https://chrome.browserless.io/webdriver?token={BROWSERLESS_TOKEN}"
        
        try:
            self.driver = webdriver.Remote(
                command_executor=remote_url,
                options=chrome_options
            )
            self.wait = WebDriverWait(self.driver, 45)
        except Exception as e:
            bot.send_message(self.chat_id, f"❌ Lỗi kết nối Cloud: `{str(e)[:100]}`")
            raise e

    def handle_alert(self):
        try: self.driver.switch_to.alert.dismiss()
        except: pass

    def send_tg(self, text):
        bot.send_message(self.chat_id, text, parse_mode="Markdown")

    def start_bot(self):
        try:
            self.send_tg("🌐 Đang kết nối trình duyệt Cloud (0% RAM Usage)...")
            self.create_driver()
            self.driver.get("https://zefoy.com")
            
            # Đợi qua màn hình bảo trì/load trang
            time.sleep(15)
            self.handle_alert()

            # Chụp ảnh Captcha
            captcha_img = self.wait.until(EC.presence_of_element_located((By.XPATH, "//img")))
            captcha_img.screenshot("captcha.png")
            
            with open("captcha.png", "rb") as photo:
                bot.send_photo(self.chat_id, photo, caption="📸 **Mời bạn nhập mã Captcha để bắt đầu:**")
            
            user_sessions[self.chat_id]['status'] = 'WAITING_CAPTCHA'
            user_sessions[self.chat_id]['manager'] = self
            
        except Exception as e:
            if self.driver: self.driver.quit()

    def submit_captcha(self, code):
        try:
            self.handle_alert()
            inp = self.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']")
            inp.send_keys(code)
            self.driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
            time.sleep(7)
            
            # Kiểm tra xem login thành công chưa bằng cách tìm nút service
            svc = self.services[self.service_id]
            self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, svc["button"]))).click()
            
            self.send_tg(f"✅ Đăng nhập thành công! Bắt đầu chạy dịch vụ: **{svc['name']}**")
            self.loop_process()
        except:
            self.send_tg("❌ Sai mã Captcha hoặc Proxy bị lag. Vui lòng gõ /start để thử lại.")
            if self.driver: self.driver.quit()

    def loop_process(self):
        svc = self.services[self.service_id]
        while True:
            try:
                self.handle_alert()
                # Nhập link video
                inp = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Video URL']")))
                inp.clear()
                inp.send_keys(self.video_url)
                
                # Nút Search
                self.driver.find_element(By.XPATH, "//button[contains(text(),'Search')]").click()
                time.sleep(8)
                
                # Kiểm tra Cooldown/Timer
                source = self.driver.page_source
                if "Please wait" in source:
                    wait_find = re.search(r"Please wait (\d+) minutes (\d+) seconds", source)
                    msg = "⏳ Hệ thống đang trong thời gian chờ..."
                    if wait_find: 
                        msg = f"⏳ Cooldown: {wait_find.group(1)} phút {wait_find.group(2)} giây."
                    self.send_tg(msg)
                    time.sleep(75)
                    self.driver.refresh()
                    continue

                # Nhấn nút thực hiện Buff (nút hiển thị số lượng hiện tại)
                buff_btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-primary')] | //button[contains(@class, 'wbutton')]")
                for btn in buff_btns:
                    if btn.is_displayed():
                        btn.click()
                        self.success_count += 1
                        self.total_stats += svc['inc']
                        
                        # Gửi báo cáo thành công về Telegram
                        report = f"✨ **THÀNH CÔNG** ✨\n"
                        report += f"🔥 Buff lần thứ: {self.success_count}\n"
                        report += f"📊 Tổng cộng: +{self.total_stats} {svc['name']}\n"
                        report += f"⏰ Thời gian: {get_current_time()}"
                        self.send_tg(report)
                        break
                
                # Nghỉ 3 phút theo cơ chế Zefoy
                time.sleep(185)
                self.driver.refresh()
                
            except Exception:
                time.sleep(20)
                try: self.driver.refresh()
                except: break

# --- XỬ LÝ LỆNH TELEGRAM ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    banner = f"🤖 **ZEFOY REMOTE CLOUD v3.1**\n"
    banner += f"🚀 Trạng thái: **Online**\n"
    banner += f"💎 Tài nguyên: **Browserless Cloud**\n\n"
    banner += "👉 Hãy gửi Link video TikTok để bắt đầu."
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
    bot.send_message(message.chat.id, "✨ Chọn loại dịch vụ muốn buff:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("svc_"))
def handle_callback(call):
    chat_id = call.message.chat.id
    svc_id = call.data.replace("svc_", "")
    url = user_sessions[chat_id]['url']
    
    manager = ZefoyManagerRemote(chat_id, url, svc_id)
    threading.Thread(target=manager.start_bot).start()
    bot.answer_callback_query(call.id, "Đang mở trình duyệt Cloud...")

@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get('status') == 'WAITING_CAPTCHA')
def handle_captcha_text(message):
    chat_id = message.chat.id
    if chat_id in user_sessions and 'manager' in user_sessions[chat_id]:
        manager = user_sessions[chat_id]['manager']
        user_sessions[chat_id]['status'] = 'RUNNING'
        threading.Thread(target=manager.submit_captcha, args=(message.text,)).start()

# --- WEB SERVER GIỮ CHỖ (CHO RENDER) ---
@app.route('/')
def home():
    return "Zefoy Remote Cloud Bot is Active!"

if __name__ == '__main__':
    # Chạy Flask ở luồng phụ port 10000
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    print("Bot is polling...")
    bot.infinity_polling()
