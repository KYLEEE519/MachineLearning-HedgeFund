import threading
import time
from fivem import OKXKlineFetcher
from buffer import kline_buffer

if __name__ == "__main__":
    kline_fetcher = OKXKlineFetcher()
    threading.Thread(target=kline_fetcher.start, daemon=True).start()

    last_timestamp = None

    while True:
        latest_kline = kline_buffer.get_latest_kline()

        if latest_kline["five_min_kline"] is not None:
            print(f"📊 [策略] 读取最新 5 分钟 K 线: {latest_kline['five_min_kline']}")
            print(f"📊 [策略] 读取最新 秒级 K 线: {latest_kline['second_kline']}")
        else:
            print("⚠️ [BUFFER] `five_min_kline` 仍然是 None")

        time.sleep(0.05)  # ✅ 每 200ms 检查一次，减少 CPU 负载


