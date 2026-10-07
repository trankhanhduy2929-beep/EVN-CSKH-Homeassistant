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

const xssName = "Nguyễn <img src=x onerror=alert(1)> Văn A";

const customer = {
  key: "PB:PC01",
  code: "PC01",
  name: xssName,
  unit: "PC01",
  region: "PB",
  available: true,
  points: [
    { id: "PD01", address: "12 Lê Lợi, Quận 1", contract: "HĐ000123", valid_from: "01/01/2024" },
    { id: "PD02", address: "8 Hai Bà Trưng, Quận 1", contract: "HĐ000456", valid_from: "15/03/2025" }
  ],
};

const invoice = (key, period, cycle, amount, tax, outstanding, status, label, paidDate, dueDate, energy, org, channel, docs) => ({
  key, period, cycle, amount, tax, outstanding, status, status_label: label, paid_date: paidDate, due_date: dueDate,
  org_code: org, payment_channel_label: channel, energy, energy_unit: "kWh", documents: docs
});

const outageAt = "2026-10-11T07:00:00+07:00";
const formattedOutage = new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", dateStyle: "short", timeStyle: "short" }).format(new Date(outageAt));

const data = {
  entries: [{ entry_id: "entry-1", title: "EVN CSKH", customers: [customer] }],
  overview: {
    customer: { key: "PB:PC01", code: "PC01", name: "Nguyễn Văn A", unit: "PC01", region: "PB" },
    available: true,
    fetched_at: "2026-10-07T10:00:00+07:00",
    info: {
      name: "Nguyễn Văn A", address: "12 Lê Lợi, Phường Bến Thành, Thành phố Hồ Chí Minh", phone: "0901234567",
      customer_type: "Khách hàng sinh hoạt", subject_type: "Cá nhân", region_code: "PB", province: "Thành phố Hồ Chí Minh",
      commune: "Phường Bến Thành", contract: "HĐ000123", pay_reference: "PC0123456", alert_count: 2,
      default_contract: true, pay_on_behalf: "Không"
    },
    contracts: [
      { number: "HĐ000123", address: "12 Lê Lợi", unit: "PC01" },
      { number: "HĐ000456", address: "8 Hai Bà Trưng", unit: "PC01" }
    ],
    banks: [
      { code: "VCB", name: "Ngân hàng Ngoại thương Việt Nam" },
      { code: "TCB", name: "Ngân hàng Kỹ thương Việt Nam" },
      { code: "MB", name: "Ngân hàng Quân đội" },
      { code: "ACB", name: "Ngân hàng Á Châu" }
    ],
    usage: [
      {
        point_id: "PD01",
        monthly: { period: "2026-09", kwh: 873 },
        daily: { period: "06/10/2026", kwh: 18.12 },
        mom: { current: 873, previous: 800, delta: 73, percent: 9.125 },
        average_12m: 654.25,
        reading: { period: "2026-09", old: 1000, new: 1873, multiplier: 1, kwh: 873, kind: "monthly" }
      },
      {
        point_id: "PD02",
        monthly: { period: "2026-09", kwh: 152.5 },
        daily: null,
        mom: null,
        average_12m: 140.5,
        reading: null
      }
    ],
    outstanding: { amount: 1640000, count: 2 },
    invoices: [
      invoice("disp-a1", "09/2026", 9, 1520000, 138000, 0, "DATT", "Đã thanh toán", "20/09/2026", "25/09/2026", 873, "VCB", "Quầy VCB", []),
      invoice("disp-a2", "10/2026", 10, 120000, 11000, 120000, "CHUATT", "Chưa thanh toán", "", "25/10/2026", 60.25, "TCB", "", [])
    ],
    paid_count: 5,
    paid_recent: [
      invoice("disp-p1", "08/2026", 8, 1450000, 132000, 0, "DATT", "Đã thanh toán", "18/08/2026", "25/08/2026", 800, "MB", "App MB", []),
      invoice("disp-p2", "07/2026", 7, 1300000, 118000, 0, "DATT", "Đã thanh toán", "19/07/2026", "25/07/2026", 720, "VCB", "Internet VCB", [])
    ],
    outages: [{ start: "2026-10-11T07:00:00+07:00", end: "2026-10-11T17:30:00+07:00", area: "Khu phố 3", reason: "Bảo trì lưới" }],
    outage_count: 1,
    next_outage: { start: "2026-10-11T07:00:00+07:00", end: "2026-10-11T17:30:00+07:00", area: "Khu phố 3", reason: "Bảo trì lưới" }
  },
  details: {
    customer: { key: "PB:PC01", code: "PC01", name: "Nguyễn Văn A", unit: "PC01", region: "PB" },
    point_id: "PD01",
    start: "2025-10-01",
    end: "2026-10-07",
    fetched_at: "2026-10-07T10:05:00+07:00",
    monthly: [
      { period: "2025-10", kwh: 402 }, { period: "2025-11", kwh: 430 }, { period: "2025-12", kwh: 455 },
      { period: "2026-01", kwh: 512 }, { period: "2026-02", kwh: 498 }, { period: "2026-03", kwh: 540 },
      { period: "2026-04", kwh: 601 }, { period: "2026-05", kwh: 655 }, { period: "2026-06", kwh: 702 },
      { period: "2026-07", kwh: 730 }, { period: "2026-08", kwh: 800 }, { period: "2026-09", kwh: 873 }
    ],
    daily: [{ period: "05/10/2026", kwh: 17.4 }, { period: "06/10/2026", kwh: 18.12 }],
    readings: [
      { period: "2026-09", meter: "CT01", register: "KT1", old: 1000, new: 1873, multiplier: 1, kwh: 873, kind: "monthly" },
      { period: "06/10/2026", meter: "CT01", register: "KT1", old: 1873, new: 1891, multiplier: 1, kwh: 18.12, kind: "daily" }
    ],
    invoices: [
      invoice("pdf-key-1", "09/2026", 9, 1520000, 138000, 0, "DATT", "Đã thanh toán", "20/09/2026", "25/09/2026", 873, "VCB", "Quầy VCB", ["invoice", "statement", "notice"]),
      invoice("pdf-key-2", "10/2026", 10, 120000, 11000, 120000, "CHUATT", "Chưa thanh toán", "", "25/10/2026", 60.25, "TCB", "", ["invoice"])
    ]
  }
};

