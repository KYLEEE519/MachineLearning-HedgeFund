import pandas as pd
import os
from okx_fetch_data import fetch_kline_df
from datetime import datetime

df_cache = None  # 临时数据缓存
df_csv = None    # 读取的CSV数据

def show_data(days, bar, instId):
    global df_cache
    df_cache = fetch_kline_df(days=days, bar=bar, instId=instId)
    if df_cache.empty:
        return "未获取到数据，请检查参数！", ""
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

def load_csv(csv_path):
    global df_csv
    if not os.path.exists(csv_path):
        return "路径不存在，请检查！", ""

    df_csv = pd.read_csv(csv_path)
    return df_csv.head().to_markdown(), ", ".join(df_csv.columns.tolist())

def save_data(instId):
    global df_cache
    if df_cache is None:
        return "请先获取数据！"
    
    # 确保目录存在
    save_dir = "./data"
    os.makedirs(save_dir, exist_ok=True)

    # 文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{instId}_{timestamp}.csv"
    save_path = os.path.join(save_dir, filename)

    # 保存
    df_cache.to_csv(save_path, index=False)

    # 返回绝对路径
    abs_path = os.path.abspath(save_path)

    return f"数据已保存至: {abs_path}"
