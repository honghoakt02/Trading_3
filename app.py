# -*- coding: utf-8 -*-
"""
HỆ THỐNG KIỂM ĐỊNH CHIẾN LƯỢC GIAO DỊCH: KẾT HỢP EMA VÀ OBV
Ứng dụng Web Định lượng trên nền tảng Streamlit Cloud
Phát triển dựa trên nghiên cứu: "Hoàn thiện Framework Chiến lược EMA & OBV cho Cổ phiếu ACB"
"""

import os
import io
import warnings
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Bỏ qua các cảnh báo không cần thiết
warnings.filterwarnings('ignore')

# Cố gắng import ta nếu có (nếu không có sẽ dùng engine toán học nội bộ thuần NumPy/Pandas)
try:
    import ta
    HAS_TA = True
except Exception:
    HAS_TA = False

# ==============================================================================
# CẤU HÌNH TRANG STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Kiểm Định Chiến Lược EMA & OBV | Cổ Phiếu ACB",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện chuẩn Fintech chuyên nghiệp
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .badge-container {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 1.2rem;
    }
    .tech-badge {
        background-color: #EFF6FF;
        color: #1D4ED8;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid #DBEAFE;
    }
    .metric-card {
        background-color: #FFFFFF;
        padding: 16px 18px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        margin-bottom: 12px;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 4px 0;
        color: #111827;
    }
    .signal-box-buy {
        background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
        border: 1px solid #10B981;
        border-left: 6px solid #059669;
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
    }
    .signal-box-sell {
        background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
        border: 1px solid #EF4444;
        border-left: 6px solid #DC2626;
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
    }
    .signal-box-hold {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border: 1px solid #3B82F6;
        border-left: 6px solid #2563EB;
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
    }
    .signal-box-cash {
        background: linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%);
        border: 1px solid #D1D5DB;
        border-left: 6px solid #9CA3AF;
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# HÀM NẠP & XỬ LÝ DỮ LIỆU
# ==============================================================================
@st.cache_data
def load_data(uploaded_file=None):
    """Đọc và xử lý dữ liệu giá lịch sử cổ phiếu."""
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Lỗi khi đọc file tải lên: {e}")
            return None
    else:
        # Đường dẫn tìm kiếm file ACB.csv
        file_candidates = ['ACB.csv', './ACB.csv', '../ACB.csv', os.path.join(os.path.dirname(__file__), 'ACB.csv')]
        csv_path = None
        for p in file_candidates:
            if os.path.exists(p):
                csv_path = p
                break
        
        if csv_path is None:
            # Tìm đệ quy trong thư mục làm việc
            for root, dirs, files in os.walk('.'):
                if 'ACB.csv' in files:
                    csv_path = os.path.join(root, 'ACB.csv')
                    break

        if csv_path and os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
        else:
            st.error("Không tìm thấy file ACB.csv. Vui lòng tải file lên ở thanh bên.")
            return None

    # Tìm kiếm cột ngày tháng
    date_col = None
    for col in df.columns:
        c_low = col.lower().strip()
        if 'date' in c_low or 'ngay' in c_low or 'ngày' in c_low:
            date_col = col
            break

    if date_col is None:
        st.error("Không tìm thấy cột Ngày (Date) trong dữ liệu.")
        return None

    df['Date'] = pd.to_datetime(df[date_col])
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)

    # Chuẩn hóa tên cột
    col_mapping = {}
    for col in df.columns:
        c_lower = col.lower().strip()
        if 'close' in c_lower or 'dongcua' in c_lower or 'đóng cửa' in c_lower:
            col_mapping[col] = 'Close'
        elif 'open' in c_lower or 'mocua' in c_lower or 'mở cửa' in c_lower:
            col_mapping[col] = 'Open'
        elif 'high' in c_lower or 'caonhat' in c_lower or 'cao nhất' in c_lower:
            col_mapping[col] = 'High'
        elif 'low' in c_lower or 'thapnhat' in c_lower or 'thấp nhất' in c_lower:
            col_mapping[col] = 'Low'
        elif 'volume' in c_lower or 'khoiluong' in c_lower or 'khối lượng' in c_lower or 'vol' in c_lower:
            col_mapping[col] = 'Volume'

    df.rename(columns=col_mapping, inplace=True)

    if 'Close' not in df.columns:
        st.error("Dữ liệu cần tối thiểu cột giá đóng cửa 'Close'.")
        return None

    if 'Volume' not in df.columns:
        df['Volume'] = 1000000.0

    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)
    df.dropna(subset=['Close'], inplace=True)

    return df

# ==============================================================================
# HÀM TÍNH CHỈ BÁO KỸ THUẬT & TÍN HIỆU
# ==============================================================================
def calculate_indicators(df, ema_period=20, obv_slope_period=3):
    """
    Tính toán các chỉ báo EMA, OBV và Độ dốc OBV (OBV Slope).
    Đồng bộ chuẩn 100% với notebook nghiên cứu.
    """
    data = df.copy()
    close = data['Close']
    volume = data['Volume']

    # 1. Tính EMA
    if HAS_TA:
        ema = ta.trend.ema_indicator(close, window=int(ema_period))
    else:
        ema = close.ewm(span=int(ema_period), adjust=False).mean()

    # 2. Tính OBV
    if HAS_TA:
        obv = ta.volume.on_balance_volume(close, volume)
    else:
        # Triển khai OBV thuần Python/Pandas siêu tốc
        price_diff = close.diff()
        direction = np.where(price_diff > 0, 1, np.where(price_diff < 0, -1, 0))
        direction[0] = 0
        obv = pd.Series((volume.values * direction).cumsum(), index=close.index)

    # 3. Tính độ dốc OBV (OBV Slope) = OBV[t] - OBV[t - obv_slope_period]
    obv_slope = obv.diff(int(obv_slope_period))

    data['EMA'] = ema
    data['OBV'] = obv
    data['OBV_Slope'] = obv_slope

    return data


