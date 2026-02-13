import pandas as pd
import numpy as np

def calculate_portfolio_history(df, hist_prices, hist_fx):
    if hist_prices.empty: return pd.Series(), pd.Series(), {}
    total_equity = pd.Series(0.0, index=hist_prices.index)
    total_cost = pd.Series(0.0, index=hist_prices.index)
    equity_dict = {}

    for _, row in df.iterrows():
        symbol, currency, buy_date = row['Symbol'], row['Waluta'], pd.to_datetime(row['Data_Zakupu'])
        if symbol not in hist_prices.columns: continue

        fx_history = 1.0
        if currency != 'PLN':
            fx_col = f"{currency}PLN=X"
            if fx_col in hist_fx.columns: fx_history = hist_fx[fx_col].reindex(hist_prices.index).ffill().bfill()

        pos_value = (hist_prices[symbol] * row['Ilosc'] * fx_history)
        pos_cost = pd.Series(0.0, index=hist_prices.index)
        mask = pos_cost.index >= buy_date
        pos_cost[mask] = row['Kwota_Poczatkowa_PLN']
        pos_value[~mask] = 0

        total_equity += pos_value
        total_cost += pos_cost
        equity_dict[symbol] = equity_dict.get(symbol, 0) + pos_value

    return total_equity, total_cost, equity_dict