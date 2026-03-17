import asyncio
import os
import re
import time
import random
import logging
from io import BytesIO
from typing import Optional, Tuple

from fastapi import FastAPI
import uvicorn

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options

# ==========================================
# CẤU HÌNH MÔI TRƯỜNG & LOGGING
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
BROWSERLESS_TOKEN = os.getenv("BROWSERLESS_TOKEN", "YOUR_BROWSERLESS_TOKEN")
PROXY_LIST = os.getenv("PROXY_LIST", "").split(",") # Dạng ip:port:user:pass

# ==========================================
# CẤU TRÚC FSM (Finite State Machine)
# ==========================================
class ZefoyFSM(StatesGroup):
    waiting_for_url = State()
    waiting_for_captcha = State()
    processing = State()

# ==========================================
# MODULE 1: TỐI ƯU HÓA ZEFOY & BROWSERLESS
# ==========================================
class ZefoyBot:
    def __init__(self, browserless_token: str, proxy: Optional[str] = None):
        self.browserless_token = browserless_token
        self.proxy = proxy
        self.driver = None
        self.wait = None

    def init_driver(self):
        """Khởi tạo Remote WebDriver kết nối với Browserless.io cực kỳ ổn định"""
        options = Options()
        
        # Các tham số cốt lõi chống crash cho môi trường Cloud
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1280,720")
        
        # Khai báo phiên bản trình duyệt để Browserless dễ cấp phát
        options.set_capability("browserVersion", "latest")
        options.set_capability("platformName", "LINUX")

        # Hỗ trợ Proxy Rotation nếu có
        if self.proxy and len(self.proxy) > 5:
            options.add_argument(f"--proxy-server={self.proxy}")

        try:
            # ÉP TRỰC TIẾP TOKEN VÀO URL - KHẮC PHỤC TRIỆT ĐỂ LỖI 502 BAD GATEWAY
            browserless_url = f"https://chrome.browserless.io/webdriver?token={self.browserless_token}"
            
            logger.info("Đang kết nối tới Browserless...")
            self.driver = webdriver.Remote(
                command_executor=browserless_url,
                options=options
            )
            self.wait = WebDriverWait(self.driver, 20)
            logger.info("Khởi tạo WebDriver thành công!")
            
        except Exception as e:
            logger.error(f"Lỗi khởi tạo driver: {e}")
            raise

    def get_captcha(self) -> bytes:
        """Truy cập Zefoy và lấy ảnh Captcha"""
        self.driver.get("https://zefoy.com")
        try:
            # Smart Selector: Tìm ảnh captcha linh hoạt
            captcha_img = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img.img-thumbnail, form img, .captcha-img"))
            )
            # Chụp riêng vùng Captcha (Crop chính xác)
            return captcha_img.screenshot_as_png
        except TimeoutException:
            raise Exception("Không tìm thấy Captcha hoặc trang load quá chậm.")

    def submit_captcha(self, captcha_text: str) -> bool:
        """Nhập captcha và kiểm tra xem có qua được không"""
        try:
            input_box = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder*='captcha'], input[type='text']")
            input_box.clear()
            input_box.send_keys(captcha_text)
            
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            time.sleep(3)
            
            # Nếu input box biến mất nghĩa là qua captcha thành công
            if len(self.driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='captcha']")) == 0:
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi submit captcha: {e}")
            return False

    def check_cooldown(self) -> int:
        """Regex Cooldown Detection: Trả về số giây cần chờ"""
        try:
            timer_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Please wait') or contains(text(), 'Wait')]")
            if not timer_elements:
                return 0

            text = timer_elements[0].text.lower()
            
            # Regex trích xuất phút và giây linh hoạt
            minutes = re.search(r'(\d+)\s*minute', text)
            seconds = re.search(r'(\d+)\s*second', text)
            
            total_wait = 0
            if minutes:
                total_wait += int(minutes.group(1)) * 60
            if seconds:
                total_wait += int(seconds.group(1))
                
            return total_wait if total_wait > 0 else 30
        except Exception as e:
            logger.warning(f"Lỗi đọc cooldown: {e}")
            return 0

    def send_views(self, video_url: str) -> Tuple[bool, str, int]:
        """Thực hiện buff view và trả về (Thành công?, Lời nhắn, Thời gian chờ)"""
        try:
            # Chọn dịch vụ Views
            view_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".t-views-button, button[data-target='#views'], button[data-target='#views']")))
            view_btn.click()
            time.sleep(2)

            # Nhập link video
            link_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Enter Video']")))
            link_input.clear()
            link_input.send_keys(video_url)
            
            search_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Search')]")
            search_btn.click()
            time.sleep(4)

            # Kiểm tra Cooldown
            cooldown = self.check_cooldown()
            if cooldown > 0:
                return False, f"⏳ Bị giới hạn Cooldown. Vui lòng chờ {cooldown} giây.", cooldown

            # Click nút buff (thường là nút hiển thị số view hiện tại)
            submit_view = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-dark, button[type='submit']")))
            submit_view.click()
            time.sleep(3)

            return True, "✅ Buff View thành công! Đang chờ lượt tiếp theo...", 120 # Thường sau khi buff xong sẽ bị cooldown ~2p

        except Exception as e:
            logger.error(f"Lỗi quá trình send view: {e}")
            return False, "❌ Đã xảy ra lỗi khi buff (Có thể web đổi giao diện hoặc sập). Đang thử lại...", 10

    def close(self):
        """QUAN TRỌNG: Giải phóng RAM và Session Browserless"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Đã đóng Browserless Session an toàn.")
            except:
                pass

# ==========================================
# MODULE 2: TELEGRAM HANDLER (AIOGRAM 3.X)
# ==========================================
router = Router()

# Lưu trữ session Zefoy tạm thời cho từng user
user_sessions = {}

def get_proxy():
    """Health check proxy (Giả lập)"""
    if not PROXY_LIST or PROXY_LIST[0] == "":
        return None
    return random.choice(PROXY_LIST)

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🚀 Chào mừng tới Zefoy Bot V5.0 (Ultra Lite & Auto Bypass).\n\n"
                         "Sử dụng lệnh /zefoy để bắt đầu quá trình tăng tương tác TikTok.")

@router.message(Command("zefoy"))
async def cmd_zefoy(message: Message, state: FSMContext):
    await message.answer("🔗 Vui lòng gửi Link video TikTok bạn muốn tăng View:")
    await state.set_state(ZefoyFSM.waiting_for_url)

@router.message(ZefoyFSM.waiting_for_url)
async def process_url(message: Message, state: FSMContext):
    video_url = message.text
    if "tiktok.com" not in video_url:
        await message.answer("❌ Link không hợp lệ. Vui lòng gửi lại link TikTok có chứa 'tiktok.com'.")
        return

    await state.update_data(video_url=video_url)
    msg = await message.answer("🔄 Đang khởi tạo kết nối Cloud Browser và lấy Captcha. Vui lòng đợi (10-20s)...")
    
    user_id = message.from_user.id
    proxy = get_proxy()
    bot_instance = ZefoyBot(BROWSERLESS_TOKEN, proxy)
    
    try:
        # Chạy Selenium trong ThreadPool để không block luồng asyncio
        await asyncio.to_thread(bot_instance.init_driver)
        captcha_bytes = await asyncio.to_thread(bot_instance.get_captcha)
        
        user_sessions[user_id] = bot_instance
        
        photo = BufferedInputFile(captcha_bytes, filename="captcha.png")
        await message.answer_photo(photo, caption="📸 Vui lòng nhập mã Captcha trong ảnh trên:")
        await state.set_state(ZefoyFSM.waiting_for_captcha)
        await msg.delete()
        
    except Exception as e:
        bot_instance.close()
        await message.answer(f"❌ Lỗi khởi tạo: {str(e)}\n\n💡 Gợi ý: Nếu trang Zefoy đang sập, vui lòng chờ 5 phút rồi gõ lại lệnh /zefoy.")
        await state.clear()

@router.message(ZefoyFSM.waiting_for_captcha)
async def process_captcha(message: Message, state: FSMContext):
    user_id = message.from_user.id
    captcha_text = message.text
    
    if user_id not in user_sessions:
        await message.answer("❌ Session đã hết hạn hoặc bị lỗi. Gõ /zefoy để làm lại.")
        await state.clear()
        return

    bot_instance: ZefoyBot = user_sessions[user_id]
    data = await state.get_data()
    video_url = data['video_url']
    
    await message.answer("🔄 Đang giải Captcha và bắt đầu Buff...")
    await state.set_state(ZefoyFSM.processing)

    try:
        # Submit Captcha
        is_passed = await asyncio.to_thread(bot_instance.submit_captcha, captcha_text)
        if not is_passed:
            await message.answer("❌ Sai Captcha hoặc Captcha hết hạn. Hãy gõ /zefoy để bắt đầu lại.")
            await asyncio.to_thread(bot_instance.close)
            del user_sessions[user_id]
            await state.clear()
            return

        await message.answer("✅ Vượt Captcha thành công! Bot bắt đầu Auto-Buff...")

        # Vòng lặp Buff tự động với Async Sleep
        while True:
            success, msg_text, cooldown = await asyncio.to_thread(bot_instance.send_views, video_url)
            
            if success:
                await message.answer(msg_text)
                await message.answer(f"💤 Đang ngủ {cooldown}s để chờ Zefoy hồi chiêu...")
                await asyncio.sleep(cooldown) # Sleep KHÔNG CHẶN (Non-blocking)
            else:
                if cooldown > 0:
                    await message.answer(msg_text)
                    await asyncio.sleep(cooldown + 5) # Chờ hết cooldown rồi tự động lặp lại
                else:
                    await message.answer(msg_text)
                    break # Lỗi nặng, thoát vòng lặp

    except Exception as e:
        logger.error(f"Lỗi Runtime: {e}")
        await message.answer("❌ Trình duyệt đã bị crash hoặc trang Zefoy đang bảo trì. Vui lòng thử lại sau.")
    finally:
        # Đảm bảo tài nguyên KHÔNG BAO GIỜ bị rò rỉ (Memory Leak)
        await asyncio.to_thread(bot_instance.close)
        if user_id in user_sessions:
            del user_sessions[user_id]
        await state.clear()

# ==========================================
# MODULE 3: FASTAPI (KEEP-ALIVE SERVER)
# ==========================================
app = FastAPI(title="Zefoy Bot V5.0 Server")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Zefoy Bot is running smoothly on Render with Browserless.io"}

# ==========================================
# ĐIỂM KHỞI CHẠY (ENTRY POINT)
# ==========================================
async def start_bot():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Xóa webhook cũ nếu có để tránh xung đột phiên bản
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot Telegram đã sẵn sàng nhận lệnh.")
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_startup():
    # Khởi chạy Bot Telegram như một Background Task cùng lúc với FastAPI
    asyncio.create_task(start_bot())

if __name__ == "__main__":
    # Render quy định cổng môi trường PORT, mặc định chạy 10000 nếu test ở Local
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
