import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
from data.market import validate_ticker, get_currency_rate
from data.sheets import save_user_data

def render_sidebar(username, portfolio):
    with st.sidebar:
        st.markdown(f'<div style="background:#1A1C24;padding:15px;border-radius:8px;border-left:5px solid #2962FF">Zalogowany jako: <b>{username}</b></div>', unsafe_allow_html=True)
        if st.button("Wyloguj"):
            st.session_state.username = None
            st.rerun()

        st.markdown("---")
        st.markdown("## Zarządzanie")
        if st.button("Odśwież (Live)", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        show_bench = st.checkbox("Pokaż Benchmark", value=True)
        benchmarks = st.multiselect("Benchmarki:", ["S&P 500", "NASDAQ 100", "WIG20", "Złoto", "Bitcoin"], default=["S&P 500"]) if show_bench else []

        st.markdown("---")
        with st.expander("➕ Dodaj Transakcję", expanded=True):
            with st.form("add_trade"):
                t_in = st.text_input("Symbol", "AAPL").upper()
                c_in = st.selectbox("Waluta Twojej Wpłaty", ["PLN", "USD", "EUR", "GBP"])
                d_in = st.date_input("Data", datetime.now())
                a_in = st.number_input(f"Kwota Wpłaty ({c_in})", min_value=1.0, value=1000.0)
                n_in = st.text_area("Notatka")
                if st.form_submit_button("Dodaj"):
                    symbol, err = validate_ticker(t_in)
                    if err: st.error(err)
                    else:
                        with st.spinner("Przeliczam..."):
                            t_obj = yf.Ticker(symbol)
                            asset_curr = t_obj.info.get('currency', 'USD').upper()
                            hist = t_obj.history(start=d_in, end=datetime.now() + timedelta(days=5))
                            if hist.empty: st.error("Brak ceny dla tej daty!")
                            else:
                                price = float(hist['Close'].iloc[0])
                                r_user = get_currency_rate(f"{c_in}PLN=X") if c_in != 'PLN' else 1.0
                                cost_pln = a_in * r_user
                                r_asset = get_currency_rate(f"{asset_curr}PLN=X") if asset_curr != 'PLN' else 1.0
                                qty = cost_pln / (price * r_asset)
                                portfolio.append({'Symbol': symbol, 'Data_Zakupu': d_in.strftime('%Y-%m-%d'), 'Waluta': asset_curr, 'Ilosc': qty, 'Kwota_Poczatkowa_PLN': cost_pln, 'Notatka': n_in})
                                if save_user_data(username, portfolio): st.success("Dodano!"); st.rerun()

        with st.expander("Edytuj Notatkę"):
            if portfolio:
                idx = st.selectbox("Transakcja", [f"{i+1}. {p['Symbol']} ({p['Data_Zakupu']})" for i,p in enumerate(portfolio)])
                i = int(idx.split('.')[0])-1
                new_n = st.text_area("Treść", value=portfolio[i].get('Notatka', ""))
                if st.button("Zapisz"):
                    portfolio[i]['Notatka'] = new_n
                    if save_user_data(username, portfolio): st.success("OK!"); st.rerun()

        with st.expander("Usuń pozycję"):
            if portfolio:
                idx_del = st.selectbox("Wybierz do usunięcia", [f"{i+1}. {p['Symbol']} ({p['Data_Zakupu']})" for i,p in enumerate(portfolio)])
                if st.button("Usuń trwale"):
                    portfolio.pop(int(idx_del.split('.')[0])-1)
                    if save_user_data(username, portfolio): st.success("Usunięto"); st.rerun()
        return benchmarks
