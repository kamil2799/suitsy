import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
import numpy as np

# ============================================================================
# CONSTANTS
# ============================================================================
CACHE_TTL = 900
MIN_INVESTMENT = 1.0
STEP_INVESTMENT = 100.0
DB_FILE = "portfolio_db.json"
MAX_HISTORICAL_DAYS = 3650

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="suitsy",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    section[data-testid="stSidebar"] { background-color: #11141D; border-right: 1px solid #2D2F3B; }

    div[data-testid="metric-container"] {
        background-color: #1A1C24; border: 1px solid #2D2F3B;
        padding: 15px; border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    div[data-testid="metric-container"] label { color: #9CA3AF; font-size: 0.85rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #FAFAFA; font-size: 1.6rem; }

    div[data-testid="stDataFrame"] { background-color: #1A1C24; border: 1px solid #2D2F3B; border-radius: 8px; padding: 10px; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; background-color: #1A1C24; border: 1px solid #2D2F3B; border-radius: 4px; color: #9CA3AF; padding: 0 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #2962FF !important; color: white !important; border: none; }

    .stTextInput > div > div > input, .stNumberInput > div > div > input,
    .stSelectbox > div > div > div, .stDateInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #1A1C24; color: white; border: 1px solid #2D2F3B;
    }

    h1, h2, h3, h4, span { color: #FAFAFA !important; }
    p, li { color: #B0B0B0 !important; }
    footer {visibility: hidden;}

    .roi-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem; }
    .roi-high { background-color: rgba(0, 230, 118, 0.2); color: #00E676; }
    .roi-medium { background-color: rgba(255, 193, 7, 0.2); color: #FFC107; }
    .roi-low { background-color: rgba(255, 82, 82, 0.2); color: #FF5252; }

    /* STYLE DLA DZIENNIKA */
    .journal-card {
        background-color: #1A1C24;
        border-left: 4px solid #2962FF;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 0 8px 8px 0;
    }
    .journal-date { color: #2962FF; font-weight: bold; font-size: 0.9rem; }
    .journal-header { font-size: 1.1rem; color: #FAFAFA; font-weight: bold; margin: 5px 0; }
    .journal-note { color: #CECECE; font-style: italic; background: #232630; padding: 10px; border-radius: 4px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clean_timezone(data):
    if data.empty: return data
    return data.ffill().bfill().tz_localize(None) if data.index.tz else data.ffill().bfill()


def get_roi_badge(roi_pct):
    if roi_pct >= 10:
        return f'<span class="roi-badge roi-high">🟢 {roi_pct:+.1f}%</span>'
    elif roi_pct >= 0:
        return f'<span class="roi-badge roi-medium">🟡 {roi_pct:+.1f}%</span>'
    else:
        return f'<span class="roi-badge roi-low">🔴 {roi_pct:+.1f}%</span>'


# ============================================================================
# DATA FETCHING
# ============================================================================

@st.cache_data(ttl=CACHE_TTL)
def get_market_data(tickers, start_date):
    if not tickers: return pd.DataFrame()
    try:
        end_date = datetime.now() + timedelta(days=1)
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close']
        if isinstance(data, pd.Series):
            data = data.to_frame()
            data.columns = tickers
        return clean_timezone(data)
    except Exception as e:
        return pd.DataFrame()


def get_live_prices(tickers):
    prices = {}
    for t in tickers:
        try:
            ticker = yf.Ticker(t)
            price = ticker.fast_info['last_price']
            if price is not None:
                prices[t] = price
        except:
            pass
    return prices


@st.cache_data(ttl=CACHE_TTL)
def get_benchmark_data(symbol, start_date):
    end_date = datetime.now() + timedelta(days=1)
    data = yf.download(symbol, start=start_date, end=end_date, progress=False)['Close']
    if isinstance(data, pd.Series): data = data.to_frame()
    return clean_timezone(data)


@st.cache_data(ttl=CACHE_TTL)
def get_currency_history(currencies, start_date):
    needed = [f"{c}PLN=X" for c in currencies if c != 'PLN']
    if not needed: return pd.DataFrame()
    end_date = datetime.now() + timedelta(days=1)
    data = yf.download(needed, start=start_date, end=end_date, progress=False)['Close']
    if isinstance(data, pd.Series):
        df = data.to_frame()
        df.columns = needed
        return df
    return data


def get_live_currencies(currencies):
    rates = {'PLN': 1.0}
    needed = [c for c in currencies if c != 'PLN']
    for c in needed:
        try:
            ticker_str = f"{c}PLN=X"
            rates[c] = yf.Ticker(ticker_str).fast_info['last_price']
        except:
            rates[c] = 1.0
    return rates


# ============================================================================
# PERSISTENCE
# ============================================================================

def save_data(data):
    to_save = []
    for item in data:
        temp = item.copy()
        temp['Data_Zakupu'] = str(item['Data_Zakupu'])
        if 'Sektor' in temp: del temp['Sektor']
        to_save.append(temp)
    with open(DB_FILE, "w") as f:
        json.dump(to_save, f, indent=2)


def load_data_from_file():
    if not os.path.exists(DB_FILE): return []
    with open(DB_FILE, "r") as f:
        raw = json.load(f)
        for record in raw:
            if isinstance(record['Data_Zakupu'], str):
                record['Data_Zakupu'] = datetime.strptime(record['Data_Zakupu'], '%Y-%m-%d').date()
            if 'Waluta' not in record: record['Waluta'] = 'PLN'
            if 'Kwota_Poczatkowa_PLN' not in record:
                record['Kwota_Poczatkowa_PLN'] = float(record.get('Kwota_Poczatkowa', 0))
            if 'Notatka' not in record: record['Notatka'] = ""
        return raw


# ============================================================================
# CALCULATION
# ============================================================================

def calculate_portfolio_metrics(df, hist_prices, live_prices_map, live_fx_map):
    def get_price(symbol):
        if symbol in live_prices_map and live_prices_map[symbol] is not None:
            return live_prices_map[symbol]
        if symbol in hist_prices.columns:
            return hist_prices[symbol].iloc[-1]
        return 0.0

    def get_fx(currency):
        return live_fx_map.get(currency, 1.0)

    df['Cena_Live'] = df['Symbol'].apply(get_price)
    df['Kurs_Live'] = df['Waluta'].apply(get_fx)

    df['Wartosc_PLN'] = df['Ilosc'] * df['Cena_Live'] * df['Kurs_Live']
    df['Zysk_PLN'] = df['Wartosc_PLN'] - df['Kwota_Poczatkowa_PLN']
    df['Zysk_Proc'] = (df['Zysk_PLN'] / df['Kwota_Poczatkowa_PLN']) * 100

    return df


def calculate_portfolio_history(df, hist_prices, hist_fx):
    if hist_prices.empty: return pd.Series(), pd.Series(), {}

    total_equity = pd.Series(0.0, index=hist_prices.index)
    total_cost = pd.Series(0.0, index=hist_prices.index)
    equity_dict = {}

    for idx, row in df.iterrows():
        symbol = row['Symbol']
        currency = row['Waluta']
        buy_date = pd.to_datetime(row['Data_Zakupu'])

        if symbol not in hist_prices.columns: continue

        asset_history = hist_prices[symbol]

        if currency == 'PLN':
            fx_history = 1.0
        else:
            fx_col = f"{currency}PLN=X"
            fx_history = hist_fx[fx_col].reindex(
                hist_prices.index).ffill().bfill() if fx_col in hist_fx.columns else 1.0

        pos_value = (asset_history * row['Ilosc'] * fx_history)
        pos_cost = pd.Series(0.0, index=hist_prices.index)

        mask = pos_cost.index >= buy_date
        pos_cost[mask] = row['Kwota_Poczatkowa_PLN']
        pos_value[~mask] = 0

        total_equity += pos_value
        total_cost += pos_cost

        if symbol in equity_dict:
            equity_dict[symbol] += pos_value
        else:
            equity_dict[symbol] = pos_value

    return total_equity, total_cost, equity_dict


# ============================================================================
# SESSION STATE
# ============================================================================

if 'pro_portfolio' not in st.session_state:
    st.session_state.pro_portfolio = load_data_from_file()

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("## Zarządzanie")

    if st.button("Odśwież Ceny (Live)", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Kliknij, jeśli ceny nie są aktualne.")

    st.markdown("---")
    st.markdown("### Ustawienia Wykresów")
    show_benchmark = st.checkbox("Pokaż Benchmark", value=True)
    benchmark_opts = {"S&P 500": "^GSPC", "NASDAQ 100": "^NDX", "WIG20": "WIG20.WA", "Złoto": "GC=F",
                      "Bitcoin": "BTC-USD"}

    if show_benchmark:
        selected_benchmarks = st.multiselect("Benchmarki:", list(benchmark_opts.keys()), default=["S&P 500"])
    else:
        selected_benchmarks = []

    st.markdown("---")
    with st.expander(" + Dodaj Transakcję", expanded=False):
        with st.form("add_trade", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ticker_input = st.text_input("Symbol", placeholder="AAPL").upper().strip()
            with c2:
                currency = st.selectbox("Waluta", ["USD", "PLN", "EUR", "GBP"])

            buy_date = st.date_input("Data zakupu", value=datetime.now())
            amount = st.number_input(f"Kwota ({currency})", min_value=1.0)
            note = st.text_area("Notatka / Powód", placeholder="Dlaczego kupujesz?", height=80)

            if st.form_submit_button("Dodaj"):
                ticker = ticker_input.replace(".PL", ".WA").replace(".UK", ".L")
                try:
                    t_obj = yf.Ticker(ticker)
                    hist = t_obj.history(period="5d")
                    if not hist.empty:
                        start_d = pd.to_datetime(buy_date)
                        idx = hist.index.get_indexer([start_d], method='nearest')[0]
                        price_at_buy = float(hist['Close'].iloc[idx]) if idx < len(hist) else float(
                            hist['Close'].iloc[-1])

                        vol = amount / price_at_buy

                        fx_buy = 1.0
                        if currency != "PLN":
                            fx_d = yf.download(f"{currency}PLN=X", start=buy_date, end=datetime.now(), progress=False)
                            if not fx_d.empty: fx_buy = float(fx_d['Close'].iloc[0])

                        st.session_state.pro_portfolio.append({
                            'Symbol': ticker, 'Data_Zakupu': buy_date, 'Waluta': currency,
                            'Ilosc': vol, 'Kwota_Poczatkowa_PLN': amount * fx_buy,
                            'Notatka': note
                        })
                        save_data(st.session_state.pro_portfolio)
                        st.rerun()
                    else:
                        st.error("Błąd symbolu!")
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- NOWA SEKCJA: Edytuj Notatkę ---
    if st.session_state.pro_portfolio:
        with st.expander("Edytuj Notatkę"):
            # Lista transakcji do wyboru
            opts_edit = [f"{i + 1}. {r['Symbol']} ({r['Data_Zakupu']})" for i, r in
                         enumerate(st.session_state.pro_portfolio)]
            selected_edit = st.selectbox("Wybierz transakcję", opts_edit)

            if selected_edit:
                idx_edit = int(selected_edit.split(".")[0]) - 1
                current_record = st.session_state.pro_portfolio[idx_edit]
                current_note = current_record.get('Notatka', "")

                # Pole edycji
                new_note = st.text_area("Treść notatki:", value=current_note, height=100)

                if st.button("Zapisz Zmianę"):
                    st.session_state.pro_portfolio[idx_edit]['Notatka'] = new_note
                    save_data(st.session_state.pro_portfolio)
                    st.success("Zaktualizowano notatkę!")
                    st.rerun()

    if st.session_state.pro_portfolio:
        with st.expander(" Usuń pozycję"):
            opts = [f"{i + 1}. {r['Symbol']}" for i, r in enumerate(st.session_state.pro_portfolio)]
            delt = st.selectbox("Pozycja do usunięcia", opts)
            if st.button("Usuń trwale"):
                idx = int(delt.split(".")[0]) - 1
                st.session_state.pro_portfolio.pop(idx)
                save_data(st.session_state.pro_portfolio)
                st.rerun()

# ============================================================================
# MAIN APP
# ============================================================================

st.title("suitsy")

if st.session_state.pro_portfolio:
    df = pd.DataFrame(st.session_state.pro_portfolio)
    if 'Notatka' not in df.columns: df['Notatka'] = ""

    tickers = df['Symbol'].unique().tolist()
    currencies = df['Waluta'].unique().tolist()
    min_date = df['Data_Zakupu'].min()

    with st.spinner('Pobieranie danych (History + Live)...'):
        hist_prices = get_market_data(tickers, min_date)
        hist_fx = get_currency_history(currencies, min_date)
        live_prices = get_live_prices(tickers)
        live_fx = get_live_currencies(currencies)

        bench_data_dict = {}
        for b in selected_benchmarks:
            bd = get_benchmark_data(benchmark_opts[b], min_date)
            if not bd.empty: bench_data_dict[b] = bd

    if hist_prices.empty:
        st.error("Problem z pobraniem danych. Kliknij 'Odśwież' w menu.")
        st.stop()

    df = calculate_portfolio_metrics(df, hist_prices, live_prices, live_fx)
    equity_curve, cost_curve, equity_map = calculate_portfolio_history(df, hist_prices, hist_fx)

    roi_series = ((equity_curve / cost_curve).fillna(1) - 1) * 100
    roi_series = roi_series.replace([float('inf'), -float('inf')], 0).fillna(0)

    # Benchmark ROI
    bench_roi_dict = {}
    for bn, bd in bench_data_dict.items():
        aligned = bd.reindex(roi_series.index).ffill().bfill()
        if not aligned.empty:
            col = aligned.columns[0]
            start_v = aligned[col].iloc[0]
            bench_roi_dict[bn] = (aligned[col] / start_v - 1) * 100

    # KPI Summary
    total_val = df['Wartosc_PLN'].sum()
    total_inv = df['Kwota_Poczatkowa_PLN'].sum()
    profit = total_val - total_inv
    roi_total = (profit / total_inv) * 100 if total_inv > 0 else 0

    # Drawdown
    cum = (1 + roi_series / 100)
    dd = (cum / cum.cummax() - 1) * 100
    max_dd = dd.min()

    # Daily Change
    daily_chg = equity_curve.iloc[-1] - equity_curve.iloc[-2] if len(equity_curve) > 1 else 0
    daily_pct = (daily_chg / equity_curve.iloc[-2]) * 100 if len(equity_curve) > 1 else 0

    # TOP METRICS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dzisiaj (vs Close)", f"{daily_chg:+,.0f} PLN", f"{daily_pct:+.2f}%")
    c2.metric("Wycena Portfela", f"{total_val:,.0f} PLN")
    c3.metric("Zysk Całkowity", f"{profit:+,.0f} PLN", f"{roi_total:+.2f}%")
    c4.metric("Max Drawdown", f"{max_dd:.2f}%")

    st.markdown("---")

    # --- TABS ---
    t1, t2, t3, t4, t5 = st.tabs(["Wartość", "ROI", "Alokacja", "Dziennik", "Szczegóły"])

    with t1:
        # Stacked Area
        eq_df = pd.DataFrame(equity_map).fillna(0)
        last_row = eq_df.iloc[-1]
        sorted_cols = last_row.sort_values(ascending=False).index
        eq_df = eq_df[sorted_cols]

        fig = px.area(eq_df, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Bold)
        fig.update_layout(height=450, paper_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title="Wartość (PLN)")
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        fig_roi = go.Figure()
        for bn, br in bench_roi_dict.items():
            fig_roi.add_trace(go.Scatter(x=br.index, y=br, mode='lines', name=bn, line=dict(dash='dot', width=1)))

        fig_roi.add_trace(go.Scatter(x=roi_series.index, y=roi_series, mode='lines', name='Twój Portfel',
                                     line=dict(color='#FAFAFA', width=3)))

        fig_roi.add_trace(go.Scatter(x=roi_series.index, y=roi_series.clip(lower=0), mode='none', fill='tozeroy',
                                     fillcolor='rgba(0, 230, 118, 0.1)', hoverinfo='skip', showlegend=False))
        fig_roi.add_trace(go.Scatter(x=roi_series.index, y=roi_series.clip(upper=0), mode='none', fill='tozeroy',
                                     fillcolor='rgba(255, 82, 82, 0.1)', hoverinfo='skip', showlegend=False))

        fig_roi.update_layout(template="plotly_dark", height=450, paper_bgcolor='rgba(0,0,0,0)', yaxis_title="ROI (%)",
                              xaxis_title=None)
        st.plotly_chart(fig_roi, use_container_width=True)

    with t3:
        c_chart, c_list = st.columns([2, 1])
        alloc = df.groupby('Symbol')['Wartosc_PLN'].sum().reset_index().sort_values(by='Wartosc_PLN', ascending=False)
        with c_chart:
            fig_p = px.pie(alloc, values='Wartosc_PLN', names='Symbol', hole=0.5,
                           color_discrete_sequence=px.colors.qualitative.Bold)
            fig_p.update_layout(template="plotly_dark", height=400, paper_bgcolor='rgba(0,0,0,0)')
            fig_p.add_annotation(text="ASSETS", showarrow=False, font=dict(size=20, color="white"))
            st.plotly_chart(fig_p, use_container_width=True)
        with c_list:
            for _, r in alloc.iterrows():
                p = (r['Wartosc_PLN'] / total_val) * 100
                st.progress(int(p), text=f"{r['Symbol']}: {p:.1f}%")

    with t4:
        st.markdown("### Dziennik Inwestycyjny")
        journal_df = df.sort_values(by='Data_Zakupu', ascending=False)

        for idx, row in journal_df.iterrows():
            note_content = row['Notatka'] if row['Notatka'] else "Brak notatki."
            profit_color = "#00E676" if row['Zysk_PLN'] >= 0 else "#FF5252"

            st.markdown(f"""
            <div class="journal-card">
                <div class="journal-date">{row['Data_Zakupu']}</div>
                <div class="journal-header">
                    {row['Symbol']} <span style="font-weight:normal; font-size:0.9rem;">(Inwestycja: {row['Kwota_Poczatkowa_PLN']:.0f} PLN)</span>
                    <span style="float:right; color:{profit_color};">{row['Zysk_PLN']:+.0f} PLN</span>
                </div>
                <div class="journal-note">
                     {note_content}
                </div>
            </div>
            """, unsafe_allow_html=True)

    with t5:
        col_conf = {
            "Symbol": st.column_config.TextColumn("Ticker"),
            "Wartosc_PLN": st.column_config.ProgressColumn("Wycena", format="%.0f zł", min_value=0,
                                                           max_value=max(df['Wartosc_PLN'].max(), 1.0)),
            "Zysk_PLN": st.column_config.NumberColumn("Zysk Nom.", format="%.0f zł"),
            "Zysk_Proc": st.column_config.NumberColumn("ROI", format="%.2f %%"),
            "Cena_Live": st.column_config.NumberColumn("Cena Live", format="%.2f"),
            "Notatka": st.column_config.TextColumn("Notatka", width="medium")
        }


        def style_roi(v): return f'background-color: {"rgba(0, 230, 118, 0.2)" if v >= 0 else "rgba(255, 82, 82, 0.2)"}'


        st.dataframe(
            df[['Symbol', 'Data_Zakupu', 'Cena_Live', 'Wartosc_PLN', 'Zysk_PLN', 'Zysk_Proc', 'Notatka']]
            .sort_values('Wartosc_PLN', ascending=False)
            .style.applymap(style_roi, subset=['Zysk_Proc']),
            use_container_width=True,
            column_config=col_conf,
            hide_index=True,
            height=400
        )
else:
    st.info("Dodaj pierwszą transakcję w panelu bocznym.")