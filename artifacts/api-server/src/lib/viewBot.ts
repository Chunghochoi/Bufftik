import { createHash } from "crypto";
import http from "http";
import https from "https";

interface DeviceInfo {
  model: string;
  version: string;
  apiLevel: number;
}

const DEVICES: DeviceInfo[] = [
  { model: "Pixel 6", version: "12", apiLevel: 31 },
  { model: "Pixel 5", version: "11", apiLevel: 30 },
  { model: "Samsung Galaxy S21", version: "13", apiLevel: 33 },
  { model: "Oppo Reno 8", version: "12", apiLevel: 31 },
  { model: "Xiaomi Mi 11", version: "12", apiLevel: 31 },
];

const SIG_KEY = [
  0xdf, 0x77, 0xb9, 0x40, 0xb9, 0x9b, 0x84, 0x83, 0xd1, 0xb9, 0xcb, 0xd1,
  0xf7, 0xc2, 0xb9, 0x85, 0xc3, 0xd0, 0xfb, 0xc3,
];

function randomDevice(): DeviceInfo {
  return DEVICES[Math.floor(Math.random() * DEVICES.length)];
}

function md5(data: string): string {
  return createHash("md5").update(data).digest("hex");
}

function reverseByte(n: number): number {
  const hex = n.toString(16).padStart(2, "0");
  return parseInt(hex[1] + hex[0], 16);
}

function generateSignature(
  params: string,
  data: string,
  cookies: string
): { "X-Gorgon": string; "X-Khronos": string } {
  let g = md5(params);
  g += data ? md5(data) : "0".repeat(32);
  g += cookies ? md5(cookies) : "0".repeat(32);
  g += "0".repeat(32);

  const unixTimestamp = Math.floor(Date.now() / 1000);
  const payload: number[] = [];

  for (let i = 0; i < 12; i += 4) {
    const chunk = g.substring(8 * i, 8 * (i + 1));
    for (let j = 0; j < 4; j++) {
      payload.push(parseInt(chunk.substring(j * 2, (j + 1) * 2), 16));
    }
  }

  payload.push(0x0, 0x6, 0xb, 0x1c);
  payload.push(
    (unixTimestamp & 0xff000000) >> 24,
    (unixTimestamp & 0x00ff0000) >> 16,
    (unixTimestamp & 0x0000ff00) >> 8,
    unixTimestamp & 0x000000ff
  );

  let encrypted = payload.map((a, i) => a ^ SIG_KEY[i]);

  for (let i = 0; i < 0x14; i++) {
    const C = reverseByte(encrypted[i]);
    const D = encrypted[(i + 1) % 0x14];
    const F = parseInt(
      ((C ^ D) >>> 0).toString(2).padStart(8, "0").split("").reverse().join(""),
      2
    );
    const H = ((F ^ 0xffffffff) ^ 0x14) & 0xff;
    encrypted[i] = H;
  }

  const signature = encrypted.map((x) => x.toString(16).padStart(2, "0")).join("");

  return {
    "X-Gorgon": "840280416000" + signature,
    "X-Khronos": String(unixTimestamp),
  };
}

function randomHex(bytes: number): string {
  const arr = new Uint8Array(bytes);
  for (let i = 0; i < bytes; i++) arr[i] = Math.floor(Math.random() * 256);
  return Array.from(arr)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function buildRequestData(videoId: string): {
  url: string;
  params: string;
  body: string;
  cookies: string;
  headers: Record<string, string>;
} {
  const device = randomDevice();
  const deviceId = randomInt(600000000000000, 699999999999999);
  const params = [
    `channel=googleplay`,
    `aid=1233`,
    `app_name=musical_ly`,
    `version_code=400304`,
    `device_platform=android`,
    `device_type=${device.model.replace(/ /g, "+")}`,
    `os_version=${device.version}`,
    `device_id=${deviceId}`,
    `os_api=${device.apiLevel}`,
    `app_language=vi`,
    `tz_name=Asia%2FHo_Chi_Minh`,
  ].join("&");

  const url = `https://api16-core-c-alisg.tiktokv.com/aweme/v1/aweme/stats/?${params}`;

  const actionTime = Math.floor(Date.now() / 1000);
  const body = `item_id=${videoId}&play_delta=1&action_time=${actionTime}`;

  const sessionId = randomHex(16);
  const cookies = `sessionid=${sessionId}`;

  const sig = generateSignature(params, body, cookies);

  const headers: Record<string, string> = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "com.ss.android.ugc.trill/400304",
    "Accept-Encoding": "gzip",
    Connection: "keep-alive",
    Cookie: cookies,
    ...sig,
  };

  return { url, params, body, cookies, headers };
}

async function sendOneRequest(videoId: string): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      const { url, body, headers } = buildRequestData(videoId);
      const parsedUrl = new URL(url);
      const lib = parsedUrl.protocol === "https:" ? https : http;

      const options = {
        hostname: parsedUrl.hostname,
        path: parsedUrl.pathname + parsedUrl.search,
        method: "POST",
        headers: {
          ...headers,
          "Content-Length": Buffer.byteLength(body),
        },
        timeout: 20000,
        rejectUnauthorized: false,
      };

      const req = lib.request(options, (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      });

      req.on("error", () => resolve(false));
      req.on("timeout", () => {
        req.destroy();
        resolve(false);
      });

      req.write(body);
      req.end();
    } catch {
      resolve(false);
    }
  });
}

export interface BotStats {
  isRunning: boolean;
  videoUrl?: string;
  videoId?: string;
  totalViews: number;
  elapsedTime: number;
  viewsPerSecond: number;
  viewsPerMinute: number;
  viewsPerHour: number;
  successRate: number;
  successfulRequests: number;
  failedRequests: number;
  peakSpeed: number;
  workers: number;
  startedAt?: number;
}

