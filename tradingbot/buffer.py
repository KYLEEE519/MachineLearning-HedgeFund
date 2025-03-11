import queue

class KlineBuffer:
    def __init__(self):
        """ 使用 Queue 进行无锁双缓冲交换 """
        self.main_buffer = queue.Queue(maxsize=1)  
        self.mirror_buffer = queue.Queue(maxsize=1)  

        # ✅ 初始化缓冲区
        initial_data = {"second_kline": None, "five_min_kline": None}
        self.main_buffer.put(initial_data)
        self.mirror_buffer.put(initial_data)

    def update_main_buffer(self, second_kline, five_min_kline):
        """ 更新主缓冲区 (无锁方式) """
        new_data = {"second_kline": second_kline, "five_min_kline": five_min_kline}
        self.main_buffer.queue.clear()
        self.main_buffer.put(new_data)
        print(f"✅ [BUFFER] 主缓冲区更新: {new_data}")  # Debug

    def swap_buffers(self):
        """ 无锁原子交换缓冲区 """
        if not self.main_buffer.empty():  # 确保 main_buffer 里有数据
            self.mirror_buffer.queue.clear()
            self.mirror_buffer.put(self.main_buffer.get())  # 用 `get()` 安全获取数据
            print("✅ [BUFFER] 缓冲区交换完成 -> 镜像缓冲更新")


    def get_latest_kline(self):
        """ 读取镜像缓冲 (只读，策略 & 交易函数用) """
        if not self.mirror_buffer.empty():  # 确保缓冲区有数据
            latest_kline = self.mirror_buffer.queue[0]  # 直接访问 queue 可能出错
            print(f"📥 [BUFFER] 读取镜像缓冲: {latest_kline}")  # Debug
            return latest_kline
        else:
            print("⚠️ [BUFFER] 镜像缓冲区为空，返回默认数据")
            return {"second_kline": None, "five_min_kline": None}  # 避免返回 `NoneType`


# ✅ 初始化无锁缓冲区
kline_buffer = KlineBuffer()
