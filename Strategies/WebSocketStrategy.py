import pandas as pd
from collections import deque

class WebSocketStrategy:
    def __init__(self, df, params=None):
        """
        使用 WebSocket 交易逻辑，在历史数据上回测
        """
        # 默认参数
        default_params = {
            "volatility_window": 30,  # 计算标准差的窗口
            "z_threshold": 1.5,       # Z-score 触发开仓的阈值
        }
        
        # 合并参数
        self.params = default_params if params is None else {**default_params, **params}
        
        # 复制数据
        self.df = df.copy()
        
        # 计算信号
        self.calculate_signals()
    
    def calculate_signals(self):
        """在历史数据上模拟 WebSocket 策略逻辑"""
        p = self.params
        
        # 存储最近 30 根 K 线的收盘价
        price_buffer = deque(maxlen=p["volatility_window"])
        
        # 初始化 open_signal
        self.df["open_signal"] = 0
        self.df["close_signal"] = 0
        
        position_open = False  # 持仓状态
        entry_price = 0  # 开仓价格
        partial_taken = False  # 是否部分止盈
        partial_target_price = None  # 部分止盈目标价位
        peak_profit_price = None  # 最高浮盈价
        
        for i in range(len(self.df)):
            price = self.df.loc[i, "close"]
            price_buffer.append(price)
            
            if len(price_buffer) >= p["volatility_window"]:
                # 计算均值和标准差
                mean_30 = sum(price_buffer) / len(price_buffer)
                std_30 = (sum((p - mean_30) ** 2 for p in price_buffer) / len(price_buffer)) ** 0.5
                z_score = (price - mean_30) / std_30 if std_30 != 0 else 0
                
                # === 开仓逻辑 ===
                if not position_open and z_score > p["z_threshold"]:
                    self.df.loc[i, "open_signal"] = -1  # 做空信号
                    position_open = True
                    entry_price = price
                    partial_taken = False
                    partial_target_price = entry_price - 0.5 * std_30 if std_30 > 0 else entry_price
                    peak_profit_price = None
                
                # === 止盈 / 追踪止盈 ===
                if position_open:
                    if not partial_taken and partial_target_price and price <= partial_target_price:
                        partial_taken = True
                        peak_profit_price = price
                    
                    if partial_taken and peak_profit_price and price >= peak_profit_price + 0.5 * std_30:
                        self.df.loc[i, "close_signal"] = 1  # 平仓信号
                        position_open = False

    def get_strategy_df(self):
        """返回带有策略信号的 DataFrame"""
        return self.df[["timestamp", "open", "high", "low", "close", "open_signal", "close_signal"]]
