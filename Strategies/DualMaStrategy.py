import pandas as pd

class DualMaStrategy:
    def __init__(self, 
                 df: pd.DataFrame, 
                 fast_ma: int,
                 slow_ma: int,
                 position_ratio: float,
                 tp_rate: float,
                 sl_rate: float):
        self.df = df.copy()
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.position_ratio = position_ratio
        self.tp_rate = tp_rate
        self.sl_rate = sl_rate

        self.df["fast_ma"] = self.df["close"].rolling(fast_ma).mean()
        self.df["slow_ma"] = self.df["close"].rolling(slow_ma).mean()
        self.warmup_period = max(fast_ma, slow_ma)

    def generate_signal(self, index: int, current_balance: float, leverage: float = 1.0, current_position: int = 0):
        if index < self.slow_ma:
            return (0, None, None, 0, 0, 1.0)  # 无信号

        row = self.df.iloc[index]
        prev = self.df.iloc[index - 1]

        if pd.isna(row["fast_ma"]) or pd.isna(row["slow_ma"]) or pd.isna(prev["fast_ma"]) or pd.isna(prev["slow_ma"]):
            return (0, None, None, 0, 0, 1.0)

        long_condition = prev["fast_ma"] <= prev["slow_ma"] and row["fast_ma"] > row["slow_ma"]
        short_condition = prev["fast_ma"] >= prev["slow_ma"] and row["fast_ma"] < row["slow_ma"]

        # 无信号就什么都不做
        if not long_condition and not short_condition:
            return (0, None, None, 0, 0, 1.0)

        direction = 1 if long_condition else -1

        # 如果已有持仓方向相同，则不重复开仓
        if direction == current_position:
            return (0, None, None, 0, 0, 1.0)

        entry_price = row["close"]
        nominal_value = current_balance * self.position_ratio * leverage
        position_size = nominal_value / entry_price

        # 设置止盈止损
        if direction == 1:
            take_profit = entry_price * (1 + self.tp_rate)
            stop_loss = entry_price * (1 - self.sl_rate)
        else:
            take_profit = entry_price * (1 - self.tp_rate)
            stop_loss = entry_price * (1 + self.sl_rate)

        return (direction, take_profit, stop_loss, position_size, 0, 1.0)
