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
BB_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Zefoy Cloud V3 is running!"

class ZefoyCloud:
    def __init__(self, chat_id, context, loop):
        self.chat_id = chat_id
        self.context = context
        self.loop = loop
        self.driver = None

    def send_telegram_msg(self, text):
        """Gửi tin nhắn an toàn từ luồng Selenium về Telegram"""
        asyncio.run_coroutine_threadsafe(
            self.context.bot.send_message(chat_id=self.chat_id, text=f"🤖 {text}"),
            self.loop
        )

    def setup_driver(self):
        """Kết nối Browserbase theo chuẩn mới nhất của Selenium 4"""
        options = webdriver.ChromeOptions()
        # Chèn API Key trực tiếp vào capability
        bb_options = {
            "apiKey": BB_API_KEY,
        }
        if BB_PROJECT_ID:
            bb_options["projectId"] = BB_PROJECT_ID
            
        options.set_capability("browserbase:options", bb_options)

        try:
            # URL chuẩn để tránh lỗi POST /webdriver
            self.driver = webdriver.Remote(
                command_executor="https://connect.browserbase.com/webdriver",
                options=options
            )
            self.wait = WebDriverWait(self.driver, 45) # Tăng time chờ cho server Render
            return True
        except Exception as e:
            self.send_telegram_msg(f"❌ Lỗi Driver: Vui lòng kiểm tra Browserbase API Key.")
            print(f"DEBUG Driver Error: {str(e)}")
            return False

    def solve_captcha_logic(self):
        if not self.setup_driver(): return

        try:
            self.driver.get("https://zefoy.com")
            time.sleep(10) # Chờ Zefoy load
            
            # Tìm ảnh captcha bằng XPATH linh hoạt
            img = self.wait.until(EC.presence_of_element_located((By.XPATH, "//img[contains(@class, 'img-thumbnail')] | //img[contains(@src, 'captcha')]")))
            
            path = f"captcha_{self.chat_id}.png"
            img.screenshot(path)

            asyncio.run_coroutine_threadsafe(
                self.context.bot.send_photo(
                    chat_id=self.chat_id, 
                    photo=open(path, 'rb'), 
                    caption="🔑 Nhập mã Captcha (viết hoa/thường khớp ảnh):"
                ),
                self.loop
            )
        except Exception as e:
            self.send_telegram_msg(f"❌ Lỗi: Không tải được Captcha. Hãy thử gửi lại link.")
            if self.driver: self.driver.quit()

active_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot đã kết nối thành công! Gửi link TikTok để bắt đầu buff.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    loop = asyncio.get_running_loop()

    if "tiktok.com" in text:
        await update.message.reply_text("⏳ Đang kết nối Browserbase... (mất khoảng 10-15s)")
        
        # Ngắt driver cũ nếu user gửi link mới
        if chat_id in active_sessions:
            try: active_sessions[chat_id]["instance"].driver.quit()
            except: pass
            
        bot_instance = ZefoyCloud(chat_id, context, loop)
        active_sessions[chat_id] = {"instance": bot_instance, "step": "WAIT_CAPTCHA"}
        threading.Thread(target=bot_instance.solve_captcha_logic).start()

    elif chat_id in active_sessions and active_sessions[chat_id]["step"] == "WAIT_CAPTCHA":
        bot = active_sessions[chat_id]["instance"]
        await update.message.reply_text("🔍 Đang xác thực mã captcha...")
        
        def input_captcha():
            try:
                # Thử tìm ô nhập captcha
                inp = bot.driver.find_element(By.TAG_NAME, "input")
                inp.clear()
                inp.send_keys(text)
                
                # Tìm nút Submit
                btn = bot.driver.find_element(By.TAG_NAME, "button")
                btn.click()
                
                time.sleep(5)
                bot.send_telegram_msg("✅ Đã gửi mã! Nếu bot không phản hồi thêm, có thể mã sai. Hãy thử gửi lại link TikTok.")
            except Exception as e:
                bot.send_telegram_msg("❌ Lỗi: Trình duyệt đã đóng hoặc quá hạn. Hãy gửi lại link.")
        
        threading.Thread(target=input_captcha).start()

def run_flask():
    # Flask chạy cổng 8080 cho Render
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    # Chạy Web Server ngầm
    threading.Thread(target=run_flask, daemon=True).start()

    # Khởi tạo Telegram Bot
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # drop_pending_updates=True giúp xóa lệnh cũ, fix lỗi Conflict
    print("Bot is starting...")
    application.run_polling(drop_pending_updates=True)
