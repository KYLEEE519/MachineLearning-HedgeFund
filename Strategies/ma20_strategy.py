import pandas as pd

class Ma20Strategy:
    def __init__(self, 
                 df: pd.DataFrame, 
                 ma_length: int = 20,
                 position_ratio: float = 0.5):
        """
        参数:
          - df: 历史K线数据(DataFrame)，至少包含['open','high','low','close']
          - ma_length: 用于计算20周期移动平均线
          - position_ratio: 策略内定义的开仓仓位比例(0~1之间)，
                            例如0.5表示用当前余额的50%来开仓
        """
        self.df = df.copy()
        self.ma_length = ma_length
        self.position_ratio = position_ratio
        
        # 计算移动平均线
        self.df['ma'] = self.df['close'].rolling(self.ma_length).mean()

    def generate_signal(self, 
                        index: int, 
                        current_balance: float, 
                        leverage: float = 1.0,
                        current_position: int = 0):
        """
        生成交易信号，返回 (direction, take_profit, stop_loss, position_size, exit_signal)

        参数:
          - index: 当前K线索引
          - current_balance: 当前账户可用余额(由外部传入)
          - leverage: 杠杆倍数(默认1.0表示无杠杆)
          - current_position: 当前持仓方向
             * 1 = 持有多单
             * -1 = 持有空单
             * 0 = 当前无仓位
        
        返回:
          (direction, None, None, position_size, exit_signal)
            direction: 1=做多, -1=做空, 0=无操作
            take_profit: None (本策略不做止盈)
            stop_loss: None   (本策略不做止损)
            position_size: 本次计划开仓手数
            exit_signal: True=先平仓再开仓, False=不平

        策略逻辑:
          - 前一根K线low <= ma, 当前K线low > ma => 多头信号
          - 前一根K线high >= ma, 当前K线high < ma => 空头信号
          - 如果当前已有持仓，且信号方向与持仓方向相同，则忽略信号
        """
        # 如果数据不足或索引太小 => 不交易
        if index < self.ma_length:
            return (0, None, None, 0, False)
        
        row = self.df.iloc[index]
        prev = self.df.iloc[index - 1]

        if pd.isna(row['ma']) or pd.isna(prev['ma']):
            # 均线还没算出来
            return (0, None, None, 0, False)

        # 判断做多 or 做空信号
        long_condition = (prev['low'] <= prev['ma']) and (row['low'] > row['ma'])
        short_condition = (prev['high'] >= prev['ma']) and (row['high'] < row['ma'])

        if long_condition:
            direction = 1
            exit_signal = True   # 先平再做多
        elif short_condition:
            direction = -1
            exit_signal = True   # 先平再做空
        else:
            return (0, None, None, 0, False)  # 无信号
        
        # **新增逻辑: 检查当前是否已有同方向仓位**
        if current_position == direction:
            print(f"[{row['timestamp']}] 信号 {direction} 但已有持仓 {current_position}，忽略本次交易")
            return (0, None, None, 0, False)  # 忽略开仓信号
        
        # 计算要开的仓位手数
        entry_price = row['close']
        if entry_price <= 0:
            return (0, None, None, 0, False)
        
        # 资金管理: 每次用 balance * position_ratio * leverage
        nominal_value = current_balance * self.position_ratio * leverage
        position_size = nominal_value / entry_price
        
        if position_size <= 0:
            return (0, None, None, 0, False)

        return direction, None, None, position_size, exit_signal
