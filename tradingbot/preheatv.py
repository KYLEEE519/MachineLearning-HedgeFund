import pandas as pd
import time
from datetime import datetime
from okx import MarketData
from buffer import kline_buffer  # 导入双缓冲管理器
import numpy as np

def fetch_5m_data(instId="DOGE-USDT-SWAP", num_bars=22):
    """
    获取最近 num_bars 根 5 分钟 K 线数据（这里抓取22根历史数据）
    """
    market = MarketData.MarketAPI(api_key="", api_secret_key="", passphrase="", flag="0")
    all_data = []
    after = None
    retry = 0
    max_retries = 3

    print(f"▶️ 开始获取 {instId} 最近 {num_bars} 根 5 分钟 K 线数据...")

    while len(all_data) < num_bars and retry < max_retries:
        try:
            params = {"instId": instId, "bar": "5m", "limit": min(300, num_bars - len(all_data))}
            if after is not None:
                params["after"] = str(after)

            resp = market.get_candlesticks(**params)
            if resp.get("code") != "0":
                print(f"⚠️ API错误: {resp.get('msg')}")
                retry += 1
                time.sleep(1)
                continue

            batch = resp.get("data", [])
            if not batch:
                print("✅ 已获取全部可用数据")
                break

            all_data.extend(batch)
            oldest_ts = int(batch[-1][0])
            after = oldest_ts - 1

            print(f"  已获取 {len(batch):3d} 条，累计 {len(all_data):4d}/{num_bars}", end="\r")
            time.sleep(0.15)
            retry = 0

        except Exception as e:
            print(f"🔴 请求异常: {str(e)}")
            retry += 1
            time.sleep(2 ** retry)

    if all_data:
        columns = ["timestamp", "open", "high", "low", "close", "vol", "volCcy", "volCcyQuote", "confirm"]
        full_df = pd.DataFrame(all_data, columns=columns)
        df = full_df[["timestamp", "open", "high", "low", "close", "vol"]].copy()

        numeric_cols = ["open", "high", "low", "close", "vol"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True).dt.tz_convert(None)
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

 #       print(f"\n✅ 最终获取 {len(df)} 条有效 5 分钟 K 线数据")
        return df

#    print("❌ 未获取到任何有效数据")
    return None

def initialize_buffer_with_historical_data():
    """
    用获取的 22 根 5 分钟 K 线数据初始化 KlineBuffer：
      - 将 22 根数据中的前 21 根作为历史记录写入 buffer.history
      - 不用将第 22 根写入 buffer 的实时部分，等待实时更新逻辑生成最新数据
    """
    num_bars = 22
    df = fetch_5m_data(num_bars=num_bars)
    if df is None or df.empty:
   #     print("⚠️ [BUFFER] 无法初始化，5 分钟 K 线数据为空")
        return

    # 将 DataFrame 转换为字典列表（按时间从旧到新排列）
    kline_list = df.to_dict(orient="records")
    # 如果数据数量足够，则取前 21 根作为历史记录
    if len(kline_list) < num_bars:
 #       print(f"⚠️ [BUFFER] 数据不足：只有 {len(kline_list)} 根")
        return

    history_list = kline_list[:-1]  # 删除最后一根，第22根
    for candle in history_list:
        with kline_buffer.lock:
            kline_buffer.history.append(candle)
 #       print(f"✅ [BUFFER] 预热历史记录追加: {candle}")

    # 初始化实时部分为空（或用默认空数据）
    empty_second_kline = {
        "open": None, "high": None, "low": None, "close": None, "vol": None, "timestamp": None
    }
    kline_buffer.update_main_buffer(empty_second_kline, None, finished=False)
    kline_buffer.swap_buffers()
#    print("✅ [BUFFER] 预热完成，历史数据加载成功")
    
if __name__ == "__main__":
    initialize_buffer_with_historical_data()
