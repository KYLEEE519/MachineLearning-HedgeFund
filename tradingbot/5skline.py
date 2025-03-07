import websocket
import json
import pandas as pd
import threading
import time
from datetime import datetime

OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"

class OKXKlineFetcher:
    def __init__(self, symbol="DOGE-USDT-SWAP"):
        self.symbol = symbol
        self.df = pd.DataFrame(columns=["timestamp", "price", "size", "side"])
        self.ws = None
        self.lock = threading.Lock()
        self.last_output_timestamp = None  # 记录上次秒级 K 线的时间
        
        # ✅ 5 分钟 K 线存储
        self.current_5min_start = None
        self.current_5min_kline = None
        self.last_printed_5min_kline = None  # 记录上次打印的 5 分钟 K 线

    def on_message(self, ws, message):
        """ 处理 WebSocket 返回的交易数据 """
        data = json.loads(message)
        if "data" in data:
            trades = []
            for entry in data["data"]:
                trade_time = datetime.utcfromtimestamp(int(entry["ts"]) / 1000)
                trade = {
                    "timestamp": trade_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],  # ✅ 转换时间格式
                    "price": float(entry["px"]),
                    "size": float(entry["sz"]),
                    "side": entry["side"]
                }
                trades.append(trade)

            with self.lock:
                self.df = pd.concat([self.df, pd.DataFrame(trades)], ignore_index=True)

    def on_open(self, ws):
        """ 订阅逐笔交易数据 """
        params = {
            "op": "subscribe",
            "args": [{"channel": "trades", "instId": self.symbol}]
        }
        ws.send(json.dumps(params))
        print(f"✅ 已订阅 {self.symbol} 交易数据")

    def start(self):
        """ 启动 WebSocket 连接 """
        self.ws = websocket.WebSocketApp(
            OKX_WS_URL,
            on_message=self.on_message,
            on_open=self.on_open
        )
        print("✅ K 线 WebSocket 连接启动")
        self.ws.run_forever()

    def get_second_kline(self):
        """ 计算秒级 K 线 """
        with self.lock:
            if self.df.empty:
                return None

            self.df["timestamp"] = pd.to_datetime(self.df["timestamp"])
            self.df["second"] = self.df["timestamp"].dt.floor("s")

            second_kline = self.df.groupby("second").agg(
                open=("price", "first"),
                high=("price", "max"),
                low=("price", "min"),
                close=("price", "last"),
                vol=("size", "sum")
            ).reset_index()

            # ✅ 只有新数据时才输出
            if not second_kline.empty:
                last_timestamp = second_kline.iloc[-1]["second"]

                if self.last_output_timestamp is None or last_timestamp > self.last_output_timestamp:
                    self.last_output_timestamp = last_timestamp  # ✅ 更新记录
                    return second_kline.iloc[-1]  # 只返回最新一秒的 K 线数据

            return None  # ❌ K 线没有更新，不输出

    def update_5min_kline(self, latest_second_kline):
        """ 实时更新 5 分钟 K 线 """
        with self.lock:
            if latest_second_kline is None:
                return None

            latest_time = latest_second_kline["second"]
            current_5min_time = latest_time.floor("5min")  # ✅ 修复 `floor("5T")` 警告

            # ✅ 如果当前 5 分钟窗口变了，开启新的 5 分钟 K 线
            if self.current_5min_start is None or current_5min_time > self.current_5min_start:
                # ✅ 如果有旧的 5 分钟 K 线，先输出（仅当有新 5 分钟窗口时）
                if self.current_5min_kline is not None:
                    print(f"🔥 [完整 5 分钟 K 线] {self.current_5min_kline}")

                # ✅ 开启新的 5 分钟 K 线
                self.current_5min_start = current_5min_time
                self.current_5min_kline = {
                    "timestamp": current_5min_time,
                    "open": float(latest_second_kline["open"]),  # ✅ 转换为 `float`
                    "high": float(latest_second_kline["high"]),
                    "low": float(latest_second_kline["low"]),
                    "close": float(latest_second_kline["close"]),
                    "vol": float(latest_second_kline["vol"])  # ✅ 修正 `vol`
                }
            else:
                # ✅ 继续更新当前 5 分钟 K 线
                self.current_5min_kline["high"] = max(self.current_5min_kline["high"], float(latest_second_kline["high"]))
                self.current_5min_kline["low"] = min(self.current_5min_kline["low"], float(latest_second_kline["low"]))
                self.current_5min_kline["close"] = float(latest_second_kline["close"])
                self.current_5min_kline["vol"] += float(latest_second_kline["vol"])  # ✅ 确保 `vol` 累加

            return self.current_5min_kline

if __name__ == "__main__":
    kline_fetcher = OKXKlineFetcher()

    threading.Thread(target=kline_fetcher.start, daemon=True).start()

    while True:
        time.sleep(1)
        latest_second_kline = kline_fetcher.get_second_kline()
        if latest_second_kline is not None:
            five_minute_kline = kline_fetcher.update_5min_kline(latest_second_kline)
            
            # ✅ 只有当 5 分钟 K 线更新时，才打印最新的
            if five_minute_kline and five_minute_kline != kline_fetcher.last_printed_5min_kline:
                print(f"🔥 [实时更新 5 分钟 K 线] {five_minute_kline}")  # ✅ 只输出最新一条 5 分钟 K 线
                kline_fetcher.last_printed_5min_kline = five_minute_kline.copy()  # ✅ 复制字典，确保不会被修改

