const STYLE = `
:host{display:block;min-width:0;color:var(--primary-text-color,#212121);background:var(--primary-background-color,#f4f5f7);font-family:var(--primary-font-family,inherit);font-size:14px;line-height:1.5;color-scheme:light;--evn-surface:var(--card-background-color,#fff);--evn-line:var(--divider-color,#dce0e4);--evn-muted:var(--secondary-text-color,#61666d);--evn-accent:var(--primary-color,#0075a8);--evn-hover:color-mix(in srgb,var(--primary-text-color,#212121) 6%,var(--evn-surface))}
:host([dark]){color-scheme:dark}*{box-sizing:border-box;min-width:0}h1,h2,h3,p,dl,dd,figure{margin:0}h1{font-size:20px;font-weight:600}h2{font-size:18px;font-weight:600}h3{font-size:16px;font-weight:600}p,dd,h2,h3{overflow-wrap:anywhere}button,input,select{font:inherit;color:inherit;max-width:100%}button,input,select{border:1px solid var(--evn-line);border-radius:12px;background:var(--evn-surface);min-height:40px;padding:8px 12px}button{cursor:pointer;font-weight:500;line-height:1.4}button:hover:not(:disabled):not([aria-disabled=true]){background:var(--evn-hover)}button:disabled,button[aria-disabled=true]{cursor:not-allowed;opacity:.6}button[aria-busy=true]{cursor:progress;opacity:1}button.primary{background:var(--evn-accent);border-color:transparent;color:var(--text-primary-color,#fff)}button.primary:hover:not([aria-disabled=true]){background:color-mix(in srgb,var(--evn-accent) 85%,var(--primary-text-color,#212121))}button.quiet{background:transparent;border-color:transparent}button.link{border-color:transparent;color:var(--evn-accent);background:transparent;text-align:left}button.link:hover{text-decoration:underline}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--evn-accent);outline-offset:3px}input,select{width:100%;height:40px}input[aria-invalid=true]{border-color:var(--error-color,#db4437)}label{display:block;width:fit-content;font-size:12px;font-weight:500;color:var(--evn-muted);margin-bottom:6px}svg{display:block;width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8}button.icon{display:inline-flex;align-items:center;justify-content:center;width:40px;padding:8px;flex:none}.topbar{background:var(--evn-surface);border-bottom:1px solid var(--evn-line)}.top-inner{max-width:1328px;margin:auto;padding:16px 24px;display:flex;align-items:center;gap:24px}.brand{display:flex;align-items:center;gap:12px;flex:1}.account-tools{display:flex;align-items:end;gap:12px}.account-field{width:320px}.account-tools>button{min-width:106px}#menu{display:none}:host([narrow]) #menu{display:inline-flex}.shell{max-width:1328px;margin:auto;padding:24px}.intro{display:flex;align-items:start;justify-content:space-between;gap:16px;margin-bottom:24px}.intro h2{font-size:20px}.intro p{margin-top:4px}.muted,.meta{color:var(--evn-muted)}.meta{font-size:12px}.freshness{text-align:right;max-width:300px}.tabs{display:flex;gap:24px;border-bottom:1px solid var(--evn-line);margin-bottom:24px;padding:4px 4px 0}.tabs button{border:0;border-bottom:2px solid transparent;border-radius:0;background:transparent;min-height:48px;padding:10px 4px;color:var(--evn-muted);white-space:nowrap}.tabs button[aria-selected=true]{border-bottom-color:var(--evn-accent);color:var(--evn-accent)}.stack{display:grid;gap:16px}.card{background:var(--evn-surface);border:1px solid var(--evn-line);border-radius:12px;padding:20px}.card-head{display:flex;align-items:start;justify-content:space-between;gap:16px;margin-bottom:16px}.card-head p{margin-top:4px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.metric{min-height:146px;display:flex;flex-direction:column;gap:8px}.metric-label{color:var(--evn-muted);font-size:13px}.metric-value{font-size:24px;line-height:1.3;font-weight:600;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.metric-value.compact{font-size:18px}.metric .meta{margin-top:auto}.overview-grid{display:grid;grid-template-columns:minmax(0,2.2fr) minmax(0,1fr);gap:16px;align-items:start}.chart-card{min-height:366px}.chart{display:grid;gap:6px;margin-top:32px}.chart-column{text-align:center;min-width:0}.track{height:164px;position:relative;margin:0 auto;max-width:32px}.bar{position:absolute;inset-inline:0;background:var(--evn-accent);border-radius:4px 4px 0 0}.bar.current{opacity:.65}.bar-number{position:absolute;width:100%;font-size:12px;color:var(--evn-muted);line-height:20px;white-space:nowrap;display:flex;justify-content:center}.chart-label{font-size:12px;color:var(--evn-muted);padding-top:12px;margin-top:4px;border-top:1px solid var(--evn-line);white-space:nowrap}.chart.daily .bar-number{display:none}.chart-footer{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:16px;flex-wrap:wrap}.stat-list{display:grid;gap:16px}.stat-list>div{display:grid;gap:4px}.stat-list dt{color:var(--evn-muted);font-size:13px}.stat-list dd{font-weight:500;font-variant-numeric:tabular-nums}.summary-number{font-size:24px;font-weight:600}.notice{border-top:1px solid var(--evn-line);padding-top:16px;margin-top:16px}.notice p{margin-top:8px}.notice button{margin-top:8px}.empty{padding:32px 0;color:var(--evn-muted);text-align:center;overflow-wrap:anywhere}.placeholder{min-height:242px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;text-align:center}.loading{color:var(--evn-muted)}.loading::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--evn-accent);margin-right:8px;animation:pulse 1.4s ease-in-out infinite}.banner{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px;background:var(--evn-surface);border:1px solid var(--evn-line);border-radius:12px;margin-bottom:16px}.banner.error{border-inline-start:3px solid var(--error-color,#db4437)}.banner p{max-width:75ch}.banner button{flex:none}.filters{display:grid;grid-template-columns:minmax(160px,2fr) repeat(2,minmax(140px,1fr)) auto;align-items:end;gap:12px}.filter-help{grid-column:1/-1}.filter-error{color:var(--error-color,#db4437);grid-column:1/-1}.section-tools{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}.segmented{display:inline-flex;gap:4px;padding:4px;border:1px solid var(--evn-line);border-radius:12px;background:var(--evn-surface)}.segmented button{border-color:transparent;min-height:32px;border-radius:8px;padding:6px 12px}.segmented button[aria-pressed=true]{background:var(--evn-hover);color:var(--evn-accent)}.table-wrap{width:100%;overflow:auto;border:1px solid var(--evn-line);border-radius:12px;background:var(--evn-surface);scrollbar-width:thin}.table-wrap:focus-visible{outline-offset:2px}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:14px;text-align:left}caption{text-align:left;padding:12px 16px;font-weight:500;color:var(--evn-muted);font-size:12px}th,td{padding:12px 16px;border-top:1px solid var(--evn-line);vertical-align:middle;overflow-wrap:anywhere}thead th{color:var(--evn-muted);font-weight:500;font-size:12px;background:var(--evn-surface)}td.number,th.number{text-align:right}.reading-table{min-width:680px}.reading-table tbody th{position:sticky;left:0;background:var(--evn-surface);font-weight:500;max-width:140px}.invoice-table tbody tr{cursor:pointer}.invoice-table tbody tr:hover{background:var(--evn-hover)}.invoice-table td:first-child{font-weight:500}.invoice-table button{padding-left:0;padding-right:0}.badge{display:inline-flex;border-radius:8px;padding:4px 8px;font-size:12px;font-weight:500;background:var(--evn-hover);color:var(--evn-muted)}.badge.paid{color:var(--success-color,#168039);background:color-mix(in srgb,var(--success-color,#168039) 10%,var(--evn-surface))}.badge.unpaid{color:var(--warning-color,#9b6511);background:color-mix(in srgb,var(--warning-color,#9b6511) 10%,var(--evn-surface))}.invoice-filters{display:grid;grid-template-columns:minmax(0,1fr) 200px;gap:12px}.pagination{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:16px}.pagination nav{display:flex;gap:8px;align-items:center}.pagination p{font-size:13px;color:var(--evn-muted)}.invoice-cards{display:none}.invoice-card{border-top:1px solid var(--evn-line);padding:16px 0;display:grid;gap:12px}.invoice-card:first-child{border-top:0;padding-top:0}.invoice-card .row{display:flex;align-items:center;justify-content:space-between;gap:12px}.invoice-card strong{font-size:18px;font-weight:600}.invoice-card button{padding:4px 0}.outages{list-style:none;margin:0;padding:0}.outages li{padding:20px 0;border-top:1px solid var(--evn-line)}.outages li:first-child{padding-top:0;border-top:0}.outage-time{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}.outages p{margin-top:8px;white-space:pre-wrap;max-width:80ch}.outages h3{margin-bottom:12px}.lock{padding:32px 0;max-width:640px}.lock h2{margin-bottom:12px}dialog{color:inherit;background:var(--evn-surface);border:1px solid var(--evn-line);border-radius:12px;width:560px;max-width:calc(100vw - 32px);max-height:calc(100dvh - 32px);padding:0;overflow:auto}dialog::backdrop{background:rgba(0,0,0,.42)}.dialog-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px;border-bottom:1px solid var(--evn-line)}.dialog-body{padding:20px;display:grid;gap:20px}.invoice-total{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums}.dialog-info{display:grid;gap:12px}.dialog-info>div{display:grid;grid-template-columns:minmax(100px,1fr) minmax(0,1.3fr);gap:16px}.dialog-info dt{color:var(--evn-muted)}.dialog-info dd{font-variant-numeric:tabular-nums}.pdf-actions{display:flex;gap:8px;flex-wrap:wrap}.pdf-status{min-height:24px}.pdf-status[role=alert]{color:var(--error-color,#db4437)}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.data-table{margin-top:16px}.data-table td:last-child{text-align:right}.data-table table{min-width:240px}[hidden]{display:none!important}@keyframes pulse{50%{opacity:.35}}
@media(max-width:1000px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.overview-grid{grid-template-columns:1fr}.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.freshness{max-width:220px}}
@media(max-width:767px){.top-inner{padding:12px 16px;gap:12px;flex-wrap:wrap}.brand{width:100%}#menu{display:inline-flex}.account-tools{width:100%;gap:8px}.account-field{flex:1;width:auto}.shell{padding:16px}.intro{display:block;margin-bottom:16px}.freshness{text-align:left;max-width:none;margin-top:12px}.tabs{gap:0;justify-content:space-between;margin-bottom:16px}.tabs button{font-size:12px;padding:10px 2px}.card{padding:16px}.metric{min-height:142px}.metric-value{font-size:22px}.metric-value.compact{font-size:16px}.metric-label{font-size:12px}.card-head{gap:12px}.filters{gap:12px}.filters>.point-field{grid-column:1/-1}.filters>button{grid-column:1/-1}input,select{font-size:16px;height:44px}button{min-height:44px}.segmented button{min-height:36px}.bar-number{display:none}.chart{gap:4px}.chart-label{font-size:12px}.track{height:148px}.chart-card{min-height:340px}.invoice-filters{grid-template-columns:1fr}.invoice-table-wrap{display:none}.invoice-cards{display:block}.banner{align-items:start;flex-direction:column}.pagination{align-items:start;flex-direction:column}.pagination nav{width:100%;justify-content:space-between}.outage-time{grid-template-columns:1fr;gap:12px}.dialog-head,.dialog-body{padding:16px}.pdf-actions{display:grid;grid-template-columns:1fr;width:100%}.dialog-info>div{grid-template-columns:1fr 1.2fr;gap:12px}.section-tools{gap:12px}.intro h2{font-size:18px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
`;

