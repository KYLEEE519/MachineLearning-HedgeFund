
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

    def calculate_total_balance_and_roi(self, current_price):
        """ 计算总余额（账户余额 + 持仓价值）以及盈亏比（ROI） """
        total_balance = self.balance
        for symbol, positions in self.positions.items():
            for pos in positions:
                position_value = pos['size'] * current_price/self.leverage  # 计算当前持仓市值
                total_balance += position_value
        
        # 计算盈亏比 ROI
        roi = ((total_balance - self.initial_balance) / self.initial_balance) * 100

        # 统计交易次数（开仓 + 平仓）
        total_trades = len(self.trade_log)

        return total_balance, roi, total_trades

    def open_position(self, symbol, direction, entry_price, take_profit, stop_loss, position_size, timestamp):
        """ 开仓逻辑 """
        if position_size <= 0:
            print(f"[{timestamp}] {symbol} 开仓失败，无效的仓位数量({position_size})")
            return False
        
        # 计算资金需求
        before_balance = self.balance  # 记录开仓前余额
        margin = (entry_price * position_size) / self.leverage
        entry_fee = entry_price * position_size * self.open_fee_rate
        total_cost = margin + entry_fee  # 总花费（保证金 + 开仓手续费）

        if self.balance < total_cost:
            print(f"[{timestamp}] {symbol} 开仓失败，需要 {total_cost:.5f}，可用 {self.balance:.5f}")
            return False
        
        # 资金更新
        self.balance -= total_cost
        after_balance = self.balance  # 记录开仓后余额

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
        self.positions.setdefault(symbol, []).append(pos)
        
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
            'fee': entry_fee,
            'open_timestamp': timestamp
        })
        
        print(f"[{timestamp}] 开仓成功: {symbol} 方向:{direction} 数量:{position_size} 价格:{entry_price:.5f}")
        print(f"         ▶ 开仓前余额: {before_balance:.5f},  开仓后余额: {after_balance:.5f}, 花费: {total_cost:.5f}")

        return True

    def close_position(self, symbol, pos, exit_price, timestamp):
        """ 平仓逻辑 """
        before_balance = self.balance  # 记录平仓前余额
        
        direction = pos['direction']
        size = pos['size']
        entry_price = pos['entry_price']
        margin = pos['margin']
        entry_fee = pos['entry_fee']

        # 计算盈亏
        if direction == 1:  # 多头
            profit = (exit_price - entry_price) * size
        else:               # 空头
            profit = (entry_price - exit_price) * size

        # 计算平仓手续费
        exit_fee = (exit_price * size) * self.close_fee_rate
        net_profit = profit - exit_fee

        # 返还保证金 + 盈亏
        return_amount = margin + net_profit
        self.balance += return_amount
        after_balance = self.balance  # 记录平仓后余额

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
            'margin': margin,
            'open_timestamp': pos.get('open_timestamp', timestamp) 
        })
        
        print(f"[{timestamp}] 平仓: {symbol} 方向:{direction} 数量:{size} 入场价:{entry_price:.5f} 出场价:{exit_price:.5f}")
        print(f"         ▶ 平仓前余额: {before_balance:.5f}, 平仓后余额: {after_balance:.5f}, 返还: {return_amount:.5f}")

        return net_profit


    def process_closing(self, symbol, kline, signal):
        """
        处理 **强平、止盈止损、策略平仓信号**（只执行平仓，不涉及开仓）

        参数:
        - symbol: 交易对名称（例如 "BTC-USDT"）
        - kline: 当前K线数据（包含时间、开盘价、最高价、最低价、收盘价）
        - signal: 策略生成的交易信号 (direction, take_profit, stop_loss, position_size, exit_signal)

        主要逻辑:
        1. 检查是否需要 **强制平仓**
        2. 检查是否触发 **止盈/止损**
        3. **检查 `exit_flag` 是否为 True，决定是否执行策略平仓**
        """
        timestamp = kline['timestamp']
        current_close = kline['close']

        # **解包信号**
        direction, _, _, _, exit_signal, exit_ratio = signal  # 只关心 exit_flag 是否需要平仓

        # ---------- 1️⃣ 强制平仓检查 ----------
        if symbol in self.positions:
            for pos in self.positions[symbol][:]:
                if pos['direction'] == 1:
                    eval_price = kline['low']  # 多头用最低价判断强平
                    unrealized = (eval_price - pos['entry_price']) * pos['size']
                else:
                    eval_price = kline['high']  # 空头用最高价判断强平
                    unrealized = (pos['entry_price'] - eval_price) * pos['size']
                
                position_value = pos['size'] * eval_price
                maintenance_margin = position_value * self.maintenance_margin_rate
                
                if (pos['margin'] + unrealized) < maintenance_margin:
                    print(f"[{timestamp}] 触发强平 | 持仓价值:{position_value:.2f} "
                        f"当前保证金:{pos['margin'] + unrealized:.2f} "
                        f"要求保证金:{maintenance_margin:.2f}")
                    self.close_position(symbol, pos, eval_price, timestamp)
                    self.positions[symbol].remove(pos)

        # ---------- 2️⃣ 止盈止损检查 ----------
        if symbol in self.positions:
            for pos in self.positions[symbol][:]:
                direction = pos['direction']
                if direction == 1:
                    if pos['take_profit'] is not None and kline['high'] >= pos['take_profit']:
                        self.close_position(symbol, pos, pos['take_profit'], timestamp)
                        self.positions[symbol].remove(pos)
                    elif pos['stop_loss'] is not None and kline['low'] <= pos['stop_loss']:
                        self.close_position(symbol, pos, pos['stop_loss'], timestamp)
                        self.positions[symbol].remove(pos)
                else:
                    if pos['take_profit'] is not None and kline['low'] <= pos['take_profit']:
                        self.close_position(symbol, pos, pos['take_profit'], timestamp)
                        self.positions[symbol].remove(pos)
                    elif pos['stop_loss'] is not None and kline['high'] >= pos['stop_loss']:
                        self.close_position(symbol, pos, pos['stop_loss'], timestamp)
                        self.positions[symbol].remove(pos)

        # ---------- 3️⃣ exit_signal 触发的平仓 ----------
        if exit_signal != 0 and symbol in self.positions:
            for pos in self.positions[symbol][:]:
                # 🧠 只平与 exit_signal 对应方向相反的仓位
                if pos['direction'] == exit_signal:
                    if exit_ratio < 1.0:
                        partial_size = pos['size'] * exit_ratio
                        partial_pos = copy.deepcopy(pos)
                        partial_pos['size'] = partial_size
                        self.close_position(symbol, partial_pos, current_close, timestamp)
                        pos['size'] -= partial_size
                    else:
                        self.close_position(symbol, pos, current_close, timestamp)
                        self.positions[symbol].remove(pos)

    def process_opening(self, symbol, kline, signal):
        """
        处理 **开仓** 逻辑（仅执行开仓，不涉及平仓）

        主要逻辑：
        1. 如果 signal.direction == 0，则不执行开仓
        2. 检查是否允许开多仓
        3. 计算新的开仓手数
        4. 执行 open_position()
        """
        timestamp = kline['timestamp']
        current_close = kline['close']

        # 解析新信号
        direction, tp, sl, plan_size, _, _ = signal

        # (a) 若 direction=0 => 不开仓
        if direction == 0:
            return

        # (b) 若不允许多仓 且已有持仓 => 跳过
        if not self.allow_multiple_positions:
            if symbol in self.positions and len(self.positions[symbol]) > 0:
                print(f"[{timestamp}] 已有持仓，不执行新开仓 (allow_multiple_positions=False).")
                return

        # ---------- 计算开仓手数 ----------
        final_pos_size = plan_size  # 取策略给的size
        # final_pos_size = self._round_position_size(final_pos_size)

        if final_pos_size > 0:
            self.open_position(symbol, direction, current_close, tp, sl, final_pos_size, timestamp)
