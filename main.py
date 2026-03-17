import asyncio
import os
import re
import random
import logging
from typing import Optional, Tuple

from fastapi import FastAPI
import uvicorn

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from playwright.async_api import async_playwright, Browser, Page, Playwright

# ==========================================
# CẤU HÌNH MÔI TRƯỜNG & LOGGING
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
BROWSERLESS_TOKEN = os.getenv("BROWSERLESS_TOKEN", "YOUR_BROWSERLESS_TOKEN")

# ==========================================
# CẤU TRÚC FSM
# ==========================================
class ZefoyFSM(StatesGroup):
    waiting_for_url = State()
    waiting_for_captcha = State()
    processing = State()

# ==========================================
# MODULE 1: TỐI ƯU HÓA ZEFOY BẰNG PLAYWRIGHT
# ==========================================
class ZefoyBot:
    def __init__(self, token: str):
        self.browserless_token = token
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def init_browser(self):
        """Kết nối WebSocket siêu tốc độ & Ổn định tới Browserless"""
        self.playwright = await async_playwright().start()
        
        # Endpoint WebSocket kết nối thẳng vào engine Playwright của Browserless
        ws_endpoint = f"wss://chrome.browserless.io/?token={self.browserless_token}&stealth=true&blockAds=true"
        
        try:
            logger.info("Đang kết nối WebSocket tới Browserless...")
            self.browser = await self.playwright.chromium.connect_over_cdp(ws_endpoint)
            context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            self.page = await context.new_page()
            # Set timeout mặc định là 30s
            self.page.set_default_timeout(30000)
            logger.info("✅ Đã khởi tạo phiên bản Playwright thành công!")
        except Exception as e:
            logger.error(f"❌ Lỗi kết nối Browserless: {e}")
            raise

    async def get_captcha(self) -> bytes:
        """Tải Zefoy và chụp ảnh Captcha cực mượt"""
        await self.page.goto("https://zefoy.com", wait_until="domcontentloaded")
        
        try:
            # Chờ ảnh captcha xuất hiện (Lách Cloudflare tự động nếu có)
            captcha_img = await self.page.wait_for_selector("img.img-thumbnail, form img", state="visible", timeout=20000)
            await asyncio.sleep(1) # Chờ load hẳn hình
            
            # Chụp riêng vùng ảnh Captcha
            image_bytes = await captcha_img.screenshot()
            return image_bytes
        except Exception as e:
            raise Exception("Không tải được trang hoặc bị Cloudflare chặn quá lâu.")

    async def submit_captcha(self, captcha_text: str) -> bool:
        """Nhập captcha và kiểm tra"""
        try:
            await self.page.fill("input[placeholder*='captcha'], input[type='text']", captcha_text)
            await self.page.click("button[type='submit']")
            await asyncio.sleep(3)
            
            # Kiểm tra xem ô input captcha có biến mất không
            is_visible = await self.page.is_visible("input[placeholder*='captcha']")
            return not is_visible
        except Exception as e:
            logger.error(f"Lỗi submit: {e}")
            return False

    async def check_cooldown(self) -> int:
        """Kiểm tra cooldown nhẹ nhàng bằng Regex trên nội dung Text của trang"""
        content = await self.page.content()
        if "Please wait" in content or "Wait" in content:
            minutes = re.search(r'(\d+)\s*minute', content.lower())
            seconds = re.search(r'(\d+)\s*second', content.lower())
            
            total_wait = 0
            if minutes: total_wait += int(minutes.group(1)) * 60
            if seconds: total_wait += int(seconds.group(1))
            return total_wait if total_wait > 0 else 30
        return 0

    async def send_views(self, video_url: str) -> Tuple[bool, str, int]:
        """Buff View nhanh chóng"""
        try:
            # Click vào dịch vụ Views
            await self.page.click(".t-views-button, button[data-target='#views']")
            await asyncio.sleep(2)

            # Nhập link
            await self.page.fill("input[placeholder*='Enter Video']", video_url)
            await self.page.click("//button[contains(., 'Search')]")
            await asyncio.sleep(4)

            # Check Cooldown
            cooldown = await self.check_cooldown()
            if cooldown > 0:
                return False, f"⏳ Bị giới hạn Cooldown. Vui lòng chờ {cooldown} giây.", cooldown

            # Nhấn nút buff view
            await self.page.click("button.btn-dark, button[type='submit']")
            await asyncio.sleep(3)

            return True, "✅ Buff View thành công! Đang chờ lượt tiếp theo...", 120
        except Exception as e:
            logger.error(f"Lỗi Buff: {e}")
            return False, "❌ Lỗi tương tác giao diện Zefoy. Đang thử lại...", 10

    async def close(self):
        """Đóng session gọn gàng"""
        if self.page: await self.page.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        logger.info("🔒 Đã đóng Browserless Session.")

