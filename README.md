# EVN CSKH — Home Assistant

Custom integration đọc dữ liệu **EVN CSKH thống nhất** (`com.evn.cskh.vn`,
app EVN toàn quốc) vào Home Assistant, kèm **bảng điều khiển EVN** trong sidebar
với lịch sử điện năng, chỉ số công tơ, hóa đơn và tải PDF hóa đơn.

Toàn bộ dự án nằm tại `/opt/apk-lab/input/evncskh/`; XAPK gốc được giữ nguyên
và không phát hành kèm.

## Trạng thái

- **v0.2.0 thử nghiệm.** Đã **đăng nhập, refresh token, đọc dữ liệu và tải hóa
  đơn PDF thật thành công** trên tài khoản EVNSPC (miền Nam).
- Qua **1.412 pytest** (offline + runtime HA 2025.12.5 với API giả lập) và
  **17 kiểm thử giao diện Playwright** trên mock loopback.
- **Chưa đối chiếu từng số liệu với app** và **chưa chạy trên HA production**.

## Tính năng

- Đăng nhập tài khoản EVN CSKH thống nhất; tự chọn miền theo cấu hình server
  (`PB` = EVNSPC, `PC` = EVNCPC, `PA` = NPC, `HN`, `PE`), không đoán theo prefix.
- Sensors mỗi điểm đo: điện năng kỳ tháng gần nhất, khoảng ghi nhận gần nhất (kWh).
- Sensors mỗi khách hàng: tiền/số hóa đơn chưa thanh toán, lịch ngừng cấp điện
  dự kiến gần nhất, lần cập nhật thành công.
- **Panel EVN** (sidebar, chỉ admin): Tổng quan, Điện năng (biểu đồ + bảng số,
  khoảng lọc), Hóa đơn (lọc/tìm, chi tiết, tải PDF/bảng kê/thông báo), Lịch
  ngừng điện. Theo theme sáng/tối của HA, responsive tới 375px.
- Không dùng `total_increasing` hay Energy Dashboard vì kỳ tháng không phải bộ
  đếm suốt đời và dữ liệu ngày có thể gộp nhiều ngày.

## Kiến trúc

- `custom_components/evn_cskh/api.py`: aiohttp; login/refresh, cấu hình miền,
  danh sách khách hàng, chuyển ngữ cảnh token, các endpoint đọc (`diemdo`,
  `diennangngay/thang`, `chisongay/thang`, hóa đơn, lịch ngừng điện), tải PDF.
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
5. Mở panel **EVN CSKH** ở sidebar (chỉ tài khoản admin).

Cài thủ công: giải nén `dist/evn_cskh-0.2.0.zip` vào thư mục cấu hình HA rồi
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
node tests/frontend-panel.mjs
.venv/bin/python build_release.py
```

Xem thêm `analysis/REPORT.md` cho bằng chứng reverse-engineer theo file/dòng.
