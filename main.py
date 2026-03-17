import os
import time
import threading
import telebot
from telebot import types
from flask import Flask
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome
import re

# --- CẤU HÌNH ---
API_TOKEN = '8725772455:AAGVE5UM0qtlES1TWSygwz7flhaaLLbwqlI'
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Lưu trạng thái người dùng
user_sessions = {}

@app.route('/')
def home():
    return "Zefoy Bot is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

class ZefoyManager:
    def __init__(self, chat_id, video_url, service_id):
        self.chat_id = chat_id
        self.video_url = video_url
        self.service_id = service_id
        self.services = {
            "2": "t-hearts-button",
            "3": "t-chearts-button",
            "4": "t-views-button",
            "5": "t-shares-button",
            "6": "t-favorites-button"
        }
        
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)

    def start_process(self):
        try:
            bot.send_message(self.chat_id, "🌐 Đang truy cập Zefoy...")
            self.driver.get("https://zefoy.com")
            
            # Chụp captcha
            time.sleep(5)
            captcha_img = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
            captcha_img.screenshot("captcha.png")
            
            with open("captcha.png", "rb") as photo:
                bot.send_photo(self.chat_id, photo, caption="📸 Nhập mã Captcha để tiếp tục:")
            
            user_sessions[self.chat_id]['status'] = 'WAITING_CAPTCHA'
            user_sessions[self.chat_id]['manager'] = self
            
        except Exception as e:
            bot.send_message(self.chat_id, f"❌ Lỗi khởi tạo: {str(e)}")
            self.driver.quit()

    def submit_captcha(self, code):
        try:
            input_box = self.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']")
            input_box.send_keys(code)
            self.driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
            time.sleep(5)
            
            # Click vào service đã chọn
            service_btn_class = self.services.get(self.service_id)
            btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, service_btn_class)))
            btn.click()
            
            bot.send_message(self.chat_id, "✅ Captcha đúng! Bắt đầu chạy tăng tương tác...")
            self.loop_service()
            
        except Exception as e:
            bot.send_message(self.chat_id, "❌ Captcha sai hoặc lỗi. Thử lại /start")
            self.driver.quit()

    def loop_service(self):
        while True:
            try:
                # Tìm ô nhập link
                form = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Video URL']")))
                form.clear()
                form.send_keys(self.video_url)
                
                search_btn = self.driver.find_element(By.XPATH, "//button[contains(text(),'Search')]")
                search_btn.click()
                time.sleep(5)
                
                # Kiểm tra có phải đợi không
                page_text = self.driver.page_source
                if "Please wait" in page_text:
                    timer_match = re.search(r"Please wait (\d+) minutes (\d+) seconds", page_text)
                    wait_msg = "⏳ Đang trong thời gian chờ (cooldown)..."
                    if timer_match:
                        wait_msg = f"⏳ Đợi {timer_match.group(1)} phút {timer_match.group(2)} giây nữa."
                    bot.send_message(self.chat_id, wait_msg)
                    time.sleep(60)
                    self.driver.refresh()
                    continue

                # Nhấn nút thực hiện (Submit/Send)
                # Zefoy thường hiện số lượng hiện tại, nhấn vào đó để buff
                submit_btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'btn-primary')]")
                submit_btn.click()
                
                bot.send_message(self.chat_id, "🚀 Đã gửi yêu cầu thành công! Đợi vòng tiếp theo...")
                time.sleep(120) # Nghỉ 2 phút
                self.driver.refresh()
                
            except Exception as e:
                bot.send_message(self.chat_id, "⚠️ Đang tải lại trang...")
                self.driver.get("https://zefoy.com")
                time.sleep(5)

# --- TELEGRAM HANDLERS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "Chào bạn! Hãy gửi Link TikTok (từng cái một) để bắt đầu.")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def get_link(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {'url': message.text, 'status': 'SELECT_SERVICE'}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Views", callback_data="4"),
               types.InlineKeyboardButton("Hearts", callback_data="2"))
    markup.add(types.InlineKeyboardButton("Shares", callback_data="5"),
               types.InlineKeyboardButton("Favorites", callback_data="6"))
    
    bot.send_message(chat_id, "Chọn dịch vụ muốn chạy:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    if chat_id in user_sessions:
        service_id = call.data
        url = user_sessions[chat_id]['url']
        
        manager = ZefoyManager(chat_id, url, service_id)
        threading.Thread(target=manager.start_process).start()
        bot.answer_callback_query(call.id, "Đang khởi động trình duyệt...")

@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get('status') == 'WAITING_CAPTCHA')
def handle_captcha(message):
    chat_id = message.chat.id
    code = message.text
    manager = user_sessions[chat_id]['manager']
    user_sessions[chat_id]['status'] = 'RUNNING'
    threading.Thread(target=manager.submit_captcha, args=(code,)).start()

if __name__ == '__main__':
    # Chạy Flask để Render không die
    threading.Thread(target=run_flask).start()
    print("Bot is starting...")
    bot.infinity_polling()
