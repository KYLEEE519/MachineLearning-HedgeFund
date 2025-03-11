import pandas as pd
import time
from datetime import datetime
from okx import MarketData
from buffer import kline_buffer  # ✅ 导入双缓冲
import numpy as np

def fetch_5m_data(instId="DOGE-USDT-SWAP", num_bars=22):
    """
    获取最近 num_bars 根 5 分钟 K 线数据
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

    # 整理成 DataFrame
    if all_data:
        columns = ["timestamp", "open", "high", "low", "close", "vol", "volCcy", "volCcyQuote", "confirm"]
        full_df = pd.DataFrame(all_data, columns=columns)
        df = full_df[["timestamp", "open", "high", "low", "close", "vol"]].copy()

        numeric_cols = ["open", "high", "low", "close", "vol"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True).dt.tz_convert(None)
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

        print(f"\n✅ 最终获取 {len(df)} 条有效 5 分钟 K 线数据")
        return df

    print("❌ 未获取到任何有效数据")
    return None

def initialize_buffer_with_historical_data():
    """
    用获取的 22 根 5 分钟 K 线数据初始化 `KlineBuffer`
    """
    df = fetch_5m_data()
    if df is None or df.empty:
        print("⚠️ [BUFFER] 无法初始化，5 分钟 K 线数据为空")
        return

    # 取最近 22 根 5 分钟 K 线
    latest_5m_kline = df.iloc[-1].to_dict()

    # 先填充一个空的秒级 K 线
    empty_second_kline = {
        "open": np.nan, "high": np.nan, "low": np.nan, "close": np.nan, "vol": np.nan, "timestamp": None
    }

    # ✅ 更新缓冲区，确保策略可以运行
    kline_buffer.update_main_buffer(empty_second_kline, latest_5m_kline)
    kline_buffer.swap_buffers()
    print(f"✅ [BUFFER] 预热数据加载成功: {latest_5m_kline}")

if __name__ == "__main__":
    initialize_buffer_with_historical_data()