def generate_all_signals(data, ema_period, obv_slope_period):
    """
    Tạo tín hiệu mua/bán cho cả 3 chiến lược:
    1. EMA Riêng lẻ
    2. OBV Riêng lẻ
    3. EMA + OBV Kết hợp

    QUAN TRỌNG: Tất cả tín hiệu đều được shift(1) để loại bỏ Look-ahead bias,
    nghĩa là quyết định giao dịch cho phiên hôm nay chỉ dùng dữ liệu của phiên trước.
    """
    close = data['Close']
    ema = data['EMA']
    obv_slope = data['OBV_Slope']

    # --- Chiến lược 1: EMA Riêng lẻ ---
    raw_entries_ema = (close > ema)
    raw_exits_ema = (close < ema)
    entries_ema = raw_entries_ema.shift(1, fill_value=False)
    exits_ema = raw_exits_ema.shift(1, fill_value=False)

    # --- Chiến lược 2: OBV Riêng lẻ ---
    raw_entries_obv = (obv_slope > 0)
    raw_exits_obv = (obv_slope < 0)
    entries_obv = raw_entries_obv.shift(1, fill_value=False)
    exits_obv = raw_exits_obv.shift(1, fill_value=False)

    # --- Chiến lược 3: EMA + OBV Kết hợp ---
    raw_entries_comb = (close > ema) & (obv_slope > 0)
    raw_exits_comb = (close < ema)
    entries_comb = raw_entries_comb.shift(1, fill_value=False)
    exits_comb = raw_exits_comb.shift(1, fill_value=False)

    signals_dict = {
        'EMA': (entries_ema, exits_ema),
        'OBV': (entries_obv, exits_obv),
        'Combined': (entries_comb, exits_comb)
    }
    return signals_dict

