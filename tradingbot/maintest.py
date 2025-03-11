import threading
import time
from fivem import OKXKlineFetcher
from buffer import kline_buffer
from preheatv import initialize_buffer_with_historical_data
from tradeL import execute_trade  # 交易模块中的函数

def main():
    # 预热阶段：加载历史数据到 buffer.history（例如21根5分钟K线）
    initialize_buffer_with_historical_data()

    # 启动实时更新线程：启动 WebSocket 抓取并更新实时5分钟K线
    kline_fetcher = OKXKlineFetcher()
    ws_thread = threading.Thread(target=kline_fetcher.start, daemon=False)
    ws_thread.start()

    # 更新线程：每秒计算最新秒级K线并更新5分钟K线（写入 buffer）
    def update_loop():
        while True:
            latest_second_kline = kline_fetcher.get_second_kline()
            if latest_second_kline is not None:
                kline_fetcher.update_5min_kline(latest_second_kline)
            time.sleep(1)
    update_thread = threading.Thread(target=update_loop, daemon=False)
    update_thread.start()

    # 交易线程：周期性执行交易逻辑
    def trade_loop():
        while True:
            execute_trade()  # 内部会从全局 buffer 获取最新的历史+实时数据构造 DataFrame
            time.sleep(0.3)
    trade_thread = threading.Thread(target=trade_loop, daemon=False)
    trade_thread.start()

    try:
        # 主循环：打印调试 buffer 中的数据
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
    except KeyboardInterrupt:
        print("收到退出信号，正在退出...")
        ws_thread.join(timeout=1)
        update_thread.join(timeout=1)
        trade_thread.join(timeout=1)
        print("程序已退出。")

if __name__ == "__main__":
    main()
