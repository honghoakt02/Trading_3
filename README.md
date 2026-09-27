# 📈 Hệ Thống Kiểm Định Chiến Lược Giao Dịch Định Lượng: Kết Hợp EMA & OBV

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Dự án xây dựng ứng dụng Web tương tác trên nền tảng **Streamlit Cloud** nhằm kiểm định, phân tích định lượng (Quantitative Backtesting) và trực quan hóa hiệu quả của chiến lược giao dịch kết hợp giữa hai chỉ báo kỹ thuật kinh điển:
- **Đường trung bình động lũy thừa (Exponential Moving Average - EMA)**
- **Khối lượng cân bằng (On-Balance Volume - OBV)**

Được chuẩn hóa dựa trên đề tài nghiên cứu: *"Hoàn thiện Framework Chiến lược EMA & OBV cho Cổ phiếu ACB"* với việc khắc phục triệt để các lỗi học thuật quan trọng: **Hạch toán vị thế (Position Accounting)**, **Phòng chống Look-ahead Bias** và **Đánh giá rủi ro Quá khớp (Overfitting)** giữa mẫu In-Sample (Train) và Out-of-Sample (Test).

---

## 🎯 1. Bối Cảnh Nghiên Cứu & Khắc Phục Góp Ý Của Giảng Viên

1. **Lỗi không hạch toán đúng vị thế giao dịch (Position Accounting):**
   - Thuật toán tối ưu hóa tham số (Hyperopt) chỉ dựa trên Sharpe Ratio mà không kiểm soát số lượng lệnh thực sự được mở.
   - Khi bộ tham số khiến hệ thống gần như không vào lệnh, phương sai lợi nhuận triệt tiêu ($\sigma \to 0$), làm xuất hiện hiện tượng **Sharpe Ratio bùng nổ thành vô cực (`Sharpe = inf`) hoặc `NaN`**.
   - **Cách giải quyết:** Bổ sung ràng buộc ngặt **`MIN_TRADES >= 5`** vào hàm mục tiêu; nếu số giao dịch không đạt ngưỡng thống kê tối thiểu, hệ thống sẽ loại bỏ bộ tham số đó.
2. **Khối xuất tín hiệu thực chiến không nhận biết trạng thái tài khoản:**
   - Tín hiệu kỹ thuật bản chất là tín hiệu trạng thái (duy trì nhiều phiên). Nếu không theo dõi tài khoản đang nắm giữ cổ phiếu hay tiền mặt, hệ thống có thể liên tục khuyến nghị MUA thêm (dù đã full vị thế) hoặc báo BÁN khống.
   - **Cách giải quyết:** Theo dõi biến vị thế `current_position` kết hợp với tín hiệu để xuất ra 4 hành động chuẩn xác: **MUA (BUY)**, **BÁN (SELL)**, **TIẾP TỤC NẮM GIỮ (HOLD)**, hoặc **ĐỨNG NGOÀI (STAND ASIDE)**.
3. **Triệt tiêu Look-ahead Bias & Chi phí ma sát:**
   - Áp dụng cơ chế **`shift(1)`** trên toàn bộ tín hiệu để đảm bảo quyết định phiên hôm nay chỉ sử dụng thông tin khi nến phiên hôm trước đã đóng cửa hoàn toàn.
   - Đưa vào mô phỏng đầy đủ: Phí giao dịch (0.2%), Trượt giá (0.1%) và Cắt lỗ cứng Stop-loss (7.0%).

---

## 📊 2. Quy Tắc Vào / Thoát Lệnh Của Chiến Lược

| Chiến Lược | Điều Kiện Mua (Entry Signal) | Điều Kiện Bán (Exit Signal) | Ghi Chú |
| :--- | :--- | :--- | :--- |
| **EMA Riêng Lẻ** | Giá đóng cửa vượt trên đường EMA: <br> `Close > EMA` | Giá đóng cửa rơi xuống dưới EMA: <br> `Close < EMA` | Đi theo xu hướng giá |
| **OBV Riêng Lẻ** | Độ dốc OBV dương qua $N$ phiên: <br> `OBV_Slope > 0` | Độ dốc OBV âm qua $N$ phiên: <br> `OBV_Slope < 0` | Xác nhận áp lực dòng tiền |
| **EMA + OBV Kết Hợp** | **Giá nằm trên EMA VÀ OBV dốc lên:** <br> `(Close > EMA) & (OBV_Slope > 0)` | **Giá cắt xuống dưới EMA:** <br> `Close < EMA` | Lọc bớt tín hiệu nhiễu (Whipsaw) |

*Mọi tín hiệu đều được dịch chuyển 1 phiên: `entries.shift(1)` và `exits.shift(1)`.*

---

## ⚖️ 3. Kết Quả Kiểm Định: Train (2014-2020) vs Test (2021-2023)

| Chiến Lược | Tập Dữ Liệu | Bộ Tham Số | Sharpe Ratio | Tổng Lợi Nhuận (%) | Max Drawdown (%) | Số Lệnh Đã Đóng |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **EMA Riêng lẻ** | **Train** (2014-2020) | EMA=36 | **1.0797** | **+211.97%** | -28.69% | 70 |
| **EMA Riêng lẻ** | **Test** (2021-2023) | EMA=36 | **-0.8601** | **-37.69%** | -59.19% | 41 |
| **OBV Riêng lẻ** | **Train** (2014-2020) | OBV=19 | **1.1735** | **+277.80%** | -30.46% | 51 |
| **OBV Riêng lẻ** | **Test** (2021-2023) | OBV=19 | **-0.6135** | **-38.73%** | -62.50% | 38 |
| **EMA + OBV Kết Hợp** | **Train** (2014-2020) | EMA=36, OBV=20 | **1.1514** | **+236.56%** | **-23.87%** *(Thấp nhất)* | 64 |
| **EMA + OBV Kết Hợp** | **Test** (2021-2023) | EMA=36, OBV=20 | **-0.8298** | **-36.47%** | -60.14% | 37 |
| *Benchmark Buy & Hold* | *Test* (2021-2023) | - | - | *+30.34%* | -45.10% | 1 |

---

## 📁 4. Cấu Trúc Thư Mục Cần Đẩy Lên GitHub

```text
├── app.py            # Mã nguồn chính Streamlit (Engine định lượng thuần NumPy/Pandas, không lỗi)
├── requirements.txt  # Thư viện phụ thuộc siêu nhẹ (streamlit, pandas, numpy, plotly)
├── ACB.csv           # File dữ liệu lịch sử giá cổ phiếu ACB (2014 - 2023)
└── README.md         # Hướng dẫn chi tiết dự án
```

---

## 🚀 5. Hướng Dẫn Cập Nhật GitHub & Deploy Lên Streamlit Cloud

1. **Cập nhật các file lên kho GitHub của bạn (repo `trading_1`):**
   - Tải lên (hoặc kéo thả đè) 2 file quan trọng:
     * `app.py`
     * `requirements.txt`
   - Đảm bảo file `ACB.csv` cũng nằm ở thư mục gốc của repository.
2. **Khởi động lại app trên Streamlit Cloud:**
   - Truy cập [share.streamlit.io](https://share.streamlit.io).
   - Chọn app của bạn, nhấn vào mục **Manage app** (góc dưới bên phải) -> Chọn **Reboot app** (hoặc Streamlit sẽ tự động re-deploy khi nhận commit mới từ GitHub).
   - Ứng dụng sẽ build thành công trong vòng vài giây mà không còn bất kỳ lỗi `ValueError` hay xung đột `vectorbt` nào!
