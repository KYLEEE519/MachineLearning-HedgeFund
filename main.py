# main.py
from Data.getdata import OKXDataFetcher
from Strategies.simple_strategy import SimpleMovingAverageStrategy
from Backtest.backtest import Backtester
from Strategies.test_strategy import MovingAverageStrategy
from Backtest.backtest_without_close_signal import Backtest
from Strategies.strategy_1 import VolatilityStrategy
# def main():
#     # ========== 参数设置 ==========

#     # 数据参数
#     inst_id = "BTC-USDT"
#     days = 1

#     # 策略参数
#     short_window = 5
#     long_window = 20

#     # 回测参数
#     initial_balance = 10000.0
#     leverage = 2.0
#     fee_rate = 0.001
#     slippage = 0.0005

#     # ========== 1️⃣ 获取数据 ========== 
#     print("🚀 获取数据中...")
#     fetcher = OKXDataFetcher(instId=inst_id)
#     fetcher.fetch_1m_data(days=days)
#     df = fetcher.get_cleaned_data()

#     if df is None or df.empty:
#         print("❌ 数据获取失败，程序退出。")
#         return

#     # ========== 2️⃣ 应用策略 ==========
#     print("📊 计算交易信号...")
#     strategy = SimpleMovingAverageStrategy(short_window=short_window, long_window=long_window)
#     df = strategy.generate_signals(df)

#     # ========== 3️⃣ 运行回测 ==========
#     print("🔄 运行回测...")
#     backtester = Backtester(
#         initial_balance=initial_balance,
#         leverage=leverage,
#         fee_rate=fee_rate,
#         slippage=slippage
#     )
#     results, trade_log = backtester.run_backtest(df)

#     # ========== 4️⃣ 输出回测结果 ==========
#     print("\n========== 回测交易记录 ========== ")
#     for trade in trade_log:
#         trade_type, trade_time, trade_price, size, current_balance = trade
#         print(
#             f"{trade_type:<4} | {trade_time} | "
#             f"价格: {trade_price:.2f}, 数量: {size:.6f}, 余额: {current_balance:.2f}"
#         )

#     # 打印回测核心指标
#     print("\n========== 回测最终结果 ========== ")
#     final_balance = results['equity_curve'].iloc[-1]
#     total_return = (final_balance - initial_balance) / initial_balance
#     max_drawdown = results["drawdown"].max()

#     print(f"初始资金: {initial_balance:.2f}")
#     print(f"最终资金: {final_balance:.2f}")
#     print(f"总收益率: {total_return:.2%}")
#     print(f"最大回撤: {max_drawdown:.2%}")
#     print(f"交易次数: {len(trade_log)//2} 次")


# if __name__ == "__main__":
#     main()
# main.py

def main():
    # 1. 初始化数据抓取器
    fetcher = OKXDataFetcher(instId="BNB-USDT")
    
    # 2. 获取过去 1 天的 1m K 线数据
    fetcher.fetch_1m_data(days=1)
    
    # 3. 获取清洗后的 DataFrame
    df = fetcher.get_cleaned_data()
    if df is None or df.empty:
        print("❌ 未能获取到任何市场数据，程序退出。")
        return

    print("✅ 成功获取市场数据，开始策略计算...")

    # 4. 初始化并计算策略信号
    strategy = VolatilityStrategy(df)
    strategy_df = strategy.get_strategy_df()

    # 注意：
    # `MovingAverageStrategy` 中我们定义了 `open_signal` 和 `close_signal`。
    # 当前 backtest_without_close_signal.py 只使用了 `open_signal`，请确认你在回测中如何使用或者忽略 `close_signal`.

    # 5. 运行回测
    print("▶️ 开始回测...")
    bt = Backtest(
        df=strategy_df,
        initial_balance=10000,
        leverage=5,
        open_fee=0.0005,
        close_fee=0.0005,
        tp_ratio=0.1,
        sl_ratio=0.05
    )

    # 6. 输出回测结果
    results_df = bt.get_results()

    print("✅ 回测完成。交易结果记录如下：")
    print(results_df)

    # 也可以做一些简单的统计分析
    if not results_df.empty:
        final_balance = results_df["final_balance"].iloc[-1]
        print(f"💰 最终余额: {final_balance:.2f}")

if __name__ == "__main__":
    main()