async function resolveVideoId(url: string): Promise<string | null> {
  const directPatterns = [/\/video\/(\d+)/, /tiktok\.com\/@[^/]+\/(\d+)/, /(\d{18,19})/];
  for (const p of directPatterns) {
    const m = url.match(p);
    if (m) return m[1];
  }

  return new Promise((resolve) => {
    try {
      const parsedUrl = new URL(url);
      const lib = parsedUrl.protocol === "https:" ? https : http;
      const options = {
        hostname: parsedUrl.hostname,
        path: parsedUrl.pathname + parsedUrl.search,
        method: "GET",
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          Accept:
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.5",
          Connection: "keep-alive",
        },
        timeout: 15000,
        rejectUnauthorized: false,
      };

      const req = lib.request(options, (res) => {
        if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          const loc = res.headers.location;
          res.resume();
          const pagePatterns = [
            /\/video\/(\d+)/,
            /"aweme_id":"(\d+)"/,
            /(\d{19})/,
          ];
          for (const p of pagePatterns) {
            const m = loc.match(p);
            if (m) { resolve(m[1]); return; }
          }
        }
        let html = "";
        res.on("data", (chunk) => { html += chunk.toString(); });
        res.on("end", () => {
          const pagePatterns = [
            /"video":\{"id":"(\d+)"/,
            /"aweme_id":"(\d+)"/,
            /\/video\/(\d+)/,
            /(\d{19})/,
          ];
          for (const p of pagePatterns) {
            const m = html.match(p);
            if (m) { resolve(m[1]); return; }
          }
          resolve(null);
        });
      });

      req.on("error", () => resolve(null));
      req.on("timeout", () => { req.destroy(); resolve(null); });
      req.end();
    } catch {
      resolve(null);
    }
  });
}

class ViewBot {
  private count = 0;
  private startTime = 0;
  private isRunning = false;
  private successfulRequests = 0;
  private failedRequests = 0;
  private peakSpeed = 0;
  private videoUrl?: string;
  private videoId?: string;
  private workers = 0;
  private startedAt?: number;
  private workerLoops: Promise<void>[] = [];

  async start(videoUrl: string, requestedWorkers?: number): Promise<{ success: boolean; message: string }> {
    if (this.isRunning) {
      return { success: false, message: "Bot đang chạy rồi! Dừng lại trước khi bắt đầu mới." };
    }

    const videoId = await resolveVideoId(videoUrl);
    if (!videoId) {
      return { success: false, message: "Không thể lấy Video ID từ URL. Kiểm tra lại link TikTok." };
    }

    const numWorkers = requestedWorkers ?? 500;

    this.count = 0;
    this.successfulRequests = 0;
    this.failedRequests = 0;
    this.peakSpeed = 0;
    this.videoUrl = videoUrl;
    this.videoId = videoId ?? undefined;
    this.workers = numWorkers;
    this.startTime = Date.now();
    this.startedAt = Date.now();
    this.isRunning = true;

    this.workerLoops = [];
    for (let i = 0; i < numWorkers; i++) {
      this.workerLoops.push(this.workerLoop());
    }

    return {
      success: true,
      message: `Bot đã khởi động! Video ID: ${videoId} | Workers: ${numWorkers}`,
    };
  }

  private async workerLoop(): Promise<void> {
    let consecutiveSuccess = 0;

    while (this.isRunning) {
      try {
        const success = await sendOneRequest(this.videoId!);
        if (success) {
          this.count++;
          this.successfulRequests++;
          consecutiveSuccess++;
        } else {
          this.failedRequests++;
          consecutiveSuccess = 0;
        }

        const elapsed = (Date.now() - this.startTime) / 1000;
        const vps = elapsed > 0 ? this.count / elapsed : 0;
        if (vps > this.peakSpeed) this.peakSpeed = vps;

        let delay = success ? (consecutiveSuccess > 100 ? 0.5 : consecutiveSuccess > 50 ? 0.7 : 1) : 2;
        if (vps > 500) delay *= 1.5;

        await sleep(delay);
      } catch {
        await sleep(5);
      }
    }
  }

  stop(): { success: boolean; message: string } {
    if (!this.isRunning) {
      return { success: false, message: "Bot không đang chạy." };
    }
    this.isRunning = false;
    return {
      success: true,
      message: `Bot đã dừng! Tổng view gửi: ${this.count.toLocaleString()}`,
    };
  }

  getStats(): BotStats {
    const elapsed = this.isRunning ? (Date.now() - this.startTime) / 1000 : 0;
    const vps = elapsed > 0 ? this.count / elapsed : 0;
    const total = this.successfulRequests + this.failedRequests;
    const successRate = total > 0 ? (this.successfulRequests / total) * 100 : 0;

    return {
      isRunning: this.isRunning,
      videoUrl: this.videoUrl,
      videoId: this.videoId,
      totalViews: this.count,
      elapsedTime: elapsed,
      viewsPerSecond: vps,
      viewsPerMinute: vps * 60,
      viewsPerHour: vps * 3600,
      successRate,
      successfulRequests: this.successfulRequests,
      failedRequests: this.failedRequests,
      peakSpeed: this.peakSpeed,
      workers: this.workers,
      startedAt: this.startedAt,
    };
  }

  getStatus() {
    return {
      isRunning: this.isRunning,
      videoUrl: this.videoUrl,
      videoId: this.videoId,
      startedAt: this.startedAt,
    };
  }
}

function sleep(seconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, seconds * 1000));
}

export const viewBot = new ViewBot();
