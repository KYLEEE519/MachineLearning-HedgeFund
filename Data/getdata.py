import pandas as pd
import time
import threading
from datetime import datetime
from okx import MarketData
'''
df每分钟第58秒自动更新
先执行：
fetcher = OKXDataFetcher(instId="TRUMP-USDT")  可以选择不同币
fetcher.fetch_1m_data(days=1)  
fetcher.start_real_time_fetch()
然后每次调用：df = fetcher.get_cleaned_data()可以获得最新df
'''
class OKXDataFetcher:
    def __init__(self, instId="BTC-USDT"):
        self.instId = instId
        self.df = None
        self._initialize_api()

    def _initialize_api(self):
        """即使公共API也需要基础配置"""
        self.market = MarketData.MarketAPI(
            api_key="",
            api_secret_key="",
            passphrase="",
            flag="0"  # 0: 实盘 1: 模拟盘
        )

    def fetch_1m_data(self, days=1):
        """
        初次获取 1 天数据（1440 条）
        """
        total_limit = 1440 * days
        all_data = []
        after = None
        retry = 0
        max_retries = 3

        print(f"▶️ 开始获取 {self.instId} {days}天数据...")

        while len(all_data) < total_limit and retry < max_retries:
            try:
                params = {
                    "instId": self.instId,
                    "bar": "1m",
                    "limit": min(300, total_limit - len(all_data))
                }
                if after is not None:
                    params["after"] = str(after)

                resp = self.market.get_candlesticks(**params)

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
                oldest = batch[-1]
                oldest_ts = int(oldest[0])
                after = oldest_ts - 1

                print(
                    f"▏已获取 {len(batch):>3} 条，"
                    f"累计 {len(all_data):>4}/{total_limit}",
                    end="\r"
                )
                time.sleep(0.15)
                retry = 0

            except Exception as e:
                print(f"🔴 请求异常: {str(e)}")
                retry += 1
                time.sleep(2 ** retry)

        # 整理成 DataFrame
        if all_data:
            columns = [
                "timestamp", "open", "high", "low", "close",
                "vol", "volCcy", "volCcyQuote", "confirm"
            ]

            full_df = pd.DataFrame(all_data, columns=columns)
            self.df = full_df[["timestamp", "open", "high", "low", "close", "vol"]].copy()

            numeric_cols = ["open", "high", "low", "close", "vol"]
            self.df[numeric_cols] = self.df[numeric_cols].apply(pd.to_numeric, errors="coerce")

            self.df["timestamp"] = pd.to_datetime(
                pd.to_numeric(self.df["timestamp"]),
                unit="ms",
                utc=True
            ).dt.tz_convert(None)

            self.df = self.df.drop_duplicates(subset=["timestamp"])
            self.df = self.df.sort_values("timestamp").reset_index(drop=True)

            print(f"\n✅ 最终获取 {len(self.df)} 条有效数据")
            if not self.df.empty:
                print(f"⏰ 时间范围: {self.df.timestamp.iloc[0]} 至 {self.df.timestamp.iloc[-1]}")
        else:
            print("❌ 未获取到任何有效数据")

    def fetch_latest_data(self):
        """
        每分钟获取最新 1m 数据并更新 df（滚动窗口）
        """
        try:
            params = {
                "instId": self.instId,
                "bar": "1m",
                "limit": 1  # 只获取 1 条最新数据
            }
            resp = self.market.get_candlesticks(**params)

            if resp.get("code") != "0":
                print(f"⚠️ API错误: {resp.get('msg')}")
                return

            latest = resp.get("data", [])[0]
            if not latest:
                print("❌ 未获取到最新数据")
                return

            latest_data = pd.DataFrame([latest], columns=[
                "timestamp", "open", "high", "low", "close",
                "vol", "volCcy", "volCcyQuote", "confirm"
            ])

            latest_data = latest_data[["timestamp", "open", "high", "low", "close", "vol"]].copy()
            latest_data[["open", "high", "low", "close", "vol"]] = latest_data[["open", "high", "low", "close", "vol"]].apply(pd.to_numeric, errors="coerce")
            latest_data["timestamp"] = pd.to_datetime(pd.to_numeric(latest_data["timestamp"]), unit="ms", utc=True).dt.tz_convert(None)

            # **处理第一次更新的问题**
            if self.df is not None and not self.df.empty:
                last_timestamp = self.df["timestamp"].iloc[-1]
                new_timestamp = latest_data["timestamp"].iloc[0]

                if last_timestamp == new_timestamp:
                    print(f"🔄 替换已有数据 {new_timestamp}（第一次更新修正）")
                    self.df.iloc[-1] = latest_data.iloc[0]  # 直接替换最后一行
                    print(f"\n📊 最新 5 条数据:\n{self.df.tail(5)}\n")
                    return  # 替换完成，返回，不执行后续追加操作

            # **正常追加新数据**
            if self.df is None or self.df.empty:
                self.df = latest_data
            else:
                self.df = pd.concat([self.df, latest_data]).drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

                if len(self.df) > 1440:  # 只保留最新的 1440 条数据
                    self.df = self.df.iloc[-1440:]

            print(f"✅ 新增数据: {latest_data['timestamp'].iloc[0]} {latest_data['close'].iloc[0]}")
            print(f"\n📊 最新 5 条数据:\n{self.df.tail(5)}\n")

        except Exception as e:
            print(f"🔴 请求异常: {str(e)}")

    def start_real_time_fetch(self):
        """
        每分钟倒数第三秒（58s）获取最新数据
        """
        def fetch_loop():
            while True:
                now = datetime.utcnow()
                if now.second == 58:  # 只在每分钟的 58 秒执行
                    self.fetch_latest_data()
                    time.sleep(1)  # 避免多次执行
                time.sleep(0.5)

        threading.Thread(target=fetch_loop, daemon=True).start()

    def get_cleaned_data(self):
        """返回最新的 DataFrame"""
        return self.df.copy() if self.df is not None else None

