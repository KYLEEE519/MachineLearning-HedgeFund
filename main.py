from Data.getdata import OKXDataFetcher
from Strategies.simple_strategy import SimpleMovingAverageStrategy
from Backtest.backtest import Backtester

def main():
    # 1️⃣ **获取数据**
    print("🚀 获取数据中...")
    fetcher = OKXDataFetcher(instId="BTC-USDT")
    fetcher.fetch_1m_data(days=1)  # 只获取过去 1440 个数据点
    df = fetcher.get_cleaned_data()

    if df is None or df.empty:
        print("❌ 数据获取失败，程序退出。")
        return

    # 2️⃣ **应用策略**
    print("📊 计算交易信号...")
    strategy = SimpleMovingAverageStrategy(short_window=5, long_window=20)
    df = strategy.generate_signals(df)

    # 3️⃣ **运行回测**
    print("🔄 运行回测...")
    backtester = Backtester(initial_balance=10000, leverage=2, fee_rate=0.001, slippage=0.0005)
    results, trade_log = backtester.run_backtest(df)

    # 4️⃣ **输出回测结果**
    print("\n📜 交易记录:")
    for trade in trade_log:
        print(trade)

    print("\n📈 回测结果:")
    print(results.tail())  # 打印最后几行数据

if __name__ == "__main__":
    main()