const TABS = ["Tổng quan", "Điện năng", "Hóa đơn", "Lịch ngừng điện"];
const DOCUMENTS = { invoice: "Tải hóa đơn PDF", statement: "Bảng kê PDF", notice: "Thông báo PDF" };
const MAX_PDF = 16 * 1024 * 1024;
const numberFormat = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 3 });
const moneyFormat = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 });
const timeFormat = new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", dateStyle: "short", timeStyle: "short" });
const finite = value => typeof value === "number" && Number.isFinite(value);
const numeric = value => finite(value) ? numberFormat.format(value) : "Chưa có dữ liệu";
const money = value => finite(value) ? moneyFormat.format(value) : "Chưa có dữ liệu";
const text = value => value == null || value === "" ? "Chưa có thông tin" : String(value);
const array = value => Array.isArray(value) ? value : [];
const node = (tag, content, className) => {
  const element = document.createElement(tag);
  if (content != null) element.textContent = String(content);
  if (className) element.className = className;
  return element;
};
const time = value => {
  if (!value) return "Chưa có thời gian";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Chưa có thời gian" : timeFormat.format(date);
};
const today = () => {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Ho_Chi_Minh", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  return ["year", "month", "day"].map(type => parts.find(part => part.type === type).value).join("-");
};
const defaultRange = () => {
  const end = today();
  const [year, month] = end.split("-").map(Number);
  return { start: new Date(Date.UTC(year, month - 12, 1)).toISOString().slice(0, 10), end };
};
const validDate = value => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
const paymentState = invoice => {
  const label = String(invoice.status_label || "").toLocaleLowerCase("vi");
  if ((finite(invoice.outstanding) && invoice.outstanding > 0) || label.includes("chưa thanh toán") || label.includes("thanh toán một phần")) return "unpaid";
  if (label.includes("đã thanh toán") || invoice.paid_date) return "paid";
  return "unknown";
};

