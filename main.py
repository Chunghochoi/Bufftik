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
BB_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID") # Có thể để trống nếu không có

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Zefoy Cloud is live!"

class ZefoyCloud:
    def __init__(self, chat_id, context, loop):
        self.chat_id = chat_id
        self.context = context
        self.loop = loop
        self.driver = None

    def send_telegram_msg(self, text):
        asyncio.run_coroutine_threadsafe(
            self.context.bot.send_message(chat_id=self.chat_id, text=f"🤖 {text}"),
            self.loop
        )

    def setup_driver(self):
        """Kết nối Browserbase bằng cách truyền API Key vào Capabilities"""
        self.send_telegram_msg("Đang khởi tạo trình duyệt Browserbase...")
        
        options = webdriver.ChromeOptions()
        # Cách kết nối chuẩn của Browserbase cho Selenium
        options.set_capability("browserbase:options", {
            "apiKey": BB_API_KEY,
            "projectId": BB_PROJECT_ID if BB_PROJECT_ID else ""
        })

        try:
            # URL rút gọn, API Key đã nằm trong Capabilities
            self.driver = webdriver.Remote(
                command_executor="https://connect.browserbase.com/webdriver",
                options=options
            )
            self.wait = WebDriverWait(self.driver, 30)
            return True
        except Exception as e:
            self.send_telegram_msg(f"❌ Lỗi Driver: API Key không hợp lệ hoặc hết hạn.")
            print(f"Driver Error: {str(e)}")
            return False

    def solve_captcha_logic(self):
        if not self.setup_driver(): return

        try:
            self.driver.get("https://zefoy.com")
            time.sleep(8) # Tăng thời gian chờ trang load
            
            # Kiểm tra xem có bị Cloudflare chặn không
            if "Cloudflare" in self.driver.title:
                self.send_telegram_msg("❌ Bị Cloudflare chặn. Đang thử lại...")
                self.driver.quit()
                return

            # Tìm ảnh captcha bằng XPATH chính xác hơn
            try:
                img = self.wait.until(EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'captcha')]")))
            except:
                img = self.driver.find_element(By.TAG_NAME, "img") # Fallback

            path = f"captcha_{self.chat_id}.png"
            img.screenshot(path)

            # Gửi ảnh về Telegram kèm hướng dẫn
            asyncio.run_coroutine_threadsafe(
                self.context.bot.send_photo(
                    chat_id=self.chat_id, 
                    photo=open(path, 'rb'), 
                    caption="🔑 Nhập mã Captcha để tiếp tục:"
                ),
                self.loop
            )
        except Exception as e:
            self.send_telegram_msg(f"❌ Lỗi Zefoy: Không tìm thấy Captcha. Có thể trang đang bảo trì.")
            if self.driver: self.driver.quit()

# Lưu trữ phiên
active_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot Online! Hãy gửi link video TikTok.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    loop = asyncio.get_running_loop()

    if "tiktok.com" in text:
        # Xóa session cũ nếu có để tránh Conflict Driver
        if chat_id in active_sessions:
            try: active_sessions[chat_id]["instance"].driver.quit()
            except: pass
            
        bot_instance = ZefoyCloud(chat_id, context, loop)
        active_sessions[chat_id] = {"instance": bot_instance, "step": "WAIT_CAPTCHA"}
        threading.Thread(target=bot_instance.solve_captcha_logic).start()

    elif chat_id in active_sessions and active_sessions[chat_id]["step"] == "WAIT_CAPTCHA":
        bot = active_sessions[chat_id]["instance"]
        await update.message.reply_text("⌛ Đang xác thực mã...")
        
        def input_captcha():
            try:
                inp = bot.driver.find_element(By.XPATH, "//input[@placeholder='Enter Word']")
                inp.send_keys(text)
                inp.submit()
                time.sleep(3)
                bot.send_telegram_msg("✅ Đã nhập! Đang chuyển hướng...")
                # Thêm logic chọn menu tại đây nếu cần
            except Exception as e:
                bot.send_telegram_msg("❌ Lỗi: Không thể điền mã. Thử gửi lại link TikTok.")
        
        threading.Thread(target=input_captcha).start()

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    app_tg = ApplicationBuilder().token(TOKEN).build()
    app_tg.add_handler(CommandHandler('start', start))
    app_tg.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app_tg.run_polling()
