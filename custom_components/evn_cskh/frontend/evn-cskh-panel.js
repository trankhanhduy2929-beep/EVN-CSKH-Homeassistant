const STYLE = `
:host{display:block;min-width:0;color:var(--primary-text-color,#212121);background:var(--primary-background-color,#f4f5f7);font-family:var(--primary-font-family,inherit);font-size:14px;line-height:1.5;color-scheme:light;--evn-surface:var(--card-background-color,#fff);--evn-line:var(--divider-color,#dce0e4);--evn-muted:var(--secondary-text-color,#61666d);--evn-accent:var(--primary-color,#0b74b8);--evn-chart-1:#0b74b8;--evn-chart-2:#12a19a;--evn-chart-3:#f4a300;--evn-chart-4:#7c5cff;--evn-track-h:164px;--evn-error:var(--error-color,#db4437);--evn-success:var(--success-color,#168039);--evn-warning:var(--warning-color,#9b6511);--evn-hover:color-mix(in srgb,var(--primary-text-color,#212121) 6%,var(--evn-surface))}
:host([dark]){color-scheme:dark;--evn-chart-1:#4aa3dd;--evn-chart-2:#3cc7bf;--evn-chart-3:#f6b733;--evn-chart-4:#a08cff}*{box-sizing:border-box;min-width:0}h1,h2,h3,p,dl,dd,figure,ul{margin:0}ul{padding:0;list-style:none}h1{font-size:20px;font-weight:600}h2{font-size:18px;font-weight:600}h3{font-size:16px;font-weight:600}p,dd,h2,h3{overflow-wrap:anywhere}button,input,select{font:inherit;color:inherit;max-width:100%}button,input,select{border:1px solid var(--evn-line);border-radius:12px;background:var(--evn-surface);min-height:40px;padding:8px 12px}button{cursor:pointer;font-weight:500;line-height:1.4}button:hover:not(:disabled):not([aria-disabled=true]){background:var(--evn-hover)}button:disabled,button[aria-disabled=true]{cursor:not-allowed;opacity:.6}button[aria-busy=true]{cursor:progress;opacity:1}button.primary{background:var(--evn-accent);border-color:transparent;color:var(--text-primary-color,#fff)}button.primary:hover:not([aria-disabled=true]){background:color-mix(in srgb,var(--evn-accent) 85%,var(--primary-text-color,#212121))}button.quiet{background:transparent;border-color:transparent}button.link{border-color:transparent;color:var(--evn-accent);background:transparent;text-align:left}button.link:hover{text-decoration:underline}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--evn-accent);outline-offset:3px}input,select{width:100%;height:40px}input[aria-invalid=true]{border-color:var(--evn-error)}label{display:block;width:fit-content;font-size:12px;font-weight:500;color:var(--evn-muted);margin-bottom:6px}svg{display:block;width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8}button.icon{display:inline-flex;align-items:center;justify-content:center;width:40px;padding:8px;flex:none;color:var(--evn-muted)}.topbar{background:var(--evn-surface);border-bottom:1px solid var(--evn-line)}.top-inner{max-width:1328px;margin:auto;padding:16px 24px;display:flex;align-items:center;gap:24px}.brand{display:flex;align-items:center;gap:12px;flex:1}.account-tools{display:flex;align-items:end;gap:12px}.account-field{width:320px}.account-tools>button{min-width:106px}#menu{display:none}:host([narrow]) #menu{display:inline-flex}.shell{max-width:1328px;margin:auto;padding:24px;display:grid;gap:20px}.intro{display:flex;align-items:start;justify-content:space-between;gap:16px}.intro h2{font-size:20px}.intro p{margin-top:4px}.muted,.meta{color:var(--evn-muted)}.meta{font-size:12px}.freshness{text-align:right;max-width:300px}.tabs{display:flex;gap:24px;border-bottom:1px solid var(--evn-line);padding:4px 4px 0}.tabs button{border:0;border-bottom:2px solid transparent;border-radius:0;background:transparent;min-height:48px;padding:10px 4px;color:var(--evn-muted);white-space:nowrap;flex:none}.tabs button[aria-selected=true]{border-bottom-color:var(--evn-accent);color:var(--evn-accent);font-weight:600}.stack{display:grid;gap:16px}.card{background:var(--evn-surface);border:1px solid var(--evn-line);border-radius:14px;padding:20px;animation:evn-fade .28s ease-out both}.card-head{display:flex;align-items:start;justify-content:space-between;gap:16px;margin-bottom:16px}.card-head p{margin-top:4px}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.metric{min-height:134px;display:flex;flex-direction:column;gap:8px}.metric-label{color:var(--evn-muted);font-size:13px}.metric-value{font-size:24px;line-height:1.3;font-weight:600;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.metric-value.compact{font-size:18px}.metric .meta{margin-top:auto}.overview-grid{display:grid;grid-template-columns:minmax(0,2.2fr) minmax(0,1fr);gap:16px;align-items:start}.chart-card{min-height:340px}
.chart{display:grid;gap:6px;margin-top:32px;position:relative}.chart-column{text-align:center;min-width:0}.track{height:var(--evn-track-h,164px);position:relative;margin:0 auto;max-width:32px}.bar{position:absolute;inset-inline:0;background:var(--evn-chart-1);border-radius:6px 6px 0 0;transform-origin:bottom;animation:evn-bar .36s ease-out both}.bar.current{opacity:.65}.bar-number{position:absolute;width:100%;font-size:12px;color:var(--evn-muted);line-height:20px;white-space:nowrap;display:flex;justify-content:center}.chart.daily .bar-number{display:none}.chart-label{font-size:12px;color:var(--evn-muted);padding-top:12px;margin-top:4px;border-top:1px solid var(--evn-line);white-space:nowrap}.smooth-chart{column-gap:0}.smooth-chart .bar{display:none}.history-overlay{position:absolute;left:0;right:0;top:0;height:var(--evn-track-h,164px);width:100%;pointer-events:none;overflow:visible}.history-line{fill:none;stroke:var(--evn-chart-1);stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round;stroke-dasharray:1400;animation:evn-draw .6s ease-out both}.history-area{stroke:none}.history-grid{stroke:var(--evn-line);stroke-opacity:.7;stroke-width:1}.history-dot{position:absolute;left:50%;width:12px;height:12px;margin:-6px 0 0 -6px;border-radius:50%;background:var(--evn-surface);border:2px solid var(--evn-chart-1);pointer-events:auto}.history-dot:hover,.history-dot:focus{background:var(--evn-chart-1)}.stat-list{display:grid;gap:12px}.stat-list>div{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);gap:12px}.stat-list dt{color:var(--evn-muted);font-size:13px}.stat-list dd{font-weight:500;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.notice{border-top:1px solid var(--evn-line);padding-top:16px;margin-top:16px}.notice p{margin-top:8px}.notice button{margin-top:8px}.empty{padding:28px 0;color:var(--evn-muted);text-align:center;overflow-wrap:anywhere}.placeholder{min-height:220px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;text-align:center}.loading{color:var(--evn-muted);display:flex;align-items:center;gap:10px}.loading::before{content:"";flex:none;width:10px;height:10px;border-radius:50%;background:var(--evn-chart-1);opacity:.85}.loading::after{content:"";height:8px;flex:1;max-width:220px;border-radius:999px;background:linear-gradient(90deg,var(--evn-hover),color-mix(in srgb,var(--evn-chart-1) 22%,var(--evn-surface)),var(--evn-hover));background-size:200% 100%;animation:evn-shimmer 1.4s ease-out 1}.banner{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px;background:var(--evn-surface);border:1px solid var(--evn-line);border-radius:12px}.banner.error{border-inline-start:3px solid var(--evn-error)}.banner.warn{border-inline-start:3px solid var(--evn-warning)}.banner.ok{border-inline-start:3px solid var(--evn-success)}.banner p{max-width:75ch}.banner button{flex:none}.filters{display:grid;grid-template-columns:minmax(160px,2fr) repeat(2,minmax(140px,1fr)) auto;align-items:end;gap:12px}.filter-help{grid-column:1/-1}.filter-error{color:var(--evn-error);grid-column:1/-1}.section-tools{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}.segmented{display:inline-flex;gap:4px;padding:4px;border:1px solid var(--evn-line);border-radius:12px;background:var(--evn-surface)}.segmented button{border-color:transparent;min-height:32px;border-radius:8px;padding:6px 12px}.segmented button[aria-pressed=true]{background:var(--evn-hover);color:var(--evn-accent)}.table-wrap{width:100%;overflow:auto;border:1px solid var(--evn-line);border-radius:12px;background:var(--evn-surface);scrollbar-width:thin}.table-wrap:focus-visible{outline-offset:2px}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:14px;text-align:left}caption{text-align:left;padding:12px 16px;font-weight:500;color:var(--evn-muted);font-size:12px}th,td{padding:12px 16px;border-top:1px solid var(--evn-line);vertical-align:middle;overflow-wrap:anywhere}thead th{color:var(--evn-muted);font-weight:500;font-size:12px;background:var(--evn-surface);white-space:nowrap}td.number,th.number{text-align:right;white-space:nowrap}td.nowrap,th.nowrap{white-space:nowrap}.scroll-table{min-width:680px}.scroll-table tbody th{position:sticky;left:0;background:var(--evn-surface);font-weight:500;max-width:150px}.invoice-table{min-width:620px}.invoice-table tbody tr{cursor:pointer}.invoice-table tbody tr:hover{background:var(--evn-hover)}.invoice-table td:first-child{font-weight:500}.invoice-table button{padding-left:0;padding-right:0}.badge{display:inline-flex;border-radius:8px;padding:4px 8px;font-size:12px;font-weight:500;background:var(--evn-hover);color:var(--evn-muted);white-space:nowrap}.badge.paid{color:var(--evn-success);background:color-mix(in srgb,var(--evn-success) 10%,var(--evn-surface))}.badge.unpaid{color:var(--evn-warning);background:color-mix(in srgb,var(--evn-warning) 10%,var(--evn-surface))}.invoice-filters{display:grid;grid-template-columns:minmax(0,1fr) 200px;gap:12px}.pagination{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:16px}.pagination nav{display:flex;gap:8px;align-items:center}.pagination p{font-size:13px;color:var(--evn-muted)}.invoice-cards{display:none}.invoice-card{border-top:1px solid var(--evn-line);padding:16px 0;display:grid;gap:12px}.invoice-card:first-child{border-top:0;padding-top:0}.invoice-card .row{display:flex;align-items:center;justify-content:space-between;gap:12px}.invoice-card strong{font-size:18px;font-weight:600}.invoice-card button{padding:4px 0}.point-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}.point-card{border:1px solid var(--evn-line);border-radius:12px;padding:16px;display:grid;gap:12px;background:var(--evn-surface)}.point-card p{margin-top:4px}.outages li{padding:20px 0;border-top:1px solid var(--evn-line)}.outages li:first-child{padding-top:0;border-top:0}.outage-time{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}.outages p{margin-top:8px;white-space:pre-wrap;max-width:80ch}.outages h3{margin-bottom:12px}.lock{padding:32px 0;max-width:640px}.lock h2{margin-bottom:12px}dialog{color:inherit;background:var(--evn-surface);border:1px solid var(--evn-line);border-radius:12px;width:560px;max-width:calc(100vw - 32px);max-height:calc(100dvh - 32px);padding:0;overflow:auto}dialog::backdrop{background:rgba(0,0,0,.42)}.dialog-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px;border-bottom:1px solid var(--evn-line)}.dialog-body{padding:20px;display:grid;gap:20px}.invoice-total{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums}.dialog-info{display:grid;gap:12px}.dialog-info>div{display:grid;grid-template-columns:minmax(100px,1fr) minmax(0,1.3fr);gap:16px}.dialog-info dt{color:var(--evn-muted)}.dialog-info dd{font-variant-numeric:tabular-nums}.pdf-actions{display:flex;gap:8px;flex-wrap:wrap}.pdf-status{min-height:24px}.pdf-status[role=alert]{color:var(--evn-error)}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.chart-footer{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:16px;flex-wrap:wrap}[hidden]{display:none!important}@keyframes evn-fade{from{opacity:0}to{opacity:1}}@keyframes evn-bar{from{transform:scaleY(.02)}to{transform:scaleY(1)}}@keyframes evn-bar-x{from{transform:translateX(-50%) scaleY(.02)}to{transform:translateX(-50%) scaleY(1)}}@keyframes evn-draw{from{stroke-dashoffset:1400}to{stroke-dashoffset:0}}@keyframes evn-shimmer{from{background-position:200% 0}to{background-position:-200% 0}}
.comparison-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.comparison-card{display:flex;flex-direction:column;gap:12px}.comparison-card h2{font-size:16px}.comparison-card .chart{margin:8px 0 0;gap:12px;align-items:start}.comparison-chart .track{position:relative;height:132px;max-width:none;margin:0 0 12px}.comparison-chart .bar{max-width:32px;min-height:0;left:50%;width:40%;transform:translateX(-50%);transform-origin:bottom;animation:evn-bar-x .36s ease-out both}.comparison-chart .bar.negative{transform-origin:top}.comparison-chart .bar.current{opacity:1;background:color-mix(in srgb,var(--evn-accent) 35%,var(--evn-surface))}.bar.negative{border-radius:0 0 6px 6px}.zero-axis{position:absolute;left:0;right:0;border-top:1px solid var(--evn-line)}.chart-column{position:relative}.comparison-chart .chart-label{font-size:12px;overflow-wrap:anywhere;white-space:normal;text-align:center;border-top:0;padding-top:0;margin-top:0}.slot-value{display:block;text-align:center;font-size:14px;font-weight:600;font-variant-numeric:tabular-nums;overflow-wrap:anywhere;margin-top:4px}.slot-date,.slot-state{display:block;color:var(--evn-muted);font-size:12px;text-align:center;overflow-wrap:anywhere;margin-top:4px}.comparison-values table{table-layout:fixed;width:100%;min-width:0}.comparison-values th,.comparison-values td{white-space:normal;overflow-wrap:anywhere}.comparison-values th:first-child{width:32%}.comparison-values td{font-variant-numeric:tabular-nums}.comparison-values .slot-state{text-align:left}.index-card{display:flex;flex-direction:column;gap:16px}.index-card svg.index-chart{width:100%;height:auto;max-height:300px;stroke:none;overflow:visible}.index-chart .index-grid{stroke:var(--evn-line);stroke-width:1;vector-effect:non-scaling-stroke}.index-chart .index-line{display:none}.index-chart .index-curve{stroke:var(--evn-chart-1);stroke-width:2;fill:none;vector-effect:non-scaling-stroke;stroke-linejoin:round;stroke-linecap:round;stroke-dasharray:2400;animation:evn-draw .6s ease-out both}.index-chart .index-area{stroke:none}.index-chart .index-point{fill:var(--evn-surface);stroke:var(--evn-chart-1);stroke-width:2;vector-effect:non-scaling-stroke;cursor:pointer}.index-chart .index-point:hover,.index-chart .index-point:focus{fill:var(--evn-accent)}.index-chart text{fill:var(--evn-muted);stroke:none;font-size:12px;font-variant-numeric:tabular-nums}.index-tooltip{min-height:42px;font-variant-numeric:tabular-nums}.index-values{max-height:220px;overflow:auto}.index-values table{min-width:0;width:100%}.index-values th,.index-values td{white-space:normal;overflow-wrap:anywhere}.index-values td{font-variant-numeric:tabular-nums}.index-empty{padding:24px 0}.index-series-field{max-width:100%}
@media(max-width:1100px){.overview-grid{grid-template-columns:1fr}}
@media(max-width:767px){.comparison-grid{grid-template-columns:1fr;gap:16px}.comparison-card .chart{gap:8px}.index-card svg.index-chart{min-height:180px}}
@media(max-width:1000px){.metrics{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.freshness{max-width:220px}}
@media(max-width:767px){.top-inner{padding:12px 16px;gap:12px;flex-wrap:wrap}.brand{width:100%}#menu{display:inline-flex}.account-tools{width:100%;gap:8px}.account-field{flex:1;width:auto}.shell{padding:16px;gap:16px}.intro{display:block;margin-bottom:4px}.freshness{text-align:left;max-width:none;margin-top:12px}.tabs{gap:16px;justify-content:flex-start;overflow-x:auto;scrollbar-color:transparent transparent}.tabs button{font-size:13px}.card{padding:16px}.metric{min-height:126px}.metric-value{font-size:20px}.metric-value.compact{font-size:16px}.metric-label{font-size:12px}.metrics>.metric:last-child{grid-column:1/-1}.card-head{gap:12px}.filters{gap:12px}.filters>.point-field{grid-column:1/-1}.filters>button{grid-column:1/-1}input,select{font-size:16px;height:44px}.filters button,.account-tools>button{min-height:44px}.segmented button{min-height:36px}.bar-number{display:none}.chart-label{font-size:12px}:host{--evn-track-h:148px}.track{height:var(--evn-track-h,148px)}.chart-card{min-height:320px}.invoice-filters{grid-template-columns:1fr}.invoice-table-wrap{display:none}.invoice-cards{display:block}.banner{align-items:start;flex-direction:column}.pagination{align-items:start;flex-direction:column}.pagination nav{width:100%;justify-content:space-between}.outage-time{grid-template-columns:1fr;gap:12px}.dialog-head,.dialog-body{padding:16px}.pdf-actions{display:grid;grid-template-columns:1fr;width:100%}.dialog-info>div,.stat-list>div{grid-template-columns:1fr 1.2fr;gap:12px}.point-grid{grid-template-columns:1fr}.intro h2{font-size:18px}}
@media(prefers-reduced-motion:reduce){*,*::before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
`;

