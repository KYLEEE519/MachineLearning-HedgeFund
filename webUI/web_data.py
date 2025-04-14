import gradio as gr
import pandas as pd
import json
from okx_fetch_data import fetch_kline_df
from indicators import indicator_registry, indicator_params
import os
from datetime import datetime
import gradio as gr
import pandas as pd
# import xgboost as xgb
# import matplotlib.pyplot as plt
import os
# import pickle
# import numpy as np
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import accuracy_score, mean_squared_error
from okx_fetch_data import fetch_kline_df
import traceback
import ta

df_cache = None  # 全局数据缓存

# =====================================
# 1. 数据加载与展示
# =====================================
def show_data(days, bar, instId):
    global df_cache
    df_cache = fetch_kline_df(days=days, bar=bar, instId=instId)
    if df_cache.empty:
        return "未获取到数据，请检查参数！", ""
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 2. 单指标生成 —— 生成 JSON 参数及参数说明
# =====================================
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

# =====================================
# 3. 单指标生成 —— 解析 JSON 参数并生成指标
# =====================================
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

# =====================================
# 4. 批量生成特征 —— 通过 JSON 配置一次性生成多个指标特征
# =====================================
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

def run_user_indicator_code(user_code_str):
    global df_cache
    if df_cache is None:
        return "❌ 请先加载数据再运行指标函数。", "", ""
    
    base_cols = ["timestamp", "open", "high", "low", "close", "vol"]
    df_base = df_cache[[col for col in df_cache.columns if col in base_cols]].copy()

    local_registry = {}
    def register_indicator(name):
        def decorator(func):
            local_registry[name] = func
            return func
        return decorator

    exec_globals = {
        "register_indicator": register_indicator,
        "ta": ta,
        "pd": pd,
    }

    try:
        exec(user_code_str, exec_globals)
        if not local_registry:
            return "⚠️ 未找到通过 `@register_indicator(...)` 定义的函数。", "", ""
        
        new_cols_added = []
        for name, func in local_registry.items():
            result_df = func(df_base.copy())
            if result_df is None or not isinstance(result_df, pd.DataFrame):
                return f"⚠️ 指标 `{name}` 未返回有效 DataFrame。", "", ""
            new_cols = [col for col in result_df.columns if col not in df_base.columns]
            if not new_cols:
                return f"⚠️ 指标 `{name}` 未生成任何新列。", "", ""
            df_cache = pd.merge(df_cache, result_df[["timestamp"] + new_cols], on="timestamp", how="left")
            new_cols_added.extend(new_cols)

        return "✅ 自定义指标添加成功！", df_cache.tail().to_markdown(), ", ".join(df_cache.columns)
    
    except Exception:
        return f"❌ 错误发生:\n```\n{traceback.format_exc()}\n```", "", ""
# =====================================
# 5. 生成 Target 列
# =====================================
def generate_target(target_type):
    global df_cache
    if df_cache is None:
        return "请先获取数据！", ""
    if target_type == "涨跌（1为涨，0为跌）":
        df_cache['target'] = (df_cache['close'].shift(-1) > df_cache['close']).astype(float)  # 保留 NaN
    elif target_type == "涨跌幅":
        df_cache['target'] = df_cache['close'].shift(-1) / df_cache['close'] - 1
    else:
        return "未知的 target 类型", ""
    # 最后一行不需要预测
    df_cache.loc[df_cache.index[-1], 'target'] = None
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 6. 数据清理
# =====================================
def clean_data(clean_type):
    global df_cache
    if df_cache is None:
        return "请先获取数据！", ""
    # 替换 inf 和 -inf 为 NaN
    df_cache.replace([float('inf'), float('-inf')], pd.NA, inplace=True)
    # 强制转换（非时间列）为数字
    for col in df_cache.columns:
        if col != "timestamp":
            df_cache[col] = pd.to_numeric(df_cache[col], errors='coerce')
    original_rows = df_cache.shape[0]
    # 删除全为 NaN 的列
    na_cols = df_cache.columns[df_cache.isna().all()].tolist()
    df_cache.drop(columns=na_cols, inplace=True)
    report = f"已删除全为 NaN 的列: {na_cols}\n"
    if clean_type == "中位数填充":
        df_cache.fillna(df_cache.median(), inplace=True)
        report += "已用列的中位数填充 NaN\n"
    elif clean_type == "均值填充":
        df_cache.fillna(df_cache.mean(), inplace=True)
        report += "已用列的均值填充 NaN\n"
    elif clean_type == "删除含NaN的行":
        df_cache.dropna(inplace=True)
        df_cache.reset_index(drop=True, inplace=True)
        report += "已删除包含 NaN 的行\n"
    else:
        report += "未知的清理类型\n"
    new_rows = df_cache.shape[0]
    report += f"\n数据清理前行数: {original_rows} 行，清理后行数: {new_rows} 行"
    return report + "\n\n" + df_cache.tail().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 7. 保存数据
# =====================================
def save_data(instId):
    global df_cache
    if df_cache is None:
        return "请先获取数据！"
    
    # 确保目录存在
    save_dir = "./data"
    os.makedirs(save_dir, exist_ok=True)

    # 文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{instId}_{timestamp}.csv"
    save_path = os.path.join(save_dir, filename)

    # 保存
    df_cache.to_csv(save_path, index=False)

    # 返回绝对路径
    abs_path = os.path.abspath(save_path)

    return f"数据已保存至: {abs_path}"

