# backtest_martingale.py
import pandas as pd
import numpy as np
import talib

class MartingaleBacktest:
    def __init__(self, df, short_window, long_window, atr_tp_multiplier, atr_sl_multiplier, breakout_period, leverage_list, position_list):
        self.df = df.copy()
        self.short_window = short_window
        self.long_window = long_window
        self.atr_tp_multiplier = atr_tp_multiplier
        self.atr_sl_multiplier = atr_sl_multiplier
        self.breakout_period = breakout_period
        self.leverage_list = leverage_list
        self.position_list = position_list

        self.initial_balance = 10000
        self.balance = self.initial_balance
        self.max_drawdown = 0
        self.trade_log = []

        self.position = 0  # 当前仓位方向（1多，-1空，0无仓）
        self.avg_price = 0
        self.current_level = 0  # 马丁格尔层级

    def calculate_indicators(self):
        self.df['ATR'] = talib.ATR(self.df['high'], self.df['low'], self.df['close'], timeperiod=14)
        self.df['short_ma'] = self.df['close'].rolling(self.short_window).mean()
        self.df['long_ma'] = self.df['close'].rolling(self.long_window).mean()
        self.df['high_break'] = self.df['high'].rolling(self.breakout_period).max()
        self.df['low_break'] = self.df['low'].rolling(self.breakout_period).min()

    def open_position(self, index, direction):
        self.position = direction
        self.avg_price = self.df['close'].iloc[index]
        self.current_level = 0
        size = self.position_list[self.current_level] * self.balance * self.leverage_list[self.current_level] / self.df['close'].iloc[index]
        self.trade_log.append({'time': self.df['timestamp'].iloc[index], 'action': 'open', 'price': self.avg_price, 'size': size, 'level': self.current_level})

    def add_position(self, index):
        self.current_level += 1
        if self.current_level >= len(self.leverage_list):
            self.current_level = len(self.leverage_list) - 1  # 防止越界

        size = self.position_list[self.current_level] * self.balance * self.leverage_list[self.current_level] / self.df['close'].iloc[index]
        self.avg_price = (self.avg_price + self.df['close'].iloc[index]) / 2
        self.trade_log.append({'time': self.df['timestamp'].iloc[index], 'action': 'add', 'price': self.df['close'].iloc[index], 'size': size, 'level': self.current_level})

    def close_position(self, index):
        close_price = self.df['close'].iloc[index]
        profit = self.position * (close_price - self.avg_price) * sum([log['size'] for log in self.trade_log if log['level'] <= self.current_level])

        self.balance += profit
        drawdown = (self.initial_balance - self.balance) / self.initial_balance
        self.max_drawdown = max(self.max_drawdown, drawdown)

        self.trade_log.append({'time': self.df['timestamp'].iloc[index], 'action': 'close', 'price': close_price, 'profit': profit})

        self.position = 0
        self.avg_price = 0
        self.current_level = 0

    def run(self):
        self.calculate_indicators()

        for i in range(self.long_window, len(self.df)):
            row = self.df.iloc[i]

            # 判断开仓条件
            if self.position == 0:
                if row['short_ma'] > row['long_ma'] and row['close'] > row['high_break']:
                    self.open_position(i, 1)
                elif row['short_ma'] < row['long_ma'] and row['close'] < row['low_break']:
                    self.open_position(i, -1)

            # 判断加仓和止损
            elif self.position != 0:
                atr = row['ATR']
                tp = self.avg_price + self.position * atr * self.atr_tp_multiplier
                sl = self.avg_price - self.position * atr * self.atr_sl_multiplier

                if self.position == 1 and row['close'] >= tp:
                    self.close_position(i)
                elif self.position == -1 and row['close'] <= tp:
                    self.close_position(i)
                elif self.position == 1 and row['close'] <= sl:
                    self.add_position(i)
                elif self.position == -1 and row['close'] >= sl:
                    self.add_position(i)

        sharpe = self.calculate_sharpe()
        return self.balance, self.max_drawdown, sharpe

    def calculate_sharpe(self):
        daily_returns = pd.Series([log.get('profit', 0) / self.balance for log in self.trade_log])
        if len(daily_returns) < 2 or daily_returns.std() == 0:
            return 0
        sharpe = daily_returns.mean() / daily_returns.std() * (252**0.5)
        return sharpe
