# main.py
from Data.getdata import OKXDataFetcher
from Strategies.simple_strategy import SimpleMovingAverageStrategy
from Backtest.backtest import Backtester
from Strategies.test_strategy import MovingAverageStrategy
from Backtest.backtest_without_close_signal import Backtest
from Strategies.strategy_1 import VolatilityStrategy
# def main():
#     # 1. 初始化数据抓取器
#     fetcher = OKXDataFetcher(instId="LUNA-USDT")
    
#     # 2. 获取过去 1 天的 1m K 线数据
#     fetcher.fetch_1m_data(days=1)
    
#     # 3. 获取清洗后的 DataFrame
#     df = fetcher.get_cleaned_data()
#     if df is None or df.empty:
#         print("❌ 未能获取到任何市场数据，程序退出。")
#         return

#     print("✅ 成功获取市场数据，开始策略计算...")

#     # 4. 初始化并计算策略信号
#     strategy = ChanAndSmaCombinedStrategy(short_window=5, medium_window=10, long_window=20)
#     strategy_df = strategy.generate_signals(df)
#     # 注意：
#     # `MovingAverageStrategy` 中我们定义了 `open_signal` 和 `close_signal`。
#     # 当前 backtest_without_close_signal.py 只使用了 `open_signal`，请确认你在回测中如何使用或者忽略 `close_signal`.

#     # 5. 运行回测
#     print("▶️ 开始回测...")
#     bt = Backtest(
#         df=strategy_df,
#         initial_balance=10000,
#         leverage=5,
#         open_fee=0.0005,
#         close_fee=0.0005,
#         tp_ratio=0.1,
#         sl_ratio=0.05
#     )

#     # 6. 输出回测结果
#     results_df = bt.get_results()

#     print("✅ 回测完成。交易结果记录如下：")
#     print(results_df)

#     # 也可以做一些简单的统计分析
#     if not results_df.empty:
#         final_balance = results_df["final_balance"].iloc[-1]
#         print(f"💰 最终余额: {final_balance:.2f}")

# if __name__ == "__main__":
#     main()
# main.py

def main():
    # 1. 初始化数据抓取器
    fetcher = OKXDataFetcher(instId="LUNA-USDT")
    
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
