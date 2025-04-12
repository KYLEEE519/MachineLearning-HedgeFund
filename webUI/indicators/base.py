indicator_registry = {}

def register_indicator(name):
    def decorator(func):
        indicator_registry[name] = func
        return func
    return decorator

# 每个指标的参数说明配置
indicator_params = {
    "RSI": [
        {"name": "window", "type": "int", "desc": "窗口长度，建议取5~20"},
    ],
    "MACD": [
        {"name": "window_fast", "type": "int", "desc": "快速线长度，建议12"},
        {"name": "window_slow", "type": "int", "desc": "慢速线长度，建议26"},
        {"name": "window_sign", "type": "int", "desc": "信号线长度，建议9"},
    ],
    "BOLL": [
        {"name": "window", "type": "int", "desc": "周期长度，建议20"},
        {"name": "std", "type": "float", "desc": "标准差倍数，建议2"},
    ],
    "EMA": [
        {"name": "window", "type": "int", "desc": "平滑移动平均的窗口长度，建议5~50"},
    ],
    "SMA": [
        {"name": "window", "type": "int", "desc": "简单移动平均的窗口长度，建议5~50"},
    ],
    "ATR": [
        {"name": "window", "type": "int", "desc": "平均真实波幅的窗口长度，建议14"},
    ],
    "CCI": [
        {"name": "window", "type": "int", "desc": "顺势指标周期长度，建议14"},
    ],
    "Stoch": [
        {"name": "window", "type": "int", "desc": "随机指标周期长度，建议14"},
    ],
    "WILLR": [
        {"name": "window", "type": "int", "desc": "威廉指标周期长度，建议14"},
    ],
    "ROC": [
        {"name": "window", "type": "int", "desc": "变动率指标周期长度，建议5~20"},
    ],
}