const pageScript = `
window.__data = ${JSON.stringify(data)};
window.__wsCalls = 0;
window.__fetchLog = [];
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
      window.__wsCalls += 1;
      if (data.error) throw data.error;
      if (message.type === "evn_cskh/list_entries") return { entries: data.entries };
      if (message.type === "evn_cskh/overview") return data.overview;
      if (message.type === "evn_cskh/details") return data.details;
      throw { code: "invalid_response" };
    },
    async fetchWithAuth(url) {
      window.__fetchLog.push(url);
      const bytes = new TextEncoder().encode("%PDF-1.7\\nmock\\n%%EOF\\n");
      return new Response(bytes, { status: 200, headers: { "content-type": "application/pdf" } });
    },
  });
};
`;

async function attach(page, options = {}) {
  await page.evaluate(opts => {
    document.getElementById("p").hass = window.__mock(opts);
  }, options);
}

async function settled(page) {
  await page.waitForFunction(() => {
    const root = document.getElementById("p").shadowRoot;
    return root && root.textContent.includes("Sản lượng tháng này") && root.textContent.includes("1.873");
  });
}

async function clickTab(page, index) {
  await page.evaluate(tab => {
    [...document.getElementById("p").shadowRoot.querySelectorAll("[data-action=tab]")].find(node => node.dataset.tab === tab).click();
  }, String(index));
}

