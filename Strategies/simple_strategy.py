import pandas as pd

class SimpleMovingAverageStrategy:
    """
    简单的均线交叉策略：
    - 短期均线（5）上穿长期均线（20）：做多
    - 短期均线下穿长期均线：平仓
    """
    def __init__(self, short_window=5, long_window=20):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, df):
        """
        计算交易信号：
        - 1 表示持有多单
        - 0 表示不持有
        """
        df["short_ma"] = df["close"].rolling(self.short_window).mean()
        df["long_ma"] = df["close"].rolling(self.long_window).mean()

        df["signal"] = 0  # 初始状态无持仓
        df.loc[df["short_ma"] > df["long_ma"], "signal"] = 1  # 做多
        df.loc[df["short_ma"] <= df["long_ma"], "signal"] = 0  # 平仓

        return df
