import time
import threading
import os
import telebot
from datetime import datetime, timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.alert import Alert
from undetected_chromedriver import Chrome
import re

# ĐIỀN TOKEN BOT TELEGRAM CỦA BẠN VÀO ĐÂY
TOKEN = os.getenv("TELEGRAM_TOKEN", "8725772455:AAHZhnwckpbABELRXEpdNwLX7iIkepOKBSY")
bot = telebot.TeleBot(TOKEN)

# Lưu trữ trạng thái người dùng
user_sessions = {}

class ZefoyBot:
    def __init__(self, chat_id, video_url, service_choice):
        self.chat_id = chat_id
        self.video_url = video_url
        self.service_choice = str(service_choice)
        self.start_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.session_stats = {"success_count": 0, "total_views": 0, "errors": 0}
        
        self.services = {
            "1": {"name": "Followers", "button": "t-followers-button", "increment": 0},
            "2": {"name": "Hearts", "button": "t-hearts-button", "increment": 30},
            "3": {"name": "Comments Hearts", "button": "t-chearts-button", "increment": 10},
            "4": {"name": "Views", "button": "t-views-button", "increment": 500},
            "5": {"name": "Shares", "button": "t-shares-button", "increment": 150},
            "6": {"name": "Favorites", "button": "t-favorites-button", "increment": 90},
        }
        self.current_service = self.services.get(self.service_choice)
        
        # Biến đồng bộ hóa để chờ Captcha từ Telegram
        self.captcha_event = threading.Event()
        self.captcha_answer = ""
        self.running = True

        chrome_options = Options()
        chrome_options.add_argument("--headless=new") # Bắt buộc chạy ẩn trên server
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        bot.send_message(self.chat_id, "🚀 Khởi động trình duyệt. Vui lòng đợi...")
        self.driver = Chrome(options=chrome_options, version_main=114) # Fix version tuỳ server
        self.wait = WebDriverWait(self.driver, 15)

    def send_log(self, text):
        try:
            bot.send_message(self.chat_id, text)
        except:
            pass

    def solve_captcha_manually(self):
        try:
            captcha = self.wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[5]/div[2]/form/div/div/img")))
            captcha.screenshot(f"captcha_{self.chat_id}.png")
            
            # Gửi ảnh qua Telegram
            with open(f"captcha_{self.chat_id}.png", "rb") as photo:
                bot.send_photo(self.chat_id, photo, caption="⚠️ Hệ thống yêu cầu Captcha!\n\nVui lòng nhắn tin gửi mã captcha vào đây:")
            
            # Thay đổi trạng thái user để hứng tin nhắn tiếp theo
            user_sessions[self.chat_id]['state'] = 'WAITING_CAPTCHA'
            
            # Dừng luồng Selenium để chờ Telegram gửi Captcha
            self.captcha_event.clear()
            self.captcha_event.wait() 
            
            # Đã nhận được Captcha từ Telegram
            answer = self.captcha_answer
            self.driver.find_element(By.XPATH, "/html/body/div[5]/div[2]/form/div/div/div/input").send_keys(answer)
            self.driver.find_element(By.XPATH, "/html/body/div[5]/div[2]/form/div/div/div/div/button").click()
            self.send_log("⏳ Đã gửi Captcha, đang kiểm tra...")
            time.sleep(5)
            self.driver.refresh()
            time.sleep(3)
            
        except Exception as e:
            self.send_log("❌ Lỗi xử lý Captcha.")
            self.running = False

    def select_service(self):
        try:
            button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, self.current_service["button"])))
            button.click()
            self.send_log(f"✅ Đã chọn dịch vụ: {self.current_service['name']}")
            return True
        except:
            self.send_log("❌ Dịch vụ hiện không khả dụng hoặc đang bảo trì.")
            return False

    def run(self):
        try:
            self.driver.get("https://zefoy.com")
            # Nếu có quảng cáo/captcha ở đây, gọi hàm tương ứng
            time.sleep(5)
            
            if "Just a moment" in self.driver.page_source:
               self.send_log("⚠️ Dính Cloudflare, đang thử vượt...")
               time.sleep(15)

            # Xử lý Captcha Zefoy
            try:
                if self.driver.find_element(By.XPATH, "/html/body/div[5]/div[2]/form/div/div/img"):
                    self.solve_captcha_manually()
            except NoSuchElementException:
                pass # Không có captcha

            if not self.running: return
            if not self.select_service(): return

            # Vòng lặp buff
            while self.running:
                try:
                    # Gửi link (Giả lập theo code cũ của bạn)
                    visible_forms = self.driver.find_elements(By.XPATH, "//form[not(contains(@class, 'nonec'))]")
                    for form in visible_forms:
                        link_input = form.find_element(By.XPATH, ".//input[contains(@placeholder, 'Enter')]")
                        search_btn = form.find_element(By.XPATH, ".//button[contains(., 'Search')]")
                        link_input.clear()
                        link_input.send_keys(self.video_url)
                        search_btn.click()
                        time.sleep(2)
                        break

                    # Xử lý nút bấm hoặc thời gian chờ
                    time.sleep(5)
                    try:
                        timer = self.driver.find_element(By.XPATH, "//div[contains(text(),'Please wait')]")
                        self.send_log(f"⏳ Đang chờ: {timer.text}")
                        time.sleep(30)
                    except:
                        buttons = self.driver.find_elements(By.XPATH, "//button[not(contains(@class, 'disableButton'))]")
                        for btn in buttons:
                            if any(x in btn.text.strip().lower() for x in ["send", "views", "hearts"]):
                                btn.click()
                                self.session_stats['success_count'] += 1
                                self.send_log(f"🎉 THÀNH CÔNG lần {self.session_stats['success_count']}!\nTổng buff: {self.session_stats['success_count'] * self.current_service['increment']}")
                                time.sleep(30)
                                break

                except Exception as e:
                    time.sleep(10)

        except Exception as e:
            self.send_log(f"❌ Bot dừng đột ngột: {str(e)}")
        finally:
            self.driver.quit()
            if self.chat_id in user_sessions:
                del user_sessions[self.chat_id]


