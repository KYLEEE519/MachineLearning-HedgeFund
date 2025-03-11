import threading
import time
import traceback
from fivem import OKXKlineFetcher
from buffer import kline_buffer
from preheatv import initialize_buffer_with_historical_data
from tradeL import execute_trade  # 交易模块中的函数

# 共享变量
kline_fetcher = None  # 使 kline_fetcher 变为全局变量，保证各个线程都能访问
threads = {}

def start_websocket():
    """ 启动 WebSocket 线程，并在崩溃时重连 """
    global kline_fetcher  # 让 kline_fetcher 作用于整个程序
    while True:
        try:
            print("🚀 [WebSocket] 启动 WebSocket 连接...")
            kline_fetcher = OKXKlineFetcher()
            kline_fetcher.start()
        except Exception as e:
            print(f"⚠️ [WebSocket] 连接异常: {e}")
            traceback.print_exc()
            print("🔄 [WebSocket] 5 秒后尝试重新连接...")
            time.sleep(5)  # 休息 5 秒后重试

def update_loop():
    """ 每秒更新秒级 K 线，并维护 5 分钟 K 线 """
    global kline_fetcher
    while True:
        try:
            if kline_fetcher is not None:
                latest_second_kline = kline_fetcher.get_second_kline()
                if latest_second_kline is not None:
                    kline_fetcher.update_5min_kline(latest_second_kline)
            else:
                print("⚠️ [UpdateLoop] kline_fetcher 未初始化，等待 WebSocket 连接...")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ [UpdateLoop] 更新 K 线异常: {e}")
            traceback.print_exc()

def trade_loop():
    """ 每 0.3 秒执行一次交易逻辑 """
    while True:
        try:
            execute_trade()
            time.sleep(0.3)
        except Exception as e:
            print(f"⚠️ [TradeLoop] 交易执行异常: {e}")
            traceback.print_exc()

def monitor_threads():
    """ 监视所有线程，防止 WebSocket 线程意外退出 """
    while True:
        time.sleep(5)
        active_threads = threading.enumerate()
        active_thread_names = [t.name for t in active_threads]
        print(f"🛠️ 活跃线程数: {len(active_threads)}, 线程列表: {active_thread_names}")

        # 检查 WebSocket 线程是否存活，如果崩溃则重启
        if "WebSocketThread" not in active_thread_names:
            print("⚠️ [WebSocket] 线程崩溃，正在重启...")
            ws_thread = threading.Thread(target=start_websocket, name="WebSocketThread", daemon=True)
            ws_thread.start()
            threads["WebSocket"] = ws_thread

def main():
    global kline_fetcher

    # 预热阶段：加载历史数据到 buffer.history（21 根 5 分钟 K 线）
    initialize_buffer_with_historical_data()

    # 启动 WebSocket 线程
    kline_fetcher = OKXKlineFetcher()  # 先初始化全局变量
    ws_thread = threading.Thread(target=start_websocket, name="WebSocketThread", daemon=True)
    ws_thread.start()
    threads["WebSocket"] = ws_thread

    # 启动 K 线更新线程
    update_thread = threading.Thread(target=update_loop, name="UpdateLoopThread", daemon=True)
    update_thread.start()
    threads["UpdateLoop"] = update_thread

    # 启动交易线程
    trade_thread = threading.Thread(target=trade_loop, name="TradeLoopThread", daemon=True)
    trade_thread.start()
    threads["TradeLoop"] = trade_thread

    # 启动线程监控
    monitor_thread = threading.Thread(target=monitor_threads, name="MonitorThread", daemon=True)
    monitor_thread.start()
    threads["Monitor"] = monitor_thread

    # 主循环
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("⏹️ 收到退出信号，正在退出...")
        for name, t in threads.items():
            print(f"⏳ 等待线程 {name} 结束...")
            t.join(timeout=1)
        print("✅ 程序已退出。")

if __name__ == "__main__":
    main()
