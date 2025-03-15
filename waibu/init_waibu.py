import pandas as pd

class SimulatedExchange:
    def __init__(self, initial_balance, fee_rate, leverage, position_ratio, 
                 maintenance_margin_rate=0.005, min_unit=10):
        """
        参数说明：
          - initial_balance: 初始本金
          - fee_rate: 手续费比率（例如0.001表示万分之一）
          - leverage: 杠杆倍率
          - position_ratio: 仓位比例，用于计算单笔持仓的最大仓位价值
          - maintenance_margin_rate: 维持保证金率（默认0.5%）
          - min_unit: 最小交易单位（例如每次交易的数量为10的倍数）
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.fee_rate = fee_rate
        self.leverage = leverage
        self.position_ratio = position_ratio
        self.maintenance_margin_rate = maintenance_margin_rate
        self.min_unit = min_unit
        self.positions = {}
        self.trade_log = []
    
    def _round_position_size(self, raw_size):
        """将仓位数量取整为min_unit的倍数"""
        return round(raw_size / self.min_unit) * self.min_unit

    def open_position(self, symbol, direction, entry_price, take_profit, stop_loss, position_size, timestamp):
        """开仓逻辑"""
        # 确保仓位数量符合最小单位要求
        position_size = self._round_position_size(position_size)
        if position_size <= 0:
            print(f"[{timestamp}] {symbol} 开仓失败，无效的仓位数量")
            return False
        
        # 计算保证金和手续费
        margin = (entry_price * position_size) / self.leverage
        entry_fee = entry_price * position_size * self.fee_rate
        total_cost = margin + entry_fee
        
        if self.balance < total_cost:
            print(f"[{timestamp}] {symbol} 开仓失败，需要 {total_cost:.5f}，可用 {self.balance:.5f}")
            return False
        
        # 扣除资金
        self.balance -= total_cost
        
        # 记录持仓信息
        pos = {
            'size': position_size,
            'direction': direction,
            'entry_price': entry_price,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'margin': margin,
            'entry_fee': entry_fee,
            'open_timestamp': timestamp
        }
        if symbol not in self.positions:
            self.positions[symbol] = []
        self.positions[symbol].append(pos)
        
        # 记录日志
        self.trade_log.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'action': 'open',
            'direction': direction,
            'price': entry_price,
            'size': position_size,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'margin': margin,
            'fee': entry_fee
        })
        print(f"[{timestamp}] 开仓成功: {symbol} 方向:{direction} 数量:{position_size} 价格:{entry_price:.5f} 手续费:{entry_fee:.5f}")
        return True

    def close_position(self, symbol, pos, exit_price, timestamp):
        """平仓逻辑"""
        # 计算平仓信息
        direction = pos['direction']
        size = pos['size']
        entry_price = pos['entry_price']
        margin = pos['margin']
        entry_fee = pos['entry_fee']
        
        # 计算盈亏
        if direction == 1:
            profit = (exit_price - entry_price) * size
        else:
            profit = (entry_price - exit_price) * size
        
        # 计算平仓手续费
        exit_fee = exit_price * size * self.fee_rate
        net_profit = profit - exit_fee
        
        # 更新账户余额（保证金返还 + 净盈亏）
        self.balance += margin + net_profit
        
        # 记录日志
        self.trade_log.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'action': 'close',
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'size': size,
            'profit': net_profit,
            'fee': exit_fee,
            'margin': margin
        })
        print(f"[{timestamp}] 平仓: {symbol} 方向:{direction} 数量:{size} "
              f"入场价:{entry_price:.5f} 出场价:{exit_price:.5f} "
              f"净盈亏:{net_profit:.5f} 手续费:{exit_fee:.5f}")
        return net_profit

    def process_kline(self, symbol, kline, signal):
        """处理K线数据"""
        timestamp = kline['timestamp']
        current_close = kline['close']
        
        # 1. 先处理强制平仓（使用更严格的价格评估）
        if symbol in self.positions:
            for pos in self.positions[symbol][:]:
                # 根据持仓方向选择评估价格
                if pos['direction'] == 1:
                    eval_price = kline['low']  # 多头按最低价评估强平
                else:
                    eval_price = kline['high']  # 空头按最高价评估
                
                # 计算未实现盈亏
                if pos['direction'] == 1:
                    unrealized = (eval_price - pos['entry_price']) * pos['size']
                else:
                    unrealized = (pos['entry_price'] - eval_price) * pos['size']
                
                # 计算维持保证金要求
                position_value = pos['size'] * eval_price
                maintenance_margin = position_value * self.maintenance_margin_rate
                
                # 检查保证金是否充足
                if (pos['margin'] + unrealized) < maintenance_margin:
                    print(f"[{timestamp}] 触发强平 | 持仓价值:{position_value:.2f} "
                          f"当前保证金:{pos['margin'] + unrealized:.2f} "
                          f"要求保证金:{maintenance_margin:.2f}")
                    # 以评估价格平仓
                    self.close_position(symbol, pos, eval_price, timestamp)
                    self.positions[symbol].remove(pos)
        
        # 2. 处理止盈止损
        if symbol in self.positions:
            for pos in self.positions[symbol][:]:
                # 多头止盈止损检查
                if pos['direction'] == 1:
                    if pos['take_profit'] is not None and kline['high'] >= pos['take_profit']:
                        self.close_position(symbol, pos, pos['take_profit'], timestamp)
                        self.positions[symbol].remove(pos)
                    elif pos['stop_loss'] is not None and kline['low'] <= pos['stop_loss']:
                        self.close_position(symbol, pos, pos['stop_loss'], timestamp)
                        self.positions[symbol].remove(pos)
                
                # 空头止盈止损检查
                elif pos['direction'] == -1:
                    if pos['take_profit'] is not None and kline['low'] <= pos['take_profit']:
                        self.close_position(symbol, pos, pos['take_profit'], timestamp)
                        self.positions[symbol].remove(pos)
                    elif pos['stop_loss'] is not None and kline['high'] >= pos['stop_loss']:
                        self.close_position(symbol, pos, pos['stop_loss'], timestamp)
                        self.positions[symbol].remove(pos)
        
        # 3. 处理新交易信号
        direction, take_profit, stop_loss, position_size = signal
        if direction != 0:
            # 重新计算实际可开仓位（考虑最新余额）
            available_margin = self.balance * self.position_ratio
            max_position_value = available_margin * self.leverage
            calculated_size = max_position_value / kline['close']
            position_size = self._round_position_size(calculated_size)
            
            # 执行开仓
            if position_size > 0:
                self.open_position(symbol, direction, kline['close'], 
                                  take_profit, stop_loss, position_size, timestamp)

# 示例使用
if __name__ == "__main__":
    # 初始化交易所（添加维持保证金率参数）
    exchange = SimulatedExchange(
        initial_balance=10000,
        fee_rate=0.001,
        leverage=10,
        position_ratio=0.1,
        maintenance_margin_rate=0.005  # 0.5%维持保证金率
    )

    # 构造测试数据
    data = {
        'timestamp': pd.date_range(start='2023-01-01 09:00', periods=5, freq='5T'),
        'open': [100, 101, 102, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'close': [100.5, 101.5, 102.5, 103.5, 104.5],
        'vol': [1000, 2000, 3000, 4000, 5000]
    }
    df = pd.DataFrame(data)

    # 测试信号（第1根K线开多，第3根K线开空）
    signals = [
        (1, 102, 99, 0),   # 信号会自动计算实际仓位
        (0, 0, 0, 0),
        (-1, 100, 105, 0),
        (0, 0, 0, 0),
        (0, 0, 0, 0)
    ]

    # 运行模拟
    for idx, row in df.iterrows():
        exchange.process_kline(
            symbol="BTC",
            kline=row.to_dict(),
            signal=signals[idx] if idx < len(signals) else (0, 0, 0, 0)
        )
    
    # 输出最终结果
    print("\n最终账户余额:", exchange.balance)
    print("剩余持仓:", exchange.positions)
