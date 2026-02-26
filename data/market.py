import yfinance as yf
import pandas as pd
import streamlit as st
import requests
from datetime import datetime, timedelta
from core.metrics import clean_timezone


def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    return session


@st.cache_data(ttl=3600, show_spinner=False)
def get_market_data(tickers, start_date):
    """Pobiera dane historyczne z retry logic"""
    if not tickers:
        return pd.DataFrame()

    # Zapewnienie okresu minimum 30 dni wstecz
    start = pd.to_datetime(start_date)
    if (datetime.now() - start).days < 30:
        start = datetime.now() - timedelta(days=365)

    for attempt in range(3):  # 3 próby
        try:
            data = yf.download(
                tickers,
                start=start,
                end=datetime.now() + timedelta(days=1),
                progress=False,
                session=get_session(),
                auto_adjust=True  # Uproszczone dane
            )

            if data.empty:
                continue

            # Obsługa Close
            if 'Close' in data.columns:
                data = data['Close']
            elif isinstance(data.columns, pd.MultiIndex):
                data = data['Close'] if 'Close' in data.columns.get_level_values(0) else data

            if isinstance(data, pd.Series):
                data = data.to_frame()
                data.columns = [tickers] if isinstance(tickers, str) else tickers

            return clean_timezone(data)
        except Exception as e:
            if attempt == 2:  # Ostatnia próba
                st.warning(f"Nie udało się pobrać danych: {str(e)}")

    return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_live_prices(tickers):
    """Pobiera aktualne ceny z fallbackiem na dane historyczne"""
    if not tickers:
        return {}

    try:
        # Próba 1: Pobranie danych z ostatnich 5 dni
        data = yf.download(
            tickers,
            period="5d",
            progress=False,
            session=get_session()
        )['Close']

        if data.empty:
            return {}

        # Forward fill dla brakujących wartości (weekendy)
        data = data.ffill()

        if isinstance(data, pd.Series):
            return {tickers[0]: float(data.iloc[-1])} if not data.empty else {}

        last_prices = data.iloc[-1].to_dict()
        return {t: float(p) for t, p in last_prices.items() if pd.notna(p)}

    except Exception:
        return {}


@st.cache_data(ttl=900, show_spinner=False)
def get_benchmark_data(symbols, start_date):
    """Wrapper dla get_market_data z obsługą list"""
    if not symbols:
        return pd.DataFrame()
    return get_market_data(symbols, start_date)


@st.cache_data(ttl=900, show_spinner=False)
def get_live_currencies(currencies):
    """Pobiera kursy walut z fallbackiem"""
    rates = {'PLN': 1.0}
    to_fetch = [f"{c}PLN=X" for c in currencies if c != 'PLN']

    if not to_fetch:
        return rates

    try:
        data = yf.download(
            to_fetch,
            period="5d",  # Więcej dni dla pewności
            progress=False,
            session=get_session()
        )['Close']

        if data.empty:
            # Fallback - zwróć 1.0 dla wszystkich
            for c in currencies:
                if c != 'PLN': rates[c] = 1.0
            return rates

        data = data.ffill()  # Forward fill

        if isinstance(data, pd.Series):
            curr_code = to_fetch[0].replace('PLN=X', '')
            rates[curr_code] = float(data.iloc[-1]) if not data.empty else 1.0
        else:
            last_row = data.iloc[-1]
            for col in data.columns:
                curr_code = col.replace('PLN=X', '')
                rates[curr_code] = float(last_row[col]) if pd.notna(last_row[col]) else 1.0

    except Exception:
        # Fallback na 1.0
        for c in currencies:
            if c not in rates:
                rates[c] = 1.0

    return rates


# TE FUNKCJE NIE MOGĄ MIEĆ CACHE - używane w formularzach!
def validate_ticker(ticker):
    """Waliduje ticker - BEZ CACHE bo używane w formularzu"""
    ticker = ticker.upper().strip().replace('.PL', '.WA')
    try:
        test = yf.download(ticker, period="5d", progress=False, session=get_session())
        if test.empty:
            return None, f"Symbol {ticker} nieznany lub brak danych"
        return ticker, None
    except Exception as e:
        return None, f"Błąd walidacji: {str(e)}"


def get_currency_rate(pair):
    """Pobiera kurs walutowy - BEZ CACHE bo używane w formularzu"""
    if not pair or "PLNPLN" in pair:
        return 1.0
    try:
        data = yf.download(pair, period="5d", progress=False, session=get_session())['Close']
        if not data.empty:
            return float(data.ffill().iloc[-1])
        return 1.0
    except Exception:
        return 1.0
