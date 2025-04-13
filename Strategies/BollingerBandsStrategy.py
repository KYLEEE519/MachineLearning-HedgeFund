import pandas as pd

class BollingerBandsStrategy:
    def __init__(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0, position_ratio: float = 1.0, tp_rate: float = 0.02, sl_rate: float = 0.01):
        self.df = df.copy()
        self.period = period
        self.std_dev = std_dev
        self.position_ratio = position_ratio
        self.tp_rate = tp_rate
        self.sl_rate = sl_rate
        self.warmup_period = period
        self.df['ma'] = self.df['close'].rolling(window=self.period).mean()
        self.df['std'] = self.df['close'].rolling(window=self.period).std()
        self.df['upper'] = self.df['ma'] + self.std_dev * self.df['std']
        self.df['lower'] = self.df['ma'] - self.std_dev * self.df['std']

    def generate_signal(self, index: int, current_balance: float, leverage: float = 1.0, current_position: int = 0):
        if index < self.warmup_period:
            return (0, None, None, 0, False)

        row = self.df.iloc[index]
        prev = self.df.iloc[index - 1]

        if pd.isna(row['upper']) or pd.isna(row['lower']) or pd.isna(prev['upper']) or pd.isna(prev['lower']):
            return (0, None, None, 0, False)

        long_condition = prev['close'] > prev['lower'] and row['close'] < row['lower']
        short_condition = prev['close'] < prev['upper'] and row['close'] > row['upper']

        if long_condition:
            direction = 1
        elif short_condition:
            direction = -1
        else:
            return (0, None, None, 0, False)

        if direction == current_position:
            return (0, None, None, 0, False)

        entry_price = row['close']
        nominal_value = current_balance * self.position_ratio * leverage
        position_size = nominal_value / entry_price

        if direction == 1:
            take_profit = entry_price * (1 + self.tp_rate)
            stop_loss = entry_price * (1 - self.sl_rate)
        else:
            take_profit = entry_price * (1 - self.tp_rate)
            stop_loss = entry_price * (1 + self.sl_rate)

        return (direction, take_profit, stop_loss, position_size, False)