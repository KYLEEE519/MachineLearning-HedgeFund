# class BollingerStrategy:
#     def __init__(self, 
#                  df,  # 新增参数
#                  initial_balance=10000,
#                  leverage=10,
#                  position_ratio=0.1,
#                  open_fee_rate=0.0005,
#                  close_fee_rate=0.0005,
#                  take_profit_ratio=0.01,
#                  stop_loss_ratio=0.01,
#                  bb_window=20,
#                  bb_std_mult=3):
        
#         # 资金参数
#         self.balance = initial_balance
#         self.leverage = leverage
#         self.position_ratio = position_ratio
        
#         # 费用参数
#         self.open_fee_rate = open_fee_rate
#         self.close_fee_rate = close_fee_rate
        
#         # 风险参数
#         self.take_profit_ratio = take_profit_ratio  
#         self.stop_loss_ratio = stop_loss_ratio      
        
#         # 布林带参数
#         self.bb_window = bb_window
#         self.bb_std_mult = bb_std_mult
        
#         # 存储数据
#         self.df = df.copy()
#         self.df = self.calculate_bollinger_bands(self.df)

#     def calculate_bollinger_bands(self, df):
#         """计算布林带指标"""
#         df = df.copy()
#         df['ma'] = df['close'].rolling(self.bb_window).mean()
#         df['std'] = df['close'].rolling(self.bb_window).std(ddof=0)
#         df['upper'] = df['ma'] + df['std'] * self.bb_std_mult
#         df['lower'] = df['ma'] - df['std'] * self.bb_std_mult
#         return df

#     def update_balance(self, new_balance):
#         """
#         更新策略内部的余额信息，以便后续计算仓位时使用最新余额
#         """
#         self.balance = new_balance

#     def generate_signal(self, index):
#         """
#         生成交易信号和止盈止损价格
#         index: 当前K线索引
#         返回: (signal, take_profit_price, stop_loss_price, position_size)
#         """
#         if index < self.bb_window:
#             return 0, None, None, None

#         current = self.df.iloc[index]
#         prev = self.df.iloc[index - 1]
#         signal = 0

#         # 做空信号
#         if prev['high'] < prev['upper'] and current['high'] >= current['upper']:
#             signal = -1
            
#         # 做多信号
#         elif prev['low'] > prev['lower'] and current['low'] <= current['lower']:
#             signal = 1
#         else:
#             return 0, None, None, None
        
#         # 以当前收盘价作为开仓价格
#         entry_price = current['close']
#         if entry_price <= 0:
#             return 0, None, None, None
        
#         # 使用最新的余额来计算仓位
#         position_value = self.balance * self.position_ratio * self.leverage
#         position_size = round(position_value / entry_price / 10) * 10  # 取整为10的倍数
        
#         # 计算手续费
#         open_fee = position_size * entry_price * self.open_fee_rate
        
#         # 计算目标盈利和最大亏损（基于总资金）
#         target_profit = self.balance * self.take_profit_ratio
#         max_loss = self.balance * self.stop_loss_ratio
        
#         # 计算止盈止损价格
#         if signal == 1:  # 做多
#             take_profit_price = (target_profit + (entry_price * position_size) + open_fee) / (position_size * (1 - self.close_fee_rate))
#             stop_loss_price = ((entry_price * position_size) - max_loss - open_fee - max_loss * self.close_fee_rate) / position_size
#         elif signal == -1:  # 做空
#             take_profit_price = ((entry_price * position_size) - target_profit - open_fee) / (position_size * (1 + self.close_fee_rate))
#             stop_loss_price = (max_loss + (entry_price * position_size) + open_fee + max_loss * self.close_fee_rate) / position_size

#         return signal, round(take_profit_price, 5), round(stop_loss_price, 5), position_size
import pandas as pd

