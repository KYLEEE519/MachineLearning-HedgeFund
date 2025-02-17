import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, initial_balance=10000, leverage=2, fee_rate=0.001, slippage=0.0005):
        """
        初始化回测参数：
        - initial_balance: 初始资金
        - leverage: 杠杆倍数
        - fee_rate: 每次交易的手续费率
        - slippage: 滑点（按市场价格的比例计算）
        """
        self.initial_balance = initial_balance
        self.leverage = leverage
        self.fee_rate = fee_rate
        self.slippage = slippage

    def run_backtest(self, df):
        """
        运行回测
        :param df: 包含交易信号的 DataFrame
        :return: 回测结果 DataFrame
        """
        balance = self.initial_balance
        position = 0  # 持仓量
        entry_price = 0  # 开仓价格
        trade_log = []  # 交易记录

        for i in range(1, len(df)):
            prev_signal = df["signal"].iloc[i-1]
            current_signal = df["signal"].iloc[i]
            price = df["close"].iloc[i]

            if prev_signal == 0 and current_signal == 1:  # 发生做多信号
                position = (balance * self.leverage) / price  # 计算仓位
                entry_price = price * (1 + self.slippage)  # 计算滑点
                balance -= position * entry_price * self.fee_rate  # 扣除手续费
                trade_log.append(("BUY", df["timestamp"].iloc[i], entry_price, position, balance))

            elif prev_signal == 1 and current_signal == 0:  # 发生平仓信号
                exit_price = price * (1 - self.slippage)  # 计算滑点
                balance += position * exit_price  # 计算盈利
                balance -= position * exit_price * self.fee_rate  # 扣除手续费
                trade_log.append(("SELL", df["timestamp"].iloc[i], exit_price, position, balance))
                position = 0  # 清空仓位

        # 计算最终收益
        df["equity_curve"] = balance
        df["return"] = df["equity_curve"].pct_change().fillna(0)

        # 计算回测指标
        max_drawdown = (df["equity_curve"].cummax() - df["equity_curve"]).max() / df["equity_curve"].cummax().max()
        total_return = (balance - self.initial_balance) / self.initial_balance
        trade_count = len(trade_log)

        print(f"📊 回测完成！")
        print(f"💰 最终资产: {balance:.2f}")
        print(f"📉 最大回撤: {max_drawdown:.2%}")
        print(f"📈 总收益率: {total_return:.2%}")
        print(f"🔄 交易次数: {trade_count}")

        return df, trade_log