const TABS = ["Tổng quan", "Điện năng", "Công tơ", "Hóa đơn", "Lịch ngừng điện", "Thông tin"];
const DETAIL_TABS = [1, 2, 3];
const DOCUMENTS = { invoice: "Tải hóa đơn PDF", statement: "Tải bảng kê PDF", notice: "Tải thông báo PDF" };
const KINDS = { monthly: "Tháng", daily: "Ngày" };
const MAX_PDF = 16 * 1024 * 1024;
const numberFormat = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 3 });
const percentFormat = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 });
const moneyFormat = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 });
const timeFormat = new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", dateStyle: "short", timeStyle: "short" });
const finite = value => typeof value === "number" && Number.isFinite(value);
const numeric = value => finite(value) ? numberFormat.format(value) : "Chưa có dữ liệu";
const money = value => finite(value) ? moneyFormat.format(value) : "Chưa xác định";
const text = value => value == null || value === "" ? "Chưa có thông tin" : String(value);
const array = value => Array.isArray(value) ? value : [];
const signed = value => finite(value) ? `${value > 0 ? "+" : value < 0 ? "−" : ""}${percentFormat.format(Math.abs(value))}%` : "";
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
const displayDate = value => validDate(value) ? `${value.slice(8, 10)}/${value.slice(5, 7)}/${value.slice(0, 4)}` : "Chưa có ngày";
const dailyEnd = period => {
  if (validDate(period)) return period;
  if (typeof period !== "string") return null;
  const match = /^(\d{2})\/(\d{2})\/(\d{4})(?:\s*-\s*(\d{2})\/(\d{2})\/(\d{4}))?$/.exec(period.trim());
  if (!match) return null;
  const start = `${match[3]}-${match[2]}-${match[1]}`;
  const end = match[4] ? `${match[6]}-${match[5]}-${match[4]}` : start;
  return validDate(start) && validDate(end) && start <= end ? end : null;
};
const dailyRecords = records => [...array(records)].sort((a, b) => (dailyEnd(a?.period) || "9999").localeCompare(dailyEnd(b?.period) || "9999"));
const readingLabel = row => readingMoment(row)?.label || "Chưa có ngày ghi thực tế";
const comparisonSlots = (comparisons, pointId, field) => {
  if (!validDate(comparisons?.as_of)) return null;
  const day = new Date(`${comparisons.as_of}T00:00:00Z`);
  const periods = [2, 1, 0].map(offset => {
    const date = new Date(day);
    if (field === "daily") date.setUTCDate(date.getUTCDate() - offset);
    else { date.setUTCDate(1); date.setUTCMonth(date.getUTCMonth() - offset); }
    return date.toISOString().slice(0, field === "daily" ? 10 : 7);
  });
  const source = field === "daily" ? array(comparisons.points).find(item => item?.point_id === pointId)?.daily : comparisons.monthly;
  return periods.map((period, index) => {
    const item = array(source).find(row => row?.period === period);
    return {
      period,
      kwh: finite(item?.kwh) ? item.kwh : null,
      vnd: finite(item?.vnd) ? item.vnd : null,
      provisional: item?.provisional === true,
      label: field === "daily" ? ["Hôm kia", "Hôm qua", "Hôm nay"][index] : `${period.slice(5, 7)}/${period.slice(0, 4)}`
    };
  });
};
const columnScale = values => {
  const known = values.filter(finite);
  const magnitude = Math.max(1, ...known.map(value => Math.abs(value)));
  const low = Math.min(0, ...known.map(value => value / magnitude));
  const high = Math.max(0, ...known.map(value => value / magnitude));
  const span = high - low || 1;
  return {
    low: Math.min(0, ...known),
    high: Math.max(0, ...known),
    zero: -low / span * 100,
    height: value => Math.abs(value / magnitude) / span * 100,
    bottom: value => (Math.min(0, value / magnitude) - low) / span * 100,
    top: value => (Math.max(0, value / magnitude) - low) / span * 100
  };
};
const smoothPath = points => {
  if (points.length === 1) return `M${points[0].x.toFixed(3)},${points[0].y.toFixed(3)}`;
  const dx = [];
  const slope = [];
  for (let index = 0; index < points.length - 1; index++) {
    const step = points[index + 1].x - points[index].x || 0.001;
    dx.push(step);
    slope.push((points[index + 1].y - points[index].y) / step);
  }
  const tangent = new Array(points.length);
  tangent[0] = slope[0];
  tangent[points.length - 1] = slope.at(-1);
  for (let index = 1; index < points.length - 1; index++) {
    if (slope[index - 1] * slope[index] <= 0) tangent[index] = 0;
    else {
      const weight1 = 2 * dx[index] + dx[index - 1];
      const weight2 = dx[index] + 2 * dx[index - 1];
      tangent[index] = (weight1 + weight2) / (weight1 / slope[index - 1] + weight2 / slope[index]);
    }
  }
  let path = `M${points[0].x.toFixed(3)},${points[0].y.toFixed(3)}`;
  for (let index = 0; index < points.length - 1; index++) {
    const step = dx[index];
    const control1 = `${(points[index].x + step / 3).toFixed(3)},${(points[index].y + tangent[index] * step / 3).toFixed(3)}`;
    const control2 = `${(points[index + 1].x - step / 3).toFixed(3)},${(points[index + 1].y - tangent[index + 1] * step / 3).toFixed(3)}`;
    path += ` C${control1} ${control2} ${points[index + 1].x.toFixed(3)},${points[index + 1].y.toFixed(3)}`;
  }
  return path;
};
const readingMoment = row => {
  if (row?.resolution === "time" && typeof row.timestamp === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+07:00$/.test(row.timestamp) && validDate(row.timestamp.slice(0, 10))) {
    const stamp = Date.parse(row.timestamp);
    if (Number.isFinite(stamp) && new Date(stamp + 7 * 3600000).toISOString().slice(0, 19) === row.timestamp.slice(0, 19)) return { stamp, day: row.timestamp.slice(0, 10), label: `${row.timestamp} · ${time(row.timestamp)} · Giờ Việt Nam`, resolution: "time" };
  }
  if (row?.resolution === "day" && validDate(row.reading_date)) return { stamp: Date.parse(`${row.reading_date}T00:00:00+07:00`), day: row.reading_date, label: `${displayDate(row.reading_date)} · chỉ biết ngày`, resolution: "day" };
  return null;
};
const monthOrdinal = period => {
  if (typeof period !== "string") return null;
  const match = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(period);
  return match && Number(match[1]) > 0 ? Number(match[1]) * 12 + Number(match[2]) - 1 : null;
};
const readingIdentity = row => typeof row?.meter === "string" && row.meter.trim() && typeof row.register === "string" && row.register.trim() && Object.hasOwn(KINDS, row.kind);
const readingSeries = readings => {
  const source = array(readings).slice(0, 1000);
  const uncertain = source.filter(row => !readingIdentity(row));
  const groups = new Map();
  for (const row of source) {
    if (!row || typeof row !== "object") continue;
    const key = JSON.stringify([row.meter ?? null, row.register ?? null, row.kind ?? null]);
    if (!groups.has(key)) groups.set(key, { key, meter: row.meter, register: row.register, kind: row.kind, rows: [] });
    groups.get(key).rows.push(row);
  }
  return [...groups.values()].map(group => {
    const seen = new Set();
    const buckets = new Map();
    const unknown = [];
    for (const row of group.rows) {
      const signature = JSON.stringify([row.period, row.timestamp, row.reading_date, row.resolution, row.old, row.new, row.multiplier, row.kwh]);
      if (seen.has(signature)) continue;
      seen.add(signature);
      const moment = readingMoment(row);
      if (!moment) { unknown.push({ value: finite(row.new) ? row.new : null, label: "Chưa có ngày ghi thực tế", stamp: null }); continue; }
      const key = `${moment.resolution}:${moment.stamp}`;
      const bucket = buckets.get(key);
      const value = finite(row.new) ? row.new : null;
      const monthlyPeriod = group.kind === "monthly" && monthOrdinal(row.period) !== null ? row.period : null;
      if (bucket) {
        if (bucket.value !== value) { bucket.value = null; bucket.conflict = true; }
        if (bucket.monthlyPeriod !== monthlyPeriod) bucket.monthlyPeriod = null;
      } else buckets.set(key, { ...moment, value, monthlyPeriod, conflict: false });
    }
    const points = [...buckets.values()].sort((a, b) => a.stamp - b.stamp);
    const ambiguousDays = new Set(points.filter(point => point.resolution === "day" && points.some(other => other.day === point.day && other.resolution === "time")).map(point => point.day));
    const identity = readingIdentity(group);
    const blocked = !identity || unknown.length > 0 || uncertain.some(row => !row || !Object.hasOwn(KINDS, row.kind) || row.kind === group.kind);
    const segments = [];
    let segment = [];
    let previous = null;
    const flush = () => { if (segment.length > 1) segments.push(segment); segment = []; };
    for (const point of points) {
      const missingDay = previous && group.kind === "daily" && Date.parse(point.day) - Date.parse(previous.day) > 86400000;
      const previousMonth = monthOrdinal(previous?.monthlyPeriod);
      const currentMonth = monthOrdinal(point.monthlyPeriod);
      const missingMonth = previous && group.kind === "monthly" && (previousMonth === null || currentMonth === null || currentMonth - previousMonth < 0 || currentMonth - previousMonth > 1);
      if (missingDay || missingMonth || (previous && previous.resolution !== point.resolution)) flush();
      if (!finite(point.value) || ambiguousDays.has(point.day)) flush();
      else segment.push(point);
      previous = point;
    }
    flush();
    return { ...group, points, unknown, segments: blocked ? [] : segments, blocked, label: `Công tơ ${text(group.meter)} · ${text(group.register)} · ${KINDS[group.kind] || "Chưa rõ loại"} · Chỉ số gốc` };
  });
};
const svgNode = (tag, attributes = {}, content) => {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  if (content != null) element.textContent = String(content);
  return element;
};
const paymentState = invoice => {
  if (invoice?.status === "DATT") return "paid";
  if (invoice?.status === "CHUATT") return "unpaid";
  if (invoice?.status === "TTOANMOTPHAN") return String(invoice.status_label || "").trim().toLocaleLowerCase("vi") === "đã hoàn trả một phần" ? "unknown" : "unpaid";
  return "unknown";
};
const payableAmount = invoice => {
  if (invoice && Object.hasOwn(invoice, "payable_amount")) return finite(invoice.payable_amount) && invoice.payable_amount >= 0 ? invoice.payable_amount : null;
  const state = paymentState(invoice);
  if (state === "paid") return 0;
  return state === "unpaid" && finite(invoice?.outstanding) ? Math.abs(invoice.outstanding) : null;
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
    this._detailsCache = new Map();
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
    for (const type of ["click", "change", "input", "submit", "keydown", "focusin", "pointerover"]) {
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
    this._detailsCache.clear();
    this._overviewBusy = this._detailsBusy = this._listBusy = false;
    this._overviewError = this._detailsError = this._listError = "";
    this._authError = "";
    this._rangeError = "";
    this._tab = 0;
    this._period = "monthly";
    this._readingSeries = "";
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
    if (["404", "410", "not_found", "stale"].includes(code)) return "Dữ liệu EVN đã hết hạn hoặc không còn tồn tại. Hãy tải lại dữ liệu và thử lại.";
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
    this._readingSeries = "";
    this._range = defaultRange();
    this._overview = null;
    this._details = null;
    this._overviewBusy = this._detailsBusy = false;
    this._overviewError = this._detailsError = this._rangeError = "";
    this._query = "";
    this._paid = "all";
    this._invoicePage = this._readingPage = 0;
    this._render();
    void this._loadOverview();
    if (DETAIL_TABS.includes(this._tab)) void this._loadDetails();
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

  _detailKey() { return `${this._choice?.entry.entry_id || ""}|${this._choice?.customer.key || ""}|${this._point}|${this._range.start}|${this._range.end}`; }

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
    if (DETAIL_TABS.includes(this._tab)) void this._loadDetails();
  }

  async _loadDetails(force = false) {
    if (!this._admin() || !this._choice || !this._point || this._detailsBusy || this._cooling()) return;
    this._rangeError = this._validateRange();
    if (this._rangeError) { this._render(); return; }
    const key = this._detailKey();
    const cached = this._detailsCache.get(key);
    if (cached && !force) {
      this._details = cached;
      this._render();
      return;
    }
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
      this._detailsCache.set(key, response);
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
    if (DETAIL_TABS.includes(tab)) void this._loadDetails();
  }

  _event(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (event.type === "focusin" || event.type === "pointerover") {
      if (target.matches(".index-point")) {
        const tooltip = this.shadowRoot.getElementById("meter-index-tooltip");
        if (tooltip) tooltip.textContent = target.getAttribute("aria-label");
      }
      return;
    }
    if (event.type === "keydown" && target.matches(".index-point")) {
      const points = [...target.closest("svg").querySelectorAll(".index-point")];
      const index = points.indexOf(target);
      const next = { ArrowRight: Math.min(index + 1, points.length - 1), ArrowLeft: Math.max(0, index - 1), Home: 0, End: points.length - 1 }[event.key];
      if (next !== undefined) { event.preventDefault(); points[next]?.focus(); }
      return;
    }
    if (event.type === "keydown" && target.getAttribute("role") === "tab") {
      const index = Number(target.dataset.tab);
      const size = TABS.length;
      const next = { ArrowRight: (index + 1) % size, ArrowLeft: (index + size - 1) % size, Home: 0, End: size - 1 }[event.key];
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
      if (target.id === "point-select") { this._point = target.value; this._readingSeries = ""; this._invalidateDetails(); }
      if (target.id === "meter-series-select") { this._readingSeries = target.value; this._render(); }
      if (target.id === "date-from" || target.id === "date-to") this._invalidateDetails();
      if (target.id === "paid-select") { this._paid = target.value; this._invoicePage = 0; this._render(); }
      return;
    }
    if (event.type === "submit") {
      event.preventDefault();
      if (target.id === "history-filter") void this._loadDetails(true);
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
      if (DETAIL_TABS.includes(this._tab)) void this._loadDetails(true);
    }
    if (action === "period") { this._period = control.dataset.value; this._readingPage = 0; this._render(); }
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

  _banner(message, action, id, tone = "error") {
    const banner = node("div", null, `banner${tone === "error" ? " error" : ""}`);
    banner.setAttribute("role", tone === "error" ? "alert" : "status");
    banner.append(node("p", message));
    if (action) banner.append(this._button("Thử lại", action, id, "", this._cooling()));
    return banner;
  }

  _status(message) {
    const status = node("p", message, "loading");
    status.setAttribute("role", "status");
    return status;
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
    else if (this._listBusy) main.append(this._status("Đang tải tài khoản EVN CSKH…"));
    else if (this._listError) main.append(this._banner(this._listError, "entries", "list-retry"));
    else if (!this._choice) {
      main.append(node("h2", "Chưa có khách hàng được liên kết"), node("p", "Thêm hoặc kiểm tra tích hợp EVN CSKH trong Cài đặt Home Assistant, sau đó tải lại danh sách.", "empty"), this._button("Tải lại danh sách", "entries", "entries-reload"));
    } else {
      const tools = node("div", null, "account-tools");
      const select = node("select");
      select.id = "customer-select";
      this._choices.forEach((choice, index) => {
        const option = node("option", `${text(choice.customer.code)} · ${text(choice.customer.unit)}`);
        option.value = String(index);
        option.selected = choice === this._choice;
        select.append(option);
      });
      const refresh = this._iconButton("Cập nhật dữ liệu", "refresh", "refresh", "M21 12a9 9 0 1 1-3-6.7M21 3v6h-6");
      refresh.setAttribute("aria-busy", String(this._overviewBusy || this._detailsBusy));
      if (this._overviewBusy || this._detailsBusy || this._cooling()) refresh.setAttribute("aria-disabled", "true");
      tools.append(this._field("Tài khoản / khách hàng", select, "account-field"), refresh);
      inner.append(tools);
      const customer = this._choice.customer;
      const intro = node("section", null, "intro");
      const identity = node("div");
      identity.append(node("h2", text(customer.name)), node("p", `${text(customer.code)} · ${text(customer.unit)}`, "muted"));
      intro.append(identity);
      const freshness = node("p", this._overviewBusy ? "Đang cập nhật tổng quan…" : this._overview?.fetched_at ? `Cập nhật lúc ${time(this._overview.fetched_at)}` : "Chưa có lần cập nhật thành công", "freshness meta");
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
      if (this._overview?.available === false || customer.available === false) main.append(this._banner("Kết nối EVN hiện chưa sẵn sàng. Số liệu còn hiển thị là dữ liệu đã lưu, không phải cập nhật mới.", null, null, "warn"));
      const content = node("section", null, "stack");
      content.id = "tab-content";
      content.setAttribute("role", "tabpanel");
      content.setAttribute("aria-labelledby", `tab-${this._tab}`);
      if (this._tab === 0) this._renderOverview(content);
      if (this._tab === 1) this._renderEnergy(content);
      if (this._tab === 2) this._renderMeter(content);
      if (this._tab === 3) this._renderInvoices(content);
      if (this._tab === 4) this._renderOutages(content);
      if (this._tab === 5) this._renderInfo(content);
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

  _metricState(label, value, detail, compact = false) {
    if (this._overviewBusy && !this._overview) return this._metric(label, "Đang tải…", "Vui lòng chờ trong giây lát", compact);
    return this._metric(label, value, detail, compact);
  }

  _usageFor(pointId) {
    return array(this._overview?.usage).find(item => item.point_id === pointId) || null;
  }

  _renderOverview(parent) {
    const overview = this._overview;
    const usage = this._usageFor(this._point);
    const metrics = node("div", null, "metrics");
    const monthly = usage?.monthly;
    const mom = usage?.mom;
    const reading = usage?.reading;
    const deltaDetail = mom && finite(mom.percent) ? `${signed(mom.percent)} so với kỳ trước` : monthly?.period ? `Kỳ ${monthly.period} · Chưa có kỳ trước` : "Chưa có kỳ ghi nhận";
    metrics.append(
      this._metricState("Điện năng tháng gần nhất", finite(monthly?.kwh) ? `${numeric(monthly.kwh)} kWh` : "Chưa có dữ liệu", deltaDetail, !finite(monthly?.kwh)),
      this._metricState("TB 12 tháng", finite(usage?.average_12m) ? `${numeric(usage.average_12m)} kWh` : "Chưa có dữ liệu", "Trung bình mỗi tháng của điểm đo", !finite(usage?.average_12m)),
      this._metricState("Chỉ số mới nhất", finite(reading?.new) ? numeric(reading.new) : "Chưa có dữ liệu", reading?.period ? `Kỳ ${reading.period} · ${KINDS[reading.kind] || text(reading.kind)}` : "Chưa có chỉ số", true),
      this._metricState("Tiền còn nợ", money(overview?.outstanding?.amount), finite(overview?.outstanding?.count) ? `${numeric(overview.outstanding.count)} hóa đơn chưa trả` : "Chưa xác định số hóa đơn", !finite(overview?.outstanding?.amount)),
      this._metricState("Ngừng điện kế tiếp", overview?.next_outage?.start ? time(overview.next_outage.start) : overview ? "Chưa có lịch" : "Chưa có dữ liệu", overview?.next_outage?.area ? text(overview.next_outage.area) : "Theo kế hoạch của điện lực", true)
    );
    parent.append(metrics, this._comparisonGrid());
    const layout = node("div", null, "overview-grid");
    const chart = node("section", null, "card chart-card");
    const head = node("header", null, "card-head");
    const title = node("div");
    title.append(node("h2", "Điện năng theo tháng"), node("p", `Điểm đo ${text(this._point)} · kWh`, "meta"));
    head.append(title);
    chart.append(head);
    if (this._details) this._renderChart(chart, "monthly", this._monthly());
    else {
      const fallback = monthly ? [{ period: monthly.period, kwh: monthly.kwh }] : [];
      if (fallback.length) this._renderChart(chart, "monthly", fallback);
      else chart.append(node("p", this._overviewBusy ? "Đang tải tổng quan…" : "Chưa có sản lượng tháng gần nhất cho điểm đo này.", this._overviewBusy ? "loading" : "empty"));
      const placeholder = node("div", null, "placeholder");
      placeholder.append(node("p", "Tải lịch sử 12 tháng gần nhất để vẽ biểu đồ đầy đủ.", "muted"));
      if (this._point) placeholder.append(this._button("Tải 12 tháng gần nhất", "details", "history-load", "primary", this._detailsBusy || this._cooling()));
      else placeholder.append(node("p", "Khách hàng này chưa có điểm đo.", "meta"));
      chart.append(placeholder);
      if (this._detailsError) chart.append(this._banner(this._detailsError, "details", "chart-retry"));
    }
    layout.append(chart);
    const side = node("section", null, "card");
    side.append(node("h2", "Ngừng điện kế tiếp"));
    const next = overview?.next_outage;
    if (next) {
      const list = node("dl", null, "stat-list");
      for (const [label, value] of [["Bắt đầu", time(next.start)], ["Kết thúc dự kiến", next.end ? time(next.end) : "Chưa xác định"], ["Khu vực", text(next.area)]]) {
        const row = node("div");
        row.append(node("dt", label), node("dd", value));
        list.append(row);
      }
      side.append(list);
      if (next.reason) side.append(node("p", text(next.reason), "muted"));
    } else {
      side.append(node("p", overview ? "Chưa có kế hoạch ngừng điện cho khách hàng này." : "Chưa có dữ liệu ngừng điện.", "empty"));
    }
    const link = this._button("Xem lịch ngừng điện", "tab", "open-outages", "link");
    link.dataset.tab = "4";
    const notice = node("div", null, "notice");
    notice.append(link);
    side.append(notice);
    layout.append(side);
    parent.append(layout);
    if (array(overview?.usage).length > 1) parent.append(this._pointSummary());
  }

  _pointSummary() {
    const card = node("section", null, "card");
    card.append(node("h2", "Tóm tắt theo điểm đo"), node("p", "Mỗi điểm đo một kỳ ghi nhận gần nhất.", "meta"));
    const rows = array(this._overview.usage).map(item => [
      text(item.point_id),
      finite(item.monthly?.kwh) ? `${numeric(item.monthly.kwh)} kWh` : "—",
      finite(item.average_12m) ? `${numeric(item.average_12m)} kWh` : "—",
      finite(item.reading?.new) ? numeric(item.reading.new) : "—"
    ]);
    card.append(this._table(["Điểm đo", "Tháng gần nhất", "TB 12 tháng", "Chỉ số mới"], rows, "Tóm tắt điện năng theo từng điểm đo", "", "scroll-table"));
    return card;
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
    const window = this._details?.daily_window;
    const dailyHelp = validDate(window?.start) && validDate(window?.end) ? `Cửa sổ truy vấn ngày thực tế: ${displayDate(window.start)} → ${displayDate(window.end)}.` : "Chưa có cửa sổ truy vấn ngày thực tế.";
    const help = node("p", `Tối đa 366 ngày cho lịch sử tháng. Dữ liệu ngày được truy vấn tối đa 31 ngày đến ngày kết thúc (không sau hôm nay). ${dailyHelp} Một bản ghi có thể gộp nhiều ngày.`, "meta filter-help");
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
    return result.slice(-12);
  }

  _renderChart(parent, period, records, options = {}) {
    const values = records.map(item => ({ ...item, provisional: item.provisional === true || (period === "monthly" && array(this._overview?.comparisons?.monthly).some(row => row.period === item.period && row.provisional === true)) }));
    this._renderColumns(parent, values, { period, title: `Điện năng ${period === "monthly" ? "theo tháng" : "theo ngày"}`, smooth: options.smooth === true });
  }

  _renderColumns(parent, records, { field = "kwh", unit = "kWh", period = "monthly", title, comparison = false, smooth = false } = {}) {
    if (!records.length || (!comparison && !records.some(item => finite(item?.[field])))) {
      parent.append(node("p", "Chưa có số liệu điện năng trong khoảng này.", "empty"));
      return;
    }
    const scale = columnScale(records.map(item => item?.[field]));
    const format = value => field === "vnd" ? money(value) : numeric(value);
    const fullValue = value => finite(value) ? field === "vnd" ? money(value) : `${numeric(value)} ${unit}` : "Chưa có dữ liệu";
    const chart = node("div", null, `chart ${period}${comparison ? " comparison-chart" : ""}${smooth ? " smooth-chart" : ""}`);
    chart.dataset.unit = unit;
    chart.dataset.field = field;
    chart.dataset.min = String(scale.low);
    chart.dataset.max = String(scale.high);
    chart.setAttribute("role", "img");
    const captions = records.map(item => `${item.label || item.period} (${item.period}): ${fullValue(item[field])}${item.provisional === true ? " · Tạm tính/chưa chốt" : ""}`);
    chart.setAttribute("aria-label", `${title}, đơn vị ${unit}. ${captions.join("; ")}. Khoảng trống là chưa có dữ liệu, không phải 0.`);
    chart.style.gridTemplateColumns = `repeat(${records.length},minmax(0,1fr))`;
    records.forEach((item, index) => {
      const column = node("div", null, "chart-column");
      column.dataset.period = item.period;
      column.dataset.state = finite(item[field]) ? "known" : "missing";
      column.title = captions[index];
      column.setAttribute("aria-label", captions[index]);
      if (comparison) column.tabIndex = 0;
      const track = node("div", null, "track");
      const axis = node("div", null, "zero-axis");
      axis.style.bottom = `${scale.zero}%`;
      track.append(axis);
      const value = item[field];
      const hasValue = finite(value);
      if (hasValue) {
        const bar = node("div", null, `bar${item.provisional === true ? " current" : ""}${value < 0 ? " negative" : ""}`);
        bar.style.height = `${scale.height(value)}%`;
        bar.style.bottom = `${scale.bottom(value)}%`;
        track.append(bar);
      }
      if (smooth && hasValue) {
        const dot = node("span", null, "history-dot");
        dot.style.bottom = `calc(${scale.top(value)}% - 6px)`;
        dot.dataset.period = item.period;
        dot.setAttribute("tabindex", "0");
        dot.setAttribute("role", "button");
        dot.setAttribute("aria-label", captions[index]);
        track.append(dot);
      }
      if (!comparison) {
        const amount = node("span", hasValue ? format(value) : "—", "bar-number");
        amount.style.bottom = `${hasValue ? scale.top(value) : scale.zero}%`;
        track.append(amount);
      }
      const end = dailyEnd(item.period);
      const label = comparison ? item.label : period === "monthly" ? String(item.period).slice(5, 7) : index % Math.max(1, Math.ceil(records.length / 6)) === 0 ? end ? displayDate(end).slice(0, 5) : "—" : "";
      column.append(track, node("div", label, "chart-label"));
      if (comparison) {
        if (period === "daily") column.append(node("span", displayDate(item.period), "slot-date"));
        if (field !== "vnd") column.append(node("span", hasValue ? format(value) : "Chưa có", "slot-value"));
        if (item.provisional === true) column.append(node("span", "Tạm tính/chưa chốt", "slot-state"));
      }
      chart.append(column);
    });
    if (smooth) this._renderSmooth(chart, records, { field, unit, scale });
    parent.append(chart);
    if (comparison && field === "vnd") {
      const rows = records.map(item => [item.label, finite(item.vnd) ? money(item.vnd) : "Chưa có"]);
      parent.append(this._table(["Kỳ", "Tiền hóa đơn (VNĐ)"], rows, "Giá trị ba kỳ · chưa có khác với 0", "comparison-values"));
    }
    if (!comparison) parent.append(node("div", null, "chart-footer"));
    parent.append(node("p", `${records[0].period} → ${records.at(-1).period} · Khoảng trống là chưa có dữ liệu, không phải 0.`, "meta"));
  }

  _renderSmooth(chart, records, { field, unit, scale }) {
    const height = 164;
    const width = Math.max(1, records.length) * 100;
    const gradientId = `evn-grad-${field}-${records.length}`;
    const captions = records.map(item => `${item.label || item.period} (${item.period}): ${finite(item[field]) ? `${numeric(item[field])} ${unit}` : "Chưa có dữ liệu"}`);
    const svg = svgNode("svg", { class: "history-overlay", viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: "none", role: "img", "aria-label": `Biểu đồ đường ${unit}. ${captions.join("; ")}. Khoảng trống là chưa có dữ liệu, không phải 0.` });
    const defs = svgNode("defs");
    const gradient = svgNode("linearGradient", { id: gradientId, x1: "0", y1: "0", x2: "0", y2: "1" });
    gradient.append(svgNode("stop", { offset: "0", style: "stop-color:var(--evn-chart-1);stop-opacity:0.30" }), svgNode("stop", { offset: "1", style: "stop-color:var(--evn-chart-1);stop-opacity:0" }));
    defs.append(gradient);
    svg.append(defs);
    for (const ratio of [0, 0.5, 1]) svg.append(svgNode("line", { class: "history-grid", x1: 0, x2: width, y1: height * ratio, y2: height * ratio, "vector-effect": "non-scaling-stroke" }));
    const points = records.map((item, index) => finite(item[field]) ? { x: index * 100 + 50, y: height * (1 - scale.top(item[field]) / 100), item } : null);
    let segment = [];
    const flush = () => {
      if (segment.length > 1) {
        const path = smoothPath(segment);
        const area = `${path} L${segment.at(-1).x.toFixed(3)},${height} L${segment[0].x.toFixed(3)},${height} Z`;
        svg.append(svgNode("path", { class: "history-line", d: path, "vector-effect": "non-scaling-stroke" }));
        svg.append(svgNode("path", { class: "history-area", d: area, fill: `url(#${gradientId})` }));
      }
      segment = [];
    };
    for (const point of points) { if (point) segment.push(point); else flush(); }
    flush();
    chart.append(svg);
  }

  _comparisonCard(kind) {
    const daily = kind === "daily";
    const invoice = kind === "invoice";
    const title = daily ? "Điện năng ba ngày gần nhất" : invoice ? "Tiền hóa đơn ba kỳ gần nhất" : "Điện năng ba kỳ gần nhất";
    const card = node("section", null, "card comparison-card");
    card.dataset.chart = `${kind}-comparison`;
    card.append(node("h2", title), node("p", daily ? `Điểm đo ${text(this._point)} · kWh` : invoice ? "Tổng khách hàng · VNĐ · kỳ theo tháng" : "Tổng khách hàng · tất cả điểm đo · kỳ theo tháng EVN · kWh", "meta"));
    if (daily) card.append(node("p", "Có thể tạm tính; ngày chưa công bố để trống", "meta"));
    const comparisons = this._overview?.comparisons;
    const records = comparisonSlots(comparisons, this._point, daily ? "daily" : "monthly");
    card.setAttribute("aria-busy", String(this._overviewBusy));
    if (records) {
      card.dataset.asOf = comparisons.as_of;
      this._renderColumns(card, records, { field: invoice ? "vnd" : "kwh", unit: invoice ? "VNĐ" : "kWh", period: daily ? "daily" : "monthly", title, comparison: true });
      card.append(node("p", `Mốc dữ liệu ${comparisons.as_of} · So sánh cố định, không theo bộ lọc lịch sử.`, "meta"));
      if (!records.some(item => finite(item[invoice ? "vnd" : "kwh"]))) card.append(node("p", "Chưa có số liệu cho ba mốc này.", "meta"));
    } else card.append(this._overviewBusy ? this._status("Đang tải số liệu so sánh…") : node("p", this._overview ? "Máy chủ chưa cung cấp dữ liệu so sánh ba kỳ. Không thay bằng kỳ ghi nhận gần nhất." : "Chưa có dữ liệu so sánh.", "empty"));
    if (this._overview?.available === false || this._choice?.customer.available === false) card.append(node("p", "Kết nối EVN chưa sẵn sàng; số liệu hiển thị có thể đã cũ.", "meta"));
    return card;
  }

  _comparisonGrid() {
    const grid = node("div", null, "comparison-grid");
    grid.append(this._comparisonCard("daily"), this._comparisonCard("monthly"));
    return grid;
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

  _detailState(parent) {
    if (this._detailsError) parent.append(this._banner(this._detailsError, "details", "details-retry"));
    if (this._detailsBusy) parent.append(this._status("Đang tải dữ liệu lịch sử…"));
    if (this._details) parent.append(node("p", `Lịch sử cập nhật: ${time(this._details.fetched_at)} · Giờ Việt Nam`, "meta"));
  }

  _renderEnergy(parent) {
    parent.append(this._filters(), this._comparisonGrid());
    const content = node("section", null, "stack");
    this._detailState(content);
    if (this._details) {
      const tools = node("div", null, "section-tools");
      tools.append(node("h2", this._period === "monthly" ? "Điện năng theo tháng" : "Điện năng theo ngày"), this._segments([["monthly", "Tháng"], ["daily", "Ngày"]], this._period, "period", "Kỳ điện năng"));
      content.append(tools);
      const card = node("section", null, "card chart-card");
      card.dataset.chart = "energy-history";
      const records = this._period === "monthly" ? this._monthly() : dailyRecords(this._details.daily);
      this._renderChart(card, this._period, records, { smooth: true });
      content.append(card);
      const tableCard = node("section", null, "card");
      tableCard.append(node("h2", "Bảng số liệu"));
      if (this._period === "daily") tableCard.append(node("p", "Dữ liệu ngày có thể do điện lực gộp nhiều ngày trong một bản ghi.", "meta"));
      tableCard.append(this._table(["Kỳ ghi nhận", "Điện năng (kWh)"], records.map(item => [text(item.period), finite(item.kwh) ? `${numeric(item.kwh)} kWh` : "Chưa có dữ liệu"]), `Bảng ${this._period === "monthly" ? "tháng" : "ngày"}, đơn vị kWh`, "", "data-table"));
      content.append(tableCard);
    } else if (!this._detailsBusy && !this._detailsError) {
      content.append(node("p", this._point ? "Chọn khoảng ngày rồi bấm Tải dữ liệu để xem điện năng." : "Khách hàng này chưa có điểm đo để tra cứu.", "empty"));
    }
    parent.append(content);
  }

  _renderIndexHistory(parent) {
    const card = node("section", null, "card index-card");
    card.dataset.chart = "meter-index-history";
    card.append(node("h2", "Diễn biến chỉ số công tơ"), node("p", `Điểm đo ${text(this._point)} · Chỉ số gốc, không quy đổi thành kWh. Chỉ nối các mốc ghi thực tế cùng công tơ, bộ chỉ số và loại.`, "meta"));
    card.setAttribute("aria-busy", String(this._detailsBusy));
    parent.append(card);
    if (!this._details) {
      card.append(this._detailsBusy ? this._status("Đang tải lịch sử chỉ số…") : node("p", "Chưa có lịch sử chỉ số để vẽ biểu đồ.", "empty"));
      return;
    }
    const groups = readingSeries(this._details.readings);
    const series = groups.find(group => group.key === this._readingSeries) || groups[0];
    if (!series) { card.append(node("p", "Chưa đủ chỉ số có ngày ghi thực tế để vẽ đường.", "index-empty muted")); return; }
    if (array(this._details.readings).length > 1000) card.append(node("p", "Biểu đồ giới hạn 1.000 bản ghi đầu; bảng lịch sử vẫn giữ toàn bộ dữ liệu.", "meta"));
    if (groups.length > 1) {
      const select = node("select");
      select.id = "meter-series-select";
      groups.forEach(group => {
        const option = node("option", group.label);
        option.value = group.key;
        option.selected = group.key === series.key;
        select.append(option);
      });
      card.append(this._field("Chuỗi chỉ số", select, "index-series-field"));
    } else card.append(node("p", series.label, "meta"));
    const valid = series.points.filter(point => finite(point.value));
    const tooltip = node("p", valid.length ? `${valid.at(-1).label} · Chỉ số gốc ${numeric(valid.at(-1).value)}` : "Chưa có chỉ số hợp lệ.", "index-tooltip meta");
    tooltip.id = "meter-index-tooltip";
    tooltip.setAttribute("role", "status");
    if (series.blocked) card.append(node("p", "Có bản ghi chưa rõ ngày hoặc định danh; không nối đường qua dữ liệu chưa xác định.", "meta"));
    if (valid.length < 2) card.append(node("p", "Chưa đủ hai chỉ số có ngày ghi thực tế để vẽ đường.", "index-empty muted"));
    else {
      const values = valid.map(point => point.value);
      const low = Math.min(...values);
      const high = Math.max(...values);
      const magnitude = Math.max(1, ...values.map(value => Math.abs(value)));
      const bottom = low / magnitude;
      const span = high / magnitude - bottom;
      const first = series.points[0].stamp;
      const last = series.points.at(-1).stamp;
      const x = point => last === first ? 408 : 112 + (point.stamp - first) / (last - first) * 592;
      const y = value => span ? 216 - (value / magnitude - bottom) / span * 192 : 120;
      const description = `${series.label}. Thang chỉ số gốc từ ${numeric(low)} đến ${numeric(high)}; trục theo khoảng chỉ số, không suy ra điện năng. Khoảng trống không được nội suy.`;
      const svg = svgNode("svg", { class: "index-chart", viewBox: "0 0 720 260", role: "img", "aria-label": description, "data-min": low, "data-max": high });
      svg.append(svgNode("title", {}, description));
      const defs = svgNode("defs");
      const gradient = svgNode("linearGradient", { id: "evn-grad-meter", x1: "0", y1: "0", x2: "0", y2: "1" });
      gradient.append(svgNode("stop", { offset: "0", style: "stop-color:var(--evn-chart-1);stop-opacity:0.30" }), svgNode("stop", { offset: "1", style: "stop-color:var(--evn-chart-1);stop-opacity:0" }));
      defs.append(gradient);
      svg.append(defs);
      for (const ratio of span ? [0, 0.5, 1] : [0.5]) {
        const value = low === high ? low : (bottom + span * ratio) * magnitude;
        const position = 216 - ratio * 192;
        const label = numeric(value);
        svg.append(svgNode("line", { class: "index-grid", x1: 112, x2: 704, y1: position, y2: position }));
        const tick = svgNode("text", { x: 104, y: position + 4, "text-anchor": "end" }, label.length > 16 ? value.toExponential(3) : label);
        tick.append(svgNode("title", {}, label));
        svg.append(tick);
      }
      for (const segment of series.segments) {
        const path = segment.map((point, index) => `${index ? "L" : "M"}${x(point).toFixed(3)},${y(point.value).toFixed(3)}`).join(" ");
        const curve = smoothPath(segment.map(point => ({ x: x(point), y: y(point.value) })));
        const area = `${curve} L${x(segment.at(-1)).toFixed(3)},216 L${x(segment[0]).toFixed(3)},216 Z`;
        svg.append(svgNode("path", { class: "index-line", d: path }));
        svg.append(svgNode("path", { class: "index-curve", d: curve }));
        svg.append(svgNode("path", { class: "index-area", d: area, fill: "url(#evn-grad-meter)" }));
      }
      valid.forEach((point, index) => {
        const label = `${point.label} · Chỉ số gốc ${numeric(point.value)} · ${text(series.meter)} · ${text(series.register)} · ${KINDS[series.kind] || "Chưa rõ loại"}`;
        const dot = svgNode("circle", { class: "index-point", id: `meter-index-point-${index}`, cx: x(point).toFixed(3), cy: y(point.value).toFixed(3), r: 4, tabindex: "0", role: "button", "aria-label": label, "aria-describedby": "meter-index-tooltip" });
        dot.append(svgNode("title", {}, label));
        svg.append(dot);
      });
      svg.append(svgNode("text", { x: 112, y: 248 }, displayDate(series.points[0].day)), svgNode("text", { x: 704, y: 248, "text-anchor": "end" }, displayDate(series.points.at(-1).day)));
      card.append(node("p", `Thang chỉ số gốc: ${numeric(low)} → ${numeric(high)} · Trục thu gọn, không suy ra điện năng từ độ dốc.`, "meta"), svg);
    }
    card.append(tooltip);
    const rows = [...series.points, ...series.unknown].map(point => [point.label, point.conflict ? "Chưa xác định · chỉ số xung đột" : finite(point.value) ? numeric(point.value) : "Chưa có"]);
    if (rows.length) card.append(this._table(["Mốc ghi thực tế", "Chỉ số gốc"], rows, series.label, "index-values"));
  }

  _renderMeter(parent) {
    const content = node("section", null, "stack");
    content.append(node("p", "Chỉ số mới nhất do điện lực ghi nhận cho từng điểm đo.", "muted"));
    if (!this._overview) content.append(this._overviewBusy ? this._status("Đang tải chỉ số…") : node("p", "Chưa có dữ liệu chỉ số.", "empty"));
    else {
      const blocks = node("div", null, "point-grid");
      const points = array(this._choice.customer.points);
      if (!points.length) blocks.append(node("p", "Khách hàng này chưa có điểm đo.", "empty"));
      for (const point of points) {
        const usage = this._usageFor(point.id);
        const reading = usage?.reading;
        const card = node("article", null, "point-card");
        card.append(node("h3", text(point.id)), node("p", text(point.address), "meta"));
        if (reading) {
          const list = node("dl", null, "stat-list");
          for (const [label, value] of [
            ["Chỉ số cũ", numeric(reading.old)],
            ["Chỉ số mới", numeric(reading.new)],
            ["Hệ số", numeric(reading.multiplier)],
            ["Kỳ ghi nhận", text(reading.period)],
            ["Loại chỉ số", KINDS[reading.kind] || text(reading.kind)],
            ["Điện năng ghi nhận", finite(reading.kwh) ? `${numeric(reading.kwh)} kWh` : "Chưa có dữ liệu"]
          ]) {
            const row = node("div");
            row.append(node("dt", label), node("dd", value));
            list.append(row);
          }
          card.append(list);
        } else card.append(node("p", "Chưa có chỉ số cho điểm đo này.", "empty"));
        blocks.append(card);
      }
      content.append(blocks);
    }
    content.append(this._filters());
    this._detailState(content);
    this._renderIndexHistory(content);
    if (this._details) {
      const readings = array(this._details.readings);
      const card = node("section", null, "card");
      card.append(node("h2", "Lịch sử chỉ số công tơ"), node("p", `Điểm đo ${text(this._details.point_id)} · ${text(this._details.start)} → ${text(this._details.end)}`, "meta"));
      if (!readings.length) card.append(node("p", "Chưa có bản ghi chỉ số trong khoảng đã chọn.", "empty"));
      else {
        this._readingPage = Math.max(0, Math.min(this._readingPage, Math.ceil(readings.length / 20) - 1));
        const rows = readings.slice(this._readingPage * 20, this._readingPage * 20 + 20).map(item => [text(item.period), readingLabel(item), text(item.meter), text(item.register), numeric(item.old), numeric(item.new), numeric(item.multiplier), finite(item.kwh) ? `${numeric(item.kwh)} kWh` : "—", KINDS[item.kind] || text(item.kind)]);
        const table = this._table(["Kỳ ghi nhận", "Mốc ghi thực tế", "Công tơ", "Bộ chỉ số", "Chỉ số cũ", "Chỉ số mới", "Hệ số", "kWh", "Loại"], rows, "Chỉ số công tơ do điện lực cung cấp", "", "scroll-table");
        table.id = "reading-results";
        card.append(table, this._pagination(readings.length, this._readingPage, 20, "reading-page"));
      }
      content.append(card);
    } else if (!this._detailsBusy && !this._detailsError) {
      content.append(node("p", this._point ? "Bấm Tải dữ liệu ở tab Điện năng hoặc chờ bảng chỉ số bên dưới." : "Khách hàng này chưa có điểm đo.", "empty"));
    }
    parent.append(content);
  }

  _renderInvoices(parent) {
    const overview = this._overview;
    if (overview) {
      const amount = overview.outstanding?.amount;
      const count = overview.outstanding?.count;
      const detail = finite(count) ? ` · ${numeric(count)} hóa đơn chưa trả` : "";
      const banner = node("div", null, `banner${finite(amount) && amount > 0 ? " warn" : finite(amount) && amount === 0 ? " ok" : ""}`);
      banner.setAttribute("role", "status");
      banner.append(node("p", finite(amount) ? `Tổng tiền còn phải trả: ${money(amount)}${detail}` : `Chưa xác định được số tiền còn nợ${detail}`));
      parent.append(banner);
    }
    parent.append(this._comparisonCard("invoice"));
    const filters = node("div", null, "invoice-filters");
    const search = node("input");
    search.id = "invoice-search";
    search.type = "search";
    search.placeholder = "Ví dụ: 09/2026";
    search.value = this._query;
    search.autocomplete = "off";
    const paid = node("select");
    paid.id = "paid-select";
    for (const [value, label] of [["all", "Tất cả trạng thái"], ["paid", "Đã thanh toán"], ["unpaid", "Chưa thanh toán"]]) {
      const option = node("option", label);
      option.value = value;
      option.selected = this._paid === value;
      paid.append(option);
    }
    filters.append(this._field("Tìm kỳ hóa đơn", search), this._field("Trạng thái thanh toán", paid));
    if (this._query || this._paid !== "all") filters.append(this._button("Xóa lọc", "clear-search", "clear-search", "link"));
    parent.append(filters);
    this._detailState(parent);
    if (this._details) parent.append(this._invoiceTable());
    else if (!this._detailsBusy && !this._detailsError) parent.append(node("p", this._point ? "Đang chuẩn bị dữ liệu hóa đơn…" : "Khách hàng này chưa có điểm đo để tra cứu hóa đơn.", "empty"));
    const paidRecent = array(overview?.paid_recent);
    if (paidRecent.length) {
      const card = node("section", null, "card");
      card.append(node("h2", "Lịch sử thanh toán"), node("p", `${numeric(overview.paid_count)} hóa đơn đã thanh toán · hiển thị ${numeric(paidRecent.length)} bản ghi gần nhất (chỉ để xem, không tải được PDF từ đây)`, "meta"));
      card.append(this._table(["Kỳ hóa đơn", "Tổng tiền", "Ngày đã trả", "Kênh thanh toán"], paidRecent.map(invoice => [text(invoice.period), money(invoice.amount), text(invoice.paid_date), text(invoice.payment_channel_label)]), "Các hóa đơn vừa thanh toán gần đây", "", "scroll-table"));
      parent.append(card);
    }
  }

  _invoiceTable() {
    const results = node("section");
    results.id = "invoice-results";
    results.tabIndex = -1;
    results.setAttribute("aria-label", "Kết quả hóa đơn");
    const invoices = this._details.invoices.map((invoice, index) => ({ invoice, index })).filter(({ invoice }) => {
      const haystack = `${invoice.period} ${invoice.status_label}`.toLocaleLowerCase("vi");
      return haystack.includes(this._query.trim().toLocaleLowerCase("vi")) && (this._paid === "all" || paymentState(invoice) === this._paid);
    });
    if (!invoices.length) {
      results.append(node("p", this._query || this._paid !== "all" ? "Không có hóa đơn khớp bộ lọc. Thử kỳ khác hoặc bỏ bộ lọc." : "Chưa có hóa đơn của khách hàng này trong khoảng đã chọn.", "empty"));
      return results;
    }
    this._invoicePage = Math.max(0, Math.min(this._invoicePage, Math.ceil(invoices.length / 12) - 1));
    const visible = invoices.slice(this._invoicePage * 12, this._invoicePage * 12 + 12);
    const wrap = node("div", null, "table-wrap invoice-table-wrap");
    const table = node("table", null, "invoice-table");
    table.append(node("caption", "Hóa đơn trong khoảng đã chọn · Chọn kỳ để xem chi tiết và tải PDF"));
    const head = node("thead");
    const line = node("tr");
    for (const label of ["Kỳ hóa đơn", "Tổng tiền", "Còn phải trả", "Trạng thái", "Hạn thanh toán"]) {
      const cell = node("th", label);
      cell.scope = "col";
      if (label.includes("tiền") || label.includes("trả")) cell.classList.add("number");
      if (label === "Hạn thanh toán") cell.classList.add("nowrap");
      line.append(cell);
    }
    head.append(line);
    const body = node("tbody");
    const cards = node("div", null, "invoice-cards");
    for (const { invoice, index } of visible) {
      const row = node("tr");
      const first = node("th");
      first.scope = "row";
      first.append(this._invoiceButton(invoice, index, false));
      if (invoice.cycle != null) first.append(node("p", `Kỳ thu ${text(invoice.cycle)}`, "meta"));
      const status = node("td");
      status.append(this._badge(invoice));
      row.append(first, node("td", money(invoice.amount), "number"), node("td", money(payableAmount(invoice)), "number"), status, node("td", text(invoice.due_date), "nowrap"));
      body.append(row);
      const card = node("article", null, "invoice-card");
      const top = node("div", null, "row");
      top.append(this._invoiceButton(invoice, index, true), this._badge(invoice));
      card.append(top, node("strong", money(invoice.amount)), node("p", `Còn phải trả: ${money(payableAmount(invoice))}`, "meta"), node("p", `Hạn thanh toán: ${text(invoice.due_date)}`, "meta"));
      cards.append(card);
    }
    table.append(head, body);
    wrap.append(table);
    results.append(wrap, cards, this._pagination(invoices.length, this._invoicePage, 12, "invoice-page"));
    return results;
  }

  _invoiceButton(invoice, index, mobile) {
    const button = this._button(text(invoice.period), "invoice", `invoice-${index}${mobile ? "-mobile" : ""}`, "link");
    button.dataset.index = String(index);
    button.setAttribute("aria-label", `Xem hóa đơn ${text(invoice.period)}${invoice.cycle != null ? `, kỳ thu ${invoice.cycle}` : ""}`);
    button.setAttribute("aria-haspopup", "dialog");
    return button;
  }

  _badge(invoice) { return node("span", text(invoice.status_label), `badge ${paymentState(invoice)}`); }

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
    parent.append(node("p", "Lịch ngừng điện là kế hoạch của điện lực, không phải trạng thái mất điện thực tế. Thời gian hiển thị theo giờ Việt Nam (UTC+7).", "muted"));
    if (!this._overview) { parent.append(this._overviewBusy ? this._status("Đang tải lịch ngừng điện…") : node("p", "Chưa có dữ liệu lịch ngừng điện.", "empty")); return; }
    const outages = array(this._overview.outages);
    const count = node("h2", `${numeric(this._overview.outage_count ?? outages.length)} kế hoạch ngừng điện`);
    parent.append(count);
    if (!outages.length) { parent.append(node("p", "Chưa có lịch ngừng điện dự kiến cho khách hàng này.", "empty")); return; }
    const card = node("section", null, "card");
    const list = node("ul", null, "outages");
    for (const outage of outages) {
      const item = node("li");
      const dates = node("dl", null, "outage-time stat-list");
      for (const [label, value] of [["Bắt đầu", outage.start], ["Kết thúc dự kiến", outage.end]]) {
        const row = node("div");
        row.append(node("dt", label), node("dd", value ? time(value) : "Chưa xác định"));
        dates.append(row);
      }
      item.append(dates, node("h3", text(outage.area)), node("p", text(outage.reason), "muted"));
      list.append(item);
    }
    card.append(list);
    parent.append(card);
  }

  _renderInfo(parent) {
    const overview = this._overview;
    if (!overview) { parent.append(this._overviewBusy ? this._status("Đang tải thông tin khách hàng…") : node("p", "Chưa có thông tin khách hàng.", "empty")); return; }
    const info = overview.info || {};
    const customerCard = node("section", null, "card");
    customerCard.append(node("h2", "Thông tin khách hàng"));
    const list = node("dl", null, "stat-list");
    for (const [label, value] of [
      ["Tên khách hàng", text(info.name)],
      ["Địa chỉ", text(info.address)],
      ["Điện thoại", text(info.phone)],
      ["Loại khách hàng", text(info.customer_type)],
      ["Loại chủ thể", text(info.subject_type)],
      ["Mã vùng", text(info.region_code)],
      ["Tỉnh / thành", text(info.province)],
      ["Xã / phường", text(info.commune)],
      ["Hợp đồng", text(info.contract)],
      ["Tham chiếu thanh toán", text(info.pay_reference)],
      ["Thanh toán hộ", text(info.pay_on_behalf)],
      ["Cảnh báo tiêu thụ", finite(info.alert_count) ? `${numeric(info.alert_count)} cảnh báo` : "Chưa có thông tin"]
    ]) {
      const row = node("div");
      row.append(node("dt", label), node("dd", value));
      list.append(row);
    }
    customerCard.append(list);
    if (info.default_contract === true) {
      const flag = node("div", null, "notice");
      flag.append(node("p", "Hợp đồng áp dụng cho khách hàng này.", "meta"), this._badge({ status_label: "Hợp đồng mặc định", status: "DATT" }));
      customerCard.append(flag);
    }
    parent.append(customerCard);
    const contracts = array(overview.contracts);
    const contractsCard = node("section", null, "card");
    contractsCard.append(node("h2", "Hợp đồng"));
    if (contracts.length) contractsCard.append(this._table(["Số hợp đồng", "Địa chỉ", "Đơn vị quản lý"], contracts.map(row => [text(row.number), text(row.address), text(row.unit)]), "Danh sách hợp đồng của khách hàng", "", "scroll-table"));
    else contractsCard.append(node("p", "Chưa có hợp đồng nào được ghi nhận.", "empty"));
    parent.append(contractsCard);
    const used = new Set([...array(overview.invoices), ...array(overview.paid_recent), ...array(this._details?.invoices)].map(invoice => invoice.org_code).filter(Boolean));
    const banks = array(overview.banks);
    const banksCard = node("section", null, "card");
    banksCard.append(node("h2", "Tổ chức thanh toán"));
    if (banks.length) {
      const wrap = node("div", null, "table-wrap");
      wrap.tabIndex = 0;
      wrap.setAttribute("role", "region");
      wrap.setAttribute("aria-label", "Danh sách tổ chức thanh toán");
      const table = node("table", null, "scroll-table");
      table.append(node("caption", "Tổ chức thanh toán · đánh dấu Đã dùng nếu hóa đơn tham chiếu mã này"));
      const thead = node("thead");
      const head = node("tr");
      for (const label of ["Mã tổ chức", "Tên tổ chức", "Sử dụng"]) {
        const cell = node("th", label);
        cell.scope = "col";
        head.append(cell);
      }
      thead.append(head);
      const body = node("tbody");
      for (const bank of banks) {
        const row = node("tr");
        const code = node("th", text(bank.code));
        code.scope = "row";
        row.append(code, node("td", text(bank.name)));
        const cell = node("td");
        cell.append(used.has(bank.code) ? node("span", "Đã dùng", "badge paid") : node("span", "Chưa dùng", "badge"));
        row.append(cell);
        body.append(row);
      }
      table.append(thead, body);
      wrap.append(table);
      banksCard.append(wrap);
    } else banksCard.append(node("p", "Chưa có tổ chức thanh toán nào.", "empty"));
    parent.append(banksCard);
    const points = array(this._choice.customer.points);
    const pointsCard = node("section", null, "card");
    pointsCard.append(node("h2", "Điểm đo"));
    if (points.length) pointsCard.append(this._table(["Điểm đo", "Địa chỉ", "Hợp đồng", "Hiệu lực từ"], points.map(point => [text(point.id), text(point.address), text(point.contract), text(point.valid_from)]), "Danh sách điểm đo của khách hàng", "", "scroll-table"));
    else pointsCard.append(node("p", "Khách hàng này chưa có điểm đo.", "empty"));
    parent.append(pointsCard);
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
    headers.forEach(label => {
      const cell = node("th", label);
      cell.scope = "col";
      if (/^(Tổng tiền|T|Chỉ số|Hệ|Điện|kWh|Ngày|Hạn|Kỳ)/.test(label) && label !== "Kỳ hóa đơn") cell.classList.add("nowrap");
      heading.append(cell);
    });
    head.append(heading);
    const body = node("tbody");
    rows.forEach(row => {
      const line = node("tr");
      row.forEach((value, index) => {
        const cell = node(index ? "td" : "th", value);
        if (!index) cell.scope = "row";
        line.append(cell);
      });
      body.append(line);
    });
    table.append(head, body);
    wrap.append(table);
    return wrap;
  }

  _openInvoice(index) {
    const invoice = this._details?.invoices[index];
    if (!invoice || !this._admin()) return;
    this._cancelPdf();
    this._invoice = invoice;
    this._invoiceFocus = this.shadowRoot.activeElement?.id || `invoice-${index}`;
    this._stalePdf = false;
    const header = node("header", null, "dialog-head");
    const title = node("h2", `Hóa đơn ${text(invoice.period)}`);
    title.id = "invoice-title";
    header.append(title, this._iconButton("Đóng chi tiết hóa đơn", "close-invoice", "invoice-close", "m6 6 12 12M6 18 18 6"));
    const body = node("div", null, "dialog-body");
    body.append(node("p", money(invoice.amount), "invoice-total"), this._badge(invoice));
    const details = node("dl", null, "dialog-info");
    const unit = ["kWh", "kVArh"].includes(invoice.energy_unit) ? invoice.energy_unit : "";
    for (const [label, value] of [
      ["Kỳ hóa đơn", text(invoice.period)],
      ["Kỳ thu", text(invoice.cycle)],
      ["Thuế", money(invoice.tax)],
      ["Còn phải trả", money(payableAmount(invoice))],
      ["Hạn thanh toán", text(invoice.due_date)],
      ["Đã thanh toán ngày", text(invoice.paid_date)],
      ["Điện năng", finite(invoice.energy) ? `${numeric(invoice.energy)} ${unit}`.trim() : "Chưa có dữ liệu"],
      ["Kênh thanh toán", text(invoice.payment_channel_label)],
      ["Tổ chức thu", text(invoice.org_code)]
    ]) {
      const row = node("div");
      row.append(node("dt", label), node("dd", value));
      details.append(row);
    }
    body.append(details);
    const actions = node("div", null, "pdf-actions");
    for (const [kind, label] of Object.entries(DOCUMENTS)) {
      if (!array(invoice.documents).includes(kind)) continue;
      const button = this._button(label, "pdf", `pdf-${kind}`, kind === "invoice" ? "primary" : "");
      button.dataset.kind = kind;
      actions.append(button);
    }
    if (!actions.childElementCount) body.append(node("p", "Hóa đơn này không có tài liệu PDF để tải.", "muted"));
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
    const stale = this._stalePdf;
    this._cancelPdf();
    if (stale) void this._loadDetails(true);
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
    for (const [url, timer] of this._urls || []) {
      clearTimeout(timer);
      URL.revokeObjectURL(url);
    }
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
      if (!response.ok) {
        if (response.status === 404 || response.status === 410) {
          this._stalePdf = true;
          this._detailsCache.delete(this._detailKey());
          throw { pdf: "Liên kết tải đã hết hạn. Hãy đóng hộp thoại, dữ liệu hóa đơn sẽ được tải lại rồi mở lại để lấy liên kết mới." };
        }
        throw { code: response.status };
      }
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
            if (!current()) {
              await reader.cancel();
              return;
            }
            if (done) break;
            size += value.byteLength;
            if (size > MAX_PDF) {
              await reader.cancel();
              throw { pdf: "Tệp PDF vượt giới hạn 16 MB." };
            }
            chunks.push(value);
          }
          blob = new Blob(chunks, { type: "application/pdf" });
        } finally {
          reader.releaseLock();
        }
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
      this._urls.set(url, setTimeout(() => {
        URL.revokeObjectURL(url);
        this._urls.delete(url);
      }, 1500));
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

export { columnScale, comparisonSlots, dailyEnd, dailyRecords, readingMoment, readingSeries, paymentState, payableAmount };

if (!customElements.get("evn-cskh-panel")) customElements.define("evn-cskh-panel", EvnCskhPanel);
