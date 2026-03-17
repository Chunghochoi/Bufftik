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
API_TOKEN = '8725772455:AAGVE5UM0qtlES1TWSygwz7flhaaLLbwqlI'
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

user_sessions = {}

@app.route('/')
def home():
    return "Zefoy Bot Stealth is Running!"

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
        self.driver = None

    def create_driver(self):
        options = uc.ChromeOptions()
        # Chế độ headless mới khó bị phát hiện hơn
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # --- CẤU HÌNH GIẢ LẬP NGƯỜI DÙNG THẬT (SOLUTION 1) ---
        # 1. Sử dụng User-Agent của trình duyệt Chrome thật trên Windows
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        
        # 2. Tắt các tính năng tự động hóa bị Cloudflare soi
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--start-maximized')
        
        # 3. Tối ưu RAM cho Render
        options.add_argument('--disable-extensions')
        options.add_argument('--memory-pressure-off')

        # Khởi tạo driver với use_subprocess=True để lách tốt hơn
        self.driver = uc.Chrome(options=options, use_subprocess=True)
        self.wait = WebDriverWait(self.driver, 30)

        # 4. Xóa dấu vết WebDriver bằng Javascript (Script thực tế dev hay dùng)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def start_process(self):
        try:
            bot.send_message(self.chat_id, "🌐 Đang khởi tạo trình duyệt ẩn danh...")
            self.create_driver()
            
            # Truy cập trang web
            bot.send_message(self.chat_id, "🔗 Đang truy cập Zefoy (vượt Cloudflare)...")
            self.driver.get("https://zefoy.com")
            
            # Đợi lâu hơn một chút để trang load hoàn toàn các thành phần bảo mật
            time.sleep(15) 
            
            try:
                # Chụp ảnh toàn màn hình để kiểm tra nếu cần (debug)
                # self.driver.save_screenshot("debug.png")
                
                # Tìm ảnh captcha - Thử nhiều cách tìm khác nhau
                captcha_img = self.wait.until(EC.presence_of_element_located((By.XPATH, "//img[contains(@class, 'img-thumbnail')] | //img")))
                captcha_img.screenshot("captcha.png")
                
                with open("captcha.png", "rb") as photo:
                    bot.send_photo(self.chat_id, photo, caption="📸 Đã vượt tường lửa! Nhập mã Captcha:")
                
                user_sessions[self.chat_id]['status'] = 'WAITING_CAPTCHA'
                user_sessions[self.chat_id]['manager'] = self
                
            except Exception as e:
                # Nếu không thấy captcha, có thể trang web đang hiện Cloudflare Turnstile hoặc Access Denied
                page_source = self.driver.page_source
                if "Access denied" in page_source or "Cloudflare" in page_source:
                    bot.send_message(self.chat_id, "❌ Zefoy đã chặn IP của Server Render này hoàn toàn. Giải pháp 1 không đủ lực, bạn cần dùng Proxy dân cư.")
                else:
                    bot.send_message(self.chat_id, f"❌ Lỗi không xác định khi tìm Captcha: {str(e)[:100]}")
                self.driver.quit()

        except Exception as e:
            bot.send_message(self.chat_id, f"💥 Lỗi hệ thống: {str(e)}")
            if self.driver: self.driver.quit()

    def submit_captcha(self, code):
        try:
            # Điền captcha
            input_box = self.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']")
            input_box.send_keys(code)
            
            # Click Submit
            submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(),'Submit')] | //div[@class='input-group-append']//button")
            submit_btn.click()
            time.sleep(7)
            
            # Click vào service đã chọn
            service_btn_class = self.services.get(self.service_id)
            btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, service_btn_class)))
            btn.click()
            
            bot.send_message(self.chat_id, "✅ Đăng nhập thành công! Đang chạy buff...")
            self.loop_service()
            
        except Exception as e:
            bot.send_message(self.chat_id, "❌ Sai captcha hoặc Zefoy không phản hồi. Gõ /start để thử lại.")
            self.driver.quit()

    def loop_service(self):
        while True:
            try:
                # Tìm ô nhập link
                form = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Video URL']")))
                form.clear()
                form.send_keys(self.video_url)
                
                # Tìm nút Search cạnh ô nhập link
                search_btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'btn-search')] | //form//button")
                search_btn.click()
                time.sleep(6)
                
                page_source = self.driver.page_source
                
                # Kiểm tra Cooldown
                if "Please wait" in page_source:
                    time_find = re.search(r"Please wait (\d+) minutes (\d+) seconds", page_source)
                    msg = "⏳ Đang đợi hồi phục (cooldown)..."
                    if time_find:
                        msg = f"⏳ Còn {time_find.group(1)} phút {time_find.group(2)} giây."
                    bot.send_message(self.chat_id, msg)
                    time.sleep(70) 
                    self.driver.refresh()
                    continue

                # Nhấn nút thực hiện (Buff)
                # Tìm nút có chứa số lượng (thường là con số lượt view hiện tại)
                buff_btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-primary')] | //button[contains(@class, 'wbutton')]")
                clicked = False
                for b in buff_btns:
                    if b.is_displayed():
                        b.click()
                        bot.send_message(self.chat_id, "🚀 Buff thành công một lần! Đang đợi vòng tiếp theo...")
                        clicked = True
                        break
                
                if not clicked:
                    self.driver.refresh()
                    time.sleep(10)
                else:
                    time.sleep(180) # Nghỉ 3 phút giữa mỗi lần buff
                    self.driver.refresh()
                
            except Exception as e:
                bot.send_message(self.chat_id, "⚠️ Mạng lag hoặc lỗi nhẹ, đang tự động tải lại...")
                self.driver.refresh()
                time.sleep(10)

# --- TELEGRAM COMMANDS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "🤖 **Zefoy Stealth Bot**\n\nGửi Link TikTok để bắt đầu. Bot này đã bật chế độ lách Cloudflare.")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def handle_link(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {'url': message.text, 'status': 'SELECT_SERVICE'}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👁️ Views", callback_data="4"),
               types.InlineKeyboardButton("❤️ Hearts", callback_data="2"))
    markup.add(types.InlineKeyboardButton("↪️ Shares", callback_data="5"),
               types.InlineKeyboardButton("⭐ Favorites", callback_data="6"))
    
    bot.send_message(chat_id, "Chọn dịch vụ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    if chat_id in user_sessions:
        service_id = call.data
        url = user_sessions[chat_id]['url']
        manager = ZefoyManager(chat_id, url, service_id)
        threading.Thread(target=manager.start_process).start()
        bot.answer_callback_query(call.id, "Đang khởi động...")

@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get('status') == 'WAITING_CAPTCHA')
def handle_captcha(message):
    chat_id = message.chat.id
    code = message.text
    if 'manager' in user_sessions[chat_id]:
        manager = user_sessions[chat_id]['manager']
        user_sessions[chat_id]['status'] = 'RUNNING'
        threading.Thread(target=manager.submit_captcha, args=(code,)).start()

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling()
