import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from data.market import validate_ticker, get_currency_rate
from data.sheets import save_user_data


def render_sidebar(username, portfolio):
    with st.sidebar:
        st.markdown(
            f'<div style="background:#1A1C24;padding:15px;border-radius:8px;border-left:5px solid #2962FF">Zalogowany jako: <b>{username}</b></div>',
            unsafe_allow_html=True
        )
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
        benchmarks = (
            st.multiselect(
                "Benchmarki:",
                ["S&P 500", "NASDAQ 100", "WIG20", "Złoto", "Bitcoin"],
                default=["S&P 500"]
            )
            if show_bench
            else []
        )

        st.markdown("---")
        with st.expander("➕ Dodaj Transakcję", expanded=True):
            # Formularz musi być wewnątrz, ale selectbox waluty PRZED formularzem
            c_in = st.selectbox("Waluta Twojej Wpłaty", ["PLN", "USD", "EUR", "GBP"], key="currency_select")
            
            with st.form("add_trade"):
                t_in = st.text_input("Symbol", "AAPL").upper()
                st.info(f"Wpłata będzie w: **{c_in}**")
                d_in = st.date_input("Data", datetime.now())
                a_in = st.number_input(f"Kwota Wpłaty ({c_in})", min_value=1.0, value=1000.0, key="amount_input")
                n_in = st.text_area("Notatka")
                
                if st.form_submit_button("Dodaj"):
                    # Walidacja tickera
                    symbol, err = validate_ticker(t_in)
                    if err:
                        st.error(err)
                    else:
                        with st.spinner("Przeliczam..."):
                            try:
                                # Pobierz informacje o aktywie
                                t_obj = yf.Ticker(symbol)
                                info = t_obj.info
                                asset_curr = info.get('currency', 'USD').upper()
                                
                                # Pobierz dane historyczne z rozszerzonym zakresem (±5 dni)
                                start = d_in - timedelta(days=5)
                                end = d_in + timedelta(days=5)
                                hist = t_obj.history(start=start, end=end)
                                
                                if hist.empty:
                                    st.error("Brak ceny dla tej daty! Spróbuj innej daty lub sprawdź symbol.")
                                else:
                                    # Konwersja indeksu do dat (bez timezone)
                                    hist.index = pd.to_datetime(hist.index).date
                                    
                                    # Znajdź cenę na wybraną datę lub najbliższą dostępną
                                    if d_in in hist.index:
                                        price = float(hist.loc[d_in]['Close'])
                                        st.success(f"✓ Cena z {d_in}: {price:.2f} {asset_curr}")
                                    else:
                                        # Użyj najbliższej dostępnej daty
                                        closest_date = min(hist.index, key=lambda x: abs(x - d_in))
                                        price = float(hist.loc[closest_date]['Close'])
                                        st.info(f"ℹ️ Użyto ceny z {closest_date}: {price:.2f} {asset_curr}")
                                    
                                    # Pobierz kursy walut (bez cache - świeże dane!)
                                    r_user = get_currency_rate(f"{c_in}PLN=X") if c_in != 'PLN' else 1.0
                                    r_asset = get_currency_rate(f"{asset_curr}PLN=X") if asset_curr != 'PLN' else 1.0
                                    
                                    # Wyświetl kursy dla przejrzystości
                                    if c_in != 'PLN':
                                        st.info(f"Kurs {c_in}/PLN: {r_user:.4f}")
                                    if asset_curr != 'PLN':
                                        st.info(f"Kurs {asset_curr}/PLN: {r_asset:.4f}")
                                    
                                    # Oblicz ilość i koszt w PLN
                                    cost_pln = a_in * r_user
                                    qty = cost_pln / (price * r_asset)
                                    
                                    # Wyświetl podsumowanie
                                    st.success(f"""
                                    **Podsumowanie transakcji:**
                                    - Kupujesz: {qty:.4f} jednostek {symbol}
                                    - Cena jednostkowa: {price:.2f} {asset_curr}
                                    - Koszt całkowity: {cost_pln:.2f} PLN
                                    """)
                                    
                                    # Dodaj do portfolio
                                    portfolio.append({
                                        'Symbol': symbol,
                                        'Data_Zakupu': d_in.strftime('%Y-%m-%d'),
                                        'Waluta': asset_curr,
                                        'Ilosc': qty,
                                        'Kwota_Poczatkowa_PLN': cost_pln,
                                        'Notatka': n_in
                                    })
                                    
                                    # Zapisz i odśwież
                                    if save_user_data(username, portfolio):
                                        st.success("✅ Transakcja dodana!")
                                        st.cache_data.clear()  # Wyczyść cache dla świeżych danych
                                        st.rerun()
                                    else:
                                        st.error("Błąd zapisu do bazy danych")
                                        
                            except KeyError as e:
                                st.error(f"Błąd: Brak danych dla klucza {str(e)}")
                            except Exception as e:
                                st.error(f"Wystąpił błąd: {str(e)}")
                                st.error("Spróbuj ponownie lub wybierz inną datę/symbol")

        with st.expander("✏️ Edytuj Notatkę"):
            if portfolio:
                idx = st.selectbox(
                    "Transakcja",
                    [f"{i+1}. {p['Symbol']} ({p['Data_Zakupu']})" for i, p in enumerate(portfolio)]
                )
                i = int(idx.split('.')[0]) - 1
                new_n = st.text_area("Treść", value=portfolio[i].get('Notatka', ""))
                
                if st.button("Zapisz", key="save_note"):
                    portfolio[i]['Notatka'] = new_n
                    if save_user_data(username, portfolio):
                        st.success("✅ Notatka zaktualizowana!")
                        st.rerun()
                    else:
                        st.error("Błąd zapisu")
            else:
                st.info("Brak transakcji w portfolio")

        with st.expander("🗑️ Usuń pozycję"):
            if portfolio:
                idx_del = st.selectbox(
                    "Wybierz do usunięcia",
                    [f"{i+1}. {p['Symbol']} ({p['Data_Zakupu']})" for i, p in enumerate(portfolio)],
                    key="delete_select"
                )
                
                st.warning("⚠️ Ta operacja jest nieodwracalna!")
                
                if st.button("Usuń trwale", type="secondary"):
                    i_del = int(idx_del.split('.')[0]) - 1
                    deleted = portfolio.pop(i_del)
                    
                    if save_user_data(username, portfolio):
                        st.success(f"✅ Usunięto {deleted['Symbol']}")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Błąd zapisu")
            else:
                st.info("Brak transakcji do usunięcia")
        
        return benchmarks
