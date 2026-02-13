import pandas as pd
from datetime import datetime, date


def safe_float(val):
    try:
        if val is None: return 0.0
        if isinstance(val, (int, float)): return float(val)
        val = str(val).replace(',', '.').replace(' ', '').strip()
        return float(val) if val != "" else 0.0
    except:
        return 0.0


def safe_date(val):
    try:
        if isinstance(val, (datetime, date)): return val if isinstance(val, date) else val.date()
        val = str(val).strip()
        for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y.%m.%d'):
            try:
                return datetime.strptime(val, fmt).date()
            except:
                continue
    except:
        pass
    return datetime.now().date()


def calculate_portfolio_metrics(df, hist_prices, live_prices_map, live_fx_map):
    df = df.copy()

    def get_price(symbol):
        price = live_prices_map.get(symbol, 0.0)

        if price <= 0 and not hist_prices.empty and symbol in hist_prices.columns:
            price = hist_prices[symbol].ffill().iloc[-1]

        return float(price) if pd.notna(price) else 0.0

    df['Cena_Live'] = df['Symbol'].apply(get_price)
    df['Kurs_Live'] = df['Waluta'].apply(lambda c: live_fx_map.get(c, 1.0))

    df['Wartosc_PLN'] = df['Ilosc'] * df['Cena_Live'] * df['Kurs_Live']

    df['Zysk_PLN'] = df.apply(
        lambda r: r['Wartosc_PLN'] - r['Kwota_Poczatkowa_PLN'] if r['Cena_Live'] > 0 else 0.0,
        axis=1
    )

    df['Zysk_Proc'] = df.apply(
        lambda r: (r['Zysk_PLN'] / r['Kwota_Poczatkowa_PLN'] * 100)
        if (r['Kwota_Poczatkowa_PLN'] > 0 and r['Cena_Live'] > 0) else 0.0,
        axis=1
    )

    return df


def calculate_portfolio_history(df, hist_prices, hist_fx):
    if hist_prices.empty: return pd.Series(), pd.Series(), {}

    total_equity = pd.Series(0.0, index=hist_prices.index)
    total_cost = pd.Series(0.0, index=hist_prices.index)
    equity_map = {}

    for _, row in df.iterrows():
        symbol = row['Symbol']
        currency = row['Waluta']
        buy_date = pd.to_datetime(row['Data_Zakupu'])

        if symbol not in hist_prices.columns: continue

        asset_prices = hist_prices[symbol].ffill().bfill()

        fx_history = pd.Series(1.0, index=hist_prices.index)
        if currency != 'PLN':
            fx_col = f"{currency}PLN=X"
            found_col = next((c for c in hist_fx.columns if fx_col in c or currency in c), None)

            if found_col:
                fx_history = hist_fx[found_col].reindex(hist_prices.index).ffill().bfill()
            else:
                # Jeśli nadal nie mamy kursu, nie pozwólmy na 1.0 dla USD/EUR!
                # Możesz tu dodać logikę pobierania awaryjnego lub st.warning
                pass

        pos_val = (asset_prices * row['Ilosc'] * fx_history)
        pos_cost = pd.Series(0.0, index=hist_prices.index)

        mask = pos_val.index >= buy_date
        pos_cost[mask] = row['Kwota_Poczatkowa_PLN']
        pos_val[~mask] = 0

        total_equity = total_equity.add(pos_val, fill_value=0)
        total_cost = total_cost.add(pos_cost, fill_value=0)

        equity_map[symbol] = equity_map.get(symbol, pd.Series(0.0, index=hist_prices.index)).add(pos_val, fill_value=0)

    return total_equity, total_cost, equity_map

def clean_timezone(df):
    if isinstance(df.index, pd.DatetimeIndex):
        df.index = df.index.tz_localize(None)
    return df