# ==============================================================================
# ĐỘNG CƠ BACKTEST ĐỊNH LƯỢNG NỘI BỘ (POSITION ACCOUNTING SIMULATOR)
# ==============================================================================
def run_backtest_engine(data, entries, exits, initial_capital=100_000_000, 
                        fees=0.002, slippage=0.001, sl_stop=0.07):
    """
    Động cơ mô phỏng giao dịch định lượng chuẩn xác có hạch toán vị thế (Position Accounting):
    - Long-only, không nhồi lệnh (accumulate=False, 1 position tại một thời điểm)
    - Phí giao dịch 2 chiều (fees)
    - Trượt giá (slippage)
    - Cắt lỗ cứng (Stop-loss sl_stop, mặc định 7%)
    - Tạo bảng nhật ký lệnh (Trade Log) chi tiết
    """
    n = len(data)
    close = data['Close'].values
    dates = data.index

    # Chuỗi theo dõi
    positions = np.zeros(n, dtype=int)       # 0: Tiền mặt, 1: Nắm giữ cổ phiếu
    cash = np.zeros(n, dtype=float)
    holdings = np.zeros(n, dtype=float)
    equity = np.zeros(n, dtype=float)
    buy_orders = np.zeros(n, dtype=bool)
    sell_orders = np.zeros(n, dtype=bool)

    current_cash = float(initial_capital)
    current_shares = 0.0
    current_position = 0
    entry_price = 0.0
    entry_date = None

    trades = []

    for i in range(n):
        c_price = close[i]
        is_entry = entries.iloc[i]
        is_exit = exits.iloc[i]

        # Kiểm tra điều kiện Stop Loss trong phiên (nếu đang giữ vị thế)
        sl_triggered = False
        if current_position == 1 and sl_stop is not None and sl_stop > 0:
            if c_price <= entry_price * (1.0 - sl_stop):
                sl_triggered = True

        # Quyết định hành động
        if current_position == 0:
            if is_entry:
                # MỞ VỊ THẾ MUA (ENTRY)
                eff_buy_price = c_price * (1.0 + slippage)
                cost_per_share = eff_buy_price * (1.0 + fees)
                if current_cash > cost_per_share:
                    current_shares = current_cash / cost_per_share
                    current_cash = 0.0
                    current_position = 1
                    entry_price = eff_buy_price
                    entry_date = dates[i]
                    buy_orders[i] = True
        elif current_position == 1:
            if is_exit or sl_triggered:
                # ĐÓNG VỊ THẾ BÁN (EXIT / STOP LOSS)
                exec_price = entry_price * (1.0 - sl_stop) if sl_triggered else c_price
                eff_sell_price = exec_price * (1.0 - slippage)
                gross_revenue = current_shares * eff_sell_price
                net_revenue = gross_revenue * (1.0 - fees)
                
                # Ghi nhận nhật ký lệnh
                pnl_pct = ((eff_sell_price / entry_price) - 1.0) * 100.0 - (fees * 2 * 100.0)
                pnl_val = net_revenue - (entry_price * current_shares * (1.0 + fees))
                holding_days = (dates[i] - entry_date).days

                trades.append({
                    'Order ID': len(trades) + 1,
                    'Entry Date': entry_date,
                    'Entry Price': round(entry_price, 1),
                    'Exit Date': dates[i],
                    'Exit Price': round(eff_sell_price, 1),
                    'Holding Days': holding_days,
                    'PnL (%)': round(pnl_pct, 2),
                    'PnL (VND)': round(pnl_val, 0),
                    'Exit Reason': 'Stop Loss (7%)' if sl_triggered else 'Tín hiệu EMA cắt'
                })

                current_cash = net_revenue
                current_shares = 0.0
                current_position = 0
                entry_price = 0.0
                entry_date = None
                sell_orders[i] = True

        positions[i] = current_position
        cash[i] = current_cash
        holdings[i] = current_shares
        equity[i] = current_cash + (current_shares * c_price)

    # Chuyển đổi thành Series và DataFrame
    equity_series = pd.Series(equity, index=dates)
    positions_series = pd.Series(positions, index=dates)
    buy_series = pd.Series(buy_orders, index=dates)
    sell_series = pd.Series(sell_orders, index=dates)

    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
    else:
        trades_df = pd.DataFrame(columns=[
            'Order ID', 'Entry Date', 'Entry Price', 'Exit Date', 'Exit Price',
            'Holding Days', 'PnL (%)', 'PnL (VND)', 'Exit Reason'
        ])

    # --- TÍNH TOÁN CÁC CHỈ SỐ ĐỊNH LƯỢNG (PERFORMANCE METRICS) ---
    total_return_pct = ((equity[-1] / initial_capital) - 1.0) * 100.0
    daily_returns = equity_series.pct_change().dropna()
    
    days_count = len(data)
    years = max(days_count / 252.0, 0.01)
    cagr_pct = (((equity[-1] / initial_capital) ** (1.0 / years)) - 1.0) * 100.0 if equity[-1] > 0 else -100.0

    # Sharpe Ratio (tần suất ngày freq='D', 252 ngày/năm)
    if len(daily_returns) > 0 and daily_returns.std() > 1e-9:
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0

    # Sortino Ratio (Downside deviation)
    negative_returns = daily_returns[daily_returns < 0]
    if len(negative_returns) > 0 and negative_returns.std() > 1e-9:
        sortino_ratio = (daily_returns.mean() / negative_returns.std()) * np.sqrt(252)
    else:
        sortino_ratio = 0.0

    # Max Drawdown
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax
    max_drawdown_pct = abs(float(drawdown.min())) * 100.0

    # Calmar Ratio
    calmar_ratio = (cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else 0.0

    # Thống kê giao dịch
    num_trades = len(trades_df)
    if num_trades > 0:
        winning_trades = trades_df[trades_df['PnL (%)'] > 0]
        losing_trades = trades_df[trades_df['PnL (%)'] <= 0]
        win_rate_pct = (len(winning_trades) / num_trades) * 100.0
        
        total_win = winning_trades['PnL (VND)'].sum()
        total_loss = abs(losing_trades['PnL (VND)'].sum())
        profit_factor = (total_win / total_loss) if total_loss > 0 else (np.inf if total_win > 0 else 0.0)
        
        avg_win_pct = winning_trades['PnL (%)'].mean() if len(winning_trades) > 0 else 0.0
        avg_loss_pct = losing_trades['PnL (%)'].mean() if len(losing_trades) > 0 else 0.0
        avg_holding_days = trades_df['Holding Days'].mean()
    else:
        win_rate_pct = 0.0
        profit_factor = 0.0
        avg_win_pct = 0.0
        avg_loss_pct = 0.0
        avg_holding_days = 0.0

    # Tỷ lệ nắm giữ vị thế (Position Coverage %)
    position_coverage_pct = (positions_series.sum() / len(positions_series)) * 100.0

    metrics = {
        'Total Return [%]': total_return_pct,
        'CAGR [%]': cagr_pct,
        'Sharpe Ratio': sharpe_ratio,
        'Sortino Ratio': sortino_ratio,
        'Calmar Ratio': calmar_ratio,
        'Max Drawdown [%]': max_drawdown_pct,
        'Total Closed Trades': num_trades,
        'Win Rate [%]': win_rate_pct,
        'Profit Factor': profit_factor,
        'Avg Win [%]': avg_win_pct,
        'Avg Loss [%]': avg_loss_pct,
        'Avg Holding Days': avg_holding_days,
        'Position Coverage [%]': position_coverage_pct,
        'Initial Capital': initial_capital,
        'End Equity': equity[-1]
    }

    return {
        'metrics': metrics,
        'equity_curve': equity_series,
        'drawdown': drawdown,
        'positions': positions_series,
        'buy_orders': buy_series,
        'sell_orders': sell_series,
        'trades_df': trades_df
    }

# ==============================================================================
# THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR CONTROLS)
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bullish.png", width=64)
    st.title("Bảng Điều Khiển")
    st.caption("Chiến lược EMA & OBV | Quản trị Vị thế")
    st.markdown("---")

    # 1. Nguồn Dữ Liệu
    st.subheader("1. Nguồn Dữ Liệu")
    data_source = st.radio("Chọn tập dữ liệu:", ["Dữ liệu mẫu ACB.csv (2014 - 2023)", "Tải lên file CSV tùy chỉnh"], index=0)
    uploaded_file = None
    if data_source == "Tải lên file CSV tùy chỉnh":
        uploaded_file = st.file_uploader("Chọn file CSV (Cần cột: Date, Close, Volume):", type=["csv"])

    df_raw = load_data(uploaded_file)
    if df_raw is None:
        st.stop()

    st.success(f"Đã nạp {len(df_raw)} phiên: {df_raw.index.min().strftime('%d/%m/%Y')} → {df_raw.index.max().strftime('%d/%m/%Y')}")

    # 2. Phân Chia Tập Dữ Liệu Train / Test
    st.subheader("2. Phân Chia Dữ Liệu")
    min_date = df_raw.index.min().date()
    max_date = df_raw.index.max().date()
    
    default_split = pd.to_datetime('2020-12-31').date() if min_date <= pd.to_datetime('2020-12-31').date() <= max_date else min_date + (max_date - min_date) * 0.7
    split_date = st.date_input(
        "Ngày phân tách Train / Test:",
        value=default_split,
        min_value=min_date,
        max_value=max_date,
        help="Dữ liệu trước ngày này thuộc tập Huấn luyện (Train). Sau ngày này thuộc tập Kiểm định (Test)."
    )

    train_df = df_raw.loc[:str(split_date)].copy()
    test_df = df_raw.loc[str(split_date + pd.Timedelta(days=1)):].copy()

    if len(train_df) < 30 or len(test_df) < 10:
        st.error("Khoảng thời gian Train hoặc Test quá ngắn. Vui lòng chọn lại ngày phân tách!")
        st.stop()

    # 3. Cấu hình tham số chiến lược
    st.subheader("3. Thiết Lập Tham Số")
    param_mode = st.selectbox(
        "Chọn chế độ tham số:",
        ["Tham số tối ưu trên Train (Notebook)", "Tham số mặc định (Default)", "Tự tinh chỉnh thủ công"],
        index=0
    )

    if param_mode == "Tham số tối ưu trên Train (Notebook)":
        ema_param = 36
        obv_param = 20
        st.caption("⚡ *Tối ưu hóa: EMA = 36, OBV Slope = 20 (Kết hợp) / 19 (OBV riêng)*")
    elif param_mode == "Tham số mặc định (Default)":
        ema_param = 20
        obv_param = 3
        st.caption("⚡ *Mặc định: EMA = 20, OBV Slope = 3*")
    else:
        ema_param = st.slider("Chu kỳ EMA (EMA Period):", 5, 100, 36)
        obv_param = st.slider("Chu kỳ dốc OBV (OBV Slope):", 2, 40, 20)

    # 4. Quản trị rủi ro & Chi phí
    st.subheader("4. Quản Trị Rủi Ro & Vốn")
    init_cap = st.number_input("Vốn khởi điểm (VNĐ):", min_value=1_000_000, value=100_000_000, step=10_000_000)
    fee_rate = st.number_input("Phí giao dịch (%):", min_value=0.0, max_value=2.0, value=0.2, step=0.05) / 100.0
    slip_rate = st.number_input("Trượt giá Slippage (%):", min_value=0.0, max_value=2.0, value=0.1, step=0.05) / 100.0
    stop_loss_pct = st.number_input("Cắt lỗ Stop Loss (%):", min_value=1.0, max_value=20.0, value=7.0, step=0.5) / 100.0

# ==============================================================================
# TÍNH TOÁN DỮ LIỆU ĐỒNG LOẠT
# ==============================================================================
# 1. Tính toán chỉ báo trên toàn bộ dữ liệu, Train và Test
df_calculated = calculate_indicators(df_raw, ema_param, obv_param)
train_calc = calculate_indicators(train_df, ema_param, obv_param)
test_calc = calculate_indicators(test_df, ema_param, obv_param)

# 2. Tạo tín hiệu
signals_full = generate_all_signals(df_calculated, ema_param, obv_param)
signals_train = generate_all_signals(train_calc, ema_param, obv_param)
signals_test = generate_all_signals(test_calc, ema_param, obv_param)

# 3. Chạy backtest trên Train
bt_ema_train = run_backtest_engine(train_calc, signals_train['EMA'][0], signals_train['EMA'][1], init_cap, fee_rate, slip_rate, stop_loss_pct)
bt_obv_train = run_backtest_engine(train_calc, signals_train['OBV'][0], signals_train['OBV'][1], init_cap, fee_rate, slip_rate, stop_loss_pct)
bt_comb_train = run_backtest_engine(train_calc, signals_train['Combined'][0], signals_train['Combined'][1], init_cap, fee_rate, slip_rate, stop_loss_pct)

# 4. Chạy backtest trên Test
bt_ema_test = run_backtest_engine(test_calc, signals_test['EMA'][0], signals_test['EMA'][1], init_cap, fee_rate, slip_rate, stop_loss_pct)
bt_obv_test = run_backtest_engine(test_calc, signals_test['OBV'][0], signals_test['OBV'][1], init_cap, fee_rate, slip_rate, stop_loss_pct)
bt_comb_test = run_backtest_engine(test_calc, signals_test['Combined'][0], signals_test['Combined'][1], init_cap, fee_rate, slip_rate, stop_loss_pct)

# 5. Chạy backtest trên Toàn bộ dữ liệu (để hiển thị tín hiệu & khuyến nghị thực chiến phiên hiện tại)
bt_comb_full = run_backtest_engine(df_calculated, signals_full['Combined'][0], signals_full['Combined'][1], init_cap, fee_rate, slip_rate, stop_loss_pct)

# ==============================================================================
# TIÊU ĐỀ TRANG VÀ BADGE
# ==============================================================================
st.markdown('<div class="main-title">📈 HỆ THỐNG KIỂM ĐỊNH CHIẾN LƯỢC EMA & OBV</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Mô hình định lượng kết hợp Xu hướng (EMA) và Dòng tiền (OBV) có Hạch toán Vị thế & Triệt tiêu Look-ahead Bias</div>', unsafe_allow_html=True)

st.markdown("""
<div class="badge-container">
    <span class="tech-badge">📊 Cổ phiếu ACB</span>
    <span class="tech-badge">⚡ Streamlit Cloud Native</span>
    <span class="tech-badge">🛡️ Triệt tiêu Look-ahead Bias [shift(1)]</span>
    <span class="tech-badge">💼 Hạch toán Vị thế (Position Accounting)</span>
    <span class="tech-badge">🛑 Cắt lỗ Stop Loss (7%)</span>
    <span class="tech-badge">⚖️ Kiểm định Mẫu độc lập (Train vs Test)</span>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# BỐ CỤC 5 TABS CHỨC NĂNG
# ==============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Tín Hiệu & Khuyến Nghị Thực Chiến",
    "⚖️ Kiểm Định Hiệu Quả (Train vs Test)",
    "📝 Quản Lý Vị Thế & Nhật Ký Lệnh",
    "🎯 Tối Ưu Hóa Tham Số & Độ Nhạy",
    "📚 Phương Pháp Luận & Khắc Phục Lỗi"
])

# ==============================================================================
# TAB 1: TÍN HIỆU & BIỂU ĐỒ KỸ THUẬT
# ==============================================================================
with tab1:
    st.subheader("Trạng Thái Vị Thế & Khuyến Nghị Phiên Mới Nhất")

    # Thông tin phiên cuối cùng
    last_date = df_calculated.index[-1].strftime('%d/%m/%Y')
    last_close = df_calculated['Close'].iloc[-1]
    prev_close = df_calculated['Close'].iloc[-2]
    price_change = last_close - prev_close
    price_change_pct = (price_change / prev_close) * 100.0

    last_ema = df_calculated['EMA'].iloc[-1]
    last_obv_slope = df_calculated['OBV_Slope'].iloc[-1]
    last_position = bt_comb_full['positions'].iloc[-1]  # 0 hoặc 1

    last_entry_signal = signals_full['Combined'][0].iloc[-1]
    last_exit_signal = signals_full['Combined'][1].iloc[-1]

    # Xác định khuyến nghị hành động thực chiến
    if last_position == 1:
        if last_exit_signal:
            rec_action = "🔴 KHUYẾN NGHỊ BÁN (SELL)"
            rec_detail = "Giá đã giảm xuống dưới đường EMA. Kích hoạt tín hiệu đóng vị thế bảo toàn vốn."
            box_class = "signal-box-sell"
        else:
            rec_action = "🟡 TIẾP TỤC NẮM GIỮ (HOLD)"
            rec_detail = f"Tài khoản đang giữ cổ phiếu. Giá ({last_close:,.0f}) vẫn duy trì trên đường EMA ({last_ema:,.1f})."
            box_class = "signal-box-hold"
    else:
        if last_entry_signal:
            rec_action = "🟢 KHUYẾN NGHỊ MUA (BUY)"
            rec_detail = f"Điều kiện thỏa mãn: Giá vượt trên EMA ({last_ema:,.1f}) VÀ Độ dốc OBV dương ({last_obv_slope:+,.0f}). Mở vị thế mới."
            box_class = "signal-box-buy"
        else:
            rec_action = "⚪ ĐỨNG NGOÀI THỊ TRƯỜNG (STAND ASIDE / CASH)"
            rec_detail = "Chưa hội đủ tín hiệu đồng thuận từ cả EMA và OBV. Giữ tiền mặt để quản trị rủi ro."
            box_class = "signal-box-cash"

    # Hiển thị Callout Box Khuyến nghị
    st.markdown(f"""
    <div class="{box_class}">
        <div style="font-size: 1.25rem; font-weight: 700; margin-bottom: 4px;">{rec_action} (Phiên ngày {last_date})</div>
        <div style="font-size: 0.95rem; margin-bottom: 8px;">{rec_detail}</div>
        <div style="font-size: 0.85rem; color: #4B5563;">
            <b>Trạng thái tài khoản:</b> {'Đang nắm giữ cổ phiếu (Long 100%)' if last_position == 1 else 'Đang nắm giữ tiền mặt (Cash 100%)'} |
            <b>Giá đóng cửa:</b> {last_close:,.0f} VND ({price_change_pct:+.2f}%) |
            <b>Đường EMA({ema_param}):</b> {last_ema:,.1f} |
            <b>Độ dốc OBV({obv_param}):</b> {last_obv_slope:+,.0f}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Bộ lọc hiển thị thời gian cho biểu đồ
    st.markdown("##### 📈 Biểu Đồ Kỹ Thuật Tương Tác (Giá, EMA, Tín Hiệu & OBV)")
    timeframe_choice = st.radio(
        "Khoảng thời gian hiển thị:",
        ["Tất cả (2014 - 2023)", "Tập Test (2021 - 2023)", "1 Năm gần nhất"],
        horizontal=True
    )
    
    if timeframe_choice == "Tất cả (2014 - 2023)":
        plot_df = df_calculated.copy()
    elif timeframe_choice == "Tập Test (2021 - 2023)":
        plot_df = test_calc.copy()
    else:
        one_year_ago = df_calculated.index[-1] - pd.DateOffset(years=1)
        plot_df = df_calculated.loc[df_calculated.index >= one_year_ago].copy()

    # Lấy lệnh mua/bán tương ứng
    plot_buys = bt_comb_full['buy_orders'].loc[plot_df.index]
    plot_sells = bt_comb_full['sell_orders'].loc[plot_df.index]

    # Vẽ Subplots bằng Plotly
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.68, 0.32],
        subplot_titles=(f"Đồ thị Giá ACB & Đường EMA({ema_param}) kèm Điểm Khớp Lệnh", f"Chỉ báo On-Balance Volume (OBV) & Độ Dốc ({obv_param} phiên)")
    )

    # 1. Đường giá Close
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df['Close'], mode='lines', name='Giá Đóng Cửa',
                   line=dict(color='#1E3A8A', width=1.5)),
        row=1, col=1
    )

    # 2. Đường EMA
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df['EMA'], mode='lines', name=f'EMA ({ema_param})',
                   line=dict(color='#F59E0B', width=1.8, dash='dash')),
        row=1, col=1
    )

    # 3. Điểm Mua (Buy Orders)
    buy_points = plot_df.loc[plot_buys]
    if len(buy_points) > 0:
        fig.add_trace(
            go.Scatter(
                x=buy_points.index, y=buy_points['Close'] * 0.98,
                mode='markers', name='Điểm MUA',
                marker=dict(symbol='triangle-up', size=11, color='#10B981', line=dict(width=1, color='#047857')),
                text=[f"MUA: {p:,.0f} VND" for p in buy_points['Close']],
                hoverinfo='text+x'
            ),
            row=1, col=1
        )

    # 4. Điểm Bán (Sell Orders)
    sell_points = plot_df.loc[plot_sells]
    if len(sell_points) > 0:
        fig.add_trace(
            go.Scatter(
                x=sell_points.index, y=sell_points['Close'] * 1.02,
                mode='markers', name='Điểm BÁN',
                marker=dict(symbol='triangle-down', size=11, color='#EF4444', line=dict(width=1, color='#B91C1C')),
                text=[f"BÁN: {p:,.0f} VND" for p in sell_points['Close']],
                hoverinfo='text+x'
            ),
            row=1, col=1
        )

    # 5. Đường OBV
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df['OBV'], mode='lines', name='OBV',
                   line=dict(color='#6366F1', width=1.2)),
        row=2, col=1
    )

    # 6. Cột độ dốc OBV Slope (Màu xanh khi > 0, màu đỏ khi < 0)
    slope_colors = ['#10B981' if v > 0 else '#EF4444' for v in plot_df['OBV_Slope']]
    fig.add_trace(
        go.Bar(x=plot_df.index, y=plot_df['OBV_Slope'], name='Độ Dốc OBV',
               marker_color=slope_colors, opacity=0.7),
        row=2, col=1
    )

    fig.update_layout(
        height=580,
        margin=dict(l=30, r=30, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        hovermode="x unified"
    )
    fig.update_yaxes(title_text="Giá (VND)", row=1, col=1)
    fig.update_yaxes(title_text="OBV", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# TAB 2: KIỂM ĐỊNH HIỆU QUẢ (TRAIN VS TEST)
# ==============================================================================
with tab2:
    st.subheader("Bảng Số Liệu So Sánh Hiệu Suất Chiến Lược (Train vs Test)")
    st.markdown("""
    Đối chiếu toàn diện **3 chiến lược**:
    - **EMA Riêng Lẻ** (Mua khi Giá > EMA, Bán khi Giá < EMA)
    - **OBV Riêng Lẻ** (Mua khi OBV Slope > 0, Bán khi OBV Slope < 0)
    - **EMA + OBV Kết Hợp** (Mua khi Giá > EMA VÀ OBV Slope > 0, Bán khi Giá < EMA)
    """)

    # Chọn tập dữ liệu hiển thị bảng chi tiết
    dataset_view = st.radio("Xem bảng số liệu chi tiết:", ["Tập Huấn Luyện (Train: 2014 - 2020)", "Tập Kiểm Định (Test: 2021 - 2023)"], horizontal=True)
    
    if "Train" in dataset_view:
        active_comb = bt_comb_train['metrics']
        active_ema = bt_ema_train['metrics']
        active_obv = bt_obv_train['metrics']
    else:
        active_comb = bt_comb_test['metrics']
        active_ema = bt_ema_test['metrics']
        active_obv = bt_obv_test['metrics']

    def create_metrics_row(name, met):
        return {
            'Chiến Lược': name,
            'Sharpe Ratio': f"{met['Sharpe Ratio']:.4f}",
            'Tổng LN (%)': f"{met['Total Return [%]']:+.2f}%",
            'CAGR (%)': f"{met['CAGR [%]']:+.2f}%",
            'Max Drawdown (%)': f"-{met['Max Drawdown [%]']:.2f}%",
            'Số Lệnh Đã Đóng': f"{met['Total Closed Trades']}",
            'Win Rate (%)': f"{met['Win Rate [%]']:.1f}%",
            'Profit Factor': f"{met['Profit Factor']:.2f}",
            'Thời Gian Giữ Vị Thế (%)': f"{met['Position Coverage [%]']:.1f}%"
        }

    summary_rows = [
        create_metrics_row("⭐ EMA + OBV Kết Hợp", active_comb),
        create_metrics_row("EMA Riêng Lẻ", active_ema),
        create_metrics_row("OBV Riêng Lẻ", active_obv)
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    # Biểu đồ cột so sánh TRAIN vs TEST (Trực quan hóa trọng tâm của Notebook Cell 23)
    st.markdown("##### 📊 So Sánh Hiệu Suất Tập Huấn Luyện (Train) vs Tập Kiểm Định (Test)")
    st.caption("Biểu đồ phân tích hiện tượng suy giảm hiệu suất (Out-of-sample deterioration) tương tự Cell 23 trong Notebook.")

    comp_data = [
        {'Chiến lược': 'EMA Riêng lẻ', 'Tập': 'Train', 'Sharpe Ratio': bt_ema_train['metrics']['Sharpe Ratio'],
         'Tổng lợi nhuận (%)': bt_ema_train['metrics']['Total Return [%]'], 'Max Drawdown (%)': -bt_ema_train['metrics']['Max Drawdown [%]']},
        {'Chiến lược': 'EMA Riêng lẻ', 'Tập': 'Test', 'Sharpe Ratio': bt_ema_test['metrics']['Sharpe Ratio'],
         'Tổng lợi nhuận (%)': bt_ema_test['metrics']['Total Return [%]'], 'Max Drawdown (%)': -bt_ema_test['metrics']['Max Drawdown [%]']},
        {'Chiến lược': 'OBV Riêng lẻ', 'Tập': 'Train', 'Sharpe Ratio': bt_obv_train['metrics']['Sharpe Ratio'],
         'Tổng lợi nhuận (%)': bt_obv_train['metrics']['Total Return [%]'], 'Max Drawdown (%)': -bt_obv_train['metrics']['Max Drawdown [%]']},
        {'Chiến lược': 'OBV Riêng lẻ', 'Tập': 'Test', 'Sharpe Ratio': bt_obv_test['metrics']['Sharpe Ratio'],
         'Tổng lợi nhuận (%)': bt_obv_test['metrics']['Total Return [%]'], 'Max Drawdown (%)': -bt_obv_test['metrics']['Max Drawdown [%]']},
        {'Chiến lược': 'EMA + OBV Kết hợp', 'Tập': 'Train', 'Sharpe Ratio': bt_comb_train['metrics']['Sharpe Ratio'],
         'Tổng lợi nhuận (%)': bt_comb_train['metrics']['Total Return [%]'], 'Max Drawdown (%)': -bt_comb_train['metrics']['Max Drawdown [%]']},
        {'Chiến lược': 'EMA + OBV Kết hợp', 'Tập': 'Test', 'Sharpe Ratio': bt_comb_test['metrics']['Sharpe Ratio'],
         'Tổng lợi nhuận (%)': bt_comb_test['metrics']['Total Return [%]'], 'Max Drawdown (%)': -bt_comb_test['metrics']['Max Drawdown [%]']},
    ]
    comp_df = pd.DataFrame(comp_data)

    col_bar1, col_bar2, col_bar3 = st.columns(3)
    with col_bar1:
        fig_b1 = px.bar(comp_df, x='Chiến lược', y='Sharpe Ratio', color='Tập', barmode='group',
                        title='Sharpe Ratio (Train vs Test)', text_auto='.2f',
                        color_discrete_map={'Train': '#3B82F6', 'Test': '#F59E0B'})
        fig_b1.update_layout(template="plotly_white", height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_b1, use_container_width=True)

    with col_bar2:
        fig_b2 = px.bar(comp_df, x='Chiến lược', y='Tổng lợi nhuận (%)', color='Tập', barmode='group',
                        title='Tổng Lợi Nhuận (%) (Train vs Test)', text_auto='.1f',
                        color_discrete_map={'Train': '#10B981', 'Test': '#EF4444'})
        fig_b2.update_layout(template="plotly_white", height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_b2, use_container_width=True)

    with col_bar3:
        fig_b3 = px.bar(comp_df, x='Chiến lược', y='Max Drawdown (%)', color='Tập', barmode='group',
                        title='Max Drawdown (%) (Train vs Test)', text_auto='.1f',
                        color_discrete_map={'Train': '#6366F1', 'Test': '#EC4899'})
        fig_b3.update_layout(template="plotly_white", height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_b3, use_container_width=True)

    st.markdown("---")
    # Biểu đồ đường cong vốn (Equity Curve)
    st.markdown("##### 📈 Tăng Trưởng Giá Trị Vốn (Equity Curve)")
    
    eq_comb = bt_comb_train['equity_curve'] if "Train" in dataset_view else bt_comb_test['equity_curve']
    eq_ema = bt_ema_train['equity_curve'] if "Train" in dataset_view else bt_ema_test['equity_curve']
    eq_obv = bt_obv_train['equity_curve'] if "Train" in dataset_view else bt_obv_test['equity_curve']
    
    # Chuẩn hóa về tỷ lệ % tăng trưởng
    norm_comb = ((eq_comb / eq_comb.iloc[0]) - 1.0) * 100.0
    norm_ema = ((eq_ema / eq_ema.iloc[0]) - 1.0) * 100.0
    norm_obv = ((eq_obv / eq_obv.iloc[0]) - 1.0) * 100.0

    target_data = train_df if "Train" in dataset_view else test_df
    bh_norm = ((target_data['Close'] / target_data['Close'].iloc[0]) - 1.0) * 100.0

    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=norm_comb.index, y=norm_comb, mode='lines', name='EMA + OBV Kết Hợp', line=dict(color='#10B981', width=2.5)))
    fig_eq.add_trace(go.Scatter(x=norm_ema.index, y=norm_ema, mode='lines', name='EMA Riêng Lẻ', line=dict(color='#3B82F6', width=1.5)))
    fig_eq.add_trace(go.Scatter(x=norm_obv.index, y=norm_obv, mode='lines', name='OBV Riêng Lẻ', line=dict(color='#F59E0B', width=1.5)))
    fig_eq.add_trace(go.Scatter(x=bh_norm.index, y=bh_norm, mode='lines', name='Buy & Hold ACB', line=dict(color='#9CA3AF', width=1.5, dash='dash')))

    fig_eq.update_layout(
        height=420,
        margin=dict(l=30, r=30, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        yaxis_title="Lợi Nhuận Tích Lũy (%)",
        hovermode="x unified"
    )
    st.plotly_chart(fig_eq, use_container_width=True)

# ==============================================================================
# TAB 3: QUẢN LÝ VỊ THẾ & NHẬT KÝ LỆNH
# ==============================================================================
with tab3:
    st.subheader("Hạch Toán Vị Thế (Position Accounting) & Nhật Ký Giao Dịch")
    
    st.markdown("""
    > **Trọng tâm sửa đổi theo góp ý giảng viên:** Chiến lược chỉ duy trì vị thế Long (`direction='longonly'`),
    > không nhồi lệnh (`accumulate=False`). Một lệnh mới chỉ được mở khi tài khoản đang ở trạng thái tiền mặt (`position == 0`).
    """)

    # Chọn tập để xem nhật ký lệnh
    trade_set = st.selectbox("Chọn tập dữ liệu xem nhật ký giao dịch:", ["Tập Train (2014 - 2020)", "Tập Test (2021 - 2023)", "Toàn Bộ (2014 - 2023)"], index=0)
    if "Train" in trade_set:
        active_trades_df = bt_comb_train['trades_df']
        active_pos_series = bt_comb_train['positions']
    elif "Test" in trade_set:
        active_trades_df = bt_comb_test['trades_df']
        active_pos_series = bt_comb_test['positions']
    else:
        active_trades_df = bt_comb_full['trades_df']
        active_pos_series = bt_comb_full['positions']

    # 1. Timeline Vị Thế
    st.markdown("##### ⏱️ Dòng Thời Gian Trạng Thái Vị Thế (0: Tiền mặt | 1: Đang giữ cổ phiếu)")
    fig_pos = go.Figure()
    fig_pos.add_trace(go.Scatter(
        x=active_pos_series.index, y=active_pos_series,
        mode='lines', fill='tozeroy', name='Trạng Thái Vị Thế',
        line=dict(color='#2563EB', width=1.5),
        fillcolor='rgba(37, 99, 235, 0.25)'
    ))
    fig_pos.update_layout(
        height=200,
        margin=dict(l=30, r=30, t=20, b=20),
        yaxis=dict(tickvals=[0, 1], ticktext=["0: Tiền Mặt", "1: Giữ Cổ Phiếu"]),
        template="plotly_white"
    )
    st.plotly_chart(fig_pos, use_container_width=True)

    # 2. Nhật ký giao dịch
    st.markdown("##### 📋 Danh Sách Chi Tiết Từng Lệnh Giao Dịch Đã Đóng")
    if len(active_trades_df) > 0:
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.caption(f"Tổng số lệnh đã đóng: **{len(active_trades_df)}** | Số lệnh thắng: **{len(active_trades_df[active_trades_df['PnL (%)'] > 0])}** | Số lệnh lỗ: **{len(active_trades_df[active_trades_df['PnL (%)'] <= 0])}**")
        with col_t2:
            # Nút tải file CSV
            csv_buffer = io.StringIO()
            active_trades_df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📥 Tải Nhật Ký Lệnh (CSV)",
                data=csv_buffer.getvalue(),
                file_name=f"trade_log_{trade_set.replace(' ', '_')}.csv",
                mime="text/csv"
            )

        # Định dạng hiển thị đẹp cho DataFrame
        display_trade_df = active_trades_df.copy()
        display_trade_df['Entry Date'] = pd.to_datetime(display_trade_df['Entry Date']).dt.strftime('%d/%m/%Y')
        display_trade_df['Exit Date'] = pd.to_datetime(display_trade_df['Exit Date']).dt.strftime('%d/%m/%Y')
        display_trade_df['Entry Price'] = display_trade_df['Entry Price'].apply(lambda x: f"{x:,.0f}")
        display_trade_df['Exit Price'] = display_trade_df['Exit Price'].apply(lambda x: f"{x:,.0f}")
        display_trade_df['PnL (VND)'] = display_trade_df['PnL (VND)'].apply(lambda x: f"{x:+,.0f}")
        display_trade_df['PnL (%)'] = display_trade_df['PnL (%)'].apply(lambda x: f"{x:+.2f}%")

        st.dataframe(display_trade_df, use_container_width=True, hide_index=True)
    else:
        st.info("Không phát sinh lệnh giao dịch nào trong khoảng thời gian đã chọn.")

# ==============================================================================
# TAB 4: TỐI ƯU HÓA THAM SỐ & ĐỘ NHẠY
# ==============================================================================
with tab4:
    st.subheader("Phân Tích Độ Nhạy Tham Số & Quét Lưới (Sensitivity Heatmap)")
    st.markdown("""
    Đánh giá tính bền vững của bộ tham số trên không gian 2 chiều (Chu kỳ EMA & Chu kỳ OBV Slope).
    Hệ thống tích hợp quy tắc **`MIN_TRADES >= 5`** để triệt tiêu hoàn toàn lỗi **`Sharpe = inf / NaN`**.
    """)

    col_opt1, col_opt2 = st.columns([1, 2])
    with col_opt1:
        st.markdown("##### ⚙️ Thiết Lập Quét Lưới")
        target_opt_set = st.selectbox("Tập dữ liệu tối ưu:", ["Tập Train (2014 - 2020)", "Tập Test (2021 - 2023)"])
        opt_data = train_df if "Train" in target_opt_set else test_df
        min_trades_rule = st.number_input("Số giao dịch tối thiểu (MIN_TRADES):", min_value=1, max_value=20, value=5)
        
        btn_start_grid = st.button("🚀 Bắt Đầu Quét Ma Trận", type="primary")

    with col_opt2:
        if btn_start_grid:
            ema_list = [10, 15, 20, 25, 30, 36, 40, 50]
            obv_list = [2, 3, 5, 10, 15, 19, 20, 25]

            sharpe_grid = np.zeros((len(obv_list), len(ema_list)))
            ret_grid = np.zeros((len(obv_list), len(ema_list)))

            progress = st.progress(0.0)
            total_evals = len(ema_list) * len(obv_list)
            idx = 0

            for r, obv_val in enumerate(obv_list):
                for c, ema_val in enumerate(ema_list):
                    c_calc = calculate_indicators(opt_data, ema_val, obv_val)
                    c_sigs = generate_all_signals(c_calc, ema_val, obv_val)
                    c_bt = run_backtest_engine(c_calc, c_sigs['Combined'][0], c_sigs['Combined'][1], init_cap, fee_rate, slip_rate, stop_loss_pct)

                    n_trades = c_bt['metrics']['Total Closed Trades']
                    s_ratio = c_bt['metrics']['Sharpe Ratio']
                    tot_ret = c_bt['metrics']['Total Return [%]']

                    if n_trades >= min_trades_rule and np.isfinite(s_ratio):
                        sharpe_grid[r, c] = s_ratio
                        ret_grid[r, c] = tot_ret
                    else:
                        sharpe_grid[r, c] = np.nan
                        ret_grid[r, c] = np.nan

                    idx += 1
                    progress.progress(idx / total_evals)

            progress.empty()

            fig_hm = px.imshow(
                sharpe_grid,
                x=[f"EMA={e}" for e in ema_list],
                y=[f"OBV={o}" for o in obv_list],
                color_continuous_scale="Viridis",
                labels=dict(x="Chu kỳ EMA", y="Chu kỳ OBV Slope", color="Sharpe Ratio"),
                title="Ma Trận Sharpe Ratio (Vùng Tham Số Bền Vững)"
            )
            fig_hm.update_layout(template="plotly_white", height=420)
            st.plotly_chart(fig_hm, use_container_width=True)
            st.success("✅ Đã hoàn tất quét ma trận. Vùng màu sáng liền mạch thể hiện tham số có tính ổn định cao!")
        else:
            st.info("Bấm nút **'Bắt Đầu Quét Ma Trận'** để trực quan hóa không gian tham số và kiểm tra vùng cao nguyên bền vững.")

# ==============================================================================
# TAB 5: PHƯƠNG PHÁP LUẬN & KHẮC PHỤC LỖI
# ==============================================================================
with tab5:
    st.subheader("Khung Lý Thuyết & Các Lỗi Đã Được Khắc Phục")

    st.markdown("""
    ### 1. Nguyên lý Kết hợp Chỉ báo Xu hướng (EMA) và Dòng tiền (OBV)
    * **EMA (Exponential Moving Average):** Là chỉ báo bám theo sau xu hướng (Trend Following). Khi giá đóng cửa nằm trên đường EMA, xu hướng tăng ngắn - trung hạn được xác nhận.
    * **OBV (On-Balance Volume):** Đo lường áp lực tích lũy (mua gom) hoặc phân phối (xả hàng) của dòng tiền thông minh qua khối lượng giao dịch.
    * **Độ dốc OBV (OBV Slope):** Tính bằng `OBV[t] - OBV[t - n]`. Nếu độ dốc dương (> 0), dòng tiền thực sự đang bơm vào hỗ trợ cho đà tăng giá.
    * **Bộ quy tắc vào lệnh:**
      * **MUA:** Giá đóng cửa vượt trên EMA **VÀ** Độ dốc OBV > 0 (Đồng thuận giữa xu hướng giá và dòng tiền).
      * **BÁN:** Giá đóng cửa rơi xuống dưới đường EMA (Đà tăng suy yếu, cần thoát hàng).

    ---

    ### 2. Hai Điểm Nhấn Sửa Lỗi Cốt Tử Theo Góp Ý Của Giảng Viên

    #### ⚠️ Lỗi 1: Chưa Hạch toán Đúng Vị Thế Giao Dịch (Position Accounting)
    * **Vấn đề bản gốc:** Tín hiệu kỹ thuật `(Close > EMA) & (OBV_Slope > 0)` là tín hiệu **trạng thái** (đúng liên tục trong suốt sóng tăng). Nếu không hạch toán vị thế, code sẽ liên tục phát tín hiệu MUA ngay cả khi tài khoản đã hết tiền, hoặc phát tín hiệu BÁN khống khi tài khoản chỉ đang giữ tiền mặt.
    * **Khắc phục:** 
      - Áp dụng mô hình **Long-only** độc quyền: $Position_t \in \{0, 1\}$.
      - Chỉ khớp lệnh MUA khi $Position_{t-1} == 0$.
      - Khi $Position_{t-1} == 1$, chỉ giữ hoặc chờ điều kiện BÁN (hoặc chạm Stop-loss).
      - Xác định hành động thực chiến phiên mới nhất: **BUY / HOLD / SELL / STAND ASIDE** dựa trên trạng thái danh mục thực tế.

    #### ⚠️ Lỗi 2: Bẫy "Sharpe Ảo / Vô Cực" Do Không Ràng Buộc Số Lệnh (MIN_TRADES)
    * **Vấn đề bản gốc:** Trong quá trình tối ưu hóa bằng Hyperopt, một số bộ tham số khiến hệ thống **hầu như không vào lệnh nào** trong suốt nhiều năm. Khi đó, chuỗi lợi nhuận bằng 0, độ lệch chuẩn $\sigma \approx 0$, dẫn đến công thức tính Sharpe Ratio:
      $$\\text{Sharpe} = \\frac{\\bar{R} - R_f}{\\sigma} \\longrightarrow \\frac{0}{0} \\text{ (NaN hoặc } +\\infty\\text{)}$$
      Hậu quả là thuật toán tối ưu bị đánh lừa, chọn nhầm bộ tham số 'đứng ngoài thị trường' làm bộ tham số tối ưu.
    * **Khắc phục:** Đặt ràng buộc bắt buộc `MIN_TRADES >= 5` trong hàm mục tiêu tối ưu. Mọi tham số tạo ra ít lệnh hơn ngưỡng này đều bị loại trừ thẳng tay.

    ---

    ### 3. Triệt Tiêu Thiên Lệch Nhìn Trước (Look-ahead Bias)
    * Mọi tín hiệu MUA/BÁN đều được trễ 1 phiên thông qua hàm `.shift(1)`.
    * Quyết định giao dịch tại ngày $t$ chỉ hoàn toàn căn cứ vào giá đóng cửa và chỉ báo đã hoàn tất tại ngày $t-1$.

    ---

    ### 4. Quản Trị Rủi Ro Với Cắt Lỗ Cứng (Stop Loss 7%)
    * Mỗi vị thế được bảo vệ bằng ngưỡng cắt lỗ tối đa 7% tính từ giá khớp mua.
    * Đưa chi phí giao dịch thực tế vào kiểm định: **Phí giao dịch 0.2%** và **Trượt giá 0.1%** cho mỗi chiều.
    """)

# Footer bản quyền & thông tin
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #9CA3AF; font-size: 0.85rem;'>"
    "Hệ thống Kiểm định Chiến lược Định lượng EMA & OBV | Triển khai trên nền tảng Streamlit Cloud & GitHub"
    "</div>",
    unsafe_allow_html=True
)