# ==========================================
# MODULE 2: TELEGRAM BOT HANDLER
# ==========================================
router = Router()
user_sessions = {}

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🚀 Bot Zefoy V5.0 (Playwright Edition - Siêu mượt).\nGõ /zefoy để bắt đầu!")

@router.message(Command("zefoy"))
async def cmd_zefoy(message: Message, state: FSMContext):
    await message.answer("🔗 Gửi Link video TikTok của bạn:")
    await state.set_state(ZefoyFSM.waiting_for_url)

@router.message(ZefoyFSM.waiting_for_url)
async def process_url(message: Message, state: FSMContext):
    video_url = message.text
    if "tiktok.com" not in video_url:
        return await message.answer("❌ Link không hợp lệ.")

    await state.update_data(video_url=video_url)
    msg = await message.answer("🔄 Đang tải trình duyệt ảo siêu tốc...")
    
    user_id = message.from_user.id
    bot_instance = ZefoyBot(BROWSERLESS_TOKEN)
    
    try:
        # Không cần dùng to_thread nữa vì Playwright đã là Async!
        await bot_instance.init_browser()
        captcha_bytes = await bot_instance.get_captcha()
        
        user_sessions[user_id] = bot_instance
        
        await msg.delete()
        await message.answer_photo(
            BufferedInputFile(captcha_bytes, filename="captcha.png"), 
            caption="📸 Nhập mã Captcha trong ảnh:"
        )
        await state.set_state(ZefoyFSM.waiting_for_captcha)
        
    except Exception as e:
        await bot_instance.close()
        await message.answer(f"❌ Lỗi tải trang: {str(e)}\n(Zefoy có thể đang sập, thử lại sau 2 phút).")
        await state.clear()

@router.message(ZefoyFSM.waiting_for_captcha)
async def process_captcha(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        await state.clear()
        return await message.answer("❌ Phiên hết hạn, gõ /zefoy lại.")

    bot_instance: ZefoyBot = user_sessions[user_id]
    data = await state.get_data()
    
    await message.answer("🔄 Đang kiểm tra Captcha...")
    await state.set_state(ZefoyFSM.processing)

    try:
        is_passed = await bot_instance.submit_captcha(message.text)
        if not is_passed:
            await message.answer("❌ Sai Captcha. Gõ /zefoy để thử lại.")
            await bot_instance.close()
            del user_sessions[user_id]
            return await state.clear()

        await message.answer("✅ Mở khoá thành công! Đang tiến hành Auto-Buff...")

        while True:
            success, msg_text, cooldown = await bot_instance.send_views(data['video_url'])
            await message.answer(msg_text)
            
            if success or cooldown > 0:
                await message.answer(f"💤 Tạm nghỉ {cooldown}s...")
                await asyncio.sleep(cooldown)
            else:
                break

    except Exception as e:
        await message.answer("❌ Đã xảy ra lỗi mạng hoặc kết thúc phiên.")
    finally:
        await bot_instance.close()
        if user_id in user_sessions: del user_sessions[user_id]
        await state.clear()

# ==========================================
# MODULE 3: SERVER FASTAPI (KEEP-ALIVE)
# ==========================================
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "engine": "Playwright + Browserless WebSocket"}

async def start_bot():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
