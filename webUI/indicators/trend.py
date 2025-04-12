from .base import register_indicator
import ta

@register_indicator("MACD")
def calculate_macd(df, column='close', window_slow=26, window_fast=12, window_sign=9):
    macd = ta.trend.MACD(close=df[column], window_slow=window_slow, window_fast=window_fast, window_sign=window_sign)
    df[f'MACD_{window_fast}_{window_slow}'] = macd.macd()
    df[f'MACD_signal_{window_fast}_{window_slow}'] = macd.macd_signal()
    df[f'MACD_diff_{window_fast}_{window_slow}'] = macd.macd_diff()
    return df

@register_indicator("EMA")
def calculate_ema(df, column='close', window=14):
    df[f'EMA_{window}'] = ta.trend.EMAIndicator(close=df[column], window=window).ema_indicator()
    return df

@register_indicator("SMA")
def calculate_sma(df, column='close', window=14):
    df[f'SMA_{window}'] = ta.trend.SMAIndicator(close=df[column], window=window).sma_indicator()
    return df
