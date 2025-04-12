from .base import register_indicator
import ta

@register_indicator("BOLL")
def calculate_boll(df, column='close', window=20, std=2):
    boll = ta.volatility.BollingerBands(close=df[column], window=window, window_dev=std)
    df[f'BOLL_upper_{window}'] = boll.bollinger_hband()
    df[f'BOLL_lower_{window}'] = boll.bollinger_lband()
    df[f'BOLL_middle_{window}'] = boll.bollinger_mavg()
    return df

@register_indicator("ATR")
def calculate_atr(df, column='close', window=14):
    df[f'ATR_{window}'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df[column], window=window).average_true_range()
    return df
