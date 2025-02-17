import pandas as pd

class MovingAverageStrategy:
    def __init__(self, df):
        """
        传入固定的 df，并计算开仓和平仓信号
        """
        self.df = df.copy()
        self.calculate_signals()

    def calculate_signals(self):
        """计算 df 的开仓 & 平仓信号"""
        self.df['SMA_5'] = self.df['close'].rolling(window=5).mean()
        self.df['SMA_20'] = self.df['close'].rolling(window=20).mean()

        self.df['open_signal'] = 0
        self.df['close_signal'] = 0

        # **开仓信号**（短期均线上穿长期）
        self.df.loc[
            (self.df['SMA_5'].shift(1) <= self.df['SMA_20'].shift(1)) & (self.df['SMA_5'] > self.df['SMA_20']),
            'open_signal'
        ] = 1  # 开多
        self.df.loc[
            (self.df['SMA_5'].shift(1) >= self.df['SMA_20'].shift(1)) & (self.df['SMA_5'] < self.df['SMA_20']),
            'open_signal'
        ] = -1  # 开空

        # **平仓信号**（短期均线下穿长期）
        self.df.loc[
            (self.df['SMA_5'].shift(1) > self.df['SMA_20'].shift(1)) & (self.df['SMA_5'] <= self.df['SMA_20']),
            'close_signal'
        ] = -1  # 平多
        self.df.loc[
            (self.df['SMA_5'].shift(1) < self.df['SMA_20'].shift(1)) & (self.df['SMA_5'] >= self.df['SMA_20']),
            'close_signal'
        ] = 1  # 平空

    def get_strategy_df(self):
        """返回带有策略信号的 DataFrame"""
        return self.df