def build_data_process_ui():
    with gr.Tab("数据处理与特征工程"):
        gr.Markdown("# XGBoost 可视化训练工具（完整功能版）")
        
        # ----- 数据获取 -----
        with gr.Row():
            days = gr.Number(label="获取最近几天数据（days）", info="例如7表示最近7天")
            bar = gr.Textbox(label="K线粒度（bar）", info="例如1m、5m、1H、4H")
            instId = gr.Textbox(label="交易对（instId）", info="例如BTC-USDT")
        data_info = gr.Markdown()
        all_columns = gr.Markdown(label="全部列名")
        load_button = gr.Button("获取并展示数据")
        load_button.click(fn=show_data, inputs=[days, bar, instId], outputs=[data_info, all_columns])
        
        # ----- 单指标生成 -----
        with gr.Tab("单指标生成"):
            gr.Markdown("## 单指标生成")
            indicator_name = gr.Dropdown(choices=list(indicator_registry.keys()), label="选择指标")
            column = gr.Textbox(label="作用列", value="close")
            confirm_param_button = gr.Button("确认生成参数输入框")
            json_params = gr.Textbox(label="请在此输入指标参数（JSON 格式）", visible=False, lines=10)
            # Markdown 组件，用于显示参数说明（instruction）
            param_instructions = gr.Markdown(label="参数说明")
            confirm_param_button.click(
                fn=update_param_inputs_json,
                inputs=[indicator_name],
                outputs=[json_params, param_instructions]
            )
            new_col_name = gr.Textbox(label="新列名（可选）")
            add_indicator_button = gr.Button("生成指标")
            add_indicator_button.click(
                fn=add_indicator_json,
                inputs=[indicator_name, column, new_col_name, json_params],
                outputs=[data_info, all_columns]
            )
        
        # ----- 批量生成特征 -----
        with gr.Tab("批量生成指标"):
            gr.Markdown("## 编辑 JSON 自动批量生成特征")
            json_editor = gr.Code(
                label="指标配置 JSON", language="json",
                value='''{
            "RSI": {"enable": true, "params": {"window": 14}},
            "MACD": {"enable": true, "params": {"window_fast": 12, "window_slow": 26, "window_sign": 9}},
            "BOLL": {"enable": false, "params": {"window": 20, "std": 2.0}},
            "EMA": {"enable": false, "params": {"window": 14}},
            "SMA": {"enable": false, "params": {"window": 14}},
            "ATR": {"enable": false, "params": {"window": 14}},
            "CCI": {"enable": false, "params": {"window": 14}},
            "Stoch": {"enable": false, "params": {"window": 14}},
            "WILLR": {"enable": false, "params": {"window": 14}},
            "ROC": {"enable": false, "params": {"window": 14}}
            }'''
            )
            new_data_info = gr.Markdown()
            new_all_columns = gr.Markdown(label="最新全部列名")
            generate_button = gr.Button("批量生成特征")
            generate_button.click(
                fn=generate_features_by_json,
                inputs=[json_editor],
                outputs=[new_data_info, new_all_columns]
            )
        with gr.Tab("自定义指标"):
            gr.Markdown("## 自定义指标生成\n请使用 `@register_indicator(\"名称\")` 装饰器定义函数，返回新的 DataFrame。")

            example_code = '''# ✅ 示例模板：
@register_indicator("Stoch")
def calculate_stoch(df, column='close', window=14):
    stoch = ta.momentum.StochasticOscillator(
        high=df['high'], low=df['low'], close=df[column], window=window)
    df[f'Stoch_{window}'] = stoch.stoch()
    return df'''

            user_code = gr.Code(label="自定义指标代码", language="python", value=example_code)
            run_button = gr.Button("运行自定义指标")

            error_display = gr.Markdown()
            df_tail_preview = gr.Markdown()
            df_column_list = gr.Markdown(label="全部列名")

            run_button.click(
                fn=run_user_indicator_code,
                inputs=[user_code],
                outputs=[error_display, df_tail_preview, df_column_list]
            )
        with gr.Tab("自定义指标选择"):
            gr.Markdown("## 选择客户自定义指标并生成")
        # ----- 生成 Target 列 -----
        gr.Markdown("## 生成 Target 列")
        target_type = gr.Dropdown(choices=["涨跌（1为涨，0为跌）", "涨跌幅"], label="选择 Target 类型")
        target_data_info = gr.Markdown()
        target_all_columns = gr.Markdown(label="最新全部列名")
        generate_target_button = gr.Button("生成 Target 列")
        generate_target_button.click(
            fn=generate_target,
            inputs=[target_type],
            outputs=[target_data_info, target_all_columns]
        )
        
        # ----- 数据清理 -----
        gr.Markdown("## 数据清理")
        clean_type = gr.Dropdown(choices=["中位数填充", "均值填充", "删除含NaN的行"], label="选择数据清理方式")
        clean_info = gr.Markdown()
        clean_cols = gr.Markdown(label="最新全部列名")
        clean_button = gr.Button("执行数据清理")
        clean_button.click(
            fn=clean_data,
            inputs=[clean_type],
            outputs=[clean_info, clean_cols]
        )
        gr.Markdown("## 数据保存")

        save_path_info = gr.Markdown()
        save_button = gr.Button("保存数据为 CSV")

        save_button.click(
            fn=save_data,
            inputs=[instId],
            outputs=[save_path_info]
        )