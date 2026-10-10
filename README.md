# EVN CSKH — Home Assistant

Custom integration đọc dữ liệu **EVN CSKH thống nhất** (`com.evn.cskh.vn`,
app EVN toàn quốc) vào Home Assistant, kèm **bảng điều khiển EVN** trong sidebar
với lịch sử điện năng, chỉ số công tơ, hóa đơn và tải PDF hóa đơn.

Toàn bộ dự án nằm tại `/opt/apk-lab/input/evncskh/`; XAPK gốc được giữ nguyên
và không phát hành kèm.

## Trạng thái

- **v0.5.1:** **thêm lại khu vực Tải hóa đơn** ngay trong danh sách hóa đơn (nút tải từng dòng + bảng kê/thông báo, có trạng thái/retry), không cần mở hộp thoại. v0.5.0 đã thêm **logo/icon thương hiệu** cho integration, **icon cho mọi
  sensor/button**, **biểu đồ kiểu sóng (spline + vùng gradient)**, animation mượt
  (tôn trọng `prefers-reduced-motion`), bảng màu chuẩn biểu đồ theo chất EVN
  (xanh dương/xanh ngọc/hổ phách) dùng riêng cho biểu đồ; và **sensor lịch cắt
  điện chi tiết** phục vụ automation.
- Đã xác minh đăng nhập, refresh, đọc lịch sử và tải PDF thật trên EVNSPC.
  Dữ liệu kiểm tra mới: những ngày/tháng chưa công bố được giữ **unknown**, không
  đổi thành 0. Hóa đơn `hoadon` gồm cả bản ghi đã trả; số lượng hóa đơn không
  đồng nghĩa số hóa đơn còn nợ, phải xét trạng thái thanh toán.
- Qua **2.155 pytest** (offline + runtime HA 2025.12.5 với API giả lập) và
  **213 kiểm tra biểu đồ/giao diện** trên Chromium mock loopback.
- Người dùng báo bản trước hoạt động ổn. Bản 0.4.0 chưa được đối chiếu từng
  giá trị với app hay kiểm chứng trực tiếp trên HA production của người dùng.

## Tính năng

- Đăng nhập tài khoản EVN CSKH thống nhất; tự chọn miền theo cấu hình server
  (`PB` = EVNSPC, `PC` = EVNCPC, `PA` = NPC, `HN`, `PE`), không đoán theo prefix.
- **Sensors mỗi điểm đo:** sản lượng tháng gần nhất, sản lượng tháng trước,
  % thay đổi so với tháng trước, TB 12 tháng, khoảng ghi nhận gần nhất (kWh),
  chỉ số công tơ mới, hệ số nhân, ngày ghi.
- **Sensors mỗi khách hàng:** tiền & số hóa đơn chưa thanh toán (đúng `hoadon`),
  hóa đơn gần nhất (số tiền + trạng thái), số hóa đơn đã trả, lịch ngừng cấp
  điện kế tiếp, lần cập nhật gần nhất (kèm thông tin KH ở attributes).
- **Sensor mới theo yêu cầu:** Chỉ số tạm chốt, Chỉ số cuối kỳ trước,
  Tiêu thụ hôm nay/hôm qua/hôm kia, Chi tiết kỳ này, Hóa đơn năm nay, tiền và
  điện năng kỳ này/kỳ trước/kỳ trước nữa, mốc Cập nhật lúc.
- **Lịch cắt điện** dạng binary sensor: có lịch dự kiến trong tương lai,
  kèm thuộc tính bắt đầu/kết thúc. Không phải cảm biến đo mất điện thực tế.
- **Chi tiết lịch cắt điện để làm automation** (mỗi khách hàng): `next_outage`
  (mốc bắt đầu) nay kèm thuộc tính `end/area/reason/duration_hours/count`; thêm
  sensor `next_outage_end`, `next_outage_duration` (giờ), `next_outage_area`,
  `next_outage_reason`, `outage_count`, và các binary sensor `outage_scheduled`,
  `outage_soon` (bắt đầu trong ≤24 giờ, kèm `seconds_until`), `outage_active`
  (đang trong khung cắt điện theo lịch công bố).
