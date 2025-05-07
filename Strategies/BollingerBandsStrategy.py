import pandas as pd

class BollingerBandsStrategy:
    def __init__(self, df: pd.DataFrame, n_periods: int = 20, multiplier: float = 2.0, position_ratio: float = 0.5):
        self.df = df.copy()
        self.n_periods = n_periods
        self.multiplier = multiplier
        self.position_ratio = position_ratio
        self.warmup_period = n_periods

        # Calculate Bollinger Bands
        self.df['middle_band'] = self.df['close'].rolling(window=self.n_periods).mean()
        self.df['stddev'] = self.df['close'].rolling(window=self.n_periods).std()
        self.df['upper_band'] = self.df['middle_band'] + (self.multiplier * self.df['stddev'])
        self.df['lower_band'] = self.df['middle_band'] - (self.multiplier * self.df['stddev'])

    def generate_signal(self, index: int, current_balance: float, leverage: float = 1.0, current_position: int = 0):
        if index < self.warmup_period:
            return (0, None, None, 0, False)
        
        row = self.df.iloc[index]
        prev = self.df.iloc[index - 1]
        
        if pd.isna(row['upper_band']) or pd.isna(row['lower_band']):
            return (0, None, None, 0, False)

        # Buy condition: Price crosses above lower band
        buy_condition = (prev['close'] < prev['lower_band']) and (row['close'] > row['lower_band'])
        # Sell condition: Price crosses below upper band
        sell_condition = (prev['close'] > prev['upper_band']) and (row['close'] < row['upper_band'])

        if buy_condition:
            direction = 1
            exit_signal = True
        elif sell_condition:
            direction = -1
            exit_signal = True
        else:
            return (0, None, None, 0, False)

        if current_position == direction:
            return (0, None, None, 0, False)
        
        entry_price = row['close']
        nominal_value = current_balance * self.position_ratio * leverage
        position_size = nominal_value / entry_price

        return (direction, None, None, position_size, exit_signal)