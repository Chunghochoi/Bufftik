import TelegramBot from "node-telegram-bot-api";
import { viewBot } from "./viewBot.js";
import { logger } from "./logger.js";

let bot: TelegramBot | null = null;

function formatStats(stats: ReturnType<typeof viewBot.getStats>): string {
  if (!stats.isRunning) {
    return "⚠️ Bot đang không chạy.";
  }
  return [
    `📊 *THỐNG KÊ HIỆU SUẤT*`,
    ``,
    `🎬 Video ID: \`${stats.videoId ?? "N/A"}\``,
    `👀 Tổng view: *${stats.totalViews.toLocaleString()}*`,
    `⏰ Thời gian: ${stats.elapsedTime.toFixed(1)}s`,
    `🚀 Tốc độ hiện tại: *${stats.viewsPerSecond.toFixed(1)}* view/s`,
    `🏆 Tốc độ cao nhất: *${stats.peakSpeed.toFixed(1)}* view/s`,
    `📈 Dự kiến: ${stats.viewsPerMinute.toFixed(0)} view/phút`,
    `🏃 Dự kiến: ${stats.viewsPerHour.toFixed(0)} view/giờ`,
    `✅ Request thành công: ${stats.successfulRequests.toLocaleString()}`,
    `❌ Request thất bại: ${stats.failedRequests.toLocaleString()}`,
    `🎯 Tỷ lệ thành công: ${stats.successRate.toFixed(1)}%`,
    `⚙️ Workers: ${stats.workers}`,
  ].join("\n");
}

export function initTelegramBot(): void {
  const token = process.env["TELEGRAM_BOT_TOKEN"];
  if (!token) {
    logger.warn("TELEGRAM_BOT_TOKEN not set, Telegram bot disabled");
    return;
  }

  bot = new TelegramBot(token, { polling: true });

  const helpText = [
    `🤖 *SPY VIEW BOT PRO - Telegram Control*`,
    ``,
    `Các lệnh hỗ trợ:`,
    ``,
    `/start\\_bot <url> - Bắt đầu gửi view`,
    `/stop\\_bot - Dừng bot`,
    `/stats - Xem thống kê hiện tại`,
    `/status - Kiểm tra trạng thái bot`,
    `/help - Xem hướng dẫn này`,
    ``,
    `Ví dụ:`,
    `/start\\_bot https://www.tiktok.com/@user/video/1234567890`,
  ].join("\n");

  bot.onText(/\/start$|\/start@\w+$/, async (msg) => {
    const chatId = msg.chat.id;
    await bot!.sendMessage(chatId, helpText, { parse_mode: "Markdown" });
  });

  bot.onText(/\/help/, async (msg) => {
    const chatId = msg.chat.id;
    await bot!.sendMessage(chatId, helpText, { parse_mode: "Markdown" });
  });

  bot.onText(/\/start_bot (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const videoUrl = match?.[1]?.trim();

    if (!videoUrl) {
      await bot!.sendMessage(chatId, "❌ Vui lòng cung cấp URL video TikTok.\nVí dụ: /start\\_bot https://www.tiktok.com/@user/video/123");
      return;
    }

    await bot!.sendMessage(chatId, "⏳ Đang khởi động bot, vui lòng đợi...");

    const result = await viewBot.start(videoUrl, 300);
    await bot!.sendMessage(
      chatId,
      result.success ? `✅ ${result.message}` : `❌ ${result.message}`,
      { parse_mode: "Markdown" }
    );
  });

  bot.onText(/\/stop_bot/, async (msg) => {
    const chatId = msg.chat.id;
    const result = viewBot.stop();
    await bot!.sendMessage(
      chatId,
      result.success ? `🛑 ${result.message}` : `⚠️ ${result.message}`
    );
  });

  bot.onText(/\/stats/, async (msg) => {
    const chatId = msg.chat.id;
    const stats = viewBot.getStats();
    await bot!.sendMessage(chatId, formatStats(stats), { parse_mode: "Markdown" });
  });

  bot.onText(/\/status/, async (msg) => {
    const chatId = msg.chat.id;
    const status = viewBot.getStatus();
    const text = status.isRunning
      ? [
          `✅ Bot đang *CHẠY*`,
          `🎬 URL: ${status.videoUrl}`,
          `🆔 Video ID: \`${status.videoId}\``,
          `⏰ Bắt đầu: ${status.startedAt ? new Date(status.startedAt).toLocaleString("vi-VN") : "N/A"}`,
        ].join("\n")
      : `⛔ Bot đang *DỪNG*`;
    await bot!.sendMessage(chatId, text, { parse_mode: "Markdown" });
  });

  bot.on("polling_error", (err) => {
    logger.error({ err }, "Telegram polling error");
  });

  logger.info("Telegram bot started successfully");
}

export function stopTelegramBot(): void {
  if (bot) {
    bot.stopPolling();
    bot = null;
  }
}
