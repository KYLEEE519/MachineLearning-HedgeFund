# import pandas as pd

# class SimulatedExchange:
#     def __init__(self, initial_balance, fee_rate, leverage, position_ratio, 
#                  maintenance_margin_rate=0.005, min_unit=10,
#                  allow_multiple_positions=False):
#         """
#         参数说明：
#           - initial_balance: 初始本金
#           - fee_rate: 手续费比率（例如0.001表示千分之一）
#           - leverage: 杠杆倍率
#           - position_ratio: 仓位比例，用于计算单笔持仓的最大仓位价值
#           - maintenance_margin_rate: 维持保证金率（默认0.5%）
#           - min_unit: 最小交易单位（例如每次交易数量为10的倍数）
#           - allow_multiple_positions: 是否允许同一品种在已有持仓时再开新仓
#             如果为False，当已有持仓就不再执行新的开仓操作
#         """
#         self.initial_balance = initial_balance
#         self.balance = initial_balance
#         self.fee_rate = fee_rate
#         self.leverage = leverage
#         self.position_ratio = position_ratio
#         self.maintenance_margin_rate = maintenance_margin_rate
#         self.min_unit = min_unit
#         self.allow_multiple_positions = allow_multiple_positions

#         # 记录持仓列表 {symbol: [pos1, pos2, ...]}
#         self.positions = {}
#         # 记录交易日志
#         self.trade_log = []
    
#     def _round_position_size(self, raw_size):
#         """将仓位数量取整为min_unit的倍数"""
#         return round(raw_size / self.min_unit) * self.min_unit

#     def open_position(self, symbol, direction, entry_price, take_profit, stop_loss, position_size, timestamp):
#         """开仓逻辑"""
#         # 确保仓位数量符合最小单位要求
#         position_size = self._round_position_size(position_size)
#         if position_size <= 0:
#             print(f"[{timestamp}] {symbol} 开仓失败，无效的仓位数量({position_size})")
#             return False
        
#         # 计算保证金和手续费
#         margin = (entry_price * position_size) / self.leverage
#         entry_fee = entry_price * position_size * self.fee_rate
#         total_cost = margin + entry_fee
        
#         if self.balance < total_cost:
#             print(f"[{timestamp}] {symbol} 开仓失败，需要 {total_cost:.5f}，可用 {self.balance:.5f}")
#             return False
        
#         # 扣除资金
#         self.balance -= total_cost
        
#         # 记录持仓信息
#         pos = {
#             'size': position_size,
#             'direction': direction,
#             'entry_price': entry_price,
#             'take_profit': take_profit,
#             'stop_loss': stop_loss,
#             'margin': margin,
#             'entry_fee': entry_fee,
#             'open_timestamp': timestamp
#         }
#         if symbol not in self.positions:
#             self.positions[symbol] = []
#         self.positions[symbol].append(pos)
        
#         # 记录日志
#         self.trade_log.append({
#             'timestamp': timestamp,
#             'symbol': symbol,
#             'action': 'open',
#             'direction': direction,
#             'price': entry_price,
#             'size': position_size,
#             'take_profit': take_profit,
#             'stop_loss': stop_loss,
#             'margin': margin,
#             'fee': entry_fee
#         })
#         print(f"[{timestamp}] 开仓成功: {symbol} 方向:{direction} 数量:{position_size} 价格:{entry_price:.5f} 手续费:{entry_fee:.5f}")
#         return True

#     def close_position(self, symbol, pos, exit_price, timestamp):
#         """平仓逻辑"""
#         direction = pos['direction']
#         size = pos['size']
#         entry_price = pos['entry_price']
#         margin = pos['margin']
#         entry_fee = pos['entry_fee']
        
#         # 计算盈亏
#         if direction == 1:
#             profit = (exit_price - entry_price) * size
#         else:
#             profit = (entry_price - exit_price) * size
        
#         # 计算平仓手续费
#         exit_fee = exit_price * size * self.fee_rate
#         net_profit = profit - exit_fee
        
#         # 更新账户余额（保证金返还 + 净盈亏）
#         self.balance += (margin + net_profit)
        
#         # 记录日志
#         self.trade_log.append({
#             'timestamp': timestamp,
#             'symbol': symbol,
#             'action': 'close',
#             'direction': direction,
#             'entry_price': entry_price,
#             'exit_price': exit_price,
#             'size': size,
#             'profit': net_profit,
#             'fee': exit_fee,
#             'margin': margin
#         })
#         print(f"[{timestamp}] 平仓: {symbol} 方向:{direction} 数量:{size} "
#               f"入场价:{entry_price:.5f} 出场价:{exit_price:.5f} "
#               f"净盈亏:{net_profit:.5f} 手续费:{exit_fee:.5f}")
#         return net_profit

