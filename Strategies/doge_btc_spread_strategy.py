import pandas as pd
import numpy as np

class DogeBTCSpreadStrategy:
    def __init__(self, df: pd.DataFrame,
                 entry_threshold_low=0.005, entry_threshold_high=0.04,
                 max_spread_15m=0.005,
                 position_ratio: float = 0.5):
        """
        df: 包含['timestamp', 'btc_close', 'doge_close']的K线数据，频率为15分钟
        entry_threshold_low: 进入交易的最低振幅差
        entry_threshold_high: 进入交易的最高振幅差
        max_spread_15m: 15分钟内最大涨幅差的最小阈值
        position_ratio: 仓位使用比例
        """
        self.df = df.copy()
        self.entry_threshold_low = entry_threshold_low
        self.entry_threshold_high = entry_threshold_high
        self.max_spread_15m = max_spread_15m
        self.position_ratio = position_ratio

        self.df['btc_ret'] = self.df['btc_close'].pct_change(periods=576)
        self.df['doge_ret'] = self.df['doge_close'].pct_change(periods=576)
        self.df['spread_x'] = self.df['doge_ret'] - self.df['btc_ret']

        self.df['btc_volatility'] = self.df['btc_close'].rolling(16).apply(lambda x: (x.max()-x.min()) / x[0], raw=True)
        self.df['doge_volatility'] = self.df['doge_close'].rolling(16).apply(lambda x: (x.max()-x.min()) / x[0], raw=True)


        self.df['vol_diff'] = (self.df['doge_volatility'].rolling(288).mean() - self.df['btc_volatility'].rolling(288).mean()).abs()
        self.df['spread_15m'] = (self.df['doge_close'].pct_change(1) - self.df['btc_close'].pct_change(1)).abs().rolling(4).max()

    def generate_signal(self, 
                        index: int, 
                        current_balance: float, 
                        leverage: float = 1.0,
                        current_position: int = 0):
        """
        返回 (direction, take_profit, stop_loss, position_size, exit_signal)
        direction: 1=多DOGE空BTC, -1=空DOGE多BTC
        """
        if index < 576:
            return (0, None, None, 0, False)

        row = self.df.iloc[index]
        x = row['spread_x']
        z = row['vol_diff']
        k = row['spread_15m']

        # 判断 DOGE 的 3日最大 4小时振幅决定杠杆
        vol = self.df.iloc[index - 192:index - 48]['doge_volatility'].max()
        if 0.05 <= vol <= 0.2:
            dynamic_leverage = 3
        elif 0.01 <= vol < 0.05:
            dynamic_leverage = 5
        elif vol < 0.01:
            dynamic_leverage = 10
        else:
            dynamic_leverage = 1

        if z < self.entry_threshold_low or z > self.entry_threshold_high:
            return (0, None, None, 0, False)
        if k < self.max_spread_15m:
            return (0, None, None, 0, False)

        if x > 0:
            direction = 1
            exit_signal = True
        elif x < 0:
            direction = -1
            exit_signal = True
        else:
            return (0, None, None, 0, False)

        if current_position == direction:
            print(f"[{row['timestamp']}] 信号 {direction} 但已有持仓 {current_position}，忽略本次交易")
            return (0, None, None, 0, False)

        entry_price = row['doge_close']
        if entry_price <= 0:
            return (0, None, None, 0, False)

        nominal_value = current_balance * self.position_ratio * dynamic_leverage
        position_size = nominal_value / entry_price

        if position_size <= 0:
            return (0, None, None, 0, False)

        return direction, None, None, position_size, exit_signal