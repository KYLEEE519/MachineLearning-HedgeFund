# backtest.py
import pandas as pd

class Backtester:
    def __init__(
        self,
        initial_balance=10000.0,
        leverage=2.0,
        fee_rate=0.001,
        slippage=0.0005
    ):
        """
        :param initial_balance: 初始资金
        :param leverage: 杠杆倍数
        :param fee_rate: 费率(双边)
        :param slippage: 滑点比例(如0.0005 = 0.05%)
        """
        self.initial_balance = float(initial_balance)
        self.leverage = float(leverage)
        self.fee_rate = float(fee_rate)
        self.slippage = float(slippage)

        self.position = 0.0         # 当前持仓量
        self.entry_price = 0.0      # 入场价格
        self.required_margin = 0.0  # 当前持仓占用保证金
        self.active_position = False

    def calculate_max_trade_value(self, available_balance: float) -> float:
        """
        计算一次性最多可动用的头寸价值（不一定是最优风险管理方法）。
        """
        if available_balance <= 0:
            return 0.0
        denominator = (1 / self.leverage + self.fee_rate)
        return available_balance / denominator

    def run_backtest(self, df: pd.DataFrame):
        # 初始化资金
        balance = float(self.initial_balance)

        # 为避免 int/float 冲突，这里强制声明为浮点列
        df['equity_curve'] = float(self.initial_balance)
        df['equity_curve'] = df['equity_curve'].astype(float)

        trade_log = []

        for i in range(1, len(df)):
            current_price = float(df["close"].iloc[i])
            current_time = df["timestamp"].iloc[i]

            # -- 更新权益曲线 --
            if self.active_position:
                # 浮动盈亏 = 持仓 * (当前价 - 开仓价)
                unrealized_pnl = self.position * (current_price - self.entry_price)
                df.at[i, 'equity_curve'] = balance + unrealized_pnl
            else:
                df.at[i, 'equity_curve'] = balance

            # -- 获取当前/上一根信号 --
            prev_signal = df["signal"].iloc[i - 1]
            current_signal = df["signal"].iloc[i]

            # === 开仓逻辑 ===
            # 条件：前一根信号=0, 当前=1 且 无持仓
            if not self.active_position and prev_signal == 0 and current_signal == 1:
                max_trade_value = self.calculate_max_trade_value(balance)
                if max_trade_value <= 0:
                    continue

                # 假设多单滑点 => 买入价略高于市价
                entry_price = current_price * (1 + self.slippage)
                position_size = max_trade_value / entry_price
                trade_value = position_size * entry_price

                required_margin = trade_value / self.leverage
                fee_open = trade_value * self.fee_rate

                # 检查余额是否足够
                if (required_margin + fee_open) > balance:
                    continue

                # 扣除保证金 + 开仓手续费
                balance -= (required_margin + fee_open)

                # 记录持仓信息
                self.position = position_size
                self.entry_price = entry_price
                self.required_margin = required_margin
                self.active_position = True

                trade_log.append((
                    "BUY",
                    current_time,
                    float(entry_price),
                    float(position_size),
                    round(float(balance), 2)
                ))

            # === 平仓逻辑 ===
            # 条件：前一根信号=1, 当前=0 且 有持仓
            elif self.active_position and prev_signal == 1 and current_signal == 0:
                closing_size = self.position

                # 假设平多滑点 => 卖出价略低于市价
                exit_price = current_price * (1 - self.slippage)
                realized_pnl = (exit_price - self.entry_price) * closing_size
                fee_exit = (closing_size * exit_price) * self.fee_rate

                # 释放保证金 + 浮盈亏 - 平仓手续费
                balance += self.required_margin + realized_pnl - fee_exit

                trade_log.append((
                    "SELL",
                    current_time,
                    float(exit_price),
                    float(closing_size),
                    round(float(balance), 2)
                ))

                # 重置持仓数据
                self.position = 0.0
                self.entry_price = 0.0
                self.required_margin = 0.0
                self.active_position = False

        # 计算日度收益和回撤
        df["return"] = df["equity_curve"].pct_change().fillna(0.0)
        df["drawdown"] = (
            df["equity_curve"].cummax() - df["equity_curve"]
        ) / df["equity_curve"].cummax()
        df["drawdown"].fillna(0.0, inplace=True)

        return df, trade_log
