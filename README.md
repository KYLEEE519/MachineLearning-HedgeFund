<<<<<<< HEAD
# COIN
创建虚拟环境代码：
python -m venv coin
.\coin\Scripts\Activate
pip install -r requirements.txt
python main.py
# getdata
fetcher = OKXDataFetcher(instId="TRUMP-USDT")  创建实例，可以选择不同的币种
fetcher.fetch_1m_data(days=1) 获取1天的分钟数据
fetcher.start_real_time_fetch() 后台线程持续获取新数据，每分钟的第58秒请求这一分钟的k线，59.5秒之前就能得到新的数据
然后每次调用：df = fetcher.get_cleaned_data()可以获得最新df
# test_strategy
测试策略，策略对于df添加open_signal：1开多，-1开空，0无操作。close_signal：-1平多，1平空，0无操作。
# excute
每分钟第58秒更新数据，59.5秒对于新数据使用策略，并且返回包含策略的df
# data_clean
原始数据转化成1分钟级的k线
使用方法：
processor = KlineProcessor("")填入地址
kline_df = processor.get_kline_df()
print(kline_df.head())  # 查看转换后的 K 线数据