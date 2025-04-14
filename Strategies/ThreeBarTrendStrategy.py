import pandas as pd

class ThreeBarTrendStrategy:
    def __init__(self, 
                 df: pd.DataFrame, 
                 position_ratio: float = 0.5, 
                 tp_rate: float = 0.01, 
                 sl_rate: float = 0.005):
        self.df = df.copy()
        self.position_ratio = position_ratio
        self.tp_rate = tp_rate
        self.sl_rate = sl_rate
        self.warmup_period = 3

    def generate_signal(self, index: int, current_balance: float, leverage: float = 1.0, current_position: int = 0):
        if index < self.warmup_period:
            return (0, None, None, 0, 0, 1.0)

        prev_closes = self.df["close"].iloc[index-3:index]
        current_price = self.df["close"].iloc[index]

        # 连续上涨
        if prev_closes.is_monotonic_increasing:
            direction = 1
        # 连续下跌
        elif prev_closes.is_monotonic_decreasing:
            direction = -1
        else:
            return (0, None, None, 0, 0, 1.0)

        if direction == current_position:
            return (0, None, None, 0, 0, 1.0)

        # 计算下单量
        nominal_value = current_balance * self.position_ratio * leverage
        position_size = nominal_value / current_price

        # 止盈止损
        if direction == 1:
            take_profit = current_price * (1 + self.tp_rate)
            stop_loss = current_price * (1 - self.sl_rate)
        else:
            take_profit = current_price * (1 - self.tp_rate)
            stop_loss = current_price * (1 + self.sl_rate)

        return (direction, take_profit, stop_loss, position_size, 0, 1.0)
