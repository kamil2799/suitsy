import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from core.metrics import clean_timezone


@st.cache_data(ttl=900)
def get_market_data(tickers, start_date):
    """Pobiera dane historyczne dla wszystkich tickerów w portfelu"""
    if not tickers: return pd.DataFrame()
    try:
        data = yf.download(tickers, start=start_date, progress=False)['Close']
        if isinstance(data, pd.Series):
            data = data.to_frame()
            data.columns = tickers
        return clean_timezone(data)
    except Exception:
        return pd.DataFrame()


def get_live_prices(tickers):
    """Pobiera aktualne ceny (Batch)"""
    if not tickers: return {}
    try:
        data = yf.download(tickers, period="1d", progress=False)['Close']
        if isinstance(data, pd.Series):
            return {tickers[0]: float(data.iloc[-1])}
        last_prices = data.ffill().iloc[-1].to_dict()
        return {t: float(p) for t, p in last_prices.items() if pd.notna(p)}
    except Exception:
        return {}


@st.cache_data(ttl=900)
def get_benchmark_data(symbols, start_date):
    if not symbols: return pd.DataFrame()
    try:
        search_list = [symbols] if isinstance(symbols, str) else symbols
        data = yf.download(search_list, start=start_date, progress=False)['Close']

        if isinstance(data, pd.Series):
            data = data.to_frame()
            data.columns = search_list
        elif isinstance(data, pd.DataFrame) and len(search_list) == 1:
            data.columns = search_list

        return clean_timezone(data)
    except Exception:
        return pd.DataFrame()


def get_live_currencies(currencies):
    rates = {'PLN': 1.0}
    to_fetch = [f"{c}PLN=X" for c in currencies if c != 'PLN']
    if not to_fetch: return rates

    try:
        data = yf.download(to_fetch, period="1d", progress=False)['Close']
        if isinstance(data, pd.Series):
            rates[to_fetch[0].replace('PLN=X', '')] = float(data.iloc[-1])
        else:
            last_row = data.ffill().iloc[-1]
            for col in data.columns:
                curr_code = col.replace('PLN=X', '')
                rates[curr_code] = float(last_row[col])
    except Exception:
        for c in currencies:
            if c not in rates: rates[c] = 1.0
    return rates


def validate_ticker(ticker):
    ticker = ticker.upper().strip().replace('.PL', '.WA')
    try:
        test = yf.download(ticker, period="1d", progress=False)
        if test.empty:
            return None, f"Symbol {ticker} nieznany"
        return ticker, None
    except Exception:
        return None, "Błąd walidacji"


def get_currency_rate(pair):
    if not pair or "PLNPLN" in pair: return 1.0
    try:
        data = yf.download(pair, period="1d", progress=False)['Close']
        if not data.empty:
            return float(data.ffill().iloc[-1])
        return 1.0
    except Exception:
        return 1.0