# ================== TELEGRAM HANDLERS ==================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = """
👋 Chào mừng đến với Zefoy Bot Telegram!
Để bắt đầu, hãy gửi link TikTok bạn muốn buff.
    """
    bot.reply_to(message, text)

@bot.message_handler(func=lambda message: message.text.startswith('http'))
def handle_link(message):
    chat_id = message.chat.id
    url = message.text

    if chat_id in user_sessions:
        bot.reply_to(message, "⚠️ Bạn đang có một tiến trình chạy rồi. Đợi nó xong hoặc báo admin huỷ.")
        return

    user_sessions[chat_id] = {'url': url, 'state': 'WAITING_SERVICE'}
    
    menu = """
Vui lòng chọn dịch vụ bằng cách nhắn số tương ứng:
1. Followers (Chưa khả dụng)
2. Hearts (+30)
3. Comment Hearts (+10)
4. Views (+500)
5. Shares (+150)
6. Favorites (+90)
    """
    bot.reply_to(message, menu)

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_sessions:
        bot.reply_to(message, "Gửi link tiktok để bắt đầu.")
        return

    session = user_sessions[chat_id]

    # Nhận chọn dịch vụ
    if session['state'] == 'WAITING_SERVICE':
        if text in ["2", "3", "4", "5", "6"]:
            bot.reply_to(message, "Đã ghi nhận! Hệ thống đang khởi tạo browser...")
            session['state'] = 'RUNNING'
            
            # Chạy bot trong Thread riêng để không block Telegram
            zefoy = ZefoyBot(chat_id, session['url'], text)
            session['bot_instance'] = zefoy
            threading.Thread(target=zefoy.run).start()
        else:
            bot.reply_to(message, "Vui lòng chọn số từ 2 đến 6.")

    # Nhận Captcha từ người dùng
    elif session['state'] == 'WAITING_CAPTCHA':
        bot_instance = session.get('bot_instance')
        if bot_instance:
            bot_instance.captcha_answer = text
            bot_instance.captcha_event.set() # Bật cờ cho Selenium chạy tiếp
            session['state'] = 'RUNNING'

if __name__ == '__main__':
    print("🤖 Telegram Bot Đang Chạy...")
    bot.infinity_polling()