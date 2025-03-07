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
        self.last_output_timestamp = None  # ✅ 记录上次输出的 K 线时间

    def on_message(self, ws, message):
        """ 处理 WebSocket 返回的交易数据 """
        data = json.loads(message)
        if "data" in data:
            trades = []
            for entry in data["data"]:
                trade = {
                    "timestamp": datetime.utcfromtimestamp(int(entry["ts"]) / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
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

            # ✅ 检查最后一条 K 线是否更新
            if not second_kline.empty:
                last_timestamp = second_kline.iloc[-1]["second"]

                if self.last_output_timestamp is None or last_timestamp > self.last_output_timestamp:
                    self.last_output_timestamp = last_timestamp  # ✅ 更新记录
                    return second_kline

            return None  # ❌ K 线没有更新，不输出

if __name__ == "__main__":
    kline_fetcher = OKXKlineFetcher()

    threading.Thread(target=kline_fetcher.start, daemon=True).start()

    while True:
        time.sleep(1)
        df_second_kline = kline_fetcher.get_second_kline()
        if df_second_kline is not None:
            print(df_second_kline.tail(1))  # ✅ 只有 K 线有新数据时才打印
