import yfinance as yf
import pandas as pd
import streamlit as st
import requests
from datetime import datetime, timedelta
from core.metrics import clean_timezone

def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

@st.cache_data(ttl=3600)
def get_market_data(tickers, start_date):
    if not tickers: return pd.DataFrame()
    try:
        data = yf.download(tickers, start=start_date, progress=False, session=get_session())['Close']
        if isinstance(data, pd.Series):
            data = data.to_frame()
            data.columns = tickers
        return clean_timezone(data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_live_prices(tickers):
    if not tickers: return {}
    try:
        data = yf.download(tickers, period="1d", progress=False, session=get_session())['Close']
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
        data = yf.download(search_list, start=start_date, progress=False, session=get_session())['Close']
        if isinstance(data, pd.Series):
            data = data.to_frame()
            data.columns = search_list
        return clean_timezone(data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=900)
def get_live_currencies(currencies):
    rates = {'PLN': 1.0}
    to_fetch = [f"{c}PLN=X" for c in currencies if c != 'PLN']
    if not to_fetch: return rates

    try:
        data = yf.download(to_fetch, period="1d", progress=False, session=get_session())['Close']
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

@st.cache_data(ttl=86400) 
def validate_ticker(ticker):
    ticker = ticker.upper().strip().replace('.PL', '.WA')
    try:
        test = yf.download(ticker, period="1d", progress=False, session=get_session())
        if test.empty:
            return None, f"Symbol {ticker} nieznany"
        return ticker, None
    except Exception:
        return None, "Błąd walidacji"

@st.cache_data(ttl=3600)
def get_currency_rate(pair):
    if not pair or "PLNPLN" in pair: return 1.0
    try:
        data = yf.download(pair, period="1d", progress=False, session=get_session())['Close']
        if not data.empty:
            return float(data.ffill().iloc[-1])
        return 1.0
    except Exception:
        return 1.0
