import streamlit as st
import pandas as pd
from data.sheets import load_user_data
from data.market import get_market_data, get_live_prices, get_live_currencies, get_benchmark_data
from core.metrics import calculate_portfolio_metrics, calculate_portfolio_history, safe_float, safe_date
from ui.sidebar import render_sidebar
from ui.dashboard import render_kpi, render_main_ui

st.set_page_config(page_title="Suitsy", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    section[data-testid="stSidebar"] { background-color: #11141D; border-right: 1px solid #2D2F3B; }
    div[data-testid="metric-container"] { background-color: #1A1C24; border: 1px solid #2D2F3B; padding: 15px; border-radius: 8px; }
    div[data-testid="metric-container"] label { color: #9CA3AF; font-size: 0.85rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #FAFAFA; font-size: 1.6rem; }
    .journal-card { background-color: #1A1C24; border-left: 4px solid #2962FF; padding: 15px; margin-bottom: 15px; border-radius: 0 8px 8px 0; }
    .journal-date { color: #2962FF; font-weight: bold; font-size: 0.9rem; }
    .journal-header { font-size: 1.1rem; color: #FAFAFA; font-weight: bold; margin: 5px 0; }
    .journal-note { color: #CECECE; font-style: italic; background: #232630; padding: 10px; border-radius: 4px; margin-top: 10px; }
    h1, h2, h3, h4, span, p { color: #FAFAFA !important; }
</style>
""", unsafe_allow_html=True)

if 'username' not in st.session_state: st.session_state.username = None

if not st.session_state.username:
    st.markdown("<h1 style='text-align: center;'>Suitsy Portfolio</h1>", unsafe_allow_html=True)
    with st.columns([1, 1, 1])[1]:
        u = st.text_input("Nick")
        if st.button("Wejdź", use_container_width=True) and u:
            st.session_state.username = u
            st.rerun()
    st.stop()

u = st.session_state.username
raw = load_user_data(u)

if raw:
    df = pd.DataFrame(raw)
    df['Ilosc'] = df['Ilosc'].apply(safe_float)
    df['Kwota_Poczatkowa_PLN'] = df['Kwota_Poczatkowa_PLN'].apply(safe_float)
    df['Data_Zakupu'] = df['Data_Zakupu'].apply(safe_date)

    with st.spinner("Ładowanie danych rynkowych..."):
        min_d = pd.to_datetime(df['Data_Zakupu'].min())
        tickers = df['Symbol'].unique().tolist()
        currs = df['Waluta'].unique().tolist()

        hist_p = get_market_data(tickers, min_d)

        hist_f = get_benchmark_data([f"{c}PLN=X" for c in currs if c != 'PLN'], min_d)

        live_p = get_live_prices(tickers)
        live_f = get_live_currencies(currs)

        df_fin = calculate_portfolio_metrics(df, hist_p, live_p, live_f)
        eq_curve, cost_curve, eq_map = calculate_portfolio_history(df, hist_p, hist_f)

        if not eq_curve.empty and len(eq_curve) > 1:
            if not eq_curve.empty and len(eq_curve) > 1:
                bench_opts = {
                    "S&P 500": "^GSPC",
                    "NASDAQ 100": "^NDX",
                    "WIG20": "WIG20.WA",
                    "Złoto": "GC=F",
                    "Bitcoin": "BTC-USD"
                }

                first_trade_mask = cost_curve > 0
                if first_trade_mask.any():
                    first_trade_date = cost_curve[first_trade_mask].index[0]
                else:
                    first_trade_date = eq_curve.index[0]

                roi_ser = pd.Series(0.0, index=eq_curve.index)
                roi_ser[first_trade_mask] = ((eq_curve[first_trade_mask] / cost_curve[first_trade_mask]) - 1) * 100

                selected_b = render_sidebar(u, raw)
                b_roi = {}
                for b in selected_b:
                    if b in bench_opts:
                        bd = get_benchmark_data(bench_opts[b], min_d)
                        if not bd.empty:
                            aligned = bd.reindex(eq_curve.index).ffill().bfill()

                            try:
                                price_at_start = aligned.loc[first_trade_date].iloc[0]
                                b_roi[b] = (aligned.iloc[:, 0] / price_at_start - 1) * 100
                                b_roi[b].loc[:first_trade_date] = 0
                            except Exception:
                                b_roi[b] = (aligned.iloc[:, 0] / aligned.iloc[0, 0] - 1) * 100

                active_eq = eq_curve[first_trade_mask]
                if not active_eq.empty:
                    cummax = active_eq.cummax()
                    drawdown = (active_eq - cummax) / cummax * 100
                    max_dd = drawdown.min()
                else:
                    max_dd = 0
                daily_chg = eq_curve.iloc[-1] - eq_curve.iloc[-2]
                daily_pct = (daily_chg / eq_curve.iloc[-2] * 100) if eq_curve.iloc[-2] != 0 else 0

                st.title("Suitsy")
                render_kpi(eq_curve.iloc[-1], (eq_curve.iloc[-1] - cost_curve.iloc[-1]), roi_ser.iloc[-1], max_dd,
                           daily_chg, daily_pct)
                render_main_ui(df_fin, eq_map, roi_ser, b_roi)
        else:
            st.warning("Brak wystarczających danych historycznych do wygenerowania wykresów.")
else:
    render_sidebar(u, [])
    st.title("Suitsy")
    st.info("Brak danych w portfelu.")