export class EvnCskhPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    const style = node("style", STYLE);
    this._view = node("div");
    this._dialog = node("dialog");
    this._dialog.setAttribute("aria-labelledby", "invoice-title");
    this.shadowRoot.append(style, this._view, this._dialog);
    this._generation = 0;
    this._overviewRequest = 0;
    this._detailsRequest = 0;
    this._pdfRequest = 0;
    this._urls = new Map();
    this._reset();
  }

  set hass(value) {
    this._hass = value;
    this.toggleAttribute("dark", Boolean(value?.themes?.darkMode));
    this._ready();
  }
  get hass() { return this._hass; }
  set panel(value) { this._panel = value; }
  get panel() { return this._panel; }
  set route(value) { this._route = value; }
  get route() { return this._route; }
  set narrow(value) { this.toggleAttribute("narrow", Boolean(value)); }
  get narrow() { return this.hasAttribute("narrow"); }

  connectedCallback() {
    this._events?.abort();
    this._events = new AbortController();
    for (const type of ["click", "change", "input", "submit", "keydown"]) {
      this.shadowRoot.addEventListener(type, event => this._event(event), { signal: this._events.signal });
    }
    this._dialog.addEventListener("close", () => this._closeInvoice(), { signal: this._events.signal });
    this._ready();
  }

  disconnectedCallback() {
    this._events?.abort();
    this._session = undefined;
    this._reset();
    this._view.replaceChildren();
  }

  _admin() { return this.isConnected && this._hass?.user?.is_admin === true; }
  _cooling() { return Date.now() < (this._cooldown || 0); }

  _reset() {
    this._generation++;
    this._cancelPdf();
    clearTimeout(this._rateTimer);
    this._cooldown = 0;
    this._choices = [];
    this._choice = null;
    this._point = "";
    this._range = defaultRange();
    this._overview = null;
    this._details = null;
    this._overviewBusy = this._detailsBusy = this._listBusy = false;
    this._overviewError = this._detailsError = this._listError = "";
    this._authError = "";
    this._rangeError = "";
    this._tab = 0;
    this._period = "monthly";
    this._energyView = "chart";
    this._tableOpen = false;
    this._detailsWanted = false;
    this._query = "";
    this._paid = "all";
    this._invoicePage = this._readingPage = 0;
  }

  _ready() {
    if (!this.isConnected) return;
    const session = `${this._hass?.user?.id || ""}:${this._hass?.user?.is_admin === true}`;
    if (this._session !== session || this._connection !== this._hass?.connection) {
      this._reset();
      this._session = session;
      this._connection = this._hass?.connection;
      this._render();
      if (this._admin() && typeof this._hass.callWS === "function") void this._loadEntries();
    } else if (!this._view.firstChild) this._render();
  }

  _current(generation) { return this._admin() && generation === this._generation; }

  _error(error) {
    const code = String(error?.code || error?.status || "").toLowerCase();
    if (["401", "403", "auth", "unauthorized", "forbidden", "auth_required", "auth_failed", "invalid_auth", "reauth_required", "not_admin"].includes(code)) {
      this._reset();
      this._authError = "Phiên xác thực không còn hợp lệ. Hãy đăng nhập lại Home Assistant hoặc xác thực lại tích hợp EVN CSKH trong Cài đặt.";
      return this._authError;
    }
    if (["429", "rate_limited", "rate_limit", "too_many_requests"].includes(code)) {
      const wait = Math.max(1, Math.min(60, Number(error?.retry_after) || 30));
      this._cooldown = Date.now() + wait * 1000;
      clearTimeout(this._rateTimer);
      this._rateTimer = setTimeout(() => { if (this.isConnected) this._render(); }, wait * 1000 + 20);
      return `EVN đang giới hạn lượt truy cập. Vui lòng đợi ${Math.ceil(wait)} giây trước khi thử lại.`;
    }
    return "Chưa thể tải dữ liệu từ EVN. Kiểm tra kết nối hoặc trạng thái tích hợp rồi thử lại.";
  }

  async _loadEntries() {
    if (!this._admin() || this._listBusy || this._cooling()) return;
    this._authError = this._listError = "";
    this._listBusy = true;
    const generation = ++this._generation;
    this._render();
    try {
      const response = await this._hass.callWS({ type: "evn_cskh/list_entries" });
      if (!this._current(generation)) return;
      if (!Array.isArray(response?.entries)) throw new Error("schema");
      this._choices = response.entries.flatMap(entry => array(entry.customers).map(customer => ({ entry, customer })));
      this._listBusy = false;
      if (this._choices.length) this._selectCustomer(0);
      else this._render();
    } catch (error) {
      if (!this._current(generation)) return;
      this._listBusy = false;
      this._listError = this._error(error);
      this._render();
    }
  }

  _selectCustomer(index) {
    const selected = this._choices[index];
    if (!selected || !this._admin()) return;
    this._generation++;
    this._cancelPdf();
    this._choice = selected;
    this._point = array(selected.customer.points)[0]?.id || "";
    this._range = defaultRange();
    this._overview = this._details = null;
    this._overviewBusy = this._detailsBusy = false;
    this._overviewError = this._detailsError = this._rangeError = "";
    this._query = "";
    this._paid = "all";
    this._invoicePage = this._readingPage = 0;
    this._detailsWanted = this._tab === 1 || this._tab === 2;
    this._render();
    void this._loadOverview();
    if (this._detailsWanted) void this._loadDetails();
  }

  _args() {
    return { entry_id: this._choice.entry.entry_id, customer_key: this._choice.customer.key };
  }

  async _loadOverview(refresh = false) {
    if (!this._admin() || !this._choice || this._overviewBusy || this._cooling()) return;
    const generation = this._generation;
    const request = ++this._overviewRequest;
    this._overviewBusy = true;
    this._overviewError = "";
    this._render();
    try {
      const response = await this._hass.callWS({ type: "evn_cskh/overview", ...this._args(), ...(refresh ? { refresh: true } : {}) });
      if (!this._current(generation) || request !== this._overviewRequest) return;
      if (!response?.customer || !Array.isArray(response.usage)) throw new Error("schema");
      this._overview = response;
    } catch (error) {
      if (!this._current(generation) || request !== this._overviewRequest) return;
      this._overviewError = this._error(error);
    } finally {
      if (this._current(generation) && request === this._overviewRequest) this._overviewBusy = false;
      if (this.isConnected) this._render();
    }
  }

  _validateRange() {
    const { start, end } = this._range;
    if (!validDate(start) || !validDate(end)) return "Nhập đầy đủ ngày bắt đầu và ngày kết thúc hợp lệ.";
    if (start > end) return "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.";
    if (end > today()) return "Ngày kết thúc không được sau hôm nay.";
    if ((Date.parse(end) - Date.parse(start)) / 86400000 + 1 > 366) return "Chọn khoảng thời gian không quá 366 ngày.";
    return "";
  }

  _invalidateDetails() {
    const restartOverview = this._overviewBusy;
    this._generation++;
    this._cancelPdf();
    this._details = null;
    this._detailsBusy = this._overviewBusy = false;
    this._detailsError = this._rangeError = "";
    this._invoicePage = this._readingPage = 0;
    this._render();
    if (restartOverview) void this._loadOverview();
  }

  async _loadDetails(force = false) {
    if (!this._admin() || !this._choice || !this._point || this._detailsBusy || this._cooling()) return;
    this._detailsWanted = true;
    this._rangeError = this._validateRange();
    if (this._rangeError) { this._render(); return; }
    if (this._details && !force) return;
    const generation = this._generation;
    const request = ++this._detailsRequest;
    this._detailsBusy = true;
    this._detailsError = "";
    this._render();
    try {
      const response = await this._hass.callWS({ type: "evn_cskh/details", ...this._args(), point_id: this._point, ...this._range, ...(force ? { force: true } : {}) });
      if (!this._current(generation) || request !== this._detailsRequest) return;
      if (!response || ![response.monthly, response.daily, response.readings, response.invoices].every(Array.isArray)) throw new Error("schema");
      this._details = response;
    } catch (error) {
      if (!this._current(generation) || request !== this._detailsRequest) return;
      this._detailsError = this._error(error);
    } finally {
      if (this._current(generation) && request === this._detailsRequest) this._detailsBusy = false;
      if (this.isConnected) this._render();
    }
  }

  _setTab(tab) {
    if (!Number.isInteger(tab) || tab < 0 || tab >= TABS.length) return;
    this._tab = tab;
    this._render();
    if (tab === 1 || tab === 2) void this._loadDetails();
  }

  _event(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (event.type === "keydown" && target.getAttribute("role") === "tab") {
      const index = Number(target.dataset.tab);
      const next = { ArrowRight: (index + 1) % 4, ArrowLeft: (index + 3) % 4, Home: 0, End: 3 }[event.key];
      if (next !== undefined) {
        event.preventDefault();
        this._setTab(next);
        this.shadowRoot.getElementById(`tab-${next}`)?.focus();
      }
      return;
    }
    if (event.type === "input") {
      if (target.id === "invoice-search") {
        this._query = target.value;
        this._invoicePage = 0;
        this._render();
      }
      if (target.id === "date-from") this._range.start = target.value;
      if (target.id === "date-to") this._range.end = target.value;
      return;
    }
    if (event.type === "change") {
      if (target.id === "customer-select") this._selectCustomer(Number(target.value));
      if (target.id === "point-select") { this._point = target.value; this._invalidateDetails(); }
      if (target.id === "date-from" || target.id === "date-to") this._invalidateDetails();
      if (target.id === "paid-select") { this._paid = target.value; this._invoicePage = 0; this._render(); }
      return;
    }
    if (event.type === "submit") {
      event.preventDefault();
      if (target.id === "history-filter") void this._loadDetails();
      return;
    }
    if (event.type !== "click") return;
    const control = target.closest("[data-action]");
    if (!control || control.getAttribute("aria-disabled") === "true" || control.disabled) return;
    const action = control.dataset.action;
    if (action === "menu") {
      this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
      return;
    }
    if (!this._admin()) return;
    if (action === "tab") this._setTab(Number(control.dataset.tab));
    if (action === "entries") void this._loadEntries();
    if (action === "overview") void this._loadOverview(true);
    if (action === "details") void this._loadDetails();
    if (action === "refresh") {
      void this._loadOverview(true);
      if (this._detailsWanted && this._tab !== 3) void this._loadDetails(true);
    }
    if (action === "period") { this._period = control.dataset.value; this._readingPage = 0; this._render(); }
    if (action === "energy-view") { this._energyView = control.dataset.value; this._render(); }
    if (action === "chart-table") { this._tableOpen = !this._tableOpen; this._render(); }
    if (action === "invoice-page") { this._invoicePage += Number(control.dataset.step); this._render(); this.shadowRoot.getElementById("invoice-results")?.focus({ preventScroll: true }); }
    if (action === "reading-page") { this._readingPage += Number(control.dataset.step); this._render(); this.shadowRoot.getElementById("reading-results")?.focus({ preventScroll: true }); }
    if (action === "clear-search") { this._query = ""; this._paid = "all"; this._invoicePage = 0; this._render(); this.shadowRoot.getElementById("invoice-search")?.focus(); }
    if (action === "invoice") this._openInvoice(Number(control.dataset.index));
    if (action === "close-invoice") this._dialog.close();
    if (action === "pdf") void this._download(control.dataset.kind);
  }

  _button(label, action, id, className = "", unavailable = false) {
    const button = node("button", label, className);
    button.type = "button";
    button.dataset.action = action;
    if (id) button.id = id;
    if (unavailable) button.setAttribute("aria-disabled", "true");
    return button;
  }

  _iconButton(label, action, id, path) {
    const button = this._button(null, action, id, "quiet icon");
    button.setAttribute("aria-label", label);
    button.title = label;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    const line = document.createElementNS(svg.namespaceURI, "path");
    line.setAttribute("d", path);
    svg.append(line);
    button.append(svg);
    return button;
  }

  _field(label, input, className = "") {
    const field = node("div", null, className);
    const caption = node("label", label);
    caption.htmlFor = input.id;
    field.append(caption, input);
    return field;
  }

  _banner(message, action, id, error = true) {
    const banner = node("div", null, `banner${error ? " error" : ""}`);
    banner.setAttribute("role", error ? "alert" : "status");
    banner.append(node("p", message));
    if (action) banner.append(this._button("Thử lại", action, id, "", this._cooling()));
    return banner;
  }

  _render() {
    if (!this.isConnected) return;
    const active = this.shadowRoot.activeElement;
    const focusId = active?.id;
    const selection = active instanceof HTMLInputElement && active.type === "search" ? [active.selectionStart, active.selectionEnd] : null;
    const top = node("header", null, "topbar");
    const inner = node("div", null, "top-inner");
    const brand = node("div", null, "brand");
    brand.append(this._iconButton("Mở trình đơn Home Assistant", "menu", "menu", "M4 6h16M4 12h16M4 18h16"), node("h1", "EVN CSKH"));
    inner.append(brand);
    top.append(inner);
    const main = node("main", null, "shell");
    if (!this._admin()) {
      const lock = node("section", null, "lock");
      lock.setAttribute("role", "status");
      lock.append(node("h2", this._hass?.user ? "Chỉ dành cho quản trị viên" : "Đang chờ phiên Home Assistant"), node("p", "Thông tin điện và hóa đơn chỉ hiển thị trong phiên Home Assistant có quyền quản trị.", "muted"));
      main.append(lock);
    } else if (this._authError) main.append(this._banner(this._authError, "entries", "auth-retry"));
    else if (this._listBusy) main.append(node("p", "Đang tải tài khoản EVN CSKH…", "loading lock"));
    else if (this._listError) main.append(this._banner(this._listError, "entries", "list-retry"));
    else if (!this._choice) {
      main.append(node("h2", "Chưa có khách hàng được liên kết"), node("p", "Thêm hoặc kiểm tra tích hợp EVN CSKH trong Cài đặt Home Assistant, sau đó tải lại danh sách.", "empty"), this._button("Tải lại danh sách", "entries", "entries-reload"));
    } else {
      const tools = node("div", null, "account-tools");
      const select = node("select");
      select.id = "customer-select";
      this._choices.forEach((choice, index) => {
        const option = node("option", `${text(choice.entry.title)} · ${text(choice.customer.code)}`);
        option.value = String(index);
        option.selected = choice === this._choice;
        select.append(option);
      });
      const refresh = this._button("Cập nhật", "refresh", "refresh", "", this._overviewBusy || this._detailsBusy || this._cooling());
      refresh.setAttribute("aria-busy", String(this._overviewBusy || this._detailsBusy));
      tools.append(this._field("Tài khoản / khách hàng", select, "account-field"), refresh);
      inner.append(tools);
      const customer = this._choice.customer;
      const intro = node("section", null, "intro");
      const identity = node("div");
      identity.append(node("h2", text(customer.name)), node("p", `${text(customer.code)} · ${text(customer.unit)}`, "muted"));
      intro.append(identity);
      const freshness = node("p", this._overviewBusy ? "Đang cập nhật tổng quan…" : this._overview?.fetched_at ? `Cập nhật: ${time(this._overview.fetched_at)}` : "Chưa có lần cập nhật thành công", "freshness meta");
      freshness.setAttribute("role", "status");
      intro.append(freshness);
      main.append(intro);
      const tabs = node("nav", null, "tabs");
      tabs.setAttribute("role", "tablist");
      tabs.setAttribute("aria-label", "Thông tin điện");
      TABS.forEach((label, index) => {
        const tab = this._button(label, "tab", `tab-${index}`);
        tab.dataset.tab = String(index);
        tab.setAttribute("role", "tab");
        tab.setAttribute("aria-selected", String(index === this._tab));
        tab.setAttribute("aria-controls", "tab-content");
        tab.tabIndex = index === this._tab ? 0 : -1;
        tabs.append(tab);
      });
      main.append(tabs);
      if (this._overviewError) main.append(this._banner(this._overviewError, "overview", "overview-retry"));
      if (this._overview?.available === false || customer.available === false) main.append(this._banner("Kết nối EVN hiện chưa sẵn sàng. Số liệu còn hiển thị là dữ liệu đã lưu, không phải cập nhật mới.", null, null, false));
      const content = node("section", null, "stack");
      content.id = "tab-content";
      content.setAttribute("role", "tabpanel");
      content.setAttribute("aria-labelledby", `tab-${this._tab}`);
      if (this._tab === 0) this._renderOverview(content);
      if (this._tab === 1 || this._tab === 2) {
        content.append(this._filters());
        if (this._detailsError) content.append(this._banner(this._detailsError, "details", "details-retry"));
        if (this._detailsBusy) {
          const status = node("p", "Đang tải lịch sử điện và hóa đơn…", "loading");
          status.setAttribute("role", "status");
          content.append(status);
        }
        if (this._details) {
          content.append(node("p", `Lịch sử cập nhật: ${time(this._details.fetched_at)} · Giờ Việt Nam`, "meta"));
          if (this._tab === 1) this._renderEnergy(content);
          else this._renderInvoices(content);
        } else if (!this._detailsBusy && !this._detailsError) content.append(node("p", this._point ? "Chọn khoảng ngày và tải dữ liệu của điểm đo này." : "Khách hàng này chưa có điểm đo để tra cứu lịch sử.", "empty"));
      }
      if (this._tab === 3) this._renderOutages(content);
      main.append(content);
    }
    this._view.replaceChildren(top, main);
    if (focusId && !this._dialog.contains(active)) {
      const next = this.shadowRoot.getElementById(focusId);
      next?.focus({ preventScroll: true });
      if (selection && next instanceof HTMLInputElement) next.setSelectionRange(...selection);
    }
  }

  _metric(label, value, detail, compact = false) {
    const card = node("section", null, "card metric");
    card.append(node("h3", label, "metric-label"), node("p", value, `metric-value${compact ? " compact" : ""}`), node("p", detail, "meta"));
    return card;
  }

  _renderOverview(parent) {
    const overview = this._overview;
    const usage = array(overview?.usage).find(item => item.point_id === this._point);
    const metrics = node("div", null, "metrics");
    const energy = sample => finite(sample?.kwh) ? `${numeric(sample.kwh)} kWh` : "Chưa có dữ liệu";
    metrics.append(
      this._metric("Điện năng tháng gần nhất", energy(usage?.monthly), usage?.monthly?.period ? `Kỳ ${usage.monthly.period}` : "Chưa có kỳ ghi nhận", !finite(usage?.monthly?.kwh)),
      this._metric("Khoảng ghi nhận gần nhất", energy(usage?.daily), usage?.daily?.period ? text(usage.daily.period) : "Có thể gộp nhiều ngày", !finite(usage?.daily?.kwh)),
      this._metric("Tiền chưa thanh toán", money(overview?.outstanding?.amount), finite(overview?.outstanding?.count) ? `${numeric(overview.outstanding.count)} hóa đơn chưa thanh toán` : "Chưa xác định số hóa đơn", !finite(overview?.outstanding?.amount)),
      this._metric("Lần ngừng điện tiếp theo", overview?.next_outage?.start ? time(overview.next_outage.start) : overview ? "Chưa có lịch" : "Chưa có dữ liệu", "Theo kế hoạch của điện lực", true)
    );
    parent.append(metrics);
    const layout = node("div", null, "overview-grid");
    const chart = node("section", null, "card chart-card");
    const head = node("header", null, "card-head");
    const title = node("div");
    title.append(node("h2", "Điện năng theo tháng"), node("p", `Điểm đo ${text(this._point)} · kWh`, "meta"));
    head.append(title);
    chart.append(head);
    if (this._details) this._renderChart(chart, "monthly");
    else {
      const placeholder = node("div", null, "placeholder");
      placeholder.append(node("p", this._detailsBusy ? "Đang tải lịch sử điện…" : "Xem các kỳ điện năng của điểm đo trong 12 tháng gần đây.", this._detailsBusy ? "loading" : "muted"));
      if (this._point) placeholder.append(this._button("Xem lịch sử", "details", "history-load", "primary", this._detailsBusy || this._cooling()));
      else placeholder.append(node("p", "Khách hàng này chưa có điểm đo.", "meta"));
      chart.append(placeholder);
    }
    if (this._detailsError) chart.append(this._banner(this._detailsError, "details", "chart-retry"));
    layout.append(chart);
    const summary = node("section", null, "card");
    summary.append(node("h2", "Trong khoảng đã chọn"));
    const list = node("dl", null, "stat-list notice");
    const records = this._monthly();
    const known = records.filter(record => finite(record.kwh));
    const pairs = [
      ["Tổng điện năng đã ghi nhận", known.length ? `${numeric(known.reduce((sum, record) => sum + record.kwh, 0))} kWh` : "Chưa có dữ liệu"],
      ["Phạm vi lịch sử", `${this._range.start} → ${this._range.end}`],
      ["Kỳ có số liệu", this._details ? `${known.length} / ${records.length} tháng` : "Lịch sử chưa được tải"]
    ];
    for (const [label, value] of pairs) { const row = node("div"); row.append(node("dt", label), node("dd", value)); list.append(row); }
    summary.append(list);
    const notice = node("div", null, "notice");
    notice.append(node("h3", "Lưu ý từ điện lực"), node("p", overview?.next_outage ? text(overview.next_outage.reason) : "Lịch ngừng điện là kế hoạch, không phản ánh tình trạng điện lưới theo thời gian thực.", "muted"));
    if (overview?.next_outage?.area) notice.append(node("p", text(overview.next_outage.area), "meta"));
    const outages = this._button("Xem lịch ngừng điện", "tab", "open-outages", "link");
    outages.dataset.tab = "3";
    notice.append(outages);
    summary.append(notice);
    layout.append(summary);
    parent.append(layout);
  }

  _filters() {
    const form = node("form", null, "card filters");
    form.id = "history-filter";
    const point = node("select");
    point.id = "point-select";
    for (const item of array(this._choice.customer.points)) {
      const option = node("option", `${text(item.id)} · ${text(item.address)}`);
      option.value = item.id;
      option.selected = item.id === this._point;
      point.append(option);
    }
    point.disabled = !point.options.length;
    form.append(this._field("Điểm đo", point, "point-field"));
    for (const [id, label, key] of [["date-from", "Từ ngày", "start"], ["date-to", "Đến ngày", "end"]]) {
      const input = node("input");
      input.id = id;
      input.type = "date";
      input.required = true;
      input.max = today();
      input.value = this._range[key];
      input.setAttribute("aria-describedby", "range-help range-error");
      input.setAttribute("aria-invalid", String(Boolean(this._rangeError)));
      form.append(this._field(label, input));
    }
    const load = this._button("Tải dữ liệu", "submit-filter", "filter-load", "primary", this._detailsBusy || this._cooling());
    load.type = "submit";
    load.disabled = !this._point;
    load.setAttribute("aria-busy", String(this._detailsBusy));
    form.append(load);
    const help = node("p", "Tối đa 366 ngày. Dữ liệu ngày chỉ có trong 31 ngày gần nhất; một bản ghi có thể gộp nhiều ngày.", "meta filter-help");
    help.id = "range-help";
    const error = node("p", this._rangeError, "filter-error");
    error.id = "range-error";
    error.setAttribute("role", "alert");
    error.hidden = !this._rangeError;
    form.append(help, error);
    return form;
  }

  _monthly() {
    if (!this._details || !validDate(this._range.start) || !validDate(this._range.end)) return [];
    const values = new Map(array(this._details.monthly).map(item => [item.period, item.kwh]));
    const date = new Date(`${this._range.start.slice(0, 7)}-01T00:00:00Z`);
    const result = [];
    for (let i = 0; i < 13 && date.toISOString().slice(0, 7) <= this._range.end.slice(0, 7); i++) {
      const period = date.toISOString().slice(0, 7);
      result.push({ period, kwh: values.get(period) ?? null });
      date.setUTCMonth(date.getUTCMonth() + 1);
    }
    return result;
  }

  _renderChart(parent, period) {
    const records = period === "monthly" ? this._monthly() : [...array(this._details?.daily)].sort((a, b) => String(a.period).localeCompare(String(b.period), "vi", { numeric: true }));
    if (!records.some(item => finite(item.kwh))) {
      parent.append(node("p", "Chưa có số liệu điện năng của điểm đo trong khoảng này.", "empty"));
      return;
    }
    const known = records.filter(item => finite(item.kwh)).map(item => item.kwh);
    const low = Math.min(0, ...known);
    const high = Math.max(0, ...known);
    const span = high - low || 1;
    const chart = node("div", null, `chart ${period === "daily" ? "daily" : "monthly"}`);
    chart.setAttribute("role", "img");
    chart.setAttribute("aria-label", `Điện năng ${period === "monthly" ? "tháng" : "ngày"}, đơn vị kWh. Có bảng số liệu bên dưới; khoảng trống là chưa có dữ liệu.`);
    chart.style.gridTemplateColumns = `repeat(${records.length},minmax(0,1fr))`;
    records.forEach((item, index) => {
      const column = node("div", null, "chart-column");
      column.dataset.period = item.period;
      const track = node("div", null, "track");
      const hasValue = finite(item.kwh);
      const value = hasValue ? item.kwh : 0;
      if (hasValue) {
        const bar = node("div", null, `bar${item.period === today().slice(0, 7) ? " current" : ""}`);
        bar.style.height = `${Math.abs(value) / span * 100}%`;
        bar.style.bottom = `${(Math.min(0, value) - low) / span * 100}%`;
        track.append(bar);
      }
      const amount = node("span", hasValue ? numeric(value) : "—", "bar-number");
      amount.style.bottom = `${(Math.max(0, value) - low) / span * 100}%`;
      track.append(amount);
      column.title = `${item.period}: ${hasValue ? `${numeric(value)} kWh` : "Chưa có dữ liệu"}`;
      const label = period === "monthly" ? String(item.period).slice(5, 7) : index % Math.max(1, Math.ceil(records.length / 6)) === 0 ? String(item.period).slice(5, 10) : "";
      column.append(track, node("div", label, "chart-label"));
      chart.append(column);
    });
    parent.append(chart);
    const footer = node("div", null, "chart-footer");
    footer.append(node("p", `${records[0].period} → ${records.at(-1).period} · kWh`, "meta"));
    const toggle = this._button(this._tableOpen ? "Ẩn bảng số liệu" : "Xem bảng số liệu", "chart-table", "chart-table-toggle", "link");
    toggle.setAttribute("aria-expanded", String(this._tableOpen));
    toggle.setAttribute("aria-controls", "chart-data");
    footer.append(toggle);
    parent.append(footer, node("p", "Khoảng trống không phải là 0. Tháng hiện tại có thể chưa chốt số.", "meta"));
    const table = this._table(["Kỳ ghi nhận", "Điện năng (kWh)"], records.map(item => [text(item.period), numeric(item.kwh)]), "Số liệu điện năng, giữ nguyên khoảng thiếu dữ liệu", "data-table");
    table.id = "chart-data";
    table.hidden = !this._tableOpen;
    parent.append(table);
  }

  _segments(items, current, action, label) {
    const group = node("div", null, "segmented");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", label);
    for (const [value, caption] of items) {
      const button = this._button(caption, action, `${action}-${value}`);
      button.dataset.value = value;
      button.setAttribute("aria-pressed", String(current === value));
      group.append(button);
    }
    return group;
  }

  _renderEnergy(parent) {
    const tools = node("div", null, "section-tools");
    tools.append(this._segments([["monthly", "Theo tháng"], ["daily", "Theo ngày"]], this._period, "period", "Kỳ điện năng"), this._segments([["chart", "Biểu đồ"], ["readings", "Chỉ số công tơ"]], this._energyView, "energy-view", "Cách xem điện năng"));
    parent.append(tools);
    if (this._energyView === "chart") {
      const card = node("section", null, "card chart-card");
      card.append(node("h2", this._period === "monthly" ? "Điện năng theo tháng" : "Điện năng trong 31 ngày gần nhất"));
      this._renderChart(card, this._period);
      parent.append(card);
      return;
    }
    const records = array(this._details.readings).filter(item => item.kind === this._period);
    if (!records.length) { parent.append(node("p", "Chưa có chỉ số công tơ của điểm đo trong khoảng này.", "empty")); return; }
    this._readingPage = Math.max(0, Math.min(this._readingPage, Math.ceil(records.length / 20) - 1));
    const rows = records.slice(this._readingPage * 20, this._readingPage * 20 + 20).map(item => [text(item.period), `${text(item.meter)} / ${text(item.register)}`, numeric(item.old), numeric(item.new), numeric(item.multiplier), numeric(item.kwh)]);
    const table = this._table(["Kỳ ghi nhận", "Công tơ / bộ chỉ số", "Chỉ số cũ", "Chỉ số mới", "Hệ số", "kWh"], rows, "Chỉ số do điện lực cung cấp", "", "reading-table");
    table.id = "reading-results";
    parent.append(table, this._pagination(records.length, this._readingPage, 20, "reading-page"));
  }

  _table(headers, rows, caption, className = "", tableClass = "") {
    const wrap = node("div", null, `table-wrap ${className}`);
    wrap.tabIndex = 0;
    wrap.setAttribute("role", "region");
    wrap.setAttribute("aria-label", caption);
    const table = node("table", null, tableClass);
    table.append(node("caption", caption));
    const head = node("thead");
    const heading = node("tr");
    headers.forEach(label => { const cell = node("th", label); cell.scope = "col"; heading.append(cell); });
    head.append(heading);
    const body = node("tbody");
    rows.forEach(row => {
      const line = node("tr");
      row.forEach((value, index) => { const cell = node(index ? "td" : "th", value); if (!index) cell.scope = "row"; line.append(cell); });
      body.append(line);
    });
    table.append(head, body);
    wrap.append(table);
    return wrap;
  }

  _badge(invoice) { return node("span", text(invoice.status_label), `badge ${paymentState(invoice)}`); }

  _renderInvoices(parent) {
    const filters = node("div", null, "invoice-filters");
    const search = node("input");
    search.id = "invoice-search";
    search.type = "search";
    search.placeholder = "Ví dụ: 09/2026";
    search.value = this._query;
    search.autocomplete = "off";
    const paid = node("select");
    paid.id = "paid-select";
    for (const [value, label] of [["all", "Tất cả"], ["paid", "Đã thanh toán"], ["unpaid", "Chưa thanh toán"]]) {
      const option = node("option", label); option.value = value; option.selected = this._paid === value; paid.append(option);
    }
    filters.append(this._field("Tìm kỳ hóa đơn", search), this._field("Trạng thái thanh toán", paid));
    parent.append(filters);
    const invoices = this._details.invoices.map((invoice, index) => ({ invoice, index })).filter(({ invoice }) => {
      const haystack = `${invoice.period} ${invoice.status_label}`.toLocaleLowerCase("vi");
      return haystack.includes(this._query.trim().toLocaleLowerCase("vi")) && (this._paid === "all" || paymentState(invoice) === this._paid);
    });
    const results = node("section");
    results.id = "invoice-results";
    results.tabIndex = -1;
    results.setAttribute("aria-label", "Kết quả hóa đơn");
    if (!invoices.length) {
      results.append(node("p", this._query || this._paid !== "all" ? "Không có hóa đơn khớp bộ lọc. Thử kỳ khác hoặc bỏ bộ lọc." : "Chưa có hóa đơn của khách hàng này trong khoảng đã chọn.", "empty"));
      if (this._query || this._paid !== "all") results.append(this._button("Xóa lọc", "clear-search", "clear-search", "link"));
      parent.append(results);
      return;
    }
    this._invoicePage = Math.max(0, Math.min(this._invoicePage, Math.ceil(invoices.length / 12) - 1));
    const visible = invoices.slice(this._invoicePage * 12, this._invoicePage * 12 + 12);
    const wrap = node("div", null, "table-wrap invoice-table-wrap");
    const table = node("table", null, "invoice-table");
    table.append(node("caption", "Hóa đơn trong khoảng đã chọn · Chọn kỳ để xem chi tiết và tải PDF"));
    const head = node("thead");
    const line = node("tr");
    for (const label of ["Kỳ hóa đơn", "Tổng tiền", "Còn phải trả", "Trạng thái", "Hạn thanh toán"]) { const cell = node("th", label); cell.scope = "col"; line.append(cell); }
    head.append(line);
    const body = node("tbody");
    const cards = node("div", null, "card invoice-cards");
    for (const { invoice, index } of visible) {
      const row = node("tr");
      row.dataset.action = "invoice";
      row.dataset.index = String(index);
      const first = node("th");
      first.scope = "row";
      first.append(this._invoiceButton(invoice, index, false));
      if (invoice.cycle != null) first.append(node("p", `Kỳ thu ${text(invoice.cycle)}`, "meta"));
      const status = node("td");
      status.append(this._badge(invoice));
      row.append(first, node("td", money(invoice.amount), "number"), node("td", money(invoice.outstanding), "number"), status, node("td", text(invoice.due_date)));
      body.append(row);
      const card = node("article", null, "invoice-card");
      const top = node("div", null, "row");
      top.append(this._invoiceButton(invoice, index, true), this._badge(invoice));
      card.append(top, node("strong", money(invoice.amount)), node("p", `Còn phải trả: ${money(invoice.outstanding)}`, "meta"), node("p", `Hạn thanh toán: ${text(invoice.due_date)}`, "meta"));
      cards.append(card);
    }
    table.append(head, body);
    wrap.append(table);
    results.append(wrap, cards, this._pagination(invoices.length, this._invoicePage, 12, "invoice-page"));
    parent.append(results);
  }

  _invoiceButton(invoice, index, mobile) {
    const button = this._button(text(invoice.period), "invoice", `invoice-${index}${mobile ? "-mobile" : ""}`, "link");
    button.dataset.index = String(index);
    button.setAttribute("aria-label", `Xem hóa đơn ${text(invoice.period)}${invoice.cycle != null ? `, kỳ thu ${invoice.cycle}` : ""}`);
    button.setAttribute("aria-haspopup", "dialog");
    return button;
  }

  _pagination(total, page, size, action) {
    const footer = node("div", null, "pagination");
    const count = node("p", `${page * size + 1}–${Math.min((page + 1) * size, total)} / ${total} bản ghi`);
    count.setAttribute("role", "status");
    footer.append(count);
    if (total > size) {
      const nav = node("nav");
      nav.setAttribute("aria-label", "Phân trang");
      for (const [label, step, unavailable] of [["Trang trước", -1, page === 0], ["Trang sau", 1, (page + 1) * size >= total]]) {
        const button = this._button(label, action, `${action}-${step}`, "", unavailable);
        button.dataset.step = String(step);
        nav.append(button);
      }
      footer.append(nav);
    }
    return footer;
  }

  _renderOutages(parent) {
    parent.append(node("p", "Lịch ngừng điện dự kiến, không phải trạng thái điện lưới theo thời gian thực. Thời gian hiển thị theo giờ Việt Nam (UTC+7).", "muted"));
    if (!this._overview) { parent.append(node("p", this._overviewBusy ? "Đang tải lịch ngừng điện…" : "Chưa có dữ liệu lịch ngừng điện.", this._overviewBusy ? "loading" : "empty")); return; }
    const outages = array(this._overview.outages);
    if (!outages.length) { parent.append(node("p", "Chưa có lịch ngừng điện dự kiến cho khách hàng này.", "empty")); return; }
    const card = node("section", null, "card");
    card.append(node("h2", "Kế hoạch ngừng cấp điện"));
    const list = node("ul", null, "outages notice");
    for (const outage of outages) {
      const item = node("li");
      const dates = node("dl", null, "outage-time stat-list");
      for (const [label, value] of [["Bắt đầu", outage.start], ["Kết thúc dự kiến", outage.end]]) {
        const row = node("div"); row.append(node("dt", label), node("dd", time(value))); dates.append(row);
      }
      item.append(dates, node("h3", text(outage.area)), node("p", text(outage.reason), "muted"));
      list.append(item);
    }
    card.append(list);
    parent.append(card);
  }

  _openInvoice(index) {
    const invoice = this._details?.invoices[index];
    if (!invoice || !this._admin()) return;
    this._cancelPdf();
    this._invoice = invoice;
    this._invoiceFocus = this.shadowRoot.activeElement?.id || `invoice-${index}`;
    this._pdfMessage = "";
    const header = node("header", null, "dialog-head");
    const title = node("h2", `Hóa đơn ${text(invoice.period)}`);
    title.id = "invoice-title";
    header.append(title, this._iconButton("Đóng chi tiết hóa đơn", "close-invoice", "invoice-close", "m6 6 12 12M6 18 18 6"));
    const body = node("div", null, "dialog-body");
    body.append(node("p", money(invoice.amount), "invoice-total"), this._badge(invoice));
    const details = node("dl", null, "dialog-info");
    const unit = ["kWh", "kVArh"].includes(invoice.energy_unit) ? invoice.energy_unit : "";
    for (const [label, value] of [
      ["Kỳ hóa đơn", text(invoice.period)], ["Kỳ thu", text(invoice.cycle)], ["Thuế", money(invoice.tax)],
      ["Điện năng", finite(invoice.energy) ? `${numeric(invoice.energy)} ${unit}`.trim() : "Chưa có dữ liệu"],
      ["Còn phải trả", money(invoice.outstanding)], ["Hạn thanh toán", text(invoice.due_date)], ["Đã thanh toán ngày", text(invoice.paid_date)]
    ]) { const row = node("div"); row.append(node("dt", label), node("dd", value)); details.append(row); }
    body.append(details);
    const actions = node("div", null, "pdf-actions");
    for (const [kind, label] of Object.entries(DOCUMENTS)) {
      if (!array(invoice.documents).includes(kind)) continue;
      const button = this._button(label, "pdf", `pdf-${kind}`, kind === "invoice" ? "primary" : "");
      button.dataset.kind = kind;
      actions.append(button);
    }
    if (!actions.childElementCount) body.append(node("p", "Chưa có tài liệu PDF cho hóa đơn này.", "muted"));
    const status = node("p", "", "pdf-status");
    status.id = "pdf-status";
    status.setAttribute("role", "status");
    const retry = this._button("Thử tải lại PDF", "pdf", "pdf-retry");
    retry.hidden = true;
    body.append(actions, status, retry);
    this._dialog.replaceChildren(header, body);
    this._dialog.showModal();
    this.shadowRoot.getElementById("invoice-close").focus();
  }

  _closeInvoice() {
    const focus = this._invoiceFocus;
    this._cancelPdf();
    this.shadowRoot.getElementById(focus)?.focus({ preventScroll: true });
  }

  _cancelPdf() {
    this._pdfRequest++;
    this._pdfAbort?.abort();
    this._pdfBusy = false;
    this._invoice = null;
    this._invoiceFocus = null;
    if (this._dialog?.open) this._dialog.close();
    this._dialog?.replaceChildren();
    for (const [url, timer] of this._urls || []) { clearTimeout(timer); URL.revokeObjectURL(url); }
    this._urls?.clear();
  }

  _pdfStatus(message, error, kind) {
    const status = this.shadowRoot.getElementById("pdf-status");
    if (!status) return;
    status.textContent = message;
    status.setAttribute("role", error ? "alert" : "status");
    const retry = this.shadowRoot.getElementById("pdf-retry");
    retry.hidden = !error;
    retry.dataset.kind = kind;
    for (const button of this._dialog.querySelectorAll('[data-action="pdf"]')) {
      button.setAttribute("aria-disabled", String(this._pdfBusy || this._cooling()));
      button.setAttribute("aria-busy", String(this._pdfBusy && button.dataset.kind === kind));
    }
  }

  async _download(kind) {
    const invoice = this._invoice;
    if (!this._admin() || !invoice || this._pdfBusy || this._cooling() || !Object.hasOwn(DOCUMENTS, kind) || !array(invoice.documents).includes(kind)) return;
    if (typeof this._hass.fetchWithAuth !== "function") {
      this._pdfStatus("Phiên Home Assistant này không hỗ trợ tải tệp xác thực (fetchWithAuth). Hãy cập nhật giao diện Home Assistant rồi mở lại bảng điều khiển.", true, kind);
      return;
    }
    const generation = this._generation;
    const request = ++this._pdfRequest;
    const current = () => this._current(generation) && request === this._pdfRequest && this._invoice === invoice && this._dialog.open;
    this._pdfAbort = new AbortController();
    this._pdfBusy = true;
    this._pdfStatus("Đang tải PDF…", false, kind);
    try {
      const path = `/api/evn_cskh/invoice/${encodeURIComponent(this._choice.entry.entry_id)}/${encodeURIComponent(invoice.key)}/${kind}`;
      const response = await this._hass.fetchWithAuth(path, { method: "GET", signal: this._pdfAbort.signal });
      if (!current()) return;
      if (!response.ok) throw { code: response.status };
      if ((response.headers.get("content-type") || "").split(";")[0].trim().toLowerCase() !== "application/pdf") throw { pdf: "Máy chủ không trả về tệp PDF hợp lệ." };
      if (Number(response.headers.get("content-length")) > MAX_PDF) throw { pdf: "Tệp PDF vượt giới hạn 16 MB." };
      const reader = response.body?.getReader();
      let blob;
      if (reader) {
        let size = 0;
        const chunks = [];
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (!current()) { await reader.cancel(); return; }
            if (done) break;
            size += value.byteLength;
            if (size > MAX_PDF) { await reader.cancel(); throw { pdf: "Tệp PDF vượt giới hạn 16 MB." }; }
            chunks.push(value);
          }
          blob = new Blob(chunks, { type: "application/pdf" });
        } finally { reader.releaseLock(); }
      } else blob = await response.blob();
      if (!current()) return;
      if (blob.size > MAX_PDF) throw { pdf: "Tệp PDF vượt giới hạn 16 MB." };
      const signature = new Uint8Array(await blob.slice(0, 5).arrayBuffer());
      if (signature.length !== 5 || ![37, 80, 68, 70, 45].every((byte, index) => signature[index] === byte)) throw { pdf: "Nội dung tệp không có chữ ký PDF hợp lệ." };
      if (!current()) return;
      const url = URL.createObjectURL(blob);
      const period = /^\d{2}\/\d{4}$/.test(invoice.period) ? invoice.period.replace("/", "-") : "tai-lieu";
      const anchor = node("a");
      anchor.href = url;
      anchor.download = `evn-${kind}-${period}.pdf`;
      this.shadowRoot.append(anchor);
      anchor.click();
      anchor.remove();
      this._urls.set(url, setTimeout(() => { URL.revokeObjectURL(url); this._urls.delete(url); }, 1500));
      this._pdfBusy = false;
      this._pdfStatus("Đã gửi tệp PDF đến trình tải xuống của trình duyệt.", false, kind);
    } catch (error) {
      if (!current()) return;
      this._pdfBusy = false;
      const message = error?.pdf || this._error(error);
      if (this._authError) this._render();
      else this._pdfStatus(message, true, kind);
    }
  }
}

if (!customElements.get("evn-cskh-panel")) customElements.define("evn-cskh-panel", EvnCskhPanel);
