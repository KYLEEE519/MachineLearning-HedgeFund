import json
from indicators import indicator_registry, indicator_params
from .data_loader import df_cache
import gradio as gr

def update_param_inputs_json(indicator_name):
    """
    根据所选指标，从 indicator_params 中取出该指标所需参数，
    生成：
      1. 默认的 JSON 字符串（例如 {"window": ""}）
      2. 参数说明的 Markdown 文本（例如：- **window** (`int`): 窗口长度，建议取5~20）
    """
    params = indicator_params.get(indicator_name, [])
    default_dict = {}
    for p in params:
        default_dict[p["name"]] = ""
    json_str = json.dumps(default_dict, indent=4)
    
    # 生成说明文档，每个参数一行
    doc_lines = []
    for p in params:
        doc_lines.append(f"- **{p['name']}** (`{p['type']}`): {p['desc']}")
    doc_text = "\n".join(doc_lines)
    
    return gr.update(value=json_str, visible=True), doc_text

def add_indicator_json(indicator_name, column, new_col_name, param_json_str):
    global df_cache
    if df_cache is None:
        return "请先获取数据！", ""
    if indicator_name not in indicator_registry:
        return "❌ 未找到该指标，请检查输入是否正确！", ""
    try:
        param_json = json.loads(param_json_str)
    except Exception as e:
        return f"JSON 格式错误: {e}", ""
    
    func = indicator_registry[indicator_name]
    param_info = indicator_params[indicator_name]
    kwargs = {"column": column}
    for p in param_info:
        name = p["name"]
        value = param_json.get(name, "")
        if p["type"] == "int":
            kwargs[name] = int(value) if value else 0
        elif p["type"] == "float":
            kwargs[name] = float(value) if value else 0.0

    df_cache = func(df_cache, **kwargs)
    if new_col_name:
        df_cache.rename(columns={df_cache.columns[-1]: new_col_name}, inplace=True)
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

def generate_features_by_json(json_str):
    global df_cache
    if df_cache is None:
        return "请先获取数据！", ""
    try:
        feature_config = json.loads(json_str)
    except Exception as e:
        return f"JSON 格式错误：{e}", ""
    
    for indicator_name, config in feature_config.items():
        if not config.get("enable", False):
            continue
        if indicator_name not in indicator_registry:
            continue
        func = indicator_registry[indicator_name]
        param_dict = config.get("params", {})
        kwargs = {"column": "close"}  # 默认作用于 close 列
        kwargs.update(param_dict)
        
        new_col_name = indicator_name + "_" + "_".join(str(v) for v in param_dict.values())
        if new_col_name in df_cache.columns:
            continue
        df_cache = func(df_cache, **kwargs)
        df_cache.rename(columns={df_cache.columns[-1]: new_col_name}, inplace=True)
    
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

default_feature_config = {
    "RSI": {"enable": True, "params": {"window": 14}},
    "MACD": {"enable": True, "params": {"window_fast": 12, "window_slow": 26, "window_sign": 9}},
    "BOLL": {"enable": False, "params": {"window": 20, "std": 2.0}},
    "EMA": {"enable": False, "params": {"window": 14}},
    "SMA": {"enable": False, "params": {"window": 14}},
    "ATR": {"enable": False, "params": {"window": 14}},
    "CCI": {"enable": False, "params": {"window": 14}},
    "Stoch": {"enable": False, "params": {"window": 14}},
    "WILLR": {"enable": False, "params": {"window": 14}},
    "ROC": {"enable": False, "params": {"window": 14}},
}
