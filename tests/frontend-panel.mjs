import { createServer } from "node:http";
import { mkdir, readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(process.env.EVN_PLAYWRIGHT_BASE || import.meta.url);
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
  payable_amount: status === "DATT" ? 0 : (status === "CHUATT" || (status === "TTOANMOTPHAN" && label !== "Đã hoàn trả một phần")) && typeof outstanding === "number" && Number.isFinite(outstanding) ? Math.abs(outstanding) : null,
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
    comparisons: {
      as_of: "2026-10-07",
      points: [
        { point_id: "PD01", daily: [{ period: "2026-10-05", kwh: 34.76, provisional: true }, { period: "2026-10-06", kwh: 0, provisional: true }, { period: "2026-10-07", kwh: null, provisional: true }] },
        { point_id: "PD02", daily: [{ period: "2026-10-05", kwh: null, provisional: true }, { period: "2026-10-06", kwh: 7.25, provisional: true }, { period: "2026-10-07", kwh: 1.5, provisional: true }] }
      ],
      monthly: [
        { period: "2026-08", kwh: 910.25, vnd: 1754321, provisional: false },
        { period: "2026-09", kwh: 1025.5, vnd: 0, provisional: false },
        { period: "2026-10", kwh: 82.25, vnd: null, provisional: true }
      ]
    },
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
    daily_window: { start: "2026-09-07", end: "2026-10-07" },
    monthly: [
      { period: "2025-10", kwh: 402 }, { period: "2025-11", kwh: 430 }, { period: "2025-12", kwh: 455 },
      { period: "2026-01", kwh: 512 }, { period: "2026-02", kwh: 498 }, { period: "2026-03", kwh: 540 },
      { period: "2026-04", kwh: 601 }, { period: "2026-05", kwh: 655 }, { period: "2026-06", kwh: 702 },
      { period: "2026-07", kwh: 730 }, { period: "2026-08", kwh: 800 }, { period: "2026-09", kwh: 873 }
    ],
    daily: [{ period: "05/10/2026", kwh: 17.4 }, { period: "06/10/2026", kwh: 18.12 }, { period: "01/10/2026", kwh: 12.75 }, { period: "28/09/2026 - 30/09/2026", kwh: 41.2 }],
    readings: [
      { period: "2026-09", timestamp: null, reading_date: "2026-09-29", resolution: "day", meter: "CT01", register: "KT1", old: 1000, new: 1873, multiplier: 1, kwh: 873, kind: "monthly" },
      { period: "2026-07", timestamp: null, reading_date: "2026-07-28", resolution: "day", meter: "CT01", register: "KT1", old: 200, new: 750, multiplier: 1, kwh: 550, kind: "monthly" },
      { period: "2026-08", timestamp: null, reading_date: "2026-08-29", resolution: "day", meter: "CT01", register: "KT1", old: 750, new: 1000, multiplier: 1, kwh: 250, kind: "monthly" },
      ...Array.from({ length: 23 }, (_, index) => {
        const day = String(6 + Math.floor(index / 12)).padStart(2, "0");
        const hour = String(index % 12).padStart(2, "0");
        return { period: `${day}/10/2026`, timestamp: `2026-10-${day}T${hour}:00:00+07:00`, reading_date: `2026-10-${day}`, resolution: "time", meter: "CT01", register: "KT1", old: 1873 + index, new: index === 10 ? null : 1874 + index, multiplier: 2, kwh: 2, kind: "daily" };
      }).reverse(),
      { period: "2026-09", timestamp: null, reading_date: "2026-09-29", resolution: "day", meter: "CT02", register: "KT1", old: 0, new: 102, multiplier: 10, kwh: 1020, kind: "monthly" },
      { period: "2026-08", timestamp: null, reading_date: "2026-08-29", resolution: "day", meter: "CT02", register: "KT1", old: 0, new: 85, multiplier: 10, kwh: 850, kind: "monthly" },
      { period: "2026-09", timestamp: null, reading_date: "2026-09-30", resolution: "day", meter: "CT03", register: "KT2", old: null, new: 0, multiplier: 1, kwh: null, kind: "monthly" }
    ],
    invoices: [
      invoice("pdf-key-1", "09/2026", 9, 1520000, 138000, 1520000, "DATT", "Đã thanh toán", "20/09/2026", "25/09/2026", 873, "VCB", "Quầy VCB", ["invoice", "statement", "notice"]),
      invoice("pdf-key-2", "10/2026", 10, 120000, 11000, 120000, "CHUATT", "Chưa thanh toán", "", "25/10/2026", 60.25, "TCB", "", ["invoice"])
    ]
  }
};

