"""
Telegram Bot Automation Architecture
Python 3.11+ | Render Free Plan | Browserless.io
"""
import os
import re
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

# ==========================================
# 1. CONFIG & LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("AutoBot")

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_TOKEN")
    BROWSERLESS_TOKEN = os.getenv("BROWSERLESS_TOKEN", "YOUR_BROWSERLESS_TOKEN")
    BROWSERLESS_ENDPOINT = os.getenv("BROWSERLESS_ENDPOINT", "wss://chrome.browserless.io/")
    MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", 2)) # Render Free: keep it low (2-3)
    PORT = int(os.getenv("PORT", 10000))
    # format: "ip:port:user:pass,ip:port:user:pass"
    PROXY_LIST_RAW = os.getenv("PROXY_LIST", "")

# ==========================================
# 2. PROXY MANAGER
# ==========================================
class ProxyManager:
    def __init__(self, raw_proxies: str):
        self.proxies = [p.strip() for p in raw_proxies.split(",") if p.strip()]
        self._lock = threading.Lock()
        self._index = 0

    def get_proxy(self) -> Optional[str]:
        with self._lock:
            if not self.proxies:
                return None
            proxy = self.proxies[self._index]
            self._index = (self._index + 1) % len(self.proxies)
            return proxy

proxy_manager = ProxyManager(Config.PROXY_LIST_RAW)

# ==========================================
# 3. SESSION MANAGEMENT
# ==========================================
@dataclass
class BotSession:
    user_id: int
    is_active: bool = False
    last_active: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

class SessionManager:
    def __init__(self):
        self.sessions: Dict[int, BotSession] = {}
        self._lock = threading.Lock()

    def get_session(self, user_id: int) -> BotSession:
        with self._lock:
            if user_id not in self.sessions:
                self.sessions[user_id] = BotSession(user_id=user_id)
            return self.sessions[user_id]

session_manager = SessionManager()

# ==========================================
# 4. BROWSERLESS CLIENT
# ==========================================
class BrowserlessClient:
    @staticmethod
    def check_api_status() -> bool:
        """Kiểm tra quota và API endpoint của Browserless trước khi chạy"""
        try:
            # Tuỳ thuộc vào endpoint của Browserless/nhà cung cấp
            api_url = Config.BROWSERLESS_ENDPOINT.replace("wss://", "https://").replace("ws://", "http://")
            url = f"{api_url}config?token={Config.BROWSERLESS_TOKEN}"
            resp = requests.get(url, timeout=10)
            return resp.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Browserless API Check Failed: {e}")
            return False

    @staticmethod
    def create_remote_driver(proxy: Optional[str] = None) -> WebDriver:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,720")
        
        # Tối ưu RAM, chặn tải Media/Images/Fonts không cần thiết cho QA
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheet": 2,
            "profile.managed_default_content_settings.fonts": 2,
        }
        options.add_experimental_option("prefs", prefs)

        if proxy:
            options.add_argument(f"--proxy-server={proxy}")

        endpoint = f"{Config.BROWSERLESS_ENDPOINT}?token={Config.BROWSERLESS_TOKEN}"
        
        # Retry mechanism for connecting to remote browser
        for attempt in range(3):
            try:
                driver = webdriver.Remote(
                    command_executor=endpoint,
                    options=options
                )
                driver.set_page_load_timeout(30)
                return driver
            except Exception as e:
                logger.warning(f"Failed to connect remote browser (Attempt {attempt+1}): {e}")
                time.sleep(2)
        raise WebDriverException("Could not connect to Browserless after 3 attempts")

