import threading
import time
from fivem import OKXKlineFetcher
from buffer import kline_buffer

if __name__ == "__main__":
    kline_fetcher = OKXKlineFetcher()
    threading.Thread(target=kline_fetcher.start, daemon=True).start()

    def update_loop():
        while True:
            latest_second_kline = kline_fetcher.get_second_kline()
            if latest_second_kline is not None:
                kline_fetcher.update_5min_kline(latest_second_kline)
            time.sleep(1)

    threading.Thread(target=update_loop, daemon=True).start()

    while True:
        latest_kline = kline_buffer.get_latest_kline()
        if latest_kline["five_min_kline"] is not None:
            print(f"📊 [策略] 读取最新 5 分钟 K 线: {latest_kline['five_min_kline']}")
            print(f"📊 [策略] 读取最新 秒级 K 线: {latest_kline['second_kline']}")
        else:
            print("⚠️ [BUFFER] `five_min_kline` 仍然是 None")

        # 另外，读取历史记录
        history = kline_buffer.get_history()
        if history:
            print("📜 [历史] 5 分钟 K 线历史记录：")
            for idx, kl in enumerate(history):
                print(f"  #{idx+1}: {kl}")
        else:
            print("📜 [历史] 目前无历史记录")
            
        time.sleep(1)
