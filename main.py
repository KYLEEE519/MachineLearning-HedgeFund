# main.py
from Data.getdata import OKXDataFetcher
from Strategies.simple_strategy import SimpleMovingAverageStrategy
from Backtest.backtest import Backtester
def main():
    # ========== 参数设置 ==========

    # 数据参数
    inst_id = "BTC-USDT"
    days = 1

    # 策略参数
    short_window = 5
    long_window = 20

    # 回测参数
    initial_balance = 10000.0
    leverage = 2.0
    fee_rate = 0.001
    slippage = 0.0005

    # ========== 1️⃣ 获取数据 ========== 
    print("🚀 获取数据中...")
    fetcher = OKXDataFetcher(instId=inst_id)
    fetcher.fetch_1m_data(days=days)
    df = fetcher.get_cleaned_data()

    if df is None or df.empty:
        print("❌ 数据获取失败，程序退出。")
        return

    # ========== 2️⃣ 应用策略 ==========
    print("📊 计算交易信号...")
    strategy = SimpleMovingAverageStrategy(short_window=short_window, long_window=long_window)
    df = strategy.generate_signals(df)

    # ========== 3️⃣ 运行回测 ==========
    print("🔄 运行回测...")
    backtester = Backtester(
        initial_balance=initial_balance,
        leverage=leverage,
        fee_rate=fee_rate,
        slippage=slippage
    )
    results, trade_log = backtester.run_backtest(df)

    # ========== 4️⃣ 输出回测结果 ==========
    print("\n========== 回测交易记录 ========== ")
    for trade in trade_log:
        trade_type, trade_time, trade_price, size, current_balance = trade
        print(
            f"{trade_type:<4} | {trade_time} | "
            f"价格: {trade_price:.2f}, 数量: {size:.6f}, 余额: {current_balance:.2f}"
        )

    # 打印回测核心指标
    print("\n========== 回测最终结果 ========== ")
    final_balance = results['equity_curve'].iloc[-1]
    total_return = (final_balance - initial_balance) / initial_balance
    max_drawdown = results["drawdown"].max()

    print(f"初始资金: {initial_balance:.2f}")
    print(f"最终资金: {final_balance:.2f}")
    print(f"总收益率: {total_return:.2%}")
    print(f"最大回撤: {max_drawdown:.2%}")
    print(f"交易次数: {len(trade_log)//2} 次")


if __name__ == "__main__":
    main()