- **Button** `Cập nhật dữ liệu` cho mỗi khách hàng (force refresh).
- **Panel EVN** (sidebar, chỉ admin): 6 tab — **Tổng quan** (metric + biểu đồ +
  thẻ ngừng điện), **Điện năng** (lọc khoảng, biểu đồ/bảng tháng/ngày),
  **Công tơ** (chỉ số mới/cũ, hệ số, bảng chỉ số), **Hóa đơn** (danh sách, tìm
  + lọc trạng thái, chi tiết + tải **PDF/bảng kê/thông báo**, lịch sử thanh
  toán), **Lịch ngừng điện**, **Thông tin** (KH, hợp đồng, điểm đo, ngân hàng).
  Theo theme sáng/tối HA, responsive tới 375px, điều hướng bàn phím.
- **Biểu đồ mới:** cột ba ngày gần nhất tại Tổng quan/Điện năng; cột ba kỳ
  điện năng theo tổng khách hàng; cột tiền hóa đơn ba kỳ tại Hóa đơn; đường
  chỉ số gốc ở Công tơ, chọn từng công tơ/bộ chỉ số. Có số và bảng đi kèm,
  xem bằng bàn phím; đường bị ngắt khi thiếu kỳ hoặc đổi công tơ.
- Không dùng `total_increasing` hay Energy Dashboard vì kỳ tháng không phải bộ
  đếm suốt đời và dữ liệu ngày có thể gộp nhiều ngày.

### Cách đọc sensor và biểu đồ

- “Kỳ này/trước/trước nữa” tương ứng nhãn tháng `NAM/THANG` do EVN trả,
  cộng các kỳ ghi điện cùng tháng; không khẳng định ngày đầu/cuối đúng tháng lịch.
- Ba ngày theo `Asia/Ho_Chi_Minh`; lấy `DIEN_TTHU` trực tiếp. Không chia một
  khoảng nhiều ngày thành các ngày giả và không suy điện năng từ hai chỉ số
  đọc tại giờ tùy ý. Hôm nay có thể chưa có dữ liệu hoặc chỉ là tạm tính.
- Chỉ số tạm chốt/cuối kỳ trước là **chỉ số gốc**; không tự nhân hệ số hay
  gắn kWh khi chưa xác minh ngữ nghĩa bộ chỉ số. Nếu không phân biệt được công
  tơ/bộ chỉ số, để unknown thay vì lấy số lớn nhất.
- Hóa đơn chưa có của tháng hiện tại là **unknown**, không phải hóa đơn 0 đồng.
  Hóa đơn trùng từ lịch sử/danh sách hiện tại được khử trùng theo ID; trạng thái
  đã thanh toán không bị tô thành chưa trả chỉ vì trường nợ thô còn giá trị.
- “Cập nhật lúc” là timestamp lịch polling thật; HA tự hiển thị tương đối như
  “sau … phút”. Không cố định thành 2 phút. Lịch cũng cập nhật khi lỗi mạng
  liên tiếp; xác thực thất bại có thể dừng lịch và yêu cầu reauth.
- Với 1 khách hàng/1 điểm đo: **34 sensors + 1 button + 3 binary sensor**.
  Một số sensor chẩn đoán nằm trong nhóm Diagnostics; giữ nguyên ID của bản trước.

## Kiến trúc

- `custom_components/evn_cskh/api.py`: aiohttp; login/refresh, cấu hình miền,
  danh sách khách hàng, chuyển ngữ cảnh token, các endpoint đọc (`diemdo`,
  `customers/info`, `diennangngay/thang`, `chisongay/thang`, `hoadon`,
  `lichsu-hoadon`, `thanhtoan/danhsach-nganhang`, `ngungcapdien`), tải PDF.
- `custom_components/evn_cskh/{sensor,button,binary_sensor}.py`: sensors, button refresh, lịch cắt điện.
- `custom_components/evn_cskh/brand/`: `icon.png`, `icon@2x.png`, `logo.png`, `logo@2x.png` (thương hiệu integration; không chứa thông tin riêng tư).
- `custom_components/evn_cskh/panel.py`: WebSocket (`evn_cskh/list_entries`,
  `overview`, `details`) và route tải PDF có xác thực (`requires_auth`), cache
  hóa đơn bằng key ngẫu nhiên, giới hạn kích thước/timeout.
