import pandas as pd

class Backtest:
    def __init__(self, df, initial_balance=10000, leverage=5, open_fee=0.0005, close_fee=0.0005, tp_ratio=0.1, sl_ratio=0.05):
        """
        :param df: 包含交易信号的数据
        :param initial_balance: 初始保证金
        :param leverage: 杠杆倍数
        :param open_fee: 开仓手续费
        :param close_fee: 平仓手续费
        :param tp_ratio: 止盈比例 (如 10% = 0.1)
        :param sl_ratio: 止损比例 (如 5% = 0.05)
        """
        self.df = df.copy()
        self.balance = initial_balance  # 账户保证金
        self.leverage = leverage
        self.open_fee = open_fee
        self.close_fee = close_fee
        self.tp_ratio = tp_ratio
        self.sl_ratio = sl_ratio

        # **交易状态**
        self.position = None  # 当前仓位 (None: 无仓, 1: 多单, -1: 空单)
        self.entry_price = None  # 开仓价
        self.entry_margin = None  # 开仓保证金
        self.trade_size = None  # 持仓数量
        self.open_time = None  # 开仓时间
        self.tp_price = None  # 止盈价
        self.sl_price = None  # 止损价

        self.trades = []  # 存储交易记录

        self.run_backtest()  # 运行回测

    def run_backtest(self):
        """遍历 df，执行逐笔交易"""
        for i, row in self.df.iterrows():
            timestamp, open_, high, low, close, open_signal = row['timestamp'], row['open'], row['high'], row['low'], row['close'], row['open_signal']

            # **如果资金为负，停止回测**
            if self.balance <= 0:
                print(f"❌ 资金不足，回测终止！最终余额: {self.balance}")
                break

            # **检查止盈 / 止损**
            if self.position is not None:
                if self.position == 1 and (high >= self.tp_price or low <= self.sl_price):  # 多单止盈 / 止损
                    self.close_trade(timestamp, self.tp_price if high >= self.tp_price else self.sl_price)
                elif self.position == -1 and (low <= self.tp_price or high >= self.sl_price):  # 空单止盈 / 止损
                    self.close_trade(timestamp, self.tp_price if low <= self.tp_price else self.sl_price)

            # **开仓逻辑**
            if self.position is None and open_signal != 0:
                self.open_trade(timestamp, open_, open_signal)
        # **最后一个 K 线检查是否有未平仓单，如果有，直接用收盘价平仓**
        if self.position is not None:
            print(f"🚨 最后一个 K 线 {timestamp} 仍持仓，强制平仓！")
            self.close_trade(timestamp, close)

    def open_trade(self, timestamp, price, direction):
        """执行开仓"""
        if self.position is not None:
            return  # 只能持有一个仓位

        # **计算开仓手续费**
        open_fee = self.balance * self.open_fee  # 先扣手续费
        self.balance -= open_fee  # 账户余额减少

        # **如果扣除手续费后资金为负，则终止回测**
        if self.balance <= 0:
            print(f"❌ 资金不足，无法开仓！终止回测。当前余额: {self.balance}")
            return

        # **计算合约张数**
        self.entry_margin = self.balance  # 剩余保证金
        self.trade_size = (self.entry_margin * self.leverage) / price  # 计算合约张数

        # **记录持仓信息**
        self.position = direction
        self.entry_price = price
        self.open_time = timestamp

        # **计算止盈止损价格**
        tp_percentage = self.tp_ratio / self.leverage  # 调整后止盈
        sl_percentage = self.sl_ratio / self.leverage  # 调整后止损
        if direction == 1:  # 多单
            self.tp_price = price * (1 + tp_percentage)
            self.sl_price = price * (1 - sl_percentage)
        else:  # 空单
            self.tp_price = price * (1 - tp_percentage)
            self.sl_price = price * (1 + sl_percentage)

    def close_trade(self, timestamp, price):
        """执行平仓"""
        if self.position is None:
            return

        # **计算手续费**
        close_fee = self.entry_margin * self.close_fee  # 平仓手续费
        self.balance -= close_fee  # 先扣手续费

        # **计算收益**
        pnl = self.trade_size * (price - self.entry_price) * self.position  # 盈亏 (张数 × (卖价-买价) × 方向)
        net_pnl = pnl - close_fee  # 扣除平仓手续费后的收益

        # **更新账户余额**
        self.balance += net_pnl  # 增加收益

        # **如果资金变负，直接终止回测**
        if self.balance <= 0:
            print(f"❌ 资金不足，回测终止！最终余额: {self.balance}")
            return

        # **记录交易**
        self.trades.append({
            "open_time": self.open_time,
            "close_time": timestamp,
            "open_price": self.entry_price,
            "close_price": price,
            "trade_size": self.trade_size,
            "gross_pnl": pnl,
            "net_pnl": net_pnl,
            "open_fee": self.entry_margin * self.open_fee,
            "close_fee": close_fee,
            "final_balance": self.balance
        })

        # **重置持仓状态**
        self.position = None
        self.entry_price = None
        self.entry_margin = None
        self.trade_size = None
        self.open_time = None
        self.tp_price = None
        self.sl_price = None

    def get_results(self):
        """返回交易记录 DataFrame"""
        return pd.DataFrame(self.trades)