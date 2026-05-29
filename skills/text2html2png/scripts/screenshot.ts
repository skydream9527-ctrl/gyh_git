import puppeteer from "puppeteer-core";
import path from "node:path";
import process from "node:process";
import { mkdir } from "node:fs/promises";
import { execSync } from "node:child_process";

type CliArgs = {
  html: string | null;
  out: string | null;
  bg: string;
  width: number;
  padding: number;
  help: boolean;
};

function printUsage(): void {
  console.log(`Usage:
  npx -y bun screenshot.ts --html <file> --out <file> [--bg <color>] [--width <px>] [--padding <px>]

Options:
  --html <path>       Input HTML file path (required)
  --out <path>        Output PNG file path (required)
  --bg <color>        Background color for padding area (default: #ffffff)
  --width <px>        Viewport width in pixels (default: 860)
  --padding <px>      Padding around content (default: 32)
  -h, --help          Show help`);
}

function parseArgs(argv: string[]): CliArgs {
  const out: CliArgs = {
    html: null,
    out: null,
    bg: "#ffffff",
    width: 860,
    padding: 32,
    help: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]!;
    if (a === "--help" || a === "-h") { out.help = true; continue; }
    if (a === "--html") { out.html = argv[++i] || null; continue; }
    if (a === "--out") { out.out = argv[++i] || null; continue; }
    if (a === "--bg") { out.bg = argv[++i] || "#ffffff"; continue; }
    if (a === "--width") { out.width = parseInt(argv[++i] || "860", 10); continue; }
    if (a === "--padding") { out.padding = parseInt(argv[++i] || "32", 10); continue; }
    if (a.startsWith("-")) throw new Error(`Unknown option: ${a}`);
  }
  return out;
}

/** Find system Chrome executable */
function findChrome(): string {
  const candidates =
    process.platform === "win32"
      ? [
          process.env["PROGRAMFILES"] + "\\Google\\Chrome\\Application\\chrome.exe",
          process.env["PROGRAMFILES(X86)"] + "\\Google\\Chrome\\Application\\chrome.exe",
          process.env["LOCALAPPDATA"] + "\\Google\\Chrome\\Application\\chrome.exe",
        ]
      : process.platform === "darwin"
        ? [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
          ]
        : [
            "google-chrome",
            "google-chrome-stable",
            "chromium-browser",
            "chromium",
          ];

  for (const cmd of candidates) {
    try {
      if (process.platform === "win32") {
        // on Windows, candidates are already full paths
        const { statSync } = require("fs");
        statSync(cmd);
        return cmd;
      } else {
        // resolve command name to full path
        const fullPath = execSync(`which "${cmd}" 2>/dev/null`, { stdio: "pipe" })
          .toString()
          .trim();
        if (fullPath) return fullPath;
      }
    } catch {
      // not found, try next
    }
  }

  throw new Error(
    "Chrome not found. Please install Google Chrome.\n" +
    "  https://www.google.com/chrome/"
  );
}

async function screenshot(args: CliArgs): Promise<void> {
  const htmlPath = path.resolve(args.html!);
  const outPath = path.resolve(args.out!);
  const pad = args.padding;

  await mkdir(path.dirname(outPath), { recursive: true });

  const chromePath = findChrome();
  console.error(`[info] using Chrome: ${chromePath}`);

  const browser = await puppeteer.launch({
    executablePath: chromePath,
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const page = await browser.newPage();

    // Phase 1: measure content in a tall viewport
    await page.setViewport({ width: args.width, height: 4000, deviceScaleFactor: 4 });
    await page.goto(`file://${htmlPath}`, { waitUntil: "networkidle0" });

    // wait for fonts
    await page.evaluate(() => document.fonts.ready);

    // measure .wrap or body
    const box = await page.evaluate(() => {
      const el = document.querySelector(".wrap") || document.body;
      const r = el.getBoundingClientRect();
      return { x: r.x, y: r.y, width: r.width, height: r.height };
    });

    // Phase 2: resize viewport to exact content height + padding, then screenshot
    const clipX = Math.max(0, box.x - pad);
    const clipY = Math.max(0, box.y - pad);
    const clipW = box.width + pad * 2;
    const clipH = box.height + pad * 2;
    const viewportH = Math.ceil(clipY + clipH + 10);

    await page.setViewport({ width: args.width, height: viewportH, deviceScaleFactor: 4 });

    // set html background color to fill padding area
    await page.evaluate((bg: string) => {
      document.documentElement.style.backgroundColor = bg;
    }, args.bg);

    // let layout settle
    await new Promise((r) => setTimeout(r, 150));

    await page.screenshot({
      path: outPath,
      type: "png",
      clip: { x: clipX, y: clipY, width: clipW, height: clipH },
    });

    console.log(outPath);
  } finally {
    await browser.close();
  }
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));

  if (args.help) { printUsage(); return; }
  if (!args.html) { console.error("Error: --html is required"); printUsage(); process.exitCode = 1; return; }
  if (!args.out) { console.error("Error: --out is required"); printUsage(); process.exitCode = 1; return; }

  await screenshot(args);
}

main().catch((e) => {
  console.error(e instanceof Error ? e.message : String(e));
  process.exit(1);
});
