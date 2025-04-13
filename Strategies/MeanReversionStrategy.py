import pandas as pd

class MeanReversionStrategy:
    def __init__(self, df: pd.DataFrame, ma_short: int = 10, ma_long: int = 20, position_ratio: float = 0.6):
        self.df = df.copy()
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.position_ratio = position_ratio
        self.df['ma_short'] = self.df['close'].rolling(ma_short).mean()
        self.df['ma_long'] = self.df['close'].rolling(ma_long).mean()
        self.warmup_period = ma_long

    def generate_signal(self, index: int, current_balance: float, leverage: float = 1.0, current_position: int = 0):
        if index < self.warmup_period:
            return (0, None, None, 0, False)
        
        row = self.df.iloc[index]
        prev = self.df.iloc[index - 1]
        
        if pd.isna(row['ma_short']) or pd.isna(prev['ma_short']) or pd.isna(row['ma_long']):
            return (0, None, None, 0, False)
        
        long_condition = prev['close'] > prev['ma_short'] and row['close'] <= row['ma_short']
        exit_condition = current_position > 0 and row['close'] > row['ma_long']
        
        if long_condition:
            direction = 1
            exit_signal = False
        elif exit_condition:
            direction = 0
            exit_signal = True
        else:
            return (0, None, None, 0, False)
        
        if current_position == direction:
            return (0, None, None, 0, False)
        
        entry_price = row['close']
        nominal_value = current_balance * self.position_ratio * leverage
        position_size = nominal_value / entry_price
        
        return (direction, None, None, position_size, exit_signal)