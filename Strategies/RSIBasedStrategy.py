import pandas as pd

class RSIBasedStrategy:
    def __init__(self, 
                 df: pd.DataFrame, 
                 rsi_period: int = 14,
                 position_ratio: float = 0.5):
        """
        参数:
          - rsi_period: RSI计算周期
          - position_ratio: 开仓所用资金比例
        """
        self.df = df.copy()
        self.rsi_period = rsi_period
        self.position_ratio = position_ratio

        delta = self.df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(rsi_period).mean()
        avg_loss = loss.rolling(rsi_period).mean()
        rs = avg_gain / avg_loss
        self.df["rsi"] = 100 - (100 / (1 + rs))

        self.warmup_period = rsi_period + 1

    def generate_signal(self, 
                        index: int, 
                        current_balance: float, 
                        leverage: float = 1.0,
                        current_position: int = 0):
        if index < self.warmup_period:
            return (0, None, None, 0, False)

        row = self.df.iloc[index]
        rsi = row["rsi"]

        # 判断信号
        if rsi < 30:
            direction = 1
            exit_signal = True
        elif rsi > 70:
            direction = -1
            exit_signal = True
        else:
            return (0, None, None, 0, False)

        # 若已有相同方向仓位，忽略信号
        if direction == current_position:
            return (0, None, None, 0, False)

        entry_price = row["close"]
        nominal_value = current_balance * self.position_ratio * leverage
        position_size = nominal_value / entry_price

        return (direction, None, None, position_size, exit_signal)