- `custom_components/evn_cskh/frontend/evn-cskh-panel.js`: Web Component thuần,
  không React/Tailwind/CDN, dùng biến theme của HA.
- `custom_components/evn_cskh/{config_flow,coordinator,sensor,models,const}.py`.
- `poc/evn_cskh.py`: CLI độc lập Home Assistant.
- `tests/`: pytest offline + `frontend-panel.mjs` (Playwright, mock loopback).

## Cài đặt qua HACS

1. HACS → Integrations → ⋮ → Custom repositories.
2. Thêm `https://github.com/trankhanhduy2929-beep/EVN-CSKH-Homeassistant`,
   category **Integration**.
3. Cài **EVN CSKH**, restart Home Assistant.
4. Settings → Devices & services → Add integration → **EVN CSKH**; nhập tài
   khoản. Sau đó chọn khách hàng và chu kỳ cập nhật trong Options.
5. Mở panel **EVN CSKH** ở sidebar (chỉ tài khoản admin). Khi nâng cấp, restart
   HA rồi tải lại trình duyệt/app HA để nạp module biểu đồ mới; không cần xóa
   integration hay cấu hình lại tài khoản.

Cài thủ công: giải nén `dist/evn_cskh-0.5.1.zip` vào thư mục cấu hình HA rồi
restart. `dist/evn_cskh.zip` là layout cho HACS zip-release.

Yêu cầu **Home Assistant 2025.12 trở lên**. Poll mặc định 6 giờ (60–1440 phút).

## PoC dòng lệnh

```bash
.venv/bin/python -B poc/evn_cskh.py customers --session poc/session.json
.venv/bin/python -B poc/evn_cskh.py test --session poc/session.json
.venv/bin/python -B poc/evn_cskh.py login --session poc/session.json
```

Nhập tài khoản vào `poc/credentials.json` (quyền `600`, đã gitignore). Không
truyền mật khẩu trên dòng lệnh; không in token. `--save-raw` chỉ dùng khi cần
soi schema và tạo file riêng quyền `600`.

## Bảo mật và giới hạn

- Token chỉ nằm ở backend HA; panel tải PDF qua phiên HA có xác thực, không đưa
  token vào URL.
- Chưa kiểm chứng: rate limit, tài khoản miền khác, nhiều điểm đo/hóa đơn có nợ,
  đối chiếu số liệu với app, hành vi TLS trên thiết bị thật.
- Hóa đơn có mã thanh toán khác mã khách hàng đang chọn bị xử lý bảo thủ (có thể
  khiến snapshot unavailable) để tránh gán nhầm dữ liệu.
- Điểm đo mới hoặc đổi URL/danh sách khách hàng cần reload integration.
- Tài khoản chỉ VNeID/mật khẩu mặc định hoặc cần xác minh phải hoàn tất trong
  app EVN chính thức.

## Kiểm tra

```bash
.venv/bin/python -m pytest -q
ruff check custom_components poc tests build_release.py
.venv/bin/python -m mypy
node --check custom_components/evn_cskh/frontend/evn-cskh-panel.js
node tests/frontend-panel.mjs
.venv/bin/python build_release.py
```

Browser tests cần Playwright/Chromium đã cài; mặc định resolve `playwright` từ
môi trường project. Nếu dùng môi trường Node dùng chung, chỉ định
`EVN_PLAYWRIGHT_BASE=/duong-dan/toi/package.json` khi chạy script; không có
đường dẫn máy phát triển cố định trong runner. Tests chỉ chạy mock loopback,
không dùng tài khoản EVN thật hay HA điều khiển thiết bị.

Ảnh test là dữ liệu tổng hợp trong `analysis/ui-preview/` (không publish).
Chưa đánh giá thẩm mỹ trực tiếp từ ảnh; đã đo layout Shadow DOM tại 375/1280px,
light/dark, focus và kiểm tra các luồng. `analysis/REPORT.md` là báo cáo riêng
trong workspace phân tích, không nằm trong repository công khai.
