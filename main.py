import os
import time
import threading
import telebot
from telebot import types
from flask import Flask
import re

# Thư viện Selenium và undetected_chromedriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# --- CẤU HÌNH ---
API_TOKEN = '8725772455:AAGVE5UM0qtlES1TWSygwz7flhaaLLbwqlI' # Thay Token mới nếu cần
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Lưu trạng thái phiên làm việc của người dùng
user_sessions = {}

# --- WEB SERVER GIỮ CHỖ CHO RENDER ---
@app.route('/')
def home():
    return "Zefoy Bot is Running 24/7!"

def run_flask():
    # Render yêu cầu port 10000
    app.run(host='0.0.0.0', port=10000)

# --- LỚP ĐIỀU KHIỂN ZEFOY ---
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
        self.driver = None

    def create_driver(self):
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        # Tối ưu RAM cực thấp cho Render
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-application-cache')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-dev-tools')
        
        # Khởi tạo driver
        self.driver = uc.Chrome(options=options, use_subprocess=True)
        self.wait = WebDriverWait(self.driver, 25)

    def start_process(self):
        try:
            bot.send_message(self.chat_id, "🌐 Đang khởi động trình duyệt và truy cập Zefoy...")
            self.create_driver()
            self.driver.get("https://zefoy.com")
            
            # Đợi và chụp ảnh captcha
            time.sleep(8) 
            try:
                # Tìm ảnh captcha
                captcha_img = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
                captcha_img.screenshot("captcha.png")
                
                with open("captcha.png", "rb") as photo:
                    bot.send_photo(self.chat_id, photo, caption="📸 Hãy nhập các chữ cái bạn thấy trong ảnh:")
                
                user_sessions[self.chat_id]['status'] = 'WAITING_CAPTCHA'
                user_sessions[self.chat_id]['manager'] = self
                
            except Exception as e:
                bot.send_message(self.chat_id, "❌ Không tìm thấy ảnh Captcha. Có thể Zefoy đã chặn IP của Server.")
                self.driver.quit()

        except Exception as e:
            bot.send_message(self.chat_id, f"❌ Lỗi: {str(e)}")
            if self.driver: self.driver.quit()

    def submit_captcha(self, code):
        try:
            input_box = self.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']")
            input_box.send_keys(code)
            self.driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]").click()
            time.sleep(5)
            
            # Kiểm tra xem captcha đúng chưa bằng cách tìm nút service
            service_btn_class = self.services.get(self.service_id)
            btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, service_btn_class)))
            btn.click()
            
            bot.send_message(self.chat_id, "✅ Captcha chính xác! Bắt đầu chạy tăng tương tác...")
            self.loop_service()
            
        except Exception as e:
            bot.send_message(self.chat_id, "❌ Captcha sai hoặc không thể chọn dịch vụ. Vui lòng thử lại với /start")
            self.driver.quit()

    def loop_service(self):
        while True:
            try:
                # Nhập link video
                form = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Video URL']")))
                form.clear()
                form.send_keys(self.video_url)
                
                search_btn = self.driver.find_element(By.XPATH, "//button[contains(text(),'Search')]")
                search_btn.click()
                time.sleep(5)
                
                # Kiểm tra xem có đang bị giới hạn thời gian (Timer) không
                page_source = self.driver.page_source
                if "Please wait" in page_source:
                    wait_time = re.search(r"Please wait (\d+) minutes (\d+) seconds", page_source)
                    if wait_time:
                        msg = f"⏳ Đang đợi: {wait_time.group(1)} phút {wait_time.group(2)} giây..."
                    else:
                        msg = "⏳ Hệ thống đang trong thời gian chờ (Cooldown)..."
                    bot.send_message(self.chat_id, msg)
                    time.sleep(60) # Nghỉ 1 phút rồi check lại
                    self.driver.refresh()
                    continue

                # Nhấn nút thực hiện cuối cùng (thường là nút hiển thị con số)
                # Zefoy thay đổi cấu trúc nút này liên tục, nên ta tìm nút có màu xanh (btn-primary)
                final_btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-primary')]")
                for f_btn in final_btns:
                    if f_btn.is_displayed():
                        f_btn.click()
                        bot.send_message(self.chat_id, "🚀 Đã gửi yêu cầu thành công!")
                        break
                
                time.sleep(150) # Nghỉ 2.5 phút trước vòng lặp mới
                self.driver.refresh()
                
            except Exception as e:
                print(f"Lỗi vòng lặp: {e}")
                bot.send_message(self.chat_id, "⚠️ Có lỗi xảy ra trong vòng lặp, đang thử lại...")
                self.driver.refresh()
                time.sleep(10)

# --- XỬ LÝ LỆNH TỪ TELEGRAM ---

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "🌟 Chào mừng bạn đến với Zefoy Bot!\nHãy gửi **Link TikTok** video bạn muốn tăng tương tác.")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def handle_link(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {'url': message.text, 'status': 'SELECT_SERVICE'}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👁️ Views", callback_data="4"),
               types.InlineKeyboardButton("❤️ Hearts", callback_data="2"))
    markup.add(types.InlineKeyboardButton("↪️ Shares", callback_data="5"),
               types.InlineKeyboardButton("⭐ Favorites", callback_data="6"))
    
    bot.send_message(chat_id, "Vui lòng chọn loại dịch vụ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    if chat_id in user_sessions:
        service_id = call.data
        url = user_sessions[chat_id]['url']
        
        manager = ZefoyManager(chat_id, url, service_id)
        # Chạy Selenium trong một luồng riêng để không làm treo Bot Telegram
        threading.Thread(target=manager.start_process).start()
        bot.answer_callback_query(call.id, "Đang khởi động tiến trình...")

@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get('status') == 'WAITING_CAPTCHA')
def handle_captcha(message):
    chat_id = message.chat.id
    code = message.text
    if 'manager' in user_sessions[chat_id]:
        manager = user_sessions[chat_id]['manager']
        user_sessions[chat_id]['status'] = 'RUNNING'
        threading.Thread(target=manager.submit_captcha, args=(code,)).start()

# --- CHẠY CHƯƠNG TRÌNH ---
if __name__ == '__main__':
    # 1. Chạy Flask ở luồng phụ (port 10000)
    threading.Thread(target=run_flask, daemon=True).start()
    
    # 2. Báo cho console biết bot đang sống
    print("---------------------------------------")
    print("ZEFOY BOT TELEGRAM IS RUNNING")
    print("---------------------------------------")
    
    # 3. Chạy Telegram Bot chính
    bot.infinity_polling()
