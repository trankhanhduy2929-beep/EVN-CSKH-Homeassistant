# EVN CSKH — Home Assistant

Tích hợp đọc dữ liệu **EVN CSKH thống nhất** vào Home Assistant, kèm bảng điều
khiển trong sidebar để xem điện năng, chỉ số công tơ, hóa đơn và lịch ngừng điện.

## Tính năng

- Đăng nhập tài khoản EVN CSKH; tự chọn miền theo cấu hình server.
- **Sensor theo điểm đo:** sản lượng tháng gần nhất/trước đó, % thay đổi,
  trung bình 12 tháng, chỉ số công tơ, hệ số nhân, ngày ghi.
- **Sensor theo khách hàng:** tiền và số hóa đơn chưa thanh toán, hóa đơn gần
  nhất, số hóa đơn đã trả, lịch ngừng điện, lần cập nhật gần nhất.
- **Sensor chi tiết:** tiêu thụ hôm nay/hôm qua/hôm kia, chỉ số tạm chốt, chỉ số
  cuối kỳ trước, tiền và điện năng ba kỳ gần nhất, hóa đơn năm nay.
- **Lịch ngừng điện:** binary sensor lịch sắp tới, đang diễn ra, sắp bắt đầu
  trong 24 giờ, kèm thời gian, khu vực, lý do và số giờ mất điện.
- **Button Cập nhật dữ liệu** cho mỗi khách hàng.
- **Panel 6 tab:** Tổng quan, Điện năng, Công tơ, Hóa đơn, Lịch ngừng điện,
  Thông tin. Hỗ trợ theme sáng/tối, mobile và điều hướng bàn phím.
- **Biểu đồ tự động:** 30 ngày, 12 tháng và tối đa 5 năm; kiểu Cột/Sóng, màu
  riêng, thống kê Tổng/Trung bình/Cao nhất, animation.
- **Hóa đơn:** tìm kiếm, lọc trạng thái và năm, xem chi tiết, tải PDF hóa đơn,
  bảng kê và thông báo.

## Cài đặt

### Qua HACS

1. HACS → Integrations → ⋮ → **Custom repositories**.
2. Thêm `https://github.com/trankhanhduy2929-beep/EVN-CSKH-Homeassistant`,
   category **Integration**.
3. Cài **EVN CSKH**, sau đó restart Home Assistant.
4. Settings → Devices & services → **Add integration** → **EVN CSKH**.
5. Nhập tài khoản EVN, chọn khách hàng và chu kỳ cập nhật trong Options.

### Thủ công

Tải file ZIP mới nhất trong mục **Releases**, giải nén vào thư mục cấu hình
Home Assistant rồi restart. Với HACS, dùng file `evn_cskh.zip`.

### Sau khi cài

- Mở **EVN CSKH** ở sidebar (chỉ tài khoản admin).
- Khi nâng cấp: restart HA và tải lại trình duyệt/app để nạp giao diện mới.

Yêu cầu **Home Assistant 2025.12 trở lên**. Chu kỳ cập nhật mặc định 6 giờ
(60–1440 phút).

## Hướng dẫn sử dụng

### Tổng quan

Hiển thị điện năng tháng này, mức tăng/giảm, khoản cần xử lý, KPI, so sánh
ngày/tháng và biểu đồ sản lượng, chi phí. Dữ liệu 5 năm được tải tự động, không
cần bấm nút. Chọn **Cột** hoặc **Sóng** để đổi kiểu biểu đồ tháng/năm.

### Điện năng

- Chọn điểm đo và khoảng ngày (tối đa 5 năm; dữ liệu ngày tối đa 31 ngày).
- Xem biểu đồ và bảng theo tháng/ngày.
- Nút **Tải dữ liệu** làm mới lịch sử; dữ liệu gần đây được cache trong 5 phút.

### Công tơ

Xem chỉ số mới/cũ, hệ số nhân, ngày ghi và biểu đồ chỉ số theo từng công tơ,
bộ chỉ số.

### Hóa đơn

- Tìm theo kỳ hoặc mã hóa đơn, lọc trạng thái thanh toán và năm.
- Chọn một hóa đơn để xem chi tiết và tải PDF hóa đơn, bảng kê, thông báo.
- Biểu đồ chi phí hiển thị theo năm hoặc 12 tháng của năm đã chọn.

### Lịch ngừng điện và Thông tin

- **Lịch ngừng điện:** các đợt cắt điện dự kiến, thời gian và khu vực.
- **Thông tin:** khách hàng, hợp đồng, điểm đo và ngân hàng.

### Cách đọc số liệu

- Ngày/tháng EVN chưa công bố được giữ **unknown**, không đổi thành 0.
- Tháng hiện tại có thể là số **tạm tính** từ các ngày đã có.
- “Kỳ này/trước/trước nữa” theo nhãn tháng EVN trả về, không phải ngày đầu/cuối
  tháng lịch.
- Hóa đơn chưa có của tháng hiện tại là unknown, không phải hóa đơn 0 đồng.
- Hóa đơn trùng được khử theo ID; trạng thái thanh toán lấy theo trạng thái EVN,
  không suy từ trường nợ thô.

### Automation với lịch ngừng điện

Dùng các entity `binary_sensor.outage_scheduled`, `outage_soon`, `outage_active`
và các sensor `next_outage`, `next_outage_end`, `next_outage_duration`,
`next_outage_area`, `next_outage_reason`, `outage_count`.

## Lưu ý

- Tài khoản cần xác minh VNeID hoặc bước bảo mật phải hoàn tất trong app EVN
  chính thức trước khi dùng tích hợp.
- Thêm điểm đo mới hoặc đổi danh sách khách hàng cần reload integration.
- Panel chỉ dành cho tài khoản admin; token được giữ ở backend Home Assistant.
