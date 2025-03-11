import pandas as pd
import numpy as np

class BollingerStrategy:
    def __init__(self, 
                 df,  # 新增参数
                 initial_balance=10000,
                 leverage=10,
                 position_ratio=0.1,
                 open_fee_rate=0.0005,
                 close_fee_rate=0.0005,
                 take_profit_ratio=0.01,
                 stop_loss_ratio=0.01,
                 bb_window=20,
                 bb_std_mult=3):
        
        # 资金参数
        self.balance = initial_balance
        self.leverage = leverage
        self.position_ratio = position_ratio
        
        # 费用参数
        self.open_fee_rate = open_fee_rate
        self.close_fee_rate = close_fee_rate
        
        # 风险参数
        self.take_profit_ratio = take_profit_ratio  
        self.stop_loss_ratio = stop_loss_ratio      
        
        # 布林带参数
        self.bb_window = bb_window
        self.bb_std_mult = bb_std_mult
        
        # 存储数据
        self.df = df.copy()
        self.df = self.calculate_bollinger_bands(self.df)

    def calculate_bollinger_bands(self, df):
        """计算布林带指标"""
        df = df.copy()
        df['ma'] = df['close'].rolling(self.bb_window).mean()
        df['std'] = df['close'].rolling(self.bb_window).std(ddof=0)
        df['upper'] = df['ma'] + df['std'] * self.bb_std_mult
        df['lower'] = df['ma'] - df['std'] * self.bb_std_mult
        return df

    def generate_signal(self, index):
        """
        生成交易信号和止盈止损价格
        index: 当前K线索引
        返回: (signal, take_profit_price, stop_loss_price, position_size)
        """
        if index < self.bb_window:
            return 0, None, None, None

        current = self.df.iloc[index]
        prev = self.df.iloc[index - 1]
        signal = 0

        # 做空信号
        if prev['high'] < prev['upper'] and current['high'] >= current['upper']:
            signal = -1
            
        # 做多信号
        elif prev['low'] > prev['lower'] and current['low'] <= current['lower']:
            signal = 1
            
        else:
            return 0, None, None, None
        
        # 以当前收盘价作为开仓价格
        entry_price = current['close']
        
        if entry_price <= 0:
            return 0, None, None, None
        
        # 计算仓位
        position_value = self.balance * self.position_ratio * self.leverage
        position_size = round(position_value / entry_price / 10) * 10  # 取整为10的倍数
        
        # 计算手续费
        open_fee = position_size * entry_price * self.open_fee_rate
        
        # 计算目标盈利和最大亏损（基于总资金）
        target_profit = self.balance * self.take_profit_ratio
        max_loss = self.balance * self.stop_loss_ratio
        
        # 计算止盈止损价格
        if signal == 1:  # 做多
            take_profit_price = (target_profit + (entry_price * position_size) + open_fee) / (position_size * (1 - self.close_fee_rate))
            stop_loss_price = ((entry_price * position_size) - max_loss - open_fee - max_loss * self.close_fee_rate) / position_size
        elif signal == -1:  # 做空
            take_profit_price = ((entry_price * position_size) - target_profit - open_fee) / (position_size * (1 + self.close_fee_rate))
            stop_loss_price = (max_loss + (entry_price * position_size) + open_fee + max_loss * self.close_fee_rate) / position_size

        return signal, round(take_profit_price, 4), round(stop_loss_price, 4), position_size