const pageScript = `
window.__data = ${JSON.stringify(data)};
window.__wsCalls = 0;
window.__wsLog = [];
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
      window.__wsLog.push(message);
      if (data.error) throw data.error;
      if (message.type === "evn_cskh/list_entries") return { entries: data.entries };
      if (message.type === "evn_cskh/overview") {
        if (window.__overviewWait) await window.__overviewWait;
        return data.overview;
      }
      if (message.type === "evn_cskh/details") {
        if (window.__detailsWait) await window.__detailsWait;
        const dailyStart = new Date(Math.max(Date.parse(message.start), Date.parse(message.end) - 30 * 86400000)).toISOString().slice(0, 10);
        return structuredClone({ ...data.details, point_id: message.point_id, start: message.start, end: message.end, daily_window: { start: dailyStart, end: message.end } });
      }
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
    return root && root.textContent.includes("Điện năng tháng gần nhất") && root.textContent.includes("1.873");
  });
}

async function clickTab(page, index) {
  await page.evaluate(tab => {
    [...document.getElementById("p").shadowRoot.querySelectorAll("[data-action=tab]")].find(node => node.dataset.tab === tab).click();
  }, String(index));
}

async function chartSnapshot(page, name) {
  return page.evaluate(chartName => {
    const card = document.getElementById("p").shadowRoot.querySelector(`[data-chart="${chartName}"]`);
    if (!card) return null;
    const chart = card.querySelector(".chart");
    return {
      text: card.textContent,
      asOf: card.dataset.asOf,
      aria: chart?.getAttribute("aria-label"),
      role: chart?.getAttribute("role"),
      field: chart?.dataset.field,
      unit: chart?.dataset.unit,
      columns: [...card.querySelectorAll(".chart-column")].map(column => ({ period: column.dataset.period, state: column.dataset.state, label: column.querySelector(".chart-label")?.textContent, value: column.querySelector(".slot-value")?.textContent, title: column.title, height: column.querySelector(".bar")?.style.height ?? null, bottom: column.querySelector(".bar")?.style.bottom ?? null, provisional: Boolean(column.querySelector(".bar.current")), axis: column.querySelector(".zero-axis")?.style.bottom }))
    };
  }, name);
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
    await context.addInitScript(() => {
      const NativeDate = Date;
      const fixed = NativeDate.parse("2026-10-07T10:30:00+07:00");
      function FrozenDate(...args) {
        if (!new.target) return new NativeDate(fixed).toString();
        return Reflect.construct(NativeDate, args.length ? args : [fixed], new.target);
      }
      Object.setPrototypeOf(FrozenDate, NativeDate);
      FrozenDate.prototype = NativeDate.prototype;
      FrozenDate.now = () => fixed;
      window.Date = FrozenDate;
    });
    await context.route("**/*", route => {
      if (new URL(route.request().url()).origin === new URL(url).origin) return route.continue();
      return route.abort();
    });
    page = await context.newPage();
    page.on("console", message => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", error => consoleErrors.push(String(error)));

    await page.goto(url);
    await attach(page);
    await settled(page);

    const units = await page.evaluate(async () => {
      const { columnScale, comparisonSlots, dailyEnd, dailyRecords, readingMoment, readingSeries, paymentState, payableAmount } = await import("/evn-cskh-panel.js");
      const cases = [];
      const record = (date, value, extra = {}) => ({ period: date?.slice(0, 7) || "2026-10", timestamp: date ? `${date}T08:00:00+07:00` : null, reading_date: date, resolution: date ? "time" : null, meter: "A", register: "KT1", kind: "daily", new: value, old: 0, multiplier: 50, kwh: 999, ...extra });
      const fixtures = structuredClone(window.__data.overview.comparisons);
      const freeze = value => { if (value && typeof value === "object") { Object.values(value).forEach(freeze); Object.freeze(value); } return value; };
      freeze(fixtures);
      const before = JSON.stringify(fixtures);
      const daily = comparisonSlots(fixtures, "PD01", "daily");
      const monthly = comparisonSlots(fixtures, "PD02", "monthly");
      cases.push(["unit daily exactly three chronological slots", daily.length === 3 && daily.map(row => row.period).join() === "2026-10-05,2026-10-06,2026-10-07"]);
      cases.push(["unit zero distinct from null", daily[0].kwh === 34.76 && daily[1].kwh === 0 && daily[2].kwh === null]);
      cases.push(["unit monthly customer totals not selected point", monthly[1].kwh === 1025.5 && monthly[1].vnd === 0 && monthly[2].vnd === null]);
      cases.push(["unit immutable comparison DTO", JSON.stringify(fixtures) === before]);
      cases.push(["unit missing point remains unknown", comparisonSlots(fixtures, "not-a-point", "daily").every(row => row.kwh === null)]);
      cases.push(["unit absent comparison no latest alias", comparisonSlots(undefined, "PD01", "daily") === null]);
      cases.push(["unit invalid as_of rejected", comparisonSlots({ as_of: "2026-02-30" }, "PD01", "daily") === null]);
      const invalid = { ...fixtures, points: [{ point_id: "PD01", daily: [{ period: "2026-10-05", kwh: "34.76" }, { period: "2026-10-06", kwh: true }, { period: "2026-10-07", kwh: Infinity }] }], monthly: [{ period: "2026-08", kwh: false, vnd: "12" }, { period: "2026-09", kwh: NaN, vnd: true }, { period: "2026-10", kwh: -1.5, vnd: -25 }] };
      cases.push(["unit string boolean infinity not numeric", comparisonSlots(invalid, "PD01", "daily").every(row => row.kwh === null) && comparisonSlots(invalid, "PD01", "monthly").slice(0, 2).every(row => row.kwh === null && row.vnd === null)]);
      const rollover = { as_of: "2027-01-01", points: [], monthly: [{ period: "2027-01", kwh: 0 }, { period: "2026-11", kwh: 12 }, { period: "2026-12", kwh: 23 }] };
      cases.push(["unit year rollover backend dates", comparisonSlots(rollover, "PD01", "monthly").map(row => row.period).join() === "2026-11,2026-12,2027-01" && comparisonSlots(rollover, "PD01", "daily")[0].period === "2026-12-30"]);
      const scale = columnScale([-12, 24, 0, null, true, "99"]);
      cases.push(["unit negative correction zero axis", scale.low === -12 && scale.high === 24 && Math.abs(scale.zero - 100 / 3) < 0.001 && scale.height(0) === 0 && scale.bottom(-12) === 0]);
      const huge = columnScale([-Number.MAX_VALUE, Number.MAX_VALUE]);
      cases.push(["unit finite extreme scale", Number.isFinite(huge.height(Number.MAX_VALUE)) && huge.zero === 50 && huge.height(-Number.MAX_VALUE) === 50]);
      const dates = freeze([{ period: "02/10/2026", kwh: 2 }, { period: "29/09/2026 - 01/10/2026", kwh: 30 }, { period: "30/09/2026", kwh: 1 }]);
      cases.push(["unit VN interval rightmost date", dailyEnd(dates[1].period) === "2026-10-01" && dailyEnd("31/02/2026") === null && dailyEnd("2026-10") === null]);
      cases.push(["unit daily across month no interpolation", dailyRecords(dates).length === 3 && dailyRecords(dates)[0].period === "30/09/2026" && dailyRecords(dates)[1].kwh === 30 && dates[0].period === "02/10/2026"]);
      const dated = record("2026-10-02", 15, { timestamp: null, resolution: "day" });
      cases.push(["unit day precision never invents clock", readingMoment(dated).label.includes("chỉ biết ngày") && !readingMoment(dated).label.includes(":")]);
      cases.push(["unit normalized actual timestamp", readingMoment(record("2026-10-02", 15)).label.includes("2026-10-02T08:00:00+07:00") && readingMoment(record("2026-10-02", 15, { timestamp: "08:00" })) === null]);
      cases.push(["unit YYYY-MM never fabricated reading date", readingMoment(record(null, 15)) === null]);
      const records = freeze([record("2026-10-06", 106), record("2026-10-01", 101), record("2026-10-02", 102), record("2026-10-03", null), record("2026-10-04", 104), record("2026-10-05", 105)]);
      const copy = JSON.stringify(records);
      const series = readingSeries(records)[0];
      cases.push(["unit reading sort immutable", series.points[0].day === "2026-10-01" && JSON.stringify(records) === copy]);
      cases.push(["unit unknown index breaks path", series.segments.length === 2 && series.segments[0].length === 2 && series.segments[1].length === 3]);
      const calendar = readingSeries([record("2026-10-01", 1), record("2026-10-02", 2), record("2026-10-04", 4), record("2026-10-05", 5)])[0];
      cases.push(["unit missing calendar days gap", calendar.segments.length === 2 && calendar.segments.every(segment => segment.length === 2)]);
      const duplicate = record("2026-10-02", 2);
      const conflict = readingSeries([record("2026-10-01", 1), duplicate, { ...duplicate }, { ...duplicate, new: 9 }, record("2026-10-03", 3)])[0];
      cases.push(["unit exact duplicate dedup conflict gap", conflict.points.length === 3 && conflict.points[1].conflict && conflict.points[1].value === null && conflict.segments.length === 0]);
      const separate = readingSeries([record("2026-10-01", 10), record("2026-10-02", 11), record("2026-10-01", 50, { meter: "B" }), record("2026-10-02", 51, { meter: "B" }), record("2026-10-01", 100, { register: "KT2" }), record("2026-10-02", 101, { kind: "monthly" })]);
      cases.push(["unit meter register kind independent series", separate.length === 4 && separate.every(group => group.rows.every(row => row.meter === group.meter && row.register === group.register && row.kind === group.kind))]);
      cases.push(["unit raw index not multiplied kWh", separate[0].points[0].value === 10 && separate[0].label.includes("Chỉ số gốc")]);
      cases.push(["unit one reading never line", readingSeries([record("2026-10-01", 0)])[0].segments.length === 0]);
      cases.push(["unit undated bad row prevents joins", readingSeries([record("2026-10-01", 1), record(null, 2), record("2026-10-02", 3)])[0].segments.length === 0]);
      cases.push(["unit unknown meter no join", readingSeries([record("2026-10-01", 1, { meter: null }), record("2026-10-02", 2, { meter: null })])[0].segments.length === 0]);
      cases.push(["unit ambiguous replacement prevents known series bridge", readingSeries([record("2026-10-01", 1), record("2026-10-02", 2, { meter: null }), record("2026-10-03", 3)])[0].segments.length === 0]);
      cases.push(["unit invalid timestamps no normalization invention", readingMoment(record("2026-10-01", 1, { timestamp: "2026-10-01T24:00:00+07:00" })) === null && readingMoment(record("2026-02-30", 1)) === null]);
      const exact = readingSeries([duplicate, { ...duplicate }])[0];
      cases.push(["unit exact duplicate one actual point", exact.points.length === 1 && exact.unknown.length === 0 && exact.points[0].value === 2]);
      const mixed = readingSeries([record("2026-10-01", 1, { timestamp: null, resolution: "day" }), record("2026-10-01", 2), record("2026-10-02", 3)])[0];
      cases.push(["unit overlapping day and time precision not joined", mixed.segments.length === 0]);
      cases.push(["unit invalid raw index not numeric", readingSeries([record("2026-10-01", "1"), record("2026-10-02", false), record("2026-10-03", Infinity)])[0].points.every(point => point.value === null)]);
      const limit = readingSeries(Array.from({ length: 1005 }, (_, index) => record("2026-10-01", index, { timestamp: `2026-10-01T08:${String(Math.floor(index / 60)).padStart(2, "0")}:${String(index % 60).padStart(2, "0")}+07:00` })))[0];
      cases.push(["unit curve bounded to 1000 rows", limit.rows.length === 1000 && limit.points.length === 1000]);
      const month = (date, value, period = date?.slice(0, 7), extra = {}) => record(date, value, { kind: "monthly", period, resolution: "day", timestamp: null, ...extra });
      const january = month("2026-01-29", 100);
      const march = month("2026-03-29", 300);
      const monthlyGap = readingSeries(freeze([march, january]))[0];
      cases.push(["unit monthly missing February breaks Jan March path", monthlyGap.segments.length === 0 && monthlyGap.points.length === 2 && monthlyGap.points[0].monthlyPeriod === "2026-01" && monthlyGap.points[1].monthlyPeriod === "2026-03"]);
      cases.push(["unit monthly period never replaces actual closing date", monthlyGap.points[0].stamp === Date.parse("2026-01-29T00:00:00+07:00") && monthlyGap.points[1].day === "2026-03-29"]);
      const yearBoundary = readingSeries([month("2027-02-02", 200, "2027-01"), month("2026-12-30", 100, "2026-12")])[0];
      cases.push(["unit December January adjacent periods connect actual dates", yearBoundary.segments.length === 1 && yearBoundary.segments[0].length === 2 && yearBoundary.points[1].stamp === Date.parse("2027-02-02T00:00:00+07:00")]);
      const samePeriod = readingSeries([month("2026-01-29", 100), month("2026-01-30", 110)])[0];
      cases.push(["unit two monthly readings same period connect", samePeriod.segments.length === 1 && samePeriod.points.every(point => point.monthlyPeriod === "2026-01")]);
      const sameDay = readingSeries([month("2026-01-29", 100, "2026-01", { resolution: "time", timestamp: "2026-01-29T08:00:00+07:00" }), month("2026-01-29", 110, "2026-01", { resolution: "time", timestamp: "2026-01-29T09:00:00+07:00" })])[0];
      cases.push(["unit same-day monthly actual times remain distinct", sameDay.segments.length === 1 && sameDay.points[1].stamp - sameDay.points[0].stamp === 3600000]);
      cases.push(["unit reversed monthly labels break continuity", readingSeries([month("2026-01-29", 100, "2026-02"), month("2026-02-28", 200, "2026-01")])[0].segments.length === 0]);
      cases.push(["unit unknown monthly period conservative even adjacent dates", readingSeries([january, month("2026-01-30", 110, null)])[0].segments.length === 0]);
      cases.push(["unit unknown monthly labels with date gap not joined", readingSeries([month("2026-01-29", 100, null), month("2026-03-29", 300, "bad")])[0].segments.length === 0]);
      cases.push(["unit invalid monthly period never normalized", ["2026-00", "2026-13", "0000-01", "01/2026"].every(period => readingSeries([month("2026-01-29", 100, period)])[0].points[0].monthlyPeriod === null)]);
      const monthlyDuplicate = readingSeries([january, { ...january }])[0];
      cases.push(["unit monthly exact duplicate dedup keeps period", monthlyDuplicate.points.length === 1 && monthlyDuplicate.points[0].monthlyPeriod === "2026-01"]);
      const monthlyConflict = readingSeries([january, { ...january, new: 101 }, month("2026-02-28", 200)])[0];
      cases.push(["unit monthly distinct same-bucket index conflict gaps", monthlyConflict.points[0].conflict && monthlyConflict.points[0].value === null && monthlyConflict.segments.length === 0]);
      const periodConflict = readingSeries([january, { ...january, period: "2026-02" }, month("2026-02-28", 200)])[0];
      cases.push(["unit conflicting monthly period bucket no join", periodConflict.points[0].monthlyPeriod === null && periodConflict.points[0].value === 100 && periodConflict.segments.length === 0]);
      const paid = { status: "DATT", status_label: "Đã thanh toán", outstanding: 1520000, paid_date: null };
      const unpaid = { status: "CHUATT", status_label: "Chưa thanh toán", outstanding: -120000, paid_date: "20/09/2026" };
      const partial = { status: "TTOANMOTPHAN", status_label: "Thanh toán một phần", outstanding: -456000 };
      const refund = { ...partial, status_label: "Đã hoàn trả một phần" };
      cases.push(["unit DATT authoritative despite positive raw outstanding", paymentState(paid) === "paid" && payableAmount(paid) === 0]);
      cases.push(["unit CHUATT authoritative despite paid date negative raw", paymentState(unpaid) === "unpaid" && payableAmount(unpaid) === 120000]);
      cases.push(["unit partial payment payable abs raw", paymentState(partial) === "unpaid" && payableAmount(partial) === 456000]);
      cases.push(["unit partial refund unknown not debt", paymentState(refund) === "unknown" && payableAmount(refund) === null]);
      cases.push(["unit refund processing unknown positive outstanding stays unknown", ["DAHT", "CHUAHT", "CHOXULY", "UNKNOWN", "NEW_STATUS"].every(status => paymentState({ ...paid, status }) === "unknown" && payableAmount({ ...paid, status }) === null)]);
      cases.push(["unit missing status no paid_date or label inference", [undefined, null, "", true].every(status => paymentState({ ...paid, status, paid_date: "20/09/2026" }) === "unknown" && payableAmount({ ...paid, status }) === null)]);
      cases.push(["unit payable_amount present is sole amount source", payableAmount({ ...unpaid, payable_amount: 45678 }) === 45678 && payableAmount({ ...unpaid, payable_amount: 0 }) === 0 && payableAmount({ ...unpaid, payable_amount: null }) === null]);
      cases.push(["unit invalid payable_amount never coerced or raw fallback", ["120000", true, Infinity, NaN, -10, undefined].every(payable_amount => payableAmount({ ...unpaid, payable_amount }) === null)]);
      cases.push(["unit legacy unpaid unknown raw amount stays unknown", [null, "120000", false, Infinity].every(outstanding => payableAmount({ ...unpaid, outstanding }) === null)]);
      return cases;
    });
    for (const [name, condition] of units) check(name, condition);
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
    const dailyChart = await chartSnapshot(page, "daily-comparison");
    const monthlyChart = await chartSnapshot(page, "monthly-comparison");
    check("overview two comparison cards below metrics", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      return root.querySelectorAll("[data-chart]").length === 2 && root.querySelector(".metrics").nextElementSibling.matches(".comparison-grid");
    }));
    check("daily comparison labels dates values", dailyChart.columns.map(column => column.label).join() === "Hôm kia,Hôm qua,Hôm nay" && dailyChart.columns[0].value === "34,76" && dailyChart.columns[1].value === "0" && dailyChart.columns[2].value === "Chưa có");
    check("comparison null no bar zero height bar", dailyChart.columns[2].height === null && dailyChart.columns[1].height === "0%" && parseFloat(dailyChart.columns[0].height) > 0);
    check("daily chart aria full date and unit", dailyChart.role === "img" && dailyChart.field === "kwh" && dailyChart.unit === "kWh" && dailyChart.aria.includes("2026-10-05") && dailyChart.aria.includes("34,76 kWh") && dailyChart.aria.includes("Hôm nay"));
    check("comparison bars rounded top", await page.evaluate(() => {
      const bars = [...document.getElementById("p").shadowRoot.querySelectorAll(".comparison-chart .bar")];
      return bars.length > 0 && bars.every(bar => parseFloat(getComputedStyle(bar).borderTopLeftRadius) > 0 && parseFloat(getComputedStyle(bar).borderTopRightRadius) > 0);
    }));
    check("monthly comparison customer allpoint scope", monthlyChart.text.includes("Tổng khách hàng · tất cả điểm đo · kỳ theo tháng EVN") && monthlyChart.columns[1].value === "1.025,5");
    check("current month provisional lighter caption", monthlyChart.columns[2].provisional && monthlyChart.columns[2].title.includes("Tạm tính/chưa chốt") && await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const bars = root.querySelectorAll('[data-chart="monthly-comparison"] .bar');
      return getComputedStyle(bars[0]).backgroundColor !== getComputedStyle(bars[2]).backgroundColor;
    }));
    check("latest usage label truthful", text.includes("Điện năng tháng gần nhất") && !text.includes("Sản lượng tháng này"));
    check("comparison as_of backend not UI clock", dailyChart.asOf === "2026-10-07" && monthlyChart.asOf === "2026-10-07");
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
    check("energy comparisons once before history", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const filters = root.getElementById("history-filter");
      return filters.nextElementSibling.matches(".comparison-grid") && root.querySelectorAll('[data-chart="daily-comparison"]').length === 1 && root.querySelectorAll('[data-chart="monthly-comparison"]').length === 1 && root.querySelector(".chart-card .chart.monthly");
    }));
    check("actual daily query window explained", text.includes("07/09/2026 → 07/10/2026") && text.includes("31 ngày đến ngày kết thúc"));
    await page.evaluate(() => [...document.getElementById("p").shadowRoot.querySelectorAll("[data-action=period]")].find(node => node.dataset.value === "daily").click());
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.textContent.includes("05/10/2026"));
    check("energy daily toggle", (await shadowText()).includes("05/10/2026"));
    check("history daily chronological across month interval single bar", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const columns = [...root.querySelectorAll(".chart-card .chart-column")];
      return columns.length === 4 && columns.map(column => column.dataset.period).join() === "28/09/2026 - 30/09/2026,01/10/2026,05/10/2026,06/10/2026" && columns[0].querySelector(".chart-label").textContent === "30/09" && columns[1].querySelector(".chart-label").textContent === "01/10";
    }));
    await page.evaluate(() => [...document.getElementById("p").shadowRoot.querySelectorAll("[data-action=period]")].find(node => node.dataset.value === "monthly").click());

    const smoothHistory = await page.evaluate(() => {
      const panel = document.getElementById("p");
      const saved = panel._details;
      panel._details = { ...saved, monthly: [{ period: "2026-05", kwh: 700 }, { period: "2026-06", kwh: 701.5 }, { period: "2026-07", kwh: null }, { period: "2026-08", kwh: 0 }, { period: "2026-09", kwh: 873 }] };
      panel._render();
      const card = panel.shadowRoot.querySelector('[data-chart="energy-history"]');
      const svg = card?.querySelector("svg.history-overlay");
      const lines = svg ? [...svg.querySelectorAll(".history-line")] : [];
      const snapshot = {
        curve: lines.length > 0 && lines.every(path => /[CQ]/.test(path.getAttribute("d"))),
        segments: lines.length,
        gradient: Boolean(svg?.querySelector("linearGradient")),
        area: (svg?.querySelector(".history-area")?.getAttribute("fill") || "").startsWith("url("),
        points: card ? card.querySelectorAll(".history-dot").length : 0,
        zero: card ? [...card.querySelectorAll(".history-dot")].some(dot => dot.getAttribute("aria-label").includes("(2026-08): 0 kWh")) : false,
        grid: svg ? svg.querySelectorAll(".history-grid").length : 0,
        bounded: card ? card.scrollWidth <= card.clientWidth + 1 : false,
      };
      panel._details = saved;
      panel._render();
      return snapshot;
    });
    check("energy history smooth spline path", smoothHistory.curve);
    check("energy history gradient area fill", smoothHistory.gradient && smoothHistory.area);
    check("energy history null gap zero keeps point", smoothHistory.segments === 2 && smoothHistory.points === 4 && smoothHistory.zero && smoothHistory.bounded && smoothHistory.grid === 3);

    await clickTab(page, 2);
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.textContent.includes("Lịch sử chỉ số công tơ"));
    text = await shadowText();
    check("meter latest reading block", text.includes("Chỉ số mới nhất") || text.includes("Chỉ số mới"));
    check("meter per point empty", text.includes("Chưa có chỉ số cho điểm đo này"));
    check("meter readings table", text.includes("CT01") && text.includes("KT1"));
    check("meter table rows", await page.evaluate(() => document.getElementById("p").shadowRoot.querySelectorAll("#reading-results tbody tr").length) >= 2);
    check("meter index SVG accessible responsive raw scale", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const card = root.querySelector('[data-chart="meter-index-history"]');
      const svg = card.querySelector("svg.index-chart");
      return svg?.getAttribute("viewBox") === "0 0 720 260" && svg.getAttribute("role") === "img" && svg.querySelector("title") && svg.dataset.min === "750" && svg.dataset.max === "1873" && svg.getBoundingClientRect().width > 20 && card.textContent.includes("Chỉ số gốc") && svg.querySelectorAll(".index-grid").length === 3 && svg.querySelectorAll(".index-point").length === 3;
    }));
    check("meter smooth spline line and gradient", await page.evaluate(() => {
      const svg = document.getElementById("p").shadowRoot.querySelector(".index-chart");
      const curves = [...svg.querySelectorAll(".index-curve")];
      return curves.length > 0 && curves.every(path => /[CQ]/.test(path.getAttribute("d"))) && Boolean(svg.querySelector("linearGradient")) && (svg.querySelector(".index-area")?.getAttribute("fill") || "").startsWith("url(");
    }));
    check("meter date-only metadata no fabricated time", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const labels = [...root.querySelectorAll(".index-point")].map(point => point.getAttribute("aria-label"));
      return labels.every(label => label.includes("chỉ biết ngày") && !label.includes("00:00")) && labels[0].includes("28/07/2026") && root.getElementById("reading-results").textContent.includes("Mốc ghi thực tế");
    }));
    await page.screenshot({ path: join(outDir, "desktop-meter.png"), fullPage: true });
    await page.selectOption("#meter-series-select", { label: "Công tơ CT01 · KT1 · Ngày · Chỉ số gốc" });
    check("meter time normalized sorting null gap all pages", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const card = root.querySelector('[data-chart="meter-index-history"]');
      const points = card.querySelectorAll(".index-point");
      return points.length === 22 && card.querySelectorAll(".index-line").length === 2 && card.querySelectorAll(".index-values tbody tr").length === 23 && points[0].getAttribute("aria-label").includes("2026-10-06T00:00:00+07:00") && points[21].getAttribute("aria-label").includes("2026-10-07T10:00:00+07:00");
    }));
    await page.focus("#meter-series-select");
    await page.keyboard.press("Tab");
    check("meter keyboard focus outlined tooltip actual value", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const active = root.activeElement;
      return active?.matches(".index-point") && getComputedStyle(active).outlineStyle !== "none" && parseFloat(getComputedStyle(active).outlineWidth) >= 2 && root.getElementById("meter-index-tooltip").textContent.includes("Chỉ số gốc 1.874") && !root.getElementById("meter-index-tooltip").textContent.includes("3.748");
    }));
    await page.keyboard.press("ArrowRight");
    check("meter arrow tooltip next timestamp", await page.evaluate(() => document.getElementById("p").shadowRoot.getElementById("meter-index-tooltip").textContent.includes("2026-10-06T01:00:00+07:00")));
    await page.locator("#meter-index-point-21").hover();
    check("meter hover tooltip last timestamp", await page.evaluate(() => document.getElementById("p").shadowRoot.getElementById("meter-index-tooltip").textContent.includes("2026-10-07T10:00:00+07:00")));
    const graphBeforePage = await page.evaluate(() => document.getElementById("p").shadowRoot.querySelector(".index-chart").outerHTML);
    await page.locator('[data-action="reading-page"][data-step="1"]').click();
    check("meter pagination never limits curve", graphBeforePage === await page.evaluate(() => document.getElementById("p").shadowRoot.querySelector(".index-chart").outerHTML));
    await page.selectOption("#meter-series-select", { label: "Công tơ CT02 · KT1 · Tháng · Chỉ số gốc" });
    check("replacement meter own series never joined", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const svg = root.querySelector(".index-chart");
      return svg.querySelectorAll(".index-point").length === 2 && svg.dataset.min === "85" && svg.dataset.max === "102" && [...svg.querySelectorAll(".index-point")].every(point => point.getAttribute("aria-label").includes("CT02") && !point.getAttribute("aria-label").includes("CT01"));
    }));
    await page.selectOption("#meter-series-select", { label: "Công tơ CT03 · KT2 · Tháng · Chỉ số gốc" });
    check("one-point index no fake curve zero numeric list", await page.evaluate(() => {
      const card = document.getElementById("p").shadowRoot.querySelector('[data-chart="meter-index-history"]');
      return !card.querySelector("svg") && card.textContent.includes("Chưa đủ hai") && card.querySelector(".index-values td").textContent === "0";
    }));
    await page.selectOption("#meter-series-select", { label: "Công tơ CT01 · KT1 · Tháng · Chỉ số gốc" });
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      window.__savedDetails = panel._details;
      panel._details = null;
      panel._detailsBusy = true;
      panel._render();
    });
    check("meter history loading state no fabricated curve", await page.evaluate(() => {
      const card = document.getElementById("p").shadowRoot.querySelector('[data-chart="meter-index-history"]');
      return card.getAttribute("aria-busy") === "true" && card.textContent.includes("Đang tải") && !card.querySelector("svg");
    }));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._detailsBusy = false;
      panel._details = { ...window.__savedDetails, readings: [] };
      panel._render();
    });
    check("meter empty state no fabricated curve", await page.evaluate(() => {
      const card = document.getElementById("p").shadowRoot.querySelector('[data-chart="meter-index-history"]');
      return card.textContent.includes("Chưa đủ") && !card.querySelector("svg");
    }));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      const row = (date, value) => ({ period: date, reading_date: date, timestamp: null, resolution: "day", meter: "A", register: "KT1", kind: "daily", new: value, old: 0, multiplier: 100, kwh: 900 });
      const duplicate = row("2026-10-02", -10);
      panel._details = { ...window.__savedDetails, readings: [row("2026-10-09", 20), row("2026-10-08", 18), row("2026-10-07", 14), row("2026-10-05", 10), row("2026-10-04", 9), row("2026-10-03", null), duplicate, { ...duplicate }, row("2026-10-01", -15)] };
      panel._readingSeries = "";
      panel._render();
    });
    check("browser meter negative axis null and calendar gaps exact dedup", await page.evaluate(() => {
      const card = document.getElementById("p").shadowRoot.querySelector('[data-chart="meter-index-history"]');
      const svg = card.querySelector("svg");
      return svg.dataset.min === "-15" && svg.dataset.max === "20" && svg.querySelectorAll(".index-line").length === 3 && svg.querySelectorAll(".index-point").length === 7 && card.querySelectorAll(".index-values tbody tr").length === 8 && !/NaN|Infinity/.test(svg.outerHTML) && [...svg.querySelectorAll(".index-line")].every(path => !/[CQ]/.test(path.getAttribute("d")));
    }));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._details = { ...panel._details, readings: [...panel._details.readings, { ...panel._details.readings[6], new: -11 }] };
      panel._render();
    });
    check("browser conflicting bucket gap preserves numeric table", await page.evaluate(() => {
      const card = document.getElementById("p").shadowRoot.querySelector('[data-chart="meter-index-history"]');
      return card.querySelectorAll(".index-line").length === 2 && card.querySelectorAll(".index-point").length === 6 && card.textContent.includes("chỉ số xung đột");
    }));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._details = { ...panel._details, readings: [...panel._details.readings, { period: "2026-10", timestamp: null, reading_date: null, resolution: null, meter: "A", register: "KT1", kind: "daily", new: 15 }] };
      panel._render();
    });
    check("browser undated row never inferred from month", await page.evaluate(() => {
      const card = document.getElementById("p").shadowRoot.querySelector('[data-chart="meter-index-history"]');
      return card.querySelectorAll(".index-line").length === 0 && card.textContent.includes("Chưa có ngày ghi thực tế") && card.textContent.includes("không nối đường");
    }));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      const meter = '<img src=x onerror=alert(1)>';
      panel._details = { ...window.__savedDetails, readings: window.__savedDetails.readings.filter(row => row.kind === "monthly" && row.meter === "CT01").map(row => ({ ...row, meter, request_token: "hidden-request-token", raw_file_id: "hidden-file-id" })) };
      panel._render();
    });
    check("meter chart metadata text safe no raw fields leak", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      return !root.querySelector("img") && root.textContent.includes("<img src=x onerror=alert(1)>") && !/hidden-request-token|hidden-file-id/.test(root.innerHTML);
    }));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._details = { ...window.__savedDetails, readings: window.__savedDetails.readings.filter(row => row.kind === "monthly" && row.meter === "CT01").map(row => ({ ...row, new: 0 })) };
      panel._render();
    });
    check("constant zero index finite flat scale", await page.evaluate(() => {
      const svg = document.getElementById("p").shadowRoot.querySelector(".index-chart");
      return svg.dataset.min === "0" && svg.dataset.max === "0" && svg.querySelectorAll(".index-grid").length === 1 && svg.querySelectorAll(".index-line").length === 1 && [...svg.querySelectorAll(".index-point")].every(point => point.getAttribute("cy") === "120.000") && !/NaN|Infinity/.test(svg.outerHTML);
    }));
    const monthlyPaths = await page.evaluate(() => {
      const panel = document.getElementById("p");
      const cases = [];
      const row = (period, date, value, timestamp = null) => ({ period, reading_date: date, timestamp, resolution: timestamp ? "time" : "day", meter: "A", register: "KT1", kind: "monthly", new: value, old: 0, multiplier: 100, kwh: 900 });
      const render = readings => {
        panel._details = { ...window.__savedDetails, readings };
        panel._readingSeries = "";
        panel._render();
        return panel.shadowRoot.querySelector('[data-chart="meter-index-history"]');
      };
      let card = render([row("2026-03", "2026-03-29", 300), row("2026-01", "2026-01-29", 100)]);
      cases.push(["browser Jan March monthly missing February no bridge", card.querySelectorAll(".index-line").length === 0 && card.querySelectorAll(".index-point").length === 2 && card.querySelectorAll(".index-values tbody tr").length === 2]);
      cases.push(["browser monthly gaps retain actual date axis", card.querySelector(".index-point").getAttribute("aria-label").includes("29/01/2026") && card.querySelector("svg").textContent.includes("29/03/2026") && !card.querySelector("svg").textContent.includes("01/03/2026")]);
      card = render([row("2027-01", "2027-02-02", 200), row("2026-12", "2026-12-30", 100)]);
      cases.push(["browser Dec Jan connects adjacent periods actual closing dates", card.querySelectorAll(".index-line").length === 1 && card.querySelector(".index-line").getAttribute("d").includes("L") && [...card.querySelectorAll(".index-point")].at(-1).getAttribute("aria-label").includes("02/02/2027")]);
      card = render([row("2026-01", "2026-01-29", 100, "2026-01-29T08:00:00+07:00"), row("2026-01", "2026-01-29", 120, "2026-01-29T09:00:00+07:00")]);
      cases.push(["browser same-period same-day monthly times connect", card.querySelectorAll(".index-line").length === 1 && card.querySelectorAll(".index-point").length === 2 && [...card.querySelectorAll(".index-point")].at(-1).getAttribute("aria-label").includes("T09:00:00+07:00")]);
      const january = row("2026-01", "2026-01-29", 100);
      card = render([january, { ...january }, { ...january, new: 101 }, row("2026-02", "2026-02-28", 200)]);
      cases.push(["browser monthly same-bucket conflict no bridge", card.querySelectorAll(".index-line").length === 0 && card.querySelectorAll(".index-values tbody tr").length === 2 && card.textContent.includes("chỉ số xung đột")]);
      card = render([january, { ...january, period: "2026-02" }, row("2026-02", "2026-02-28", 200)]);
      cases.push(["browser conflicting monthly period labels no bridge", card.querySelectorAll(".index-line").length === 0 && card.querySelectorAll(".index-point").length === 2]);
      card = render([row(null, "2026-01-29", 100), row(null, "2026-03-29", 300)]);
      cases.push(["browser unknown monthly periods date gap conservative", card.querySelectorAll(".index-line").length === 0 && card.querySelectorAll(".index-point").length === 2 && !/NaN|Infinity/.test(card.querySelector("svg").outerHTML)]);
      panel._details = window.__savedDetails;
      delete window.__savedDetails;
      panel._readingSeries = "";
      panel._render();
      return cases;
    });
    for (const [name, condition] of monthlyPaths) check(name, condition);

    await clickTab(page, 3);
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.querySelectorAll("[data-action=invoice]").length >= 2);
    text = await shadowText();
    check("invoice outstanding banner", text.includes("Tổng tiền còn phải trả: 1.640.000"));
    check("invoice rows rendered", await page.evaluate(() => document.getElementById("p").shadowRoot.querySelectorAll("[data-action=invoice]").length) >= 2);
    check("paid history table", text.includes("Lịch sử thanh toán") && text.includes("App MB"));
    check("details pdf keys hidden", !text.includes("pdf-key"));
    const invoiceChart = await chartSnapshot(page, "invoice-comparison");
    check("invoice chart VND backend not display invoice arrays", invoiceChart.role === "img" && invoiceChart.field === "vnd" && invoiceChart.unit === "VNĐ" && invoiceChart.aria.includes("1.754.321") && !invoiceChart.aria.includes("1.520.000") && invoiceChart.text.includes("Tổng khách hàng · VNĐ · kỳ theo tháng"));
    check("invoice unknown current not paid zero", invoiceChart.columns.length === 3 && invoiceChart.columns[2].height === null && invoiceChart.columns[1].height === "0%" && invoiceChart.columns[2].title.includes("Chưa có dữ liệu") && invoiceChart.columns[1].title.includes("0") && invoiceChart.text.includes("Chưa có"));
    check("invoice full money values table", await page.evaluate(() => {
      const rows = [...document.getElementById("p").shadowRoot.querySelectorAll('[data-chart="invoice-comparison"] tbody tr')];
      return rows.length === 3 && rows[0].cells[1].textContent.includes("1.754.321") && rows[1].cells[1].textContent.startsWith("0") && rows[2].cells[1].textContent === "Chưa có";
    }));
    await page.fill("#invoice-search", "nothing-matches");
    await page.selectOption("#paid-select", "unpaid");
    check("invoice search status filters not comparisons", (await chartSnapshot(page, "invoice-comparison")).aria === invoiceChart.aria && (await shadowText()).includes("Không có hóa đơn khớp"));
    await page.locator("#clear-search").click();
    const originalFetchWithAuth = await page.evaluateHandle(() => document.getElementById("p").hass.fetchWithAuth);
    check("invoice download header per-row buttons no paid-history download", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const headers = [...root.querySelectorAll(".invoice-table thead th")].map(cell => cell.textContent);
      const rows = [...root.querySelectorAll(".invoice-table tbody tr")];
      const first = rows[0]?.querySelector('button[data-action="pdf-row"][data-kind="invoice"]');
      const paidCard = [...root.querySelectorAll(".card")].find(card => card.querySelector("h2")?.textContent === "Lịch sử thanh toán");
      return headers.includes("Tải hóa đơn") && Boolean(first) && first.getAttribute("aria-label").includes("09/2026") && Boolean(rows[1]?.querySelector('button[data-action="pdf-row"][data-kind="invoice"]')) && Boolean(paidCard) && !paidCard.querySelector('[data-action="pdf-row"]');
    }));
    check("invoice row secondary statement notice buttons", await page.evaluate(() => {
      const cells = [...document.getElementById("p").shadowRoot.querySelectorAll(".invoice-table tbody .pdf-cell")];
      return cells[0].querySelectorAll('[data-action="pdf-row"]').length === 3 && Boolean(cells[0].querySelector('[data-kind="statement"]')) && Boolean(cells[0].querySelector('[data-kind="notice"]')) && !cells[1].querySelector('[data-kind="statement"]');
    }));
    check("invoice row without invoice document shows dash no button", await page.evaluate(() => {
      const panel = document.getElementById("p");
      const saved = panel._details.invoices.map(invoice => invoice.documents);
      panel._details = { ...panel._details, invoices: panel._details.invoices.map((invoice, index) => index ? invoice : ({ ...invoice, documents: ["statement"] })) };
      panel._render();
      const cell = panel.shadowRoot.querySelectorAll(".invoice-table tbody .pdf-cell")[0];
      const result = !cell.querySelector('[data-kind="invoice"]') && cell.textContent.includes("—") && Boolean(cell.querySelector('[data-kind="statement"]'));
      panel._details = { ...panel._details, invoices: panel._details.invoices.map((invoice, index) => index ? invoice : ({ ...invoice, documents: saved[index] })) };
      panel._render();
      return result;
    }));
    check("invoice download buttons no key leak", await page.evaluate(() => !/pdf-key|request_token|raw_file_id/.test(document.getElementById("p").shadowRoot.querySelector(".invoice-table").outerHTML)));
    const rowDownload = page.waitForEvent("download");
    await page.evaluate(() => document.getElementById("p").shadowRoot.getElementById("pdf-row-0-invoice").click());
    const rowFile = await rowDownload;
    check("row download filename route no dialog", /^evn-invoice-09-2026\.pdf$/.test(rowFile.suggestedFilename()) && await page.evaluate(() => window.__fetchLog.includes("/api/evn_cskh/invoice/entry-1/pdf-key-1/invoice") && !document.getElementById("p").shadowRoot.querySelector("dialog[open]") && !document.getElementById("p")._pdfBusy));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      window.__rowResolve = null;
      panel.hass.fetchWithAuth = () => new Promise(resolve => { window.__rowResolve = resolve; });
      panel.shadowRoot.getElementById("pdf-row-0-invoice").click();
    });
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.getElementById("pdf-row-0-invoice").getAttribute("aria-busy") === "true");
    check("row download busy disables siblings", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const clicked = root.getElementById("pdf-row-0-invoice");
      const sibling = root.getElementById("pdf-row-1-invoice");
      return clicked.classList.contains("working") && sibling.disabled === true && sibling.getAttribute("aria-disabled") === "true" && root.getElementById("pdf-row-1-invoice-mobile").disabled === true;
    }));
    const busyDownload = page.waitForEvent("download");
    await page.evaluate(() => window.__rowResolve(new Response(new TextEncoder().encode("%PDF-1.7\nmock\n%%EOF\n"), { status: 200, headers: { "content-type": "application/pdf" } })));
    await busyDownload;
    await page.waitForFunction(() => document.getElementById("p").shadowRoot.getElementById("pdf-row-0-invoice").getAttribute("aria-busy") !== "true");
    check("row download busy cleared no dialog", await page.evaluate(() => {
      const panel = document.getElementById("p");
      const root = panel.shadowRoot;
      return panel._pdfBusy === false && panel._invoiceBusy === null && !root.querySelector("dialog[open]") && !root.getElementById("pdf-row-1-invoice").disabled;
    }));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel.hass.fetchWithAuth = async () => new Response("", { status: 410 });
      panel.shadowRoot.getElementById("pdf-row-0-invoice").click();
    });
    await page.waitForFunction(() => (document.getElementById("p").shadowRoot.getElementById("invoice-pdf-status")?.textContent || "").includes("hết hạn"));
    check("row stale 410 guidance retry cache invalidated", await page.evaluate(() => {
      const panel = document.getElementById("p");
      const root = panel.shadowRoot;
      return root.getElementById("invoice-pdf-status").getAttribute("role") === "alert" && !root.getElementById("invoice-pdf-retry").hidden && !panel._detailsCache.has(panel._detailKey()) && panel._staleRow?.index === 0 && panel._staleRow?.kind === "invoice";
    }));
    const rowStaleCalls = await page.evaluate(() => window.__wsLog.filter(message => message.type === "evn_cskh/details").length);
    await page.evaluate(() => document.getElementById("p").shadowRoot.getElementById("invoice-pdf-retry").click());
    await page.waitForFunction(previous => window.__wsLog.filter(message => message.type === "evn_cskh/details").length > previous, rowStaleCalls);
    check("row stale retry force refetches details", await page.evaluate(() => window.__wsLog.filter(message => message.type === "evn_cskh/details").at(-1).force === true));
    await page.evaluate(fn => { document.getElementById("p").hass.fetchWithAuth = fn; }, originalFetchWithAuth);
    const paymentFixtures = [
      invoice("private-paid", "09/2026", 9, 1520000, 138000, 1520000, "DATT", "Đã thanh toán", "20/09/2026", "25/09/2026", 873, "VCB", "Quầy VCB", ["invoice"]),
      invoice("private-unknown", "08/2026", 8, 999000, 0, 999000, "UNKNOWN", "Chưa rõ trạng thái", "20/08/2026", "25/08/2026", 100, "VCB", "", []),
      invoice("private-refund", "07/2026", 7, 222000, 0, 222000, "TTOANMOTPHAN", "Đã hoàn trả một phần", "20/07/2026", "25/07/2026", 100, "VCB", "", []),
      invoice("private-unpaid", "06/2026", 6, 120000, 0, -120000, "CHUATT", "Chưa thanh toán", "20/06/2026", "25/06/2026", 100, "VCB", "", []),
      invoice("private-partial", "05/2026", 5, 500000, 0, -456000, "TTOANMOTPHAN", "Thanh toán một phần", "20/05/2026", "25/05/2026", 100, "VCB", "", []),
      ...["DAHT", "CHUAHT", "CHOXULY", null].map((status, index) => invoice(`private-state-${index}`, `0${4 - index}/2026`, 4 - index, 111000, 0, 111000, status, "Chưa xác định", "20/01/2026", "25/01/2026", 100, "VCB", "", [])),
      { ...invoice("private-null", "12/2025", 12, 111000, 0, 111000, "CHUATT", "Chưa thanh toán", "", "25/12/2025", 100, "VCB", "", []), payable_amount: null },
      { ...invoice("private-source", "11/2025", 11, 111000, 0, 111000, "CHUATT", "Chưa thanh toán", "", "25/11/2025", 100, "VCB", "", []), payable_amount: 34567 }
    ];
    check("mock invoice payable DTO status contract", paymentFixtures[0].payable_amount === 0 && paymentFixtures[1].payable_amount === null && paymentFixtures[2].payable_amount === null && paymentFixtures[3].payable_amount === 120000 && paymentFixtures[4].payable_amount === 456000);
    await page.evaluate(invoices => {
      const panel = document.getElementById("p");
      window.__savedInvoiceDetails = panel._details;
      panel._details = { ...panel._details, invoices };
      panel._render();
    }, paymentFixtures);
    const payableRows = await page.evaluate(() => [...document.getElementById("p").shadowRoot.querySelectorAll(".invoice-table tbody tr")].map(row => ({ amount: row.cells[2].textContent, badge: row.querySelector(".badge").className })));
    const formattedMoney = value => new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(value);
    check("DATT positive raw shows paid payable zero desktop", payableRows[0].amount === formattedMoney(0) && payableRows[0].badge.includes("paid") && !payableRows[0].badge.includes("unpaid"));
    check("unknown refund processing missing status positive raw not debt", [1, 2, 5, 6, 7, 8].every(index => payableRows[index].amount === "Chưa xác định" && payableRows[index].badge.includes("unknown")));
    check("CHUATT partial negative raw show positive payable", payableRows[3].amount === formattedMoney(120000) && payableRows[4].amount === formattedMoney(456000) && [3, 4].every(index => payableRows[index].badge.includes("unpaid")));
    check("present payable amount sole display source including null", payableRows[9].amount === "Chưa xác định" && payableRows[10].amount === formattedMoney(34567));
    await page.selectOption("#paid-select", "paid");
    check("paid filter explicit DATT despite positive outstanding", await page.evaluate(() => {
      const rows = [...document.getElementById("p").shadowRoot.querySelectorAll(".invoice-table tbody tr")];
      return rows.length === 1 && rows[0].querySelector("[data-action=invoice]").dataset.index === "0";
    }));
    await page.selectOption("#paid-select", "unpaid");
    check("unpaid filter excludes paid unknown and refunds", await page.evaluate(() => [...document.getElementById("p").shadowRoot.querySelectorAll(".invoice-table tbody [data-action=invoice]")].map(button => button.dataset.index).join() === "3,4,9,10"));
    await page.selectOption("#paid-select", "all");
    await page.setViewportSize({ width: 375, height: 812 });
    check("mobile invoice payable identical no false debt overflow", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const cards = [...root.querySelectorAll(".invoice-card")];
      const amounts = cards.map(card => card.querySelector("p").textContent);
      return amounts[0].startsWith("Còn phải trả: 0") && [1, 2, 5, 6, 7, 8, 9].every(index => amounts[index] === "Còn phải trả: Chưa xác định") && amounts[10].includes("34.567") && cards.every(card => card.scrollWidth <= card.clientWidth + 1);
    }));
    for (const [index, expected] of [[0, formattedMoney(0)], [1, "Chưa xác định"], [2, "Chưa xác định"], [10, formattedMoney(34567)]]) {
      await page.locator(`#invoice-${index}-mobile`).click();
      check(`invoice dialog payable correct for state ${index}`, await page.evaluate(amount => {
        const dialog = document.getElementById("p").shadowRoot.querySelector("dialog");
        const row = [...dialog.querySelectorAll(".dialog-info>div")].find(row => row.querySelector("dt").textContent === "Còn phải trả");
        return row.querySelector("dd").textContent === amount && !dialog.textContent.includes("private-");
      }, expected));
      await page.keyboard.press("Escape");
      await page.waitForFunction(() => !document.getElementById("p")._invoice);
    }
    check("invoice amount chart unchanged by payment-state fixtures", (await chartSnapshot(page, "invoice-comparison")).aria === invoiceChart.aria);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._details = { ...panel._details, invoices: panel._details.invoices.map(invoice => { const { payable_amount, ...legacy } = invoice; return legacy; }) };
      panel._render();
    });
    check("legacy DTO fallback only explicit payable statuses", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      const amounts = [...root.querySelectorAll(".invoice-table tbody tr")].map(row => row.cells[2].textContent);
      return amounts[0].startsWith("0") && [1, 2, 5, 6, 7, 8].every(index => amounts[index] === "Chưa xác định") && amounts[3].includes("120.000") && amounts[4].includes("456.000") && amounts[9].includes("111.000") && amounts[10].includes("111.000");
    }));
    await page.selectOption("#paid-select", "unpaid");
    check("legacy DTO status filter ignores labels paid_date raw debt", await page.evaluate(() => [...document.getElementById("p").shadowRoot.querySelectorAll(".invoice-table tbody [data-action=invoice]")].map(button => button.dataset.index).join() === "3,4,9,10"));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._details = window.__savedInvoiceDetails;
      delete window.__savedInvoiceDetails;
      panel._paid = "all";
      panel._render();
    });
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
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel.hass.fetchWithAuth = async () => new Response("", { status: 410 });
      panel.shadowRoot.getElementById("invoice-0").click();
      panel.shadowRoot.getElementById("pdf-invoice").click();
    });
    await page.waitForFunction(() => (document.getElementById("p").shadowRoot.getElementById("pdf-status")?.textContent || "").includes("hết hạn"));
    check("stale PDF error cache invalidated retry visible", await page.evaluate(() => {
      const panel = document.getElementById("p");
      return panel.shadowRoot.getElementById("pdf-status").getAttribute("role") === "alert" && !panel.shadowRoot.getElementById("pdf-retry").hidden && !panel._detailsCache.has(panel._detailKey());
    }));
    const staleCalls = await page.evaluate(() => window.__wsLog.filter(message => message.type === "evn_cskh/details").length);
    await page.keyboard.press("Escape");
    await page.waitForFunction(previous => window.__wsLog.filter(message => message.type === "evn_cskh/details").length > previous, staleCalls);
    check("stale PDF close reloads details", await page.evaluate(() => window.__wsLog.filter(message => message.type === "evn_cskh/details").at(-1).force === true));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel.shadowRoot.getElementById("invoice-0").click();
      panel.hass.fetchWithAuth = () => new Promise(resolve => window.__pdfResolve = resolve);
      panel.shadowRoot.getElementById("pdf-invoice").click();
    });
    check("PDF busy stale controls disabled", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      return root.getElementById("pdf-invoice").getAttribute("aria-busy") === "true" && root.getElementById("pdf-statement").getAttribute("aria-disabled") === "true";
    }));
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => {
      const panel = document.getElementById("p");
      return !panel._pdfBusy && !panel._invoice && !panel.shadowRoot.querySelector("dialog[open]");
    });
    await page.evaluate(() => window.__pdfResolve(new Response("%PDF-1.7", { headers: { "content-type": "application/pdf" } })));
    check("late PDF ignored after close", await page.evaluate(() => {
      const panel = document.getElementById("p");
      return !panel._pdfBusy && panel._urls.size === 0 && !panel.shadowRoot.querySelector("dialog[open]");
    }));

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
    for (const dark of [false, true]) {
      await page.evaluate(isDark => {
        const panel = document.getElementById("p");
        const colors = isDark ? { "--primary-color": "#68b8ed", "--primary-text-color": "#e9edf1", "--secondary-text-color": "#b4bdc8", "--card-background-color": "#1c2630", "--primary-background-color": "#111820", "--divider-color": "#3c4753" } : { "--primary-color": "#0b74b8", "--primary-text-color": "#1c1c1c", "--secondary-text-color": "#5c6169", "--card-background-color": "#fff", "--primary-background-color": "#f2f4f7", "--divider-color": "#d7dbe0" };
        Object.entries(colors).forEach(([key, value]) => document.documentElement.style.setProperty(key, value));
        panel.hass = { ...panel.hass, themes: { darkMode: isDark } };
      }, dark);
      for (const width of [1280, 375]) {
        await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
        for (let tab = 0; tab < 6; tab++) {
          await clickTab(page, tab);
          const layout = await page.evaluate(() => {
            const panel = document.getElementById("p");
            const root = panel.shadowRoot;
            const shell = root.querySelector(".shell");
            const cards = [...root.querySelectorAll("[data-chart]")];
            const readable = cards.every(card => [...card.querySelectorAll(".slot-value,.chart-label")].every(value => value.scrollWidth <= value.clientWidth + 1 && getComputedStyle(value).display !== "none"));
            const bounded = cards.every(card => card.scrollWidth <= card.clientWidth + 1);
            const aligned = [...root.querySelectorAll(".comparison-chart")].every(chart => {
              const tracks = [...chart.querySelectorAll(".track")].map(track => track.getBoundingClientRect());
              const bars = [...chart.querySelectorAll(".bar")];
              return tracks.every(track => Math.abs(track.top - tracks[0].top) <= 1) && bars.every(bar => {
                const box = bar.getBoundingClientRect();
                const track = bar.parentElement.getBoundingClientRect();
                return Math.abs(box.x + box.width / 2 - track.x - track.width / 2) <= 1 && box.width >= 20;
              });
            });
            const styles = [...root.querySelectorAll(".bar,.zero-axis")].map(element => element.getAttribute("style")).join();
            const svg = root.querySelector(".index-chart");
            return { overflow: Math.max(document.documentElement.scrollWidth - document.documentElement.clientWidth, panel.scrollWidth - panel.clientWidth, shell.scrollWidth - shell.clientWidth), readable, bounded, aligned, finite: !/NaN|Infinity/.test(styles + (svg?.outerHTML || "")), svgSized: !svg || svg.getBoundingClientRect().width > 20 };
          });
          check(`${dark ? "dark" : "light"} ${width} tab ${tab} all charts bounded readable`, layout.overflow <= 1 && layout.bounded && layout.aligned && layout.readable && layout.finite && layout.svgSized);
          if (width === 375 && [0, 1, 2, 3].includes(tab)) await page.screenshot({ path: join(outDir, `${dark ? "dark" : "light"}-375-tab-${tab}.png`), fullPage: true });
        }
      }
    }
    await page.setViewportSize({ width: 1280, height: 900 });
    await clickTab(page, 1);
    const fixedDaily = (await chartSnapshot(page, "daily-comparison")).aria;
    const fixedMonthly = (await chartSnapshot(page, "monthly-comparison")).aria;
    await page.fill("#date-from", "2026-08-01");
    await page.fill("#date-to", "2026-09-30");
    await page.locator("#filter-load").click();
    await page.waitForFunction(() => !document.getElementById("p")._detailsBusy);
    check("history date range not comparison as_of values", (await chartSnapshot(page, "daily-comparison")).aria === fixedDaily && (await chartSnapshot(page, "monthly-comparison")).aria === fixedMonthly);
    await page.selectOption("#point-select", "PD02");
    await page.waitForFunction(() => !document.getElementById("p")._detailsBusy);
    check("point selector daily only monthly customer total unchanged", (await chartSnapshot(page, "daily-comparison")).columns[1].value === "7,25" && (await chartSnapshot(page, "monthly-comparison")).aria === fixedMonthly);
    const keyValues = await page.evaluate(() => {
      const panel = document.getElementById("p");
      const before = panel._detailKey();
      const original = panel._choice;
      panel._choice = { ...original, entry: { ...original.entry, entry_id: "entry-2" } };
      const after = panel._detailKey();
      panel._choice = original;
      return [before, after];
    });
    check("details cache key entry scoped", keyValues[0] !== keyValues[1] && keyValues[0].startsWith("entry-1|") && keyValues[1].startsWith("entry-2|"));
    const setterCalls = await page.evaluate(() => window.__wsCalls);
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      for (let index = 0; index < 20; index++) panel.hass = { ...panel.hass, states: { "sensor.synthetic": { state: index % 2 ? "unknown" : "unavailable" } } };
    });
    check("hass setter no fetch spam", await page.evaluate(() => window.__wsCalls) === setterCalls);
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._overview = { ...window.__data.overview, comparisons: undefined };
      panel._render();
    });
    check("old backend comparison absence helper no fake values", await page.evaluate(() => {
      const root = document.getElementById("p").shadowRoot;
      return root.querySelector('[data-chart="daily-comparison"]').textContent.includes("Máy chủ chưa cung cấp") && root.querySelector('[data-chart="monthly-comparison"]').querySelectorAll(".chart-column").length === 0;
    }));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._overview = null;
      panel._overviewBusy = true;
      panel._render();
    });
    check("comparison loading state", await page.evaluate(() => {
      const card = document.getElementById("p").shadowRoot.querySelector('[data-chart="daily-comparison"]');
      return card.getAttribute("aria-busy") === "true" && card.querySelector('[role="status"]').textContent.includes("Đang tải");
    }));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._overviewBusy = false;
      panel._overview = structuredClone(window.__data.overview);
      panel._overview.available = false;
      panel._overview.comparisons.points = [];
      panel._overview.comparisons.monthly = [];
      panel._render();
    });
    await clickTab(page, 0);
    const unavailable = await chartSnapshot(page, "daily-comparison");
    check("unavailable all null keeps three labeled slots", unavailable.columns.length === 3 && unavailable.columns.every(column => column.height === null && column.value === "Chưa có") && unavailable.text.includes("chưa sẵn sàng"));
    await clickTab(page, 3);
    const allUnknownInvoice = await chartSnapshot(page, "invoice-comparison");
    check("all unknown invoices not zero", allUnknownInvoice.columns.length === 3 && allUnknownInvoice.columns.every(column => column.height === null && column.title.includes("Chưa có dữ liệu")));
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._overview = structuredClone(window.__data.overview);
      panel._overview.comparisons = { as_of: "2027-01-01", points: [{ point_id: "PD02", daily: [{ period: "2026-12-30", kwh: -4, provisional: true }, { period: "2026-12-31", kwh: "3", provisional: true }, { period: "2027-01-01", kwh: 0, provisional: true }] }], monthly: [{ period: "2027-01", kwh: 0, vnd: null, provisional: true }, { period: "2026-11", kwh: -15.25, vnd: -150000, provisional: false }, { period: "2026-12", kwh: 25.5, vnd: 1234567890, provisional: false }] };
      panel._render();
    });
    const rolloverInvoice = await chartSnapshot(page, "invoice-comparison");
    check("browser month rollover full ISO chronology VND", rolloverInvoice.columns.map(column => column.period).join() === "2026-11,2026-12,2027-01" && rolloverInvoice.columns[0].title.includes("-150.000") && rolloverInvoice.text.includes("1.234.567.890"));
    await clickTab(page, 1);
    const rolloverMonthly = await chartSnapshot(page, "monthly-comparison");
    const rolloverDaily = await chartSnapshot(page, "daily-comparison");
    check("browser negative correction scale finite and zero axis", rolloverMonthly.columns[0].height !== null && parseFloat(rolloverMonthly.columns[0].height) > 0 && parseFloat(rolloverMonthly.columns[0].bottom) === 0 && parseFloat(rolloverMonthly.columns[0].axis) > 0 && parseFloat(rolloverMonthly.columns[0].axis) < 100 && !/NaN|Infinity/.test(JSON.stringify(rolloverMonthly)));
    check("browser rollover fixed daily labels no UI date fabrication", rolloverDaily.asOf === "2027-01-01" && rolloverDaily.columns[0].period === "2026-12-30" && rolloverDaily.columns[1].height === null && rolloverDaily.columns[2].height === "0%" && rolloverDaily.columns[0].title.includes("-4 kWh"));
    await page.setViewportSize({ width: 375, height: 812 });
    await clickTab(page, 3);
    check("large money mobile full readable caption no overflow", await page.evaluate(() => {
      const card = document.getElementById("p").shadowRoot.querySelector('[data-chart="invoice-comparison"]');
      const cells = [...card.querySelectorAll("td")];
      return card.scrollWidth <= card.clientWidth + 1 && cells.every(cell => cell.scrollWidth <= cell.clientWidth + 1) && cells[1].textContent.includes("1.234.567.890");
    }));
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel._overview = structuredClone(window.__data.overview);
      panel._render();
      window.__data.overview = structuredClone(window.__data.overview);
      window.__data.overview.comparisons.points[1].daily[2].kwh = 5.75;
      window.__overviewWait = new Promise(resolve => window.__overviewResolve = resolve);
      panel.shadowRoot.getElementById("refresh").click();
    });
    check("WS refresh busy old comparison preserved", (await chartSnapshot(page, "invoice-comparison")).asOf === "2026-10-07");
    await page.evaluate(() => { window.__overviewResolve(); delete window.__overviewWait; });
    await page.waitForFunction(() => !document.getElementById("p")._overviewBusy);
    await clickTab(page, 1);
    check("comparison value updates after overview WS refresh", (await chartSnapshot(page, "daily-comparison")).columns[2].value === "5,75");
    check("filter effective daily window follows actual DTO", (await shadowText()).includes("31/08/2026 → 30/09/2026"));
    const chartBeforeInvalidRange = (await chartSnapshot(page, "monthly-comparison")).aria;
    await page.fill("#date-from", "2026-10-02");
    await page.locator("#date-from").blur();
    check("invalid history range feedback not comparison changes", (await shadowText()).includes("Ngày bắt đầu phải trước") && (await chartSnapshot(page, "monthly-comparison")).aria === chartBeforeInvalidRange);
    await page.fill("#date-from", "2026-08-01");
    await page.locator("#date-from").blur();
    await page.waitForFunction(() => !document.getElementById("p")._detailsBusy);
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      window.__savedCallWS = panel.hass.callWS;
      panel.hass.callWS = message => {
        if (message.type === "evn_cskh/details") return new Promise(resolve => { window.__staleDetailsResolve = resolve; window.__staleDetailsRequest = message; });
        return window.__savedCallWS(message);
      };
      panel._detailsCache.clear();
      panel.shadowRoot.getElementById("point-select").value = "PD01";
      panel.shadowRoot.getElementById("point-select").dispatchEvent(new Event("change", { bubbles: true }));
    });
    await page.evaluate(() => {
      const panel = document.getElementById("p");
      panel.hass.callWS = window.__savedCallWS;
      panel.shadowRoot.getElementById("point-select").value = "PD02";
      panel.shadowRoot.getElementById("point-select").dispatchEvent(new Event("change", { bubbles: true }));
    });
    await page.waitForFunction(() => !document.getElementById("p")._detailsBusy && document.getElementById("p")._details?.point_id === "PD02");
    await page.evaluate(() => window.__staleDetailsResolve({ ...window.__data.details, point_id: "PD01", monthly: [{ period: "2026-09", kwh: 987654321 }] }));
    check("stale point request cannot overwrite selected history", await page.evaluate(() => {
      const panel = document.getElementById("p");
      return panel._point === "PD02" && panel._details.point_id === "PD02" && !panel.shadowRoot.textContent.includes("987.654.321");
    }));
    await page.emulateMedia({ reducedMotion: "reduce" });
    check("reduced motion charts no animation", await page.evaluate(() => [...document.getElementById("p").shadowRoot.querySelectorAll(".bar")].every(bar => getComputedStyle(bar).animationName === "none" && getComputedStyle(bar).transitionDuration === "0s")));
    check("reduced motion smooth line animation off", await page.evaluate(() => {
      const line = document.getElementById("p").shadowRoot.querySelector(".history-line");
      return Boolean(line) && getComputedStyle(line).animationName === "none" && getComputedStyle(line).transitionDuration === "0s";
    }));

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
    if (page && !page.isClosed()) {
      const state = await page.evaluate(() => {
        const panel = document.getElementById("p");
        return { tab: panel?._tab, overviewBusy: panel?._overviewBusy, detailsBusy: panel?._detailsBusy, pdfBusy: panel?._pdfBusy, charts: [...(panel?.shadowRoot.querySelectorAll("[data-chart]") || [])].map(card => card.dataset.chart) };
      }).catch(() => null);
      console.error("synthetic-state", JSON.stringify(state));
    }
  } finally {
    await browser.close();
    server.close();
  }

  console.log(JSON.stringify({ passed: results.filter(item => item.ok).length, total: results.length }));
  for (const item of results) console.log(`${item.ok ? "ok" : "FAIL"}  ${item.name}`);
  if (failure) {
    console.error(String(failure));
    console.error("consoleErrors", JSON.stringify(consoleErrors));
    process.exit(1);
  }
}

main();
