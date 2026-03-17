import os
import time
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CẤU HÌNH ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
BB_API_KEY = os.getenv("BROWSERBASE_API_KEY")

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

class ZefoyCloud:
    def __init__(self, chat_id, context, loop):
        self.chat_id = chat_id
        self.context = context
        self.loop = loop # Lưu lại vòng lặp chính của Telegram
        self.driver = None

    def send_telegram_msg(self, text):
        """Hàm gửi tin nhắn từ Thread Selenium về Telegram"""
        asyncio.run_coroutine_threadsafe(
            self.context.bot.send_message(chat_id=self.chat_id, text=f"ℹ️ {text}"),
            self.loop
        )

    def setup_driver(self):
        self.send_telegram_msg("Đang kết nối Browserbase...")
        options = webdriver.ChromeOptions()
        # Browserbase URL chuẩn xác:
        remote_url = f"https://connect.browserbase.com/webdriver?apiKey={BB_API_KEY}"
        
        try:
            self.driver = webdriver.Remote(
                command_executor=remote_url,
                options=options
            )
            self.wait = WebDriverWait(self.driver, 30)
            return True
        except Exception as e:
            self.send_telegram_msg(f"❌ Lỗi kết nối Driver: {str(e)}")
            return False

    def solve_captcha_logic(self):
        """Logic chạy trong Thread riêng"""
        if not self.setup_driver(): return

        try:
            self.driver.get("https://zefoy.com")
            time.sleep(5)
            
            # Tìm ảnh captcha
            img = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
            path = f"captcha_{self.chat_id}.png"
            img.screenshot(path)

            # Gửi ảnh về Telegram
            asyncio.run_coroutine_threadsafe(
                self.context.bot.send_photo(chat_id=self.chat_id, photo=open(path, 'rb'), caption="🔑 Nhập Captcha:"),
                self.loop
            )
        except Exception as e:
            self.send_telegram_msg(f"❌ Lỗi Selenium: {str(e)}")

# Lưu trữ phiên
active_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Zefoy v2.1 Online! Gửi link TikTok để bắt đầu.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    loop = asyncio.get_running_loop() # Lấy loop hiện tại

    if "tiktok.com" in text:
        await update.message.reply_text("⏳ Khởi tạo trình duyệt đám mây...")
        
        bot_instance = ZefoyCloud(chat_id, context, loop)
        active_sessions[chat_id] = {"instance": bot_instance, "step": "WAIT_CAPTCHA"}
        
        # Chạy Selenium trong Thread riêng để không làm bot bị treo (Conflict/Timeout)
        t = threading.Thread(target=bot_instance.solve_captcha_logic)
        t.start()

    elif chat_id in active_sessions and active_sessions[chat_id]["step"] == "WAIT_CAPTCHA":
        # Logic nhập captcha...
        bot = active_sessions[chat_id]["instance"]
        await update.message.reply_text("🔍 Đang gửi captcha vào trình duyệt...")
        
        def input_captcha():
            try:
                # Tìm input và nút dựa trên tag vì Zefoy hay đổi ID
                inp = bot.driver.find_element(By.TAG_NAME, "input")
                inp.send_keys(text)
                btn = bot.driver.find_element(By.TAG_NAME, "button")
                btn.click()
                bot.send_telegram_msg("✅ Đã gửi! Vui lòng đợi Zefoy xử lý...")
            except Exception as e:
                bot.send_telegram_msg(f"❌ Lỗi nhập mã: {str(e)}")
        
        threading.Thread(target=input_captcha).start()

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    # Chạy Flask
    threading.Thread(target=run_flask, daemon=True).start()

    # Chạy Telegram
    print("Bot starting...")
    app_tg = ApplicationBuilder().token(TOKEN).build()
    app_tg.add_handler(CommandHandler('start', start))
    app_tg.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app_tg.run_polling()
