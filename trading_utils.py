from decimal import *
from trading.trade import Trade

def calculate_bollinger_bands(df, window, std_dev):
    df['middle_band'] = df['close'].rolling(window).mean()
    df['upper_band'] = df['middle_band'] + std_dev * df['close'].rolling(window).std()
    df['lower_band'] = df['middle_band'] - std_dev * df['close'].rolling(window).std()
    return df

def is_overbought(last_row):
    return last_row['close'] > last_row['upper_band'] and last_row['RSI'] > 70 and last_row['MACD_signal'] < last_row['MACD']

def is_oversold(last_row):
    return last_row['close'] < last_row['lower_band'] and last_row['RSI'] < 32 and last_row['MACD_signal'] > last_row['MACD']


def calculate_cost_basis(ticker, trades): 
    avg_position = Trade(ticker=ticker, price=Decimal(0), shares=Decimal(0), fee=Decimal(0))

    for trade in trades:
        price = Decimal(trade['average'])
        shares = Decimal(trade['filled'])
        fee = Decimal(trade['fee']['cost'])
        avg_position.updateCostBasis(price=price, shares=shares, fee=fee)

    return avg_position