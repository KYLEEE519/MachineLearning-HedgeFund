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
            execute_trade()  # 只显示交易信号的 print
            time.sleep(0.3)
    trade_thread = threading.Thread(target=trade_loop, daemon=False)
    trade_thread.start()

    # 监测活跃线程数
    def monitor_threads():
        while True:
            print(f"🛠️ 活跃线程数: {threading.active_count()}, 线程列表: {[t.name for t in threading.enumerate()]}")
            time.sleep(5)  # 每 5 秒打印一次

    monitor_thread = threading.Thread(target=monitor_threads, daemon=True)
    monitor_thread.start()

    try:
        # 主循环（去掉所有 print，只监测交易信号和线程状态）
        while True:
            time.sleep(1)  # 主线程不需要打印，避免输出干扰
    except KeyboardInterrupt:
        print("收到退出信号，正在退出...")
        ws_thread.join(timeout=1)
        update_thread.join(timeout=1)
        trade_thread.join(timeout=1)
        print("程序已退出。")

if __name__ == "__main__":
    main()