class BollingerStrategy:
    def __init__(self, 
                 df: pd.DataFrame,
                 open_fee_rate=0.0005,
                 close_fee_rate=0.0005,
                 take_profit_ratio=0.01,
                 stop_loss_ratio=0.01,
                 bb_window=20,
                 bb_std_mult=3):
        """
        参数说明：
          - df: K线数据 DataFrame（至少包含['open','high','low','close']）
          - open_fee_rate: 开仓手续费率
          - close_fee_rate: 平仓手续费率
          - take_profit_ratio: 止盈比例(相对本金)
          - stop_loss_ratio: 止损比例(相对本金)
          - bb_window: 计算布林带的周期
          - bb_std_mult: 计算布林带标准差倍数
        """
        # 手续费、风控等策略相关参数
        self.open_fee_rate = open_fee_rate
        self.close_fee_rate = close_fee_rate
        self.take_profit_ratio = take_profit_ratio
        self.stop_loss_ratio = stop_loss_ratio
        
        # 布林带参数
        self.bb_window = bb_window
        self.bb_std_mult = bb_std_mult
        
        # 保存数据并计算布林带
        self.df = df.copy()
        self.df = self.calculate_bollinger_bands(self.df)

    def calculate_bollinger_bands(self, df):
        """计算布林带指标，并在DataFrame上添加 ma、std、upper、lower列"""
        df = df.copy()
        df['ma'] = df['close'].rolling(self.bb_window).mean()
        df['std'] = df['close'].rolling(self.bb_window).std(ddof=0)
        df['upper'] = df['ma'] + df['std'] * self.bb_std_mult
        df['lower'] = df['ma'] - df['std'] * self.bb_std_mult
        return df

    def generate_signal(self, index: int, 
                        current_balance: float, 
                        leverage: float, 
                        position_ratio: float):
        """
        生成交易信号和止盈止损价格。

        参数：
          - index: 当前K线在 self.df 的索引
          - current_balance: 当前账户可用资金（由外部传入）
          - leverage: 当前可用的杠杆倍数（由外部传入）
          - position_ratio: 当前策略允许用多少比例的资金开仓（外部传入）

        返回:
          (signal, take_profit_price, stop_loss_price, position_size)
          signal: 1=做多, -1=做空, 0=无交易
          take_profit_price: 止盈价，如无则 None
          stop_loss_price: 止损价，如无则 None
          position_size: 建仓数量（手数），如无则 None
        """
        # 如果数据不足以计算布林带，则不交易
        if index < self.bb_window:
            return 0, None, None, None

        current = self.df.iloc[index]
        prev = self.df.iloc[index - 1]
        signal = 0

        # 判断信号
        # 做空信号：上根K线的 high < upper，这根K线 high >= upper
        if prev['high'] < prev['upper'] and current['high'] >= current['upper']:
            signal = -1
        # 做多信号：上根K线的 low > lower，这根K线 low <= lower
        elif prev['low'] > prev['lower'] and current['low'] <= current['lower']:
            signal = 1
        else:
            # 无信号
            return 0, None, None, None

        # 以当前收盘价作为开仓价格
        entry_price = current['close']
        if entry_price <= 0:
            return 0, None, None, None
        
        # 基于当前资金、杠杆和 position_ratio 来计算可用的头寸价值
        position_value = current_balance * position_ratio * leverage
        
        # 得到实际合约数量（示例：向下取整到 10 的倍数）
        raw_size = position_value / entry_price
        position_size = round(raw_size / 10) * 10

        # 若计算出的张数 <= 0，说明余额太小或其他原因，不开仓
        if position_size <= 0:
            return 0, None, None, None

        # 计算开仓费
        open_fee = position_size * entry_price * self.open_fee_rate
        
        # 计算目标盈利和最大亏损（基于当前_balance）
        target_profit = current_balance * self.take_profit_ratio
        max_loss = current_balance * self.stop_loss_ratio

        # 根据做多/做空计算止盈止损价格
        if signal == 1:  # 做多
            # 止盈价
            take_profit_price = (target_profit + (entry_price * position_size) + open_fee) \
                                / (position_size * (1 - self.close_fee_rate))
            # 止损价
            stop_loss_price = ((entry_price * position_size) - max_loss - open_fee 
                               - max_loss * self.close_fee_rate) / position_size
        else:  # signal == -1 做空
            take_profit_price = ((entry_price * position_size) - target_profit - open_fee) \
                                / (position_size * (1 + self.close_fee_rate))
            stop_loss_price = (max_loss + (entry_price * position_size) + open_fee 
                               + max_loss * self.close_fee_rate) / position_size

        return signal, round(take_profit_price, 5), round(stop_loss_price, 5), position_size, False
