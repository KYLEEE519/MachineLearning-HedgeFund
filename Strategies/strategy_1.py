import pandas as pd

class VolatilityStrategy:
    def __init__(self, df, params=None):
        """
        传入 df 和参数 params，并计算开仓信号（去重）
        """
        # 默认参数
        default_params = {
            "volatility_window": 5,       # 波动率计算窗口
            "volatility_threshold": 0.005,  # 波动率阈值(如0.5%)
            "ma_window": 5               # 均线计算窗口
        }

        # 合并默认参数和传入参数
        self.params = default_params if params is None else {**default_params, **params}

        # 复制数据
        self.df = df.copy()

        # 计算信号
        self.calculate_signals()

    def calculate_signals(self):
        """计算 df 的开仓信号（去除重复信号）"""
        p = self.params

        # 计算波动率
        self.df['window_high'] = self.df['high'].rolling(window=p['volatility_window']).max()
        self.df['window_low'] = self.df['low'].rolling(window=p['volatility_window']).min()
        self.df['window_open'] = self.df['open'].shift(p['volatility_window'] - 1)
        self.df['volatility'] = (self.df['window_high'] - self.df['window_low']) / self.df['window_open']

        # 计算移动均线
        self.df['ma'] = self.df['close'].rolling(window=p['ma_window']).mean()

        # 计算买卖信号（初步）
        self.df['raw_buy'] = (self.df['volatility'] >= p['volatility_threshold']) & (self.df['close'] < self.df['ma'])
        self.df['raw_sell'] = (self.df['volatility'] >= p['volatility_threshold']) & (self.df['close'] > self.df['ma'])

        # 生成去重的开仓信号
        self.df['open_signal'] = 0

        # 只在趋势首次发生时开仓
        self.df.loc[(self.df['raw_buy']) & (~self.df['raw_buy'].shift(1).fillna(False)), 'open_signal'] = 1  # 开多
        self.df.loc[(self.df['raw_sell']) & (~self.df['raw_sell'].shift(1).fillna(False)), 'open_signal'] = -1  # 开空

        # 直接将平仓信号设为 0（不计算平仓）
        self.df['close_signal'] = 0

    def get_strategy_df(self):
        """返回带有策略信号的 DataFrame"""
        return self.df[['timestamp', 'open', 'high', 'low', 'close', 'volatility', 'open_signal', 'close_signal']]
