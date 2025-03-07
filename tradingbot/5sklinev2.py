import websocket
import json
import pandas as pd
import threading
import time
from datetime import datetime
from flask import Flask, jsonify
from okx import MarketData  # OKX API SDK

OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
SYMBOL = "DOGE-USDT-SWAP"

# ✅ 启动 Flask API 服务器
app = Flask(__name__)

class OKXDataHandler:
    def __init__(self, symbol=SYMBOL):
        self.symbol = symbol
        self.df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "vol"])
        self.raw_df = pd.DataFrame(columns=["timestamp", "price", "size", "side"])
        self.ws = None
        self.lock = threading.Lock()
        self.ws_thread = None
        self.current_5min_kline = None
        self.last_5min_timestamp = None
        self.market = MarketData.MarketAPI(api_key="", api_secret_key="", passphrase="", flag="0")

        # ✅ 获取历史 5 分钟 K 线数据
        self.historical_klines = self.fetch_historical_5m_klines()

    def fetch_historical_5m_klines(self):
        """ 获取历史 5 分钟 K 线（从 OKX API 拉取）"""
        try:
            params = {"instId": self.symbol, "bar": "5m", "limit": 100}
            response = self.market.get_candlesticks(**params)

            if response.get("code") != "0":
                print(f"⚠️ API 错误: {response.get('msg')}")
                return {}

            data = response.get("data", [])
            if not data:
                print("⚠️ 没有获取到历史 K 线数据")
                return {}

            # ✅ **确保正确提取数据**
            df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "vol", "volCcy", "volCcyQuote", "confirm"])

            # ✅ **只保留需要的 6 列**
            df = df[["timestamp", "open", "high", "low", "close", "vol"]]

            # ✅ **转换数据类型**
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            numeric_cols = ["open", "high", "low", "close", "vol"]
            df[numeric_cols] = df[numeric_cols].astype(float)

            df = df.sort_values("timestamp").reset_index(drop=True)

            historical_klines = {
                row["timestamp"]: row
                for _, row in df.iterrows()
            }

            print(f"✅ 获取 {len(historical_klines)} 条 5 分钟 K 线历史数据")
            return historical_klines

        except Exception as e:
            print(f"🔴 5 分钟历史数据获取失败: {str(e)}")
            return {}

    def start_websocket(self):
        """ 启动 WebSocket 连接 """
        if self.ws and self.ws.sock and self.ws.sock.connected:
            print("⚠️ WebSocket 已连接，跳过重复连接")
            return

        self.ws = websocket.WebSocketApp(
            OKX_WS_URL,
            on_message=self.on_message,
            on_open=lambda ws: ws.send(json.dumps({"op": "subscribe", "args": [{"channel": "trades", "instId": self.symbol}]}))
        )
        print("✅ WebSocket 连接启动")
        self.ws.run_forever()

    def on_message(self, ws, message):
        """ 处理 WebSocket 返回的交易数据 """
        data = json.loads(message)
        if "data" in data:
            trades = []
            for entry in data["data"]:
                trade_time = datetime.utcfromtimestamp(int(entry["ts"]) / 1000)
                trade = {
                    "timestamp": trade_time,
                    "price": float(entry["px"]),
                    "size": float(entry["sz"]),
                    "side": entry["side"]
                }
                trades.append(trade)

            with self.lock:
                self.raw_df = pd.concat([self.raw_df, pd.DataFrame(trades)], ignore_index=True)

    def get_second_kline(self):
        """ 生成秒级 K 线 """
        with self.lock:
            if self.raw_df.empty:
                return None

            self.raw_df["second"] = self.raw_df["timestamp"].dt.floor("S")

            second_kline = self.raw_df.groupby("second").agg(
                open=("price", "first"),
                high=("price", "max"),
                low=("price", "min"),
                close=("price", "last"),
                vol=("size", "sum")
            ).reset_index()

            return second_kline

    def update_5min_kline(self, latest_second_kline):
        """ 实时更新 5 分钟 K 线，并存入 DataFrame """
        latest_time = latest_second_kline["second"].iloc[-1]
        current_5min_time = latest_time.floor("5min")

        if self.last_5min_timestamp is None or self.last_5min_timestamp < current_5min_time:
            print(f"🆕 进入新的 5 分钟 K 线周期: {current_5min_time}")

            # ✅ **获取 REST API 历史数据**
            self.historical_klines = self.fetch_historical_5m_klines()

            if self.last_5min_timestamp in self.historical_klines:
                historical_kline = self.historical_klines[self.last_5min_timestamp]

                if not self.df[self.df["timestamp"] == self.last_5min_timestamp].empty:
                    self.df.loc[self.df["timestamp"] == self.last_5min_timestamp, ["open", "high", "low", "close", "vol"]] = [
                        historical_kline["open"], historical_kline["high"],
                        historical_kline["low"], historical_kline["close"],
                        historical_kline["vol"]
                    ]
                else:
                    self.df = pd.concat([self.df, pd.DataFrame([historical_kline])], ignore_index=True)

            # ✅ **初始化新 5 分钟 K 线**
            self.current_5min_kline = {
                "timestamp": current_5min_time,
                "open": latest_second_kline["open"].iloc[-1],
                "high": latest_second_kline["high"].iloc[-1],
                "low": latest_second_kline["low"].iloc[-1],
                "close": latest_second_kline["close"].iloc[-1],
                "vol": latest_second_kline["vol"].iloc[-1]
            }

            self.df = pd.concat([self.df, pd.DataFrame([self.current_5min_kline])], ignore_index=True)
            self.last_5min_timestamp = current_5min_time

        else:
            # ✅ **持续更新当前 5 分钟 K 线**
            self.current_5min_kline["high"] = max(self.current_5min_kline["high"], latest_second_kline["high"].iloc[-1])
            self.current_5min_kline["low"] = min(self.current_5min_kline["low"], latest_second_kline["low"].iloc[-1])
            self.current_5min_kline["close"] = latest_second_kline["close"].iloc[-1]
            self.current_5min_kline["vol"] += latest_second_kline["vol"].iloc[-1]

            self.df.loc[self.df["timestamp"] == self.last_5min_timestamp, ["high", "low", "close", "vol"]] = [
                self.current_5min_kline["high"], self.current_5min_kline["low"],
                self.current_5min_kline["close"], self.current_5min_kline["vol"]
            ]

        print(f"🔥 [实时更新 5 分钟 K 线] {self.current_5min_kline}")

@app.route("/get_dataframe")
def get_dataframe():
    df_cleaned = handler.df.dropna(subset=["timestamp"]).copy()
    df_cleaned["timestamp"] = df_cleaned["timestamp"].astype(str)
    return jsonify(df_cleaned.to_dict(orient="records"))

if __name__ == "__main__":
    handler = OKXDataHandler()
    threading.Thread(target=lambda: app.run(debug=True, use_reloader=False), daemon=True).start()

    while True:
        time.sleep(1)
        df_second_kline = handler.get_second_kline()
        if df_second_kline is not None:
            handler.update_5min_kline(df_second_kline)
