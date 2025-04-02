import pandas as pd
import numpy as np

class SpreadArbitrageStrategy:
    def __init__(self,
                 doge_df: pd.DataFrame,
                 btc_df: pd.DataFrame,
                 entry_threshold_low=0.005,
                 entry_threshold_high=0.04,
                 max_spread_15m=0.005,
                 position_ratio: float = 0.1):
        """
        :param doge_df: 包含 timestamp 和 OHLC 的 DataFrame
        :param btc_df: 同上
        """
        self.entry_threshold_low = entry_threshold_low
        self.entry_threshold_high = entry_threshold_high
        self.max_spread_15m = max_spread_15m
        self.position_ratio = position_ratio

        # 合并两个数据源
        df = pd.merge(
            doge_df[['timestamp', 'open', 'high', 'low', 'close']].rename(columns=lambda x: f'doge_{x}' if x != 'timestamp' else x),
            btc_df[['timestamp', 'open', 'high', 'low', 'close']].rename(columns=lambda x: f'btc_{x}' if x != 'timestamp' else x),
            on='timestamp'
        )

        # 构造特征
        df['btc_ret'] = df['btc_close'].pct_change(periods=576)
        df['doge_ret'] = df['doge_close'].pct_change(periods=576)
        df['spread_x'] = df['doge_ret'] - df['btc_ret']

        df['btc_volatility'] = df['btc_close'].rolling(16).apply(lambda x: (x.max() - x.min()) / x[0], raw=True)
        df['doge_volatility'] = df['doge_close'].rolling(16).apply(lambda x: (x.max() - x.min()) / x[0], raw=True)
        df['vol_diff'] = (df['doge_volatility'].rolling(288).mean() - df['btc_volatility'].rolling(288).mean()).abs()

        df['spread_15m'] = (df['doge_close'].pct_change(1) - df['btc_close'].pct_change(1)).abs().rolling(4).max()
        self.df = df.reset_index(drop=True)

    def generate_signal(self, index: int, balance: float, in_position: bool):
        """
        返回两个币的 signal:
          -> (direction, tp, sl, size, exit_flag, leverage)
        """
        if index < 576:
            return (0, None, None, 0, False, 1), (0, None, None, 0, False, 1)

        row = self.df.iloc[index]
        x = row['spread_x']
        z = row['vol_diff']
        k = row['spread_15m']

        vol_window = self.df.iloc[index - 192:index - 48]['doge_volatility']
        if vol_window.isna().any():
            return (0, None, None, 0, False, 1), (0, None, None, 0, False, 1)
        vol = vol_window.max()

        # 🧠 动态杠杆
        if 0.05 <= vol <= 0.2:
            dynamic_leverage = 3
        elif 0.01 <= vol < 0.05:
            dynamic_leverage = 5
        elif vol < 0.01:
            dynamic_leverage = 10
        else:
            dynamic_leverage = 1

        # 🧹 过滤条件
        if z < self.entry_threshold_low or z > self.entry_threshold_high:
            return (0, None, None, 0, False, 1), (0, None, None, 0, False, 1)
        if k < self.max_spread_15m:
            return (0, None, None, 0, False, 1), (0, None, None, 0, False, 1)

        # ✅ 开仓逻辑
        if not in_position:
            if x > 0:
                doge_dir, btc_dir = 1, -1
            elif x < 0:
                doge_dir, btc_dir = -1, 1
            else:
                return (0, None, None, 0, False, 1), (0, None, None, 0, False, 1)

            doge_size = (balance * self.position_ratio * dynamic_leverage) / row['doge_close']
            btc_size = (balance * self.position_ratio * dynamic_leverage) / row['btc_close']

            return (
                (doge_dir, None, None, doge_size, False, dynamic_leverage),
                (btc_dir, None, None, btc_size, False, dynamic_leverage)
            )

        # ✅ 平仓逻辑（简单用 dummy）
        else:
            return (
                (0, None, None, 0, True, 1),
                (0, None, None, 0, True, 1)
            )