# ==========================================
# 5. AUTOMATION MANAGER (CORE WORKFLOW)
# ==========================================
class AutomationManager:
    def __init__(self, bot: telebot.TeleBot, chat_id: int, url: str):
        self.bot = bot
        self.chat_id = chat_id
        self.url = url
        self.driver: Optional[WebDriver] = None

    def send_status(self, text: str):
        try:
            self.bot.send_message(self.chat_id, f"🔄 {text}")
        except Exception as e:
            logger.error(f"Failed to send status to {self.chat_id}: {e}")

    @staticmethod
    def parse_wait_time(text: str) -> int:
        """Trích xuất thời gian chờ (giây) từ văn bản, vd: 'wait 1 minute 30 seconds'"""
        seconds = 0
        min_match = re.search(r'(\d+)\s*(min|minute|m)', text, re.IGNORECASE)
        sec_match = re.search(r'(\d+)\s*(sec|second|s)', text, re.IGNORECASE)
        if min_match:
            seconds += int(min_match.group(1)) * 60
        if sec_match:
            seconds += int(sec_match.group(1))
        return seconds if seconds > 0 else 5 # default 5s retry

    def run_qa_workflow(self):
        proxy = proxy_manager.get_proxy()
        try:
            self.send_status("Đang khởi tạo Remote Browser...")
            self.driver = BrowserlessClient.create_remote_driver(proxy)
            
            self.send_status(f"Đang truy cập: {self.url}")
            self.driver.get(self.url)

            # VD: Kiểm tra trạng thái website (Title)
            title = self.driver.title
            self.send_status(f"Đã tải trang thành công. Tiêu đề: {title}")

            # VD: Giả lập kiểm tra Cooldown/Rate-Limit alert trên web
            try:
                alert_elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'wait')]"))
                )
                wait_text = alert_elem.text
                wait_sec = self.parse_wait_time(wait_text)
                self.send_status(f"Phát hiện Rate-Limit. Tạm dừng {wait_sec} giây...")
                time.sleep(wait_sec) # Đây là lúc hợp lệ duy nhất để sleep (tôn trọng rate-limit)
                
                self.send_status("Đang tải lại trang...")
                self.driver.refresh()
            except TimeoutException:
                pass # Không có alert

            # Chụp ảnh màn hình làm bằng chứng QA
            self.send_status("Đang chụp ảnh màn hình xác thực...")
            screenshot = self.driver.get_screenshot_as_png()
            self.bot.send_photo(self.chat_id, screenshot, caption="✅ Tác vụ hoàn tất.")

        except TimeoutException as e:
            logger.error(f"Timeout at {self.url}: {e}")
            self.send_status("❌ Lỗi: Website tải quá chậm (Timeout).")
        except WebDriverException as e:
            logger.error(f"WebDriver Error for {self.chat_id}: {e}")
            self.send_status("❌ Lỗi: Mất kết nối trình duyệt.")
        except Exception as e:
            logger.exception("Unexpected automation error")
            self.send_status(f"❌ Lỗi hệ thống: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info(f"Driver closed for user {self.chat_id}")

# ==========================================
# 6. TELEGRAM BOT APP
# ==========================================
bot = telebot.TeleBot(Config.TELEGRAM_TOKEN)
executor = ThreadPoolExecutor(max_workers=Config.MAX_CONCURRENT_JOBS)

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    text = (
        "👋 Chào mừng đến với hệ thống QA & Monitor Bot.\n\n"
        "Vui lòng gửi cho tôi một URL (bắt đầu bằng http) để bắt đầu kiểm tra trạng thái và chụp ảnh màn hình."
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith("http"))
def handle_url(message):
    user_id = message.chat.id
    session = session_manager.get_session(user_id)

    # Sử dụng Lock để ngăn chặn 1 user spam nhiều job cùng lúc
    if not session.lock.acquire(blocking=False):
        bot.send_message(user_id, "⏳ Bạn đang có một tác vụ đang chạy. Vui lòng chờ hoàn tất!")
        return

    try:
        session.is_active = True
        session.last_active = time.time()
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Kiểm tra & Chụp ảnh", callback_data=f"qa|{message.text}")
        )
        bot.send_message(
            user_id, 
            f"Đã nhận URL: {message.text}\nBạn muốn thực hiện tác vụ nào?", 
            reply_markup=markup
        )
    finally:
        session.lock.release()

@bot.callback_query_handler(func=lambda call: call.data.startswith("qa|"))
def handle_qa_callback(call):
    user_id = call.message.chat.id
    url = call.data.split("|", 1)[1]
    
    bot.answer_callback_query(call.id, "Đưa tác vụ vào hàng đợi...")
    bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=None)
    
    session = session_manager.get_session(user_id)
    if not session.lock.acquire(blocking=False):
        bot.send_message(user_id, "⏳ Vui lòng chờ tác vụ trước đó hoàn tất.")
        return

    def background_job():
        try:
            if not BrowserlessClient.check_api_status():
                bot.send_message(user_id, "❌ Lỗi: Hệ thống Remote Browser đang bảo trì hoặc hết quota.")
                return
            
            manager = AutomationManager(bot, user_id, url)
            manager.run_qa_workflow()
        finally:
            session.lock.release()
            session.is_active = False

    # Submit job vào ThreadPool thay vì chạy đồng bộ
    executor.submit(background_job)

# ==========================================
# 7. HEALTH SERVER (FLASK)
# ==========================================
app = Flask(__name__)

@app.route('/')
@app.route('/healthz')
def health_check():
    return "Bot is alive and healthy!", 200

def run_flask():
    # Chạy trên port 10000 theo chuẩn Render
    app.run(host="0.0.0.0", port=Config.PORT)

# ==========================================
# 8. MAIN ENTRY POINT
# ==========================================
if __name__ == "__main__":
    logger.info("Starting Flask Health Server...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    logger.info("Starting Telegram Bot Polling...")
    try:
        bot.infinity_polling(skip_pending=True)
    except KeyboardInterrupt:
        logger.info("Graceful shutdown initiated...")
        executor.shutdown(wait=False)
