import pandas as pd

class Ma20Strategy:
    def __init__(self, 
                 df: pd.DataFrame, 
                 ma_length: int = 20,
                 position_ratio: float = 0.5):
        self.df = df.copy()
        self.ma_length = ma_length
        self.warmup_period = ma_length
        self.position_ratio = position_ratio
        self.df['ma'] = self.df['close'].rolling(self.ma_length).mean()

    def generate_signal(self, 
                        index: int, 
                        current_balance: float, 
                        leverage: float = 1.0,
                        current_position: int = 0):
        if index < self.ma_length:
            return (0, None, None, 0, 0, 1.0)

        row = self.df.iloc[index]
        prev = self.df.iloc[index - 1]

        if pd.isna(row['ma']) or pd.isna(prev['ma']):
            return (0, None, None, 0, 0, 1.0)

        long_condition = (prev['low'] <= prev['ma']) and (row['low'] > row['ma'])
        short_condition = (prev['high'] >= prev['ma']) and (row['high'] < row['ma'])

        if long_condition:
            direction = 1
        elif short_condition:
            direction = -1
        else:
            return (0, None, None, 0, 0, 1.0)

        if current_position == direction:
            print(f"[{row['timestamp']}] 信号 {direction} 但已有持仓 {current_position}，忽略本次交易")
            return (0, None, None, 0, 0, 1.0)

        exit_signal = -direction  # 先平掉相反方向的持仓

        entry_price = row['close']
        if entry_price <= 0:
            return (0, None, None, 0, 0, 1.0)

        nominal_value = current_balance * self.position_ratio * leverage
        position_size = nominal_value / entry_price
        if position_size <= 0:
            return (0, None, None, 0, 0, 1.0)

        return direction, None, None, position_size, exit_signal, 1.0
