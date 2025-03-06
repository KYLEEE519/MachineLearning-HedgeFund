import websocket
import json
import threading
import time
import base64
import hmac

OKX_WS_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"

# ✅ 填入你的 API 认证信息
API_KEY = "df95c4bf-60e4-43b7-bc11-e2685f608605"
SECRET_KEY = "3B0DBD08C69C46C4C39AEB36B46A1731"
PASSPHRASE = "Qinmeng123@"

class OKXAccountFetcher:
    def __init__(self):
        self.ws = None
        self.lock = threading.Lock()
        self.balance = 0  # ✅ 账户余额
        self.position = None  # ✅ 持仓信息
        self.position_size = 0  # ✅ 仓位大小

    def generate_signature(self):
        """ 生成 OKX API 认证签名 """
        timestamp = str(time.time())
        message = timestamp + "GET" + "/users/self/verify"
        mac = hmac.new(bytes(SECRET_KEY, encoding='utf-8'), bytes(message, encoding='utf-8'), digestmod='sha256')
        sign = base64.b64encode(mac.digest()).decode()
        return timestamp, sign

    def on_message(self, ws, message):
        """ 处理 WebSocket 返回的数据 """
        data = json.loads(message)

        # ✅ 账户余额更新
        if "data" in data and "account" in data["arg"]["channel"]:
            balance_info = data["data"][0]
            with self.lock:
                self.balance = float(balance_info["availableEq"])
            print(f"💰 账户余额更新: {self.balance}")

        # ✅ 持仓信息更新
        if "data" in data and "positions" in data["arg"]["channel"]:
            pos_info = data["data"][0]
            with self.lock:
                if float(pos_info["pos"]) > 0:
                    self.position = {
                        "direction": "long" if float(pos_info["pos"]) > 0 else "short",
                        "entry_price": float(pos_info["avgPx"]),
                        "size": float(pos_info["pos"]),
                        "margin": float(pos_info["margin"])
                    }
                    self.position_size = self.position["size"]
                else:
                    self.position = None
                    self.position_size = 0
            print(f"📊 持仓信息更新: {self.position}")

    def on_open(self, ws):
        """ 订阅账户 & 持仓数据 """
        timestamp, sign = self.generate_signature()

        auth_data = {
            "op": "login",
            "args": [{
                "apiKey": API_KEY,
                "passphrase": PASSPHRASE,
                "timestamp": timestamp,
                "sign": sign
            }]
        }
        ws.send(json.dumps(auth_data))

        # ✅ 认证成功后订阅账户信息
        time.sleep(1)
        params = {
            "op": "subscribe",
            "args": [
                {"channel": "account", "ccy": "USDT"},  # ✅ 账户余额
                {"channel": "positions", "instType": "SWAP"}  # ✅ 持仓数据
            ]
        }
        ws.send(json.dumps(params))
        print("✅ 已订阅账户 & 持仓信息")

    def start(self):
        """ 启动 WebSocket 连接 """
        self.ws = websocket.WebSocketApp(
            OKX_WS_PRIVATE_URL,
            on_message=self.on_message,
            on_open=self.on_open
        )
        print("✅ 账户 WebSocket 连接启动")
        self.ws.run_forever()

if __name__ == "__main__":
    account_fetcher = OKXAccountFetcher()

    threading.Thread(target=account_fetcher.start, daemon=True).start()

    while True:
        time.sleep(5)
        print(f"🔍 账户余额: {account_fetcher.balance}, 持仓: {account_fetcher.position}, 仓位大小: {account_fetcher.position_size}")
