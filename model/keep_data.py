import sys
import os
import pandas as pd

# 获取当前文件的上级目录（项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 把 Data 目录添加到 sys.path
sys.path.append(os.path.join(BASE_DIR, "Data"))

# 现在可以导入 getdata.py 了
from getdata import OKXDataFetcher

# 初始化数据获取器
fetcher = OKXDataFetcher(instId="BTC-USDT")

# 获取过去 1 天的 1m K线数据
fetcher.fetch_1m_data(days=1)

# 获取清理后的数据
data = fetcher.get_cleaned_data()

# 获取 `model/` 目录的路径
model_dir = os.path.dirname(os.path.abspath(__file__))

# 设置数据保存路径
save_path = os.path.join(model_dir, "btc_1m_data.csv")

# 保存数据到 CSV 文件
if data is not None and not data.empty:
    data.to_csv(save_path, index=False)
    print(f"✅ 数据已保存至 {save_path}")
else:
    print("❌ 未能获取到有效数据")