#     def process_kline(self, symbol, kline, signal):
#         """处理K线数据"""
#         timestamp = kline['timestamp']
#         current_close = kline['close']
        
#         # 1. 先处理强制平仓检查
#         if symbol in self.positions:
#             for pos in self.positions[symbol][:]:
#                 # 根据持仓方向选择评估价格
#                 if pos['direction'] == 1:
#                     eval_price = kline['low']  # 多头用最低价来评估是否触及强平
#                 else:
#                     eval_price = kline['high'] # 空头用最高价来评估是否触及强平
                
#                 # 计算未实现盈亏
#                 if pos['direction'] == 1:
#                     unrealized = (eval_price - pos['entry_price']) * pos['size']
#                 else:
#                     unrealized = (pos['entry_price'] - eval_price) * pos['size']
                
#                 # 计算维持保证金要求
#                 position_value = pos['size'] * eval_price
#                 maintenance_margin = position_value * self.maintenance_margin_rate
                
#                 # 如果 (保证金 + 浮动盈亏) < 维持保证金要求 => 强平
#                 if (pos['margin'] + unrealized) < maintenance_margin:
#                     print(f"[{timestamp}] 触发强平 | 持仓价值:{position_value:.2f} "
#                           f"当前保证金:{pos['margin'] + unrealized:.2f} "
#                           f"要求保证金:{maintenance_margin:.2f}")
#                     # 以评估价格平仓
#                     self.close_position(symbol, pos, eval_price, timestamp)
#                     self.positions[symbol].remove(pos)
        
#         # 2. 止盈止损检查
#         if symbol in self.positions:
#             for pos in self.positions[symbol][:]:
#                 direction = pos['direction']
                
#                 if direction == 1:
#                     # 多头止盈 / 止损
#                     if pos['take_profit'] is not None and kline['high'] >= pos['take_profit']:
#                         self.close_position(symbol, pos, pos['take_profit'], timestamp)
#                         self.positions[symbol].remove(pos)
#                     elif pos['stop_loss'] is not None and kline['low'] <= pos['stop_loss']:
#                         self.close_position(symbol, pos, pos['stop_loss'], timestamp)
#                         self.positions[symbol].remove(pos)
                
#                 else:  # direction == -1
#                     # 空头止盈 / 止损
#                     if pos['take_profit'] is not None and kline['low'] <= pos['take_profit']:
#                         self.close_position(symbol, pos, pos['take_profit'], timestamp)
#                         self.positions[symbol].remove(pos)
#                     elif pos['stop_loss'] is not None and kline['high'] >= pos['stop_loss']:
#                         self.close_position(symbol, pos, pos['stop_loss'], timestamp)
#                         self.positions[symbol].remove(pos)
        
#         # 3. 处理新交易信号
#         direction, take_profit, stop_loss, position_size = signal
        
#         # 如果 signal == 0 则不开仓
#         if direction == 0:
#             return
        
#         # 如果不允许多笔持仓，而且当前已经有任意持仓，就直接跳过
#         if not self.allow_multiple_positions:
#             if symbol in self.positions and len(self.positions[symbol]) > 0:
#                 print(f"[{timestamp}] 已有持仓，不执行新开仓 (allow_multiple_positions=False).")
#                 return
        
#         # 如果上面没有 return，说明要新开一笔
#         # 重新计算实际可开仓位（考虑最新余额）
#         available_margin = self.balance * self.position_ratio
#         max_position_value = available_margin * self.leverage
#         calculated_size = max_position_value / current_close
#         position_size = self._round_position_size(calculated_size)

