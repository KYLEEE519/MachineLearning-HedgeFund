import time
from Data.getdata import OKXDataFetcher
from Strategies.test_strategy import MovingAverageStrategy

fetcher = OKXDataFetcher(instId="TRUMP-USDT")
fetcher.fetch_1m_data(days=1)  # 获取历史数据
fetcher.start_real_time_fetch()  # 启动自动数据获取

while True:
    now = datetime.utcnow()
    if now.second == 59 and now.microsecond >= 500000:  # 59.5 秒
        df = fetcher.get_cleaned_data()  # 获取最新数据
        if df is not None and not df.empty:
            strategy = MovingAverageStrategy(df)
            strategy_df = strategy.get_strategy_df()
            print(f"✅ {now.strftime('%H:%M:%S')} - 策略已更新")
            print(strategy_df.tail(5))  # 打印最新 5 条数据
        else:
            print(f"⚠️ {now.strftime('%H:%M:%S')} - 数据为空，无法计算策略")
        time.sleep(1)  # 避免重复执行
    time.sleep(0.2)  # 每 0.2 秒检查一次