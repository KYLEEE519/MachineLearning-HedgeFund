import threading
import time
from fivem import OKXKlineFetcher
from buffer import kline_buffer
from preheatv import initialize_buffer_with_historical_data
from tradeL import execute_trade  # 交易模块中的函数

if __name__ == "__main__":
    # 预热阶段：加载历史数据（例如21根5分钟K线）到 buffer.history
    initialize_buffer_with_historical_data()

    # 启动实时更新：启动 WebSocket 抓取并更新实时5分钟K线
    kline_fetcher = OKXKlineFetcher()
    threading.Thread(target=kline_fetcher.start, daemon=True).start()

    # 更新线程：每秒计算最新秒级K线并更新5分钟K线（写入buffer）
    def update_loop():
        while True:
            latest_second_kline = kline_fetcher.get_second_kline()
            if latest_second_kline is not None:
                kline_fetcher.update_5min_kline(latest_second_kline)
            time.sleep(1)

    threading.Thread(target=update_loop, daemon=True).start()

    # 主循环：读取buffer中的最新实时数据和历史记录，打印或传递给策略函数
    while True:
        latest_kline = kline_buffer.get_latest_kline()
        if latest_kline["five_min_kline"] is not None:
            print(f"📊 [策略] 读取最新 5 分钟 K 线: {latest_kline['five_min_kline']}")
            print(f"📊 [策略] 读取最新 秒级 K 线: {latest_kline['second_kline']}")
        else:
            print("⚠️ [BUFFER] `five_min_kline` 仍然是 None")

        history = kline_buffer.get_history()
        if history:
            print("📜 [历史] 5 分钟 K 线历史记录：")
            for idx, kl in enumerate(history):
                print(f"  #{idx+1}: {kl}")
        else:
            print("📜 [历史] 目前无历史记录")

        time.sleep(1)
