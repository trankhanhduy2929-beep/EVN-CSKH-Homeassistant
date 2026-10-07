import { createServer } from "node:http";
import { mkdir, readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire("/opt/work-apps/bhyt-tools/web/package.json");
const { chromium } = require("playwright");

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const panelFile = join(root, "custom_components", "evn_cskh", "frontend", "evn-cskh-panel.js");
const outDir = join(root, "analysis", "ui-preview");

const results = [];
function check(name, condition) {
  results.push({ name, ok: Boolean(condition) });
  if (!condition) throw new Error(`FAILED: ${name}`);
}

const customer = {
  key: "PB:PC01",
  code: "PC01",
  name: "Nguyễn <img src=x onerror=alert(1)> Văn A",
  unit: "PC01",
  region: "PB",
  available: true,
  points: [{ id: "PD01", address: "12 Lê Lợi, Quận 1" }],
};

const data = {
  entries: [{ entry_id: "entry-1", title: "EVN CSKH", customers: [customer] }],
  overview: {
    customer: { key: "PB:PC01", code: "PC01", name: "Nguyễn Văn A", unit: "PC01", region: "PB" },
    available: true,
    fetched_at: "2026-10-07T10:00:00+07:00",
    usage: [{ point_id: "PD01", monthly: { period: "2026-09", kwh: 873 }, daily: { period: "06/10/2026", kwh: 18.12 } }],
    outstanding: { amount: 0, count: 0 },
    outages: [{ start: "2026-10-11T07:00:00+07:00", end: "2026-10-11T17:30:00+07:00", area: "Khu phố 3", reason: "Bảo trì lưới" }],
    next_outage: { start: "2026-10-11T07:00:00+07:00", end: "2026-10-11T17:30:00+07:00", area: "Khu phố 3", reason: "Bảo trì lưới" },
  },
  details: {
    customer: { key: "PB:PC01", code: "PC01", name: "Nguyễn Văn A", unit: "PC01", region: "PB" },
    point_id: "PD01",
    start: "2026-01-01",
    end: "2026-10-06",
    fetched_at: "2026-10-07T10:00:00+07:00",
    monthly: [{ period: "2026-07", kwh: 512 }, { period: "2026-08", kwh: 601 }, { period: "2026-09", kwh: 873 }],
    daily: [{ period: "05/10/2026", kwh: 17.4 }, { period: "06/10/2026", kwh: 18.12 }],
    readings: [{ period: "2026-09", meter: "CT01", register: "KT", old: 1000, new: 1873, multiplier: 1, kwh: 873, kind: "monthly" }],
    invoices: [
      { key: "opaque-1", period: "09/2026", cycle: 9, amount: 1520000, tax: 138000, outstanding: 0, status: "DATT", status_label: "Đã thanh toán", paid_date: "20/09/2026", due_date: "25/09/2026", energy: 873, energy_unit: "kWh", documents: ["invoice", "statement", "notice"] },
      { key: "opaque-2", period: "10/2026", cycle: 10, amount: 640000, tax: 58000, outstanding: 640000, status: "CHUATT", status_label: "Chưa thanh toán", paid_date: "", due_date: "25/10/2026", energy: 120.5, energy_unit: "kWh", documents: ["invoice"] },
    ],
  },
};

const pageScript = `
window.__data = ${JSON.stringify(data)};
window.__mock = (options = {}) => {
  const data = window.__pending || window.__data;
  const base = {
    user: { id: "user-1", is_admin: options.admin !== false },
    connection: {},
    themes: { darkMode: Boolean(options.dark) },
    locale: { language: "vi" },
    states: {},
  };
  return Object.assign(base, {
    async callWS(message) {
      if (data.error) throw data.error;
      if (message.type === "evn_cskh/list_entries") return { entries: data.entries };
      if (message.type === "evn_cskh/overview") return data.overview;
      if (message.type === "evn_cskh/details") return data.details;
      throw { code: "invalid_response" };
    },
    async fetchWithAuth() {
      const bytes = new TextEncoder().encode("%PDF-1.7\\nmock\\n%%EOF\\n");
      return new Response(bytes, { status: 200, headers: { "content-type": "application/pdf" } });
    },
  });
};
`;

async function attach(page, options = {}) {
  await page.evaluate(opts => {
    const element = document.getElementById("p");
    element.hass = window.__mock(opts);
  }, options);
}

async function settled(page) {
  await page.waitForFunction(() => {
    const root = document.getElementById("p").shadowRoot;
    return root && root.textContent.includes("Điện năng tháng gần nhất");
  });
}

async function main() {
  await mkdir(outDir, { recursive: true });
  const source = await readFile(panelFile, "utf8");
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>:root{--primary-color:#0b74b8;--primary-text-color:#1c1c1c;--secondary-text-color:#5c6169;--card-background-color:#fff;--primary-background-color:#f2f4f7;--divider-color:#d7dbe0;--text-primary-color:#fff;--error-color:#c0392b}</style></head><body style="margin:0"><evn-cskh-panel id="p"></evn-cskh-panel><script>${pageScript}<\/script><script type="module" src="/evn-cskh-panel.js"></script></body></html>`;
  const server = createServer((request, response) => {
    if (request.url.startsWith("/evn-cskh-panel.js")) {
      response.writeHead(200, { "content-type": "text/javascript" });
      response.end(source);
      return;
    }
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    response.end(html);
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const url = `http://127.0.0.1:${server.address().port}/`;

  const browser = await chromium.launch();
  let failure = null;
  const consoleErrors = [];
  let page = null;
  try {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
    page = await context.newPage();
    page.on("console", message => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", error => consoleErrors.push(String(error)));

    await page.goto(url);
    await attach(page);
    await settled(page);

    const shadowText = () => page.evaluate(() => document.getElementById("p").shadowRoot.textContent);

    let text = await shadowText();
    check("tab labels", ["Tổng quan", "Điện năng", "Hóa đơn", "Lịch ngừng điện"].every(label => text.includes(label)));
    check("overview energy kwh", text.includes("873"));
    check("overview daily kwh", text.includes("18,12") || text.includes("18.12"));
    check("next outage shown", text.includes("Khu phố 3") && text.includes("Bảo trì lưới"));
    check("xss safe (no injected img)", (await page.evaluate(() => document.getElementById("p").shadowRoot.querySelectorAll("img").length)) === 0);
    await page.screenshot({ path: join(outDir, "desktop-overview.png"), fullPage: true });

    await page.evaluate(() => {
      [...document.getElementById("p").shadowRoot.querySelectorAll("[data-action=tab]")].find(node => node.dataset.tab === "2").click();
    });
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.querySelectorAll("[data-action=invoice]").length >= 2);
    check("invoice rows rendered", (await page.evaluate(() => document.getElementById("p").shadowRoot.querySelectorAll("[data-action=invoice]").length)) >= 2);
    await page.screenshot({ path: join(outDir, "desktop-invoices.png"), fullPage: true });

    await page.evaluate(() => document.getElementById("p").shadowRoot.querySelector("[data-action=invoice]").click());
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.querySelector("dialog[open]") !== null);
    const dialog = await page.evaluate(() => document.getElementById("p").shadowRoot.querySelector("dialog").textContent);
    check("invoice dialog content", dialog.includes("09/2026") && dialog.includes("Đã thanh toán"));

    const downloadPromise = page.waitForEvent("download");
    await page.evaluate(() => {
      [...document.getElementById("p").shadowRoot.querySelectorAll("[data-action=pdf]")].find(node => node.dataset.kind === "invoice").click();
    });
    const download = await downloadPromise;
    check("invoice pdf filename", /^evn-invoice-09-2026\.pdf$/.test(download.suggestedFilename()));
    await page.screenshot({ path: join(outDir, "desktop-invoice-dialog.png"), fullPage: true });

    await page.evaluate(() => document.getElementById("p").shadowRoot.querySelector("[data-action=close-invoice]").click());
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.querySelector("dialog[open]") === null);
    check("dialog closes", true);

    await page.evaluate(() => {
      const button = [...document.getElementById("p").shadowRoot.querySelectorAll("button")].find(node => node.textContent.trim().length);
      button.focus();
      window.__focusOk = document.getElementById("p").shadowRoot.activeElement === button;
    });
    check("focus visible in shadow root", await page.evaluate(() => window.__focusOk === true));

    await page.setViewportSize({ width: 375, height: 812 });
    await page.evaluate(() => {
      const element = document.getElementById("p");
      element.narrow = true;
    });
    await page.waitForTimeout(50);
    const overflow = await page.evaluate(() => {
      const element = document.getElementById("p");
      const shell = element.shadowRoot.querySelector(".shell");
      return {
        document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        panel: element.scrollWidth - element.clientWidth,
        shell: shell ? shell.scrollWidth - shell.clientWidth : 0,
      };
    });
    check("mobile 375 no horizontal scroll", overflow.document <= 1 && overflow.panel <= 1 && overflow.shell <= 1);
    check("mobile menu visible", await page.evaluate(() => {
      const menu = document.getElementById("p").shadowRoot.getElementById("menu");
      return menu ? getComputedStyle(menu).display !== "none" : false;
    }));
    await page.screenshot({ path: join(outDir, "mobile-375-overview.png"), fullPage: true });

    await page.evaluate(() => {
      const element = document.getElementById("p");
      element.hass = window.__mock({ dark: true });
    });
    await page.waitForTimeout(50);
    check("dark mode attribute", await page.evaluate(() => document.getElementById("p").hasAttribute("dark")));
    await page.screenshot({ path: join(outDir, "dark-overview.png"), fullPage: true });

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.evaluate(() => {
      window.__pending = { error: { code: "invalid_response" } };
      document.getElementById("p").hass = window.__mock({});
    });
    await page.waitForFunction(() => {
      const root = document.getElementById("p").shadowRoot;
      return root && /thử lại|Không thể|Lỗi|không hợp lệ/i.test(root.textContent);
    });
    check("error state rendered", /thử lại|Không thể|Lỗi|không hợp lệ/i.test(await shadowText()));
    await page.screenshot({ path: join(outDir, "desktop-error.png"), fullPage: true });

    await page.evaluate(() => {
      delete window.__pending;
      window.__data = { entries: [{ entry_id: "entry-1", title: "EVN CSKH", customers: [] }] };
      document.getElementById("p").hass = window.__mock({});
    });
    await page.waitForFunction(() => {
      const root = document.getElementById("p").shadowRoot;
      return root && root.textContent.length > 0 && !root.textContent.includes("Điện năng tháng gần nhất");
    });
    check("empty list state", (await shadowText()).length > 0);

    await page.evaluate(value => {
      window.__data = value;
      document.getElementById("p").hass = window.__mock({ admin: false });
    }, data);
    await page.waitForTimeout(80);
    check("non-admin shows no account data", !/873|09\/2026/.test(await shadowText()));

    check("no console errors", consoleErrors.filter(item => !item.includes("favicon")).length === 0);
  } catch (error) {
    failure = error;
  } finally {
    await browser.close();
    server.close();
  }

  console.log(JSON.stringify({ passed: results.filter(item => item.ok).length, total: results.length }));
  for (const item of results) console.log(`${item.ok ? "ok" : "FAIL"}  ${item.name}`);
  if (failure) {
    console.error(String(failure));
    console.error("consoleErrors", JSON.stringify(consoleErrors));
    if (page) {
      const dump = await page.evaluate(() => {
        const element = document.getElementById("p");
        if (!element) return "no-element";
        const root = element.shadowRoot;
        return root ? root.innerHTML.slice(0, 500) : "no-shadow";
      }).catch(error => String(error));
      console.error("shadow", dump);
    }
    process.exit(1);
  }
}

main();
