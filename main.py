import os
import time
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading

# --- CẤU HÌNH ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
BB_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BB_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is live!"

class ZefoyCloud:
    def __init__(self, chat_id, context):
        self.chat_id = chat_id
        self.context = context
        self.driver = None

    async def send_log(self, text):
        await self.context.bot.send_message(chat_id=self.chat_id, text=f"ℹ️ {text}")

    def setup_driver(self):
        # Kết nối tới Browserbase với URL chuẩn
        # Lưu ý: Browserbase yêu cầu Project ID trong URL hoặc Header
        options = webdriver.ChromeOptions()
        # Browserbase URL Connect
        remote_url = f"https://connect.browserbase.com/webdriver?apiKey={BB_API_KEY}"
        
        self.driver = webdriver.Remote(
            command_executor=remote_url,
            options=options
        )
        self.wait = WebDriverWait(self.driver, 30)

    async def solve_captcha(self):
        try:
            await self.send_log("Đang truy cập Zefoy.com...")
            self.driver.get("https://zefoy.com")
            
            # Đợi captcha xuất hiện
            await self.send_log("Đang tìm Captcha...")
            time.sleep(5) # Đợi trang load hẳn
            
            captcha_img = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
            
            # Chụp ảnh captcha
            captcha_path = f"captcha_{self.chat_id}.png"
            captcha_img.screenshot(captcha_path)
            
            with open(captcha_path, "rb") as photo:
                await self.context.bot.send_photo(
                    chat_id=self.chat_id, 
                    photo=photo, 
                    caption="🔑 Nhập mã Captcha trong ảnh bên dưới:"
                )
            return True
        except Exception as e:
            await self.send_log(f"❌ Lỗi Captcha: {str(e)}")
            if self.driver: self.driver.quit()
            return False

# Lưu trữ phiên làm việc
active_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Zefoy Cloud đã sẵn sàng! Gửi link TikTok để bắt đầu.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    # 1. Nếu là Link TikTok
    if "tiktok.com" in text:
        await update.message.reply_text("⏳ Đang khởi tạo Browserbase (Vui lòng đợi 10-20s)...")
        
        bot_instance = ZefoyCloud(chat_id, context)
        active_sessions[chat_id] = {"instance": bot_instance, "step": "WAITING_CAPTCHA", "url": text}
        
        # Chạy driver setup trong một thread riêng để không block Telegram
        def run_setup():
            try:
                bot_instance.setup_driver()
                # Sau khi setup xong thì gọi captcha (cần dùng loop của thread chính)
                asyncio.run_coroutine_threadsafe(bot_instance.solve_captcha(), asyncio.get_event_loop())
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    context.bot.send_message(chat_id=chat_id, text=f"❌ Lỗi khởi tạo: {str(e)}"), 
                    asyncio.get_event_loop()
                )

        threading.Thread(target=run_setup).start()

    # 2. Nếu là mã Captcha
    elif chat_id in active_sessions and active_sessions[chat_id]["step"] == "WAITING_CAPTCHA":
        session = active_sessions[chat_id]
        bot = session["instance"]
        
        await update.message.reply_text(f"🔍 Đang kiểm tra mã: {text}...")
        
        try:
            # Điền captcha vào web
            input_box = bot.driver.find_element(By.TAG_NAME, "input")
            input_box.send_keys(text)
            
            btn = bot.driver.find_element(By.TAG_NAME, "button")
            btn.click()
            
            time.sleep(3)
            await update.message.reply_text("✅ Đã gửi captcha! Kiểm tra dịch vụ...")
            # Tại đây bạn có thể gọi hàm bot.select_service() như code cũ của bạn
            
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi khi nhập captcha: {str(e)}")

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    # Chạy Flask
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Chạy Telegram Bot
    print("Bot is starting...")
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()