#         # 执行开仓
#         if position_size > 0:
#             self.open_position(symbol, direction, current_close,
#                                take_profit, stop_loss,
#                                position_size, timestamp)
import pandas as pd
import copy
class SimulatedExchange:
    def __init__(self, 
                 initial_balance: float,
                 open_fee_rate: float,
                 close_fee_rate: float,
                 leverage: float,
                 position_ratio: float,
                 maintenance_margin_rate: float = 0.005,
                 min_unit: int = 10,
                 allow_multiple_positions: bool = False
                 
    ):
        """
        参数说明：
          - initial_balance: 初始本金
          - open_fee_rate:   开仓手续费率 (例如 0.0002 表示万2)
          - close_fee_rate:  平仓手续费率
          - leverage:        杠杆倍率
          - position_ratio:  仓位比例，用于计算单笔持仓的最大仓位价值
          - maintenance_margin_rate: 维持保证金率（默认0.5%）
          - min_unit:        最小交易单位（例如每次交易的数量为10的倍数）
          - allow_multiple_positions: 是否允许同一品种在已有持仓时再开新仓
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.open_fee_rate = open_fee_rate
        self.close_fee_rate = close_fee_rate
        
        self.leverage = leverage
        self.position_ratio = position_ratio
        self.maintenance_margin_rate = maintenance_margin_rate
        self.min_unit = min_unit
        self.allow_multiple_positions = allow_multiple_positions
        self.last_no_position_state = None

        # 记录持仓列表 {symbol: [pos1, pos2, ...]}
        self.positions = {}
        # 记录交易日志
        self.trade_log = []
    
    def _round_position_size(self, raw_size):
        """将仓位数量取整为 min_unit 的倍数"""
        return round(raw_size / self.min_unit) * self.min_unit
    def backup_state(self):
        """ 备份账户状态（仅在无持仓时执行） """
        if not self.positions:  # 确保当前无持仓
            self.last_no_position_state = {
                "balance": self.balance,
                "trade_log": copy.deepcopy(self.trade_log)
            }
    def restore_last_state(self):
        """ 恢复到上一次无持仓状态 """
        if self.last_no_position_state is None:
            print("[WARNING] 没有可恢复的状态，跳过恢复操作")
            return
        
        print("[INFO] 存在未平仓持仓，回滚到上一次无持仓状态...")
        self.balance = self.last_no_position_state["balance"]
        self.trade_log = self.last_no_position_state["trade_log"]
        self.positions = {}  # 清空所有持仓

    def open_position(self, symbol, direction, entry_price, take_profit, stop_loss, position_size, timestamp):
        """
        开仓逻辑：
          1) 计算保证金 = (entry_price * position_size) / self.leverage
          2) 开仓手续费 = (entry_price * position_size) * self.open_fee_rate
          3) total_cost = 保证金 + 开仓手续费
          4) 若账户余额不足 total_cost，则开仓失败
          5) 否则扣除 total_cost 并记录持仓信息
        """
        # position_size = self._round_position_size(position_size)
        if position_size <= 0:
            print(f"[{timestamp}] {symbol} 开仓失败，无效的仓位数量({position_size})")
            return False
        
        # 计算保证金和“开仓手续费”
        margin = (entry_price * position_size) / self.leverage
        entry_fee = entry_price * position_size * self.open_fee_rate
        total_cost = margin + entry_fee
        
        if self.balance < total_cost:
            print(f"[{timestamp}] {symbol} 开仓失败，需要 {total_cost:.5f}，可用 {self.balance:.5f}")
            return False
        
        # 扣减账户余额
        self.balance -= total_cost
        
        # 记录持仓信息
        pos = {
            'size': position_size,
            'direction': direction,
            'entry_price': entry_price,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'margin': margin,
            'entry_fee': entry_fee,    # 记录“开仓手续费”
            'open_timestamp': timestamp
        }
        self.positions.setdefault(symbol, []).append(pos)
        
        # 写交易日志
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
        self.backup_state()  # 在成功开仓后检查是否需要备份

        return True

    def close_position(self, symbol, pos, exit_price, timestamp):
        """
        平仓逻辑：
          1) 计算浮动盈亏
             若 direction=1 (多头), profit = (exit_price - entry_price) * size
             若 direction=-1 (空头), profit = (entry_price - exit_price) * size
          2) 计算平仓手续费 = (exit_price * size) * self.close_fee_rate
          3) 净盈亏 = profit - exit_fee
          4) 返还保证金 + 净盈亏 到账户余额
        """
        direction = pos['direction']
        size = pos['size']
        entry_price = pos['entry_price']
        margin = pos['margin']
        entry_fee = pos['entry_fee']
        
        # 浮动盈亏
        if direction == 1:  # 多头
            profit = (exit_price - entry_price) * size
        else:               # 空头
            profit = (entry_price - exit_price) * size
        
        # “平仓手续费”使用 close_fee_rate
        exit_fee = (exit_price * size) * self.close_fee_rate
        net_profit = profit - exit_fee
        
        # 更新账户余额（返还保证金 + 净盈亏）
        self.balance += (margin + net_profit)
        
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
        self.backup_state()  # 在成功平仓后检查是否需要备份
        return net_profit

    def process_kline(self, symbol, kline, signal):
        """
        处理 K 线数据

        signal = (direction, take_profit, stop_loss, position_size, exit_signal)

        direction: 1=做多, -1=做空, 0=不做任何开仓
        take_profit: 止盈价
        stop_loss: 止损价
        position_size: 计划开仓手数
        exit_signal: True=策略指令立刻平仓, False=无需平仓

        流程:
          1) 强平检查
          2) 止盈止损检查
          3) 如果 exit_signal=True, 平掉当前品种所有持仓(可选：平掉后return)
          4) 如果 direction != 0, 执行开仓逻辑(需检查 allow_multiple_positions)
        """
        timestamp = kline['timestamp']
        current_close = kline['close']
        
        # ---------- 1. 强制平仓检查 ----------
        if symbol in self.positions:
            for pos in self.positions[symbol][:]:
                if pos['direction'] == 1:
                    eval_price = kline['low']  # 多头用最低价判断强平
                    unrealized = (eval_price - pos['entry_price']) * pos['size']
                else:
                    eval_price = kline['high'] # 空头用最高价判断强平
                    unrealized = (pos['entry_price'] - eval_price) * pos['size']
                
                position_value = pos['size'] * eval_price
                maintenance_margin = position_value * self.maintenance_margin_rate
                
                if (pos['margin'] + unrealized) < maintenance_margin:
                    print(f"[{timestamp}] 触发强平 | 持仓价值:{position_value:.2f} "
                          f"当前保证金:{pos['margin'] + unrealized:.2f} "
                          f"要求保证金:{maintenance_margin:.2f}")
                    self.close_position(symbol, pos, eval_price, timestamp)
                    self.positions[symbol].remove(pos)
        
        # ---------- 2. 止盈止损检查 ----------
        if symbol in self.positions:
            for pos in self.positions[symbol][:]:
                direction = pos['direction']
                if direction == 1:
                    # 多头
                    if pos['take_profit'] is not None and kline['high'] >= pos['take_profit']:
                        self.close_position(symbol, pos, pos['take_profit'], timestamp)
                        self.positions[symbol].remove(pos)
                    elif pos['stop_loss'] is not None and kline['low'] <= pos['stop_loss']:
                        self.close_position(symbol, pos, pos['stop_loss'], timestamp)
                        self.positions[symbol].remove(pos)
                else:
                    # 空头
                    if pos['take_profit'] is not None and kline['low'] <= pos['take_profit']:
                        self.close_position(symbol, pos, pos['take_profit'], timestamp)
                        self.positions[symbol].remove(pos)
                    elif pos['stop_loss'] is not None and kline['high'] >= pos['stop_loss']:
                        self.close_position(symbol, pos, pos['stop_loss'], timestamp)
                        self.positions[symbol].remove(pos)
        
        # ---------- 3. 信号解析 ----------
        direction, tp, sl, plan_size, exit_flag = signal
        
        # (a) exit_flag => 立即平仓
        if exit_flag:
            if symbol in self.positions and len(self.positions[symbol]) > 0:
                for pos in self.positions[symbol][:]:
                    self.close_position(symbol, pos, current_close, timestamp)
                    self.positions[symbol].remove(pos)
            # 如果要“平后就不再开仓”，可在此 return

        # (b) 若 direction=0 => 不开仓
        if direction == 0:
            return
        
        # (c) 若不允许多仓 且已有持仓 => 跳过
        if not self.allow_multiple_positions:
            if symbol in self.positions and len(self.positions[symbol]) > 0:
                print(f"[{timestamp}] 已有持仓，不执行新开仓 (allow_multiple_positions=False).")
                return
        
        # ---------- 4. 执行开仓逻辑 ----------
        # 若你想完全依赖策略给的 plan_size，可将下面的限制注释掉
        # available_margin = self.balance * self.position_ratio
        # max_position_value = available_margin * self.leverage
        # calc_size = max_position_value / current_close
        # final_pos_size = min(plan_size, calc_size)
        final_pos_size = plan_size  # 取策略给的size和上限之最
        # final_pos_size = self._round_position_size(final_pos_size)

        if final_pos_size > 0:
            self.open_position(symbol, direction, current_close, tp, sl, final_pos_size, timestamp)
