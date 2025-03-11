import websocket
import json
import pandas as pd
import threading
import time
from datetime import datetime
from buffer import kline_buffer  # ✅ 导入双缓冲管理器

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

    def on_message(self, ws, message):
        """ 处理 WebSocket 返回的交易数据 """
        data = json.loads(message)
        if "data" in data:
            trades = []
            for entry in data["data"]:
                trade_time = datetime.utcfromtimestamp(int(entry["ts"]) / 1000)
                trade = {
                    "timestamp": trade_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
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

            if not second_kline.empty:
                last_timestamp = second_kline.iloc[-1]["second"]

                if self.last_output_timestamp is None or last_timestamp > self.last_output_timestamp:
                    self.last_output_timestamp = last_timestamp
                    return second_kline.iloc[-1]

            return None  # ❌ 没有更新，不输出

    def update_5min_kline(self, latest_second_kline):
        """ 每次秒级 K 线更新，就实时更新 5 分钟 K 线，并存入缓冲区 """
        with self.lock:
            if latest_second_kline is None:
                print("⚠️ `latest_second_kline` 为空，无法更新 5 分钟 K 线")
                return None

            latest_time = latest_second_kline["second"]
            current_5min_time = latest_time.floor("5min")

            # ✅ 如果 5 分钟窗口变更，存储旧数据并开启新的 5 分钟 K 线
            if self.current_5min_start is None or current_5min_time > self.current_5min_start:
                if self.current_5min_kline is not None:
                    print(f"🔥 [完整 5 分钟 K 线] {self.current_5min_kline}")  
                    kline_buffer.update_main_buffer(latest_second_kline, self.current_5min_kline)
                    kline_buffer.swap_buffers()  # ✅ 交换缓冲

                # ✅ 开启新的 5 分钟 K 线
                self.current_5min_start = current_5min_time
                self.current_5min_kline = {
                    "timestamp": current_5min_time,
                    "open": float(latest_second_kline["open"]),
                    "high": float(latest_second_kline["high"]),
                    "low": float(latest_second_kline["low"]),
                    "close": float(latest_second_kline["close"]),
                    "vol": float(latest_second_kline["vol"])
                }
            else:
                # ✅ 实时更新 5 分钟 K 线
                self.current_5min_kline["high"] = max(self.current_5min_kline["high"], float(latest_second_kline["high"]))
                self.current_5min_kline["low"] = min(self.current_5min_kline["low"], float(latest_second_kline["low"]))
                self.current_5min_kline["close"] = float(latest_second_kline["close"])
                self.current_5min_kline["vol"] += float(latest_second_kline["vol"])

            # ✅ **每次 5 分钟 K 线更新，都存入 `buffer`**
            kline_buffer.update_main_buffer(latest_second_kline, self.current_5min_kline)
            kline_buffer.swap_buffers()  # ✅ 交换缓冲
            print(f"✅ [BUFFER] 5 分钟 K 线实时存入: {self.current_5min_kline}")  

            return self.current_5min_kline

