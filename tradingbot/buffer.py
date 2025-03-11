import queue
import threading

class KlineBuffer:
    def __init__(self):
        """ 使用 Queue 进行无锁双缓冲交换，同时维护历史记录 """
        self.main_buffer = queue.Queue(maxsize=1)
        self.mirror_buffer = queue.Queue(maxsize=1)
        self.history = []  # 用于保存完成的 5 分钟 K 线历史

        # 初始化缓冲区
        initial_data = {"second_kline": None, "five_min_kline": None}
        self.main_buffer.put(initial_data)
        self.mirror_buffer.put(initial_data)
        self.lock = threading.Lock()  # 用于保护 history

    def update_main_buffer(self, second_kline, five_min_kline, finished=False):
        """
        更新主缓冲区 (无锁方式)
        :param finished: 如果 True 表示这是一根完整、结束的 5 分钟 K 线，应当加入历史记录
        """
        new_data = {"second_kline": second_kline, "five_min_kline": five_min_kline}
        self.main_buffer.queue.clear()
        self.main_buffer.put(new_data)
    #    print(f"✅ [BUFFER] 主缓冲区更新: {new_data}")

        if finished and five_min_kline is not None:
            with self.lock:
                self.history.append(five_min_kline)
          #      print(f"✅ [BUFFER] 历史记录追加: {five_min_kline}")

    def swap_buffers(self):
        """ 无锁原子交换缓冲区 """
        if not self.main_buffer.empty():
            self.mirror_buffer.queue.clear()
            # 使用 get() 安全获取数据
            data = self.main_buffer.get()
            self.mirror_buffer.put(data)
        #    print("✅ [BUFFER] 缓冲区交换完成 -> 镜像缓冲更新")

    def get_latest_kline(self):
        """ 读取镜像缓冲 (只读，策略 & 交易函数用) """
        if not self.mirror_buffer.empty():
            latest_kline = self.mirror_buffer.queue[0]
       #     print(f"📥 [BUFFER] 读取镜像缓冲: {latest_kline}")
            return latest_kline
        else:
        #    print("⚠️ [BUFFER] 镜像缓冲区为空，返回默认数据")
            return {"second_kline": None, "five_min_kline": None}

    def get_history(self):
        """ 返回历史记录列表 """
        with self.lock:
            return list(self.history)

# 初始化 buffer
kline_buffer = KlineBuffer()
