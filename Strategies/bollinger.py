import pandas as pd
import numpy as np

class BollingerBandStrategy:
    def __init__(self, bb_window=20, bb_std_mult=3, fee_rate=0.001):
        """
        初始化布林带交易策略
        :param bb_window: 布林带计算的移动平均窗口
        :param bb_std_mult: 布林带标准差倍数
        :param fee_rate: 交易手续费率
        """
        self.bb_window = bb_window
        self.bb_std_mult = bb_std_mult
        self.fee_rate = fee_rate

    def calculate_bollinger_bands(self, df):
        """
        计算布林带指标
        :param df: 包含 'close' 价格的 DataFrame
        :return: 计算后的 DataFrame
        """
        df = df.copy()
        df['ma'] = df['close'].rolling(self.bb_window).mean()
        df['std'] = df['close'].rolling(self.bb_window).std(ddof=0)
        df['upper'] = df['ma'] + df['std'] * self.bb_std_mult
        df['lower'] = df['ma'] - df['std'] * self.bb_std_mult
        return df

    def generate_signal(self, df):
        """
        生成交易信号
        :param df: 包含 'high' 和 'low' 价格的 DataFrame
        :return: 1（做多）, -1（做空）, 0（无操作）
        """
        if len(df) < self.bb_window + 2:  # 确保至少有足够的数据
            return 0

        df = self.calculate_bollinger_bands(df)

        current = df.iloc[-1]
        prev = df.iloc[-2]

        # 做空信号：上轨突破
        if prev['high'] < prev['upper'] and current['high'] >= current['upper']:
            return -1

        # 做多信号：下轨突破
        if prev['low'] > prev['lower'] and current['low'] <= current['lower']:
            return 1

        return 0

    def check_exit_conditions(self, position_info, current_candle):
        """
        检查是否需要平仓
        :param position_info: 记录当前仓位的信息
        :param current_candle: 当前K线数据（包含 'high' 和 'low'）
        :return: True（平仓）, False（继续持有）
        """
        entry_price = position_info['entry_price']
        direction = position_info['direction']
        position_size = position_info['position_size']

        if direction == 1:  # 多单
            unrealized_pnl = (current_candle['high'] - entry_price) * position_size
            close_fee = position_size * current_candle['high'] * self.fee_rate
        else:  # 空单
            unrealized_pnl = (entry_price - current_candle['low']) * position_size
            close_fee = position_size * current_candle['low'] * self.fee_rate

        net_pnl = unrealized_pnl - position_info['open_fee'] - close_fee

        # 止盈检查
        if net_pnl >= position_info['target_profit']:
            return True

        # 止损检查
        if unrealized_pnl <= -abs(position_info['stop_loss']):
            return True

        return False