async function main() {
  await mkdir(outDir, { recursive: true });
  const source = await readFile(panelFile, "utf8");
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>:root{--primary-color:#0b74b8;--primary-text-color:#1c1c1c;--secondary-text-color:#5c6169;--card-background-color:#fff;--primary-background-color:#f2f4f7;--divider-color:#d7dbe0;--text-primary-color:#fff;--error-color:#c0392b;--success-color:#168039;--warning-color:#9b6511}</style></head><body style="margin:0"><evn-cskh-panel id="p"></evn-cskh-panel><script>${pageScript}<\/script><script type="module" src="/evn-cskh-panel.js"></script></body></html>`;
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
    const imgCount = () => page.evaluate(() => document.getElementById("p").shadowRoot.querySelectorAll("img").length);

    let text = await shadowText();
    check("six tab labels", ["Tổng quan", "Điện năng", "Công tơ", "Hóa đơn", "Lịch ngừng điện", "Thông tin"].every(label => text.includes(label)));
    check("overview monthly kwh", text.includes("873 kWh"));
    check("overview mom percent", text.includes("+9,1%"));
    check("overview average 12m", text.includes("654,25"));
    check("overview latest index", text.includes("1.873"));
    check("overview outstanding", text.includes("1.640.000") && text.includes("2 hóa đơn chưa trả"));
    check("overview next outage", text.includes(formattedOutage) && text.includes("Khu phố 3"));
    check("overview point summary", text.includes("Tóm tắt theo điểm đo") && text.includes("PD02"));
    check("xss literal only", text.includes("<img src=x onerror=alert(1)>") && (await imgCount()) === 0);
    check("no display keys leak", !text.includes("disp-"));
    check("select shows code and unit", text.includes("PC01 · PC01"));
    await page.screenshot({ path: join(outDir, "desktop-overview.png"), fullPage: true });

    await page.evaluate(() => document.getElementById("p").shadowRoot.getElementById("tab-0").focus());
    await page.keyboard.press("ArrowRight");
    check("arrow key tab nav", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      return root.activeElement?.id === "tab-1" && root.getElementById("tab-1").getAttribute("aria-selected") === "true";
    }));
    await page.keyboard.press("End");
    check("end key tab nav", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      return root.activeElement?.id === "tab-5" && root.getElementById("tab-5").getAttribute("aria-selected") === "true";
    }));

    await clickTab(page, 1);
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.querySelector(".chart") !== null);
    text = await shadowText();
    check("energy chart rendered", await page.evaluate(() => document.getElementById("p").shadowRoot.querySelectorAll(".chart-column").length) >= 12);
    check("energy table monthly", text.includes("Bảng số liệu") && text.includes("2026-09"));
    await page.evaluate(() => [...document.getElementById("p").shadowRoot.querySelectorAll("[data-action=period]")].find(node => node.dataset.value === "daily").click());
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.textContent.includes("05/10/2026"));
    check("energy daily toggle", (await shadowText()).includes("05/10/2026"));
    await page.evaluate(() => [...document.getElementById("p").shadowRoot.querySelectorAll("[data-action=period]")].find(node => node.dataset.value === "monthly").click());

    await clickTab(page, 2);
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.textContent.includes("Lịch sử chỉ số công tơ"));
    text = await shadowText();
    check("meter latest reading block", text.includes("Chỉ số mới nhất") || text.includes("Chỉ số mới"));
    check("meter per point empty", text.includes("Chưa có chỉ số cho điểm đo này"));
    check("meter readings table", text.includes("CT01") && text.includes("KT1"));
    check("meter table rows", await page.evaluate(() => document.getElementById("p").shadowRoot.querySelectorAll("#reading-results tbody tr").length) >= 2);
    await page.screenshot({ path: join(outDir, "desktop-meter.png"), fullPage: true });

    await clickTab(page, 3);
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.querySelectorAll("[data-action=invoice]").length >= 2);
    text = await shadowText();
    check("invoice outstanding banner", text.includes("Tổng tiền còn phải trả: 1.640.000"));
    check("invoice rows rendered", await page.evaluate(() => document.getElementById("p").shadowRoot.querySelectorAll("[data-action=invoice]").length) >= 2);
    check("paid history table", text.includes("Lịch sử thanh toán") && text.includes("App MB"));
    check("details pdf keys hidden", !text.includes("pdf-key"));
    await page.screenshot({ path: join(outDir, "desktop-invoices.png"), fullPage: true });

    await page.evaluate(() => {
      const button = document.getElementById("p").shadowRoot.querySelector("[data-action=invoice]");
      button.focus();
      button.click();
    });
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.querySelector("dialog[open]") !== null);
    const dialog = await page.evaluate(() => document.getElementById("p").shadowRoot.querySelector("dialog").textContent);
    check("invoice dialog content", dialog.includes("09/2026") && dialog.includes("Đã thanh toán") && dialog.includes("Kỳ thu") && dialog.includes("Quầy VCB"));

    const downloadPromise = page.waitForEvent("download");
    await page.evaluate(() => {
      [...document.getElementById("p").shadowRoot.querySelectorAll("[data-action=pdf]")].find(node => node.dataset.kind === "invoice").click();
    });
    const download = await downloadPromise;
    check("invoice pdf filename", /^evn-invoice-09-2026\.pdf$/.test(download.suggestedFilename()));
    check("pdf used details key", await page.evaluate(() => window.__fetchLog.includes("/api/evn_cskh/invoice/entry-1/pdf-key-1/invoice")));
    await page.screenshot({ path: join(outDir, "desktop-invoice-dialog.png"), fullPage: true });

    await page.keyboard.press("Escape");
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.querySelector("dialog[open]") === null);
    check("dialog closes on escape", true);
    check("dialog focus restored", await page.evaluate(() => document.getElementById("p").shadowRoot.activeElement?.id === "invoice-0"));

    await clickTab(page, 4);
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.textContent.includes("kế hoạch ngừng điện"));
    text = await shadowText();
    check("outages count", text.includes("1 kế hoạch ngừng điện"));
    check("outages plan note", text.includes("không phải trạng thái mất điện thực tế"));
    check("outages detail", text.includes("Bảo trì lưới") && text.includes(formattedOutage));

    await clickTab(page, 5);
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.textContent.includes("Tổ chức thanh toán"));
    text = await shadowText();
    check("info customer fields", text.includes("0901234567") && text.includes("PC0123456") && text.includes("HĐ000123"));
    check("info alert count", text.includes("2 cảnh báo"));
    check("info default contract", text.includes("Hợp đồng mặc định"));
    check("info contracts table", text.includes("8 Hai Bà Trưng"));
    check("info banks used marks", text.includes("Ngân hàng Ngoại thương Việt Nam") && text.includes("Đã dùng") && text.includes("Chưa dùng"));
    check("info points table", text.includes("Hiệu lực từ") && text.includes("15/03/2025"));
    await page.screenshot({ path: join(outDir, "desktop-info.png"), fullPage: true });

    await clickTab(page, 0);
    await settled(page);
    await page.setViewportSize({ width: 375, height: 812 });
    await page.evaluate(() => { document.getElementById("p").narrow = true; });
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

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.evaluate(() => { document.getElementById("p").narrow = false; });
    await attach(page, { dark: true });
    await settled(page);
    check("dark mode attribute", await page.evaluate(() => document.getElementById("p").hasAttribute("dark")));
    await page.screenshot({ path: join(outDir, "dark-overview.png"), fullPage: true });

    const callsBefore = await page.evaluate(() => window.__wsCalls);
    await attach(page, { admin: false });
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.textContent.includes("Chỉ dành cho quản trị viên"));
    check("non-admin lock shown", (await shadowText()).includes("Chỉ dành cho quản trị viên"));
    check("non-admin no ws calls", (await page.evaluate(() => window.__wsCalls)) === callsBefore);
    check("non-admin hides data", !/873|1\.640\.000/.test(await shadowText()));

    await page.evaluate(() => {
      window.__pending = { error: { code: "invalid_response" } };
      document.getElementById("p").hass = window.__mock({});
    });
    await page.waitForFunction(() => {
      const root = document.getElementById("p").shadowRoot;
      return root && /Thử lại|không hợp lệ|hết hạn/i.test(root.textContent);
    });
    check("error state rendered", /Thử lại/i.test(await shadowText()));
    await page.screenshot({ path: join(outDir, "desktop-error.png"), fullPage: true });

    await page.evaluate(() => {
      delete window.__pending;
      window.__data = { entries: [{ entry_id: "entry-1", title: "EVN CSKH", customers: [] }] };
      document.getElementById("p").hass = window.__mock({});
    });
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.textContent.includes("Chưa có khách hàng được liên kết"));
    check("empty list state", (await shadowText()).includes("Chưa có khách hàng được liên kết"));

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
