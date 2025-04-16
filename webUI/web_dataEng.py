import gradio as gr
import pandas as pd
import json
import os
import traceback
from datetime import datetime
import ta
from okx_fetch_data import fetch_kline_df
from indicators import indicator_registry, indicator_params
from inspect import getsource

# 全局缓存
df_cache = None
custom_indicator_log = {}  # 用于记录用户自定义的指标名及其代码
df_timestamp = None
operation_log = [] 
# =====================================
# 1. 数据加载与展示
# =====================================
def show_data(days, bar, instId):
    global df_cache, df_timestamp, operation_log
    df_cache = fetch_kline_df(days=days, bar=bar, instId=instId)
    if df_cache.empty:
        return "未获取到数据，请检查参数！", ""
    df_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    operation_log = []  # 清空之前日志
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())


# =====================================
# 2. Single Indicator Generation —— 生成 JSON 参数及参数说明
# =====================================
def update_param_inputs_json(indicator_name):
    params = indicator_params.get(indicator_name, [])
    default_dict = {p["name"]: "" for p in params}
    json_str = json.dumps(default_dict, indent=4)
    doc_lines = [f"- **{p['name']}** (`{p['type']}`): {p['desc']}" for p in params]
    return gr.update(value=json_str, visible=True), "\n".join(doc_lines)

# =====================================
# 3. Single Indicator Generation —— 解析 JSON 参数并Generate Indicator
# =====================================
def add_indicator_json(indicator_name, column, param_json_str):
    global df_cache
    if df_cache is None:
        return "Please fetch data first!", ""
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
    operation_log.append({
        "type": "单指标",
        "indicator": indicator_name,
        "params": kwargs,
        "generated_cols": [df_cache.columns[-1]],
        "code": getsource(func)
    })
    # if new_col_name:
    #     df_cache.rename(columns={df_cache.columns[-1]: new_col_name}, inplace=True)
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 4. Generate Features —— 通过 JSON 配置一次性生成多个指标特征
# =====================================
def generate_features_by_json(json_str):
    global df_cache
    if df_cache is None:
        return "Please fetch data first!", ""
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
        kwargs = {"column": "close"}
        kwargs.update(param_dict)

        new_col_name = indicator_name + "_" + "_".join(str(v) for v in param_dict.values())
        if new_col_name in df_cache.columns:
            continue
        df_cache = func(df_cache, **kwargs)
        df_cache.rename(columns={df_cache.columns[-1]: new_col_name}, inplace=True)
        operation_log.append({
            "type": "批量指标",
            "indicator": indicator_name,
            "params": kwargs,
            "generated_cols": [new_col_name],
            "code": getsource(func)
        })
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 5. Custom Indicator执行并记录代码
# =====================================
def run_user_indicator_code(user_code_str):
    global df_cache, custom_indicator_log
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

            # ✅ 重命名新增列，带上注册名
            renamed_cols = {}
            for col in new_cols:
                suffix = col.split("_")[-1] if "_" in col else col
                new_name = f"{name}_{suffix}"
                df_cache[new_name] = result_df[col]
                renamed_cols[col] = new_name
                

            new_cols_added.extend(renamed_cols.values())
            # ✅ 保存代码绑定列名
            for col in renamed_cols.values():
                custom_indicator_log[col] = user_code_str

            # ✅ 每个指标单独记录一条日志
            operation_log.append({
                "type": "Custom Indicator",
                "indicator": name,
                "params": "user-defined",
                "generated_cols": list(renamed_cols.values()),
                "code": user_code_str
            })
        return "✅ Custom Indicator添加成功！", "", ", ".join(df_cache.columns)

    except Exception as e:
        err_msg = traceback.format_exc()
        return f"❌ 错误发生:\n\n```\n{err_msg}\n```", "", ""


# =====================================
# 6. Custom Indicator选择（筛选保留）
# =====================================
def filter_custom_indicators(selected):
    global df_cache, custom_indicator_log
    if df_cache is None:
        return "请先加载数据", ""

    base_cols = ["timestamp", "open", "high", "low", "close", "vol", "target"]
    all_cols = df_cache.columns.tolist()

    # Custom Indicator列
    custom_cols = list(custom_indicator_log.keys())

    # 被选中的Custom Indicator列 + 非自定义列
    keep_cols = base_cols + [col for col in all_cols if col not in custom_cols] + selected

    # 去重 + 保留存在于 df 中的列
    keep_cols = [col for col in list(dict.fromkeys(keep_cols)) if col in df_cache.columns]

    df_cache = df_cache[keep_cols]
    operation_log.append({
        "type": "保留列",
        "keep_custom_cols": selected
    })
    return df_cache.tail().to_markdown(), ", ".join(df_cache.columns)



# 你可以将这个函数接入 gr.CheckboxGroup，用于在 UI 中让用户筛选要保留的Custom Indicator。
# =====================================
# 5. Generate Target Column
# =====================================
def generate_target(target_type):
    global df_cache
    if df_cache is None:
        return "Please fetch data first!", ""
    if target_type == "Up/Down (1 = up, 0 = down)":
        df_cache['target'] = (df_cache['close'].shift(-1) > df_cache['close']).astype(float)
    elif target_type == "Change Rate":
        df_cache['target'] = df_cache['close'].shift(-1) / df_cache['close'] - 1
    else:
        return "Unknown target type", ""
    # 最后一行不需要预测
    df_cache.loc[df_cache.index[-1], 'target'] = None
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 6. Data Cleaning
# =====================================
def clean_data(clean_type):
    global df_cache
    if df_cache is None:
        return "Please fetch data first!", ""
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
    report = f"Deleted columns entirely NaN: {na_cols}\n"
    if clean_type == "Fill with Median":
        df_cache.fillna(df_cache.median(), inplace=True)
        report += "已用列的Fill with Median NaN\n"
    elif clean_type == "Fill with Mean":
        df_cache.fillna(df_cache.mean(), inplace=True)
        report += "已用列的Fill with Mean NaN\n"
    elif clean_type == "Drop Rows with NaN":
        df_cache.dropna(inplace=True)
        df_cache.reset_index(drop=True, inplace=True)
        report += "Deleted rows with NaN\n"
    else:
        report += "Unknown cleaning method\n"
    new_rows = df_cache.shape[0]
    report += f"\nData Cleaning前行数: {original_rows} 行，Row count after cleaning: {new_rows} 行"
    return report + "\n\n" + df_cache.tail().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 7. 保存数据
# =====================================
def save_data(instId):
    global df_cache, df_timestamp, operation_log
    if df_cache is None:
        return "Please fetch data first!"

    save_dir = "./data"
    os.makedirs(save_dir, exist_ok=True)

    # ✅ 使用 show_data 时生成的时间戳，而不是现在的时间
    filename = f"{instId}_{df_timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')}"
    csv_path = os.path.join(save_dir, f"{filename}.csv")
    txt_path = os.path.join(save_dir, f"{filename}.txt")

    df_cache.to_csv(csv_path, index=False)

    with open(txt_path, "w", encoding="utf-8") as f:
        for i, op in enumerate(operation_log, 1):
            f.write(f"--- Step {i} ---\n")
            for k, v in op.items():
                if k == "code":
                    f.write(f"\nUser-defined Code:\n{v}\n")
                else:
                    f.write(f"{k}: {json.dumps(v, ensure_ascii=False, indent=4)}\n")
            f.write("\n")

    return f"Data saved to:\nCSV: {os.path.abspath(csv_path)}\nTXT: {os.path.abspath(txt_path)}"


def build_data_process_ui():
    with gr.Tab("Data Processing & Feature Engineering"):
        gr.Markdown("Visual Training Tool")
        
        # ----- 数据获取 -----
        with gr.Row():
            days = gr.Number(label="Fetch Days of Data", info="例如7表示最近7天")
            bar = gr.Textbox(label="K-line Interval (bar)", info="例如1m、5m、1H、4H")
            instId = gr.Textbox(label="Trading Pair (instId)", info="例如BTC-USDT")
        data_info = gr.Markdown()
        all_columns = gr.Markdown(label="All Columns")
        load_button = gr.Button("Fetch and Display Data")
        load_button.click(fn=show_data, inputs=[days, bar, instId], outputs=[data_info, all_columns])
        
        # ----- Single Indicator Generation -----
        with gr.Tab("Single Indicator Generation"):
            gr.Markdown("## Single Indicator Generation")
            indicator_name = gr.Dropdown(choices=list(indicator_registry.keys()), label="Select Indicator")
            column = gr.Textbox(label="Target Column", value="close")
            confirm_param_button = gr.Button("Generate Parameter Input")
            json_params = gr.Textbox(label="Enter Indicator Parameters (JSON Format)", visible=False, lines=10)
            # Markdown 组件，用于显示参数说明（instruction）
            param_instructions = gr.Markdown(label="Parameter Instructions")
            confirm_param_button.click(
                fn=update_param_inputs_json,
                inputs=[indicator_name],
                outputs=[json_params, param_instructions]
            )
            # new_col_name = gr.Textbox(label="New Column Name (Optional)")
            add_indicator_button = gr.Button("Generate Indicator")
            add_indicator_button.click(
                fn=add_indicator_json,
                inputs=[indicator_name, column, json_params],
                outputs=[data_info, all_columns]
            )
        
        # ----- Generate Features -----
        with gr.Tab("批量Generate Indicator"):
            gr.Markdown("## Auto-generate Features from JSON")
            json_editor = gr.Code(
                label="Indicator Config JSON", language="json",
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
            new_all_columns = gr.Markdown(label="Updated Column List")
            generate_button = gr.Button("Generate Features")
            generate_button.click(
                fn=generate_features_by_json,
                inputs=[json_editor],
                outputs=[new_data_info, new_all_columns]
            )
        with gr.Tab("Custom Indicator"):
            gr.Markdown("## Custom Indicator生成\n请使用 `@register_indicator(\"名称\")` 装饰器定义函数，返回新的 DataFrame。")

            example_code = '''# ✅ Example Template：
@register_indicator("Stoch")
def calculate_stoch(df, column='close', window=14):
    stoch = ta.momentum.StochasticOscillator(
        high=df['high'], low=df['low'], close=df[column], window=window)
    df[f'Stoch_{window}'] = stoch.stoch()
    return df'''

            user_code = gr.Code(label="Custom Indicator Code", language="python", value=example_code)
            run_button = gr.Button("运行Custom Indicator")

            error_display = gr.Markdown()
            df_column_list = gr.Markdown(label="Current Columns")

            run_button.click(
                fn=run_user_indicator_code,
                inputs=[user_code],
                outputs=[error_display, df_column_list]
            )

        with gr.Tab("Custom Indicator选择"):
            gr.Markdown("## 选择保留的Custom Indicator列")
            selectable_cols = gr.CheckboxGroup(choices=[], label="Selectable Custom Columns")
            preview_filtered = gr.Markdown()
            updated_columns = gr.Markdown(label="Updated Columns")

            def update_selectable_cols():
                from web_data import custom_indicator_log
                return gr.update(choices=list(custom_indicator_log.keys()))

            refresh_button = gr.Button("🔄 Refresh Selectable Columns")
            refresh_button.click(fn=update_selectable_cols, inputs=[], outputs=[selectable_cols])

            apply_filter_button = gr.Button("✅ Apply Filter")
            apply_filter_button.click(
                fn=filter_custom_indicators,
                inputs=[selectable_cols],
                outputs=[preview_filtered, updated_columns]
            )

        # ----- Generate Target Column -----
        gr.Markdown("## Generate Target Column")
        target_type = gr.Dropdown(choices=["Up/Down (1 = up, 0 = down)", "Change Rate"], label="Select Target Type")
        target_data_info = gr.Markdown()
        target_all_columns = gr.Markdown(label="Updated Column List")
        generate_target_button = gr.Button("Generate Target Column")
        generate_target_button.click(
            fn=generate_target,
            inputs=[target_type],
            outputs=[target_data_info, target_all_columns]
        )
        
        # ----- Data Cleaning -----
        gr.Markdown("## Data Cleaning")
        clean_type = gr.Dropdown(choices=["Fill with Median", "Fill with Mean", "Drop Rows with NaN"], label="选择Data Cleaning方式")
        clean_info = gr.Markdown()
        clean_cols = gr.Markdown(label="Updated Column List")
        clean_button = gr.Button("执行Data Cleaning")
        clean_button.click(
            fn=clean_data,
            inputs=[clean_type],
            outputs=[clean_info, clean_cols]
        )
        gr.Markdown("## Save Data")

        save_path_info = gr.Markdown()
        save_button = gr.Button("Save Data as CSV")

        save_button.click(
            fn=save_data,
            inputs=[instId],
            outputs=[save_path_info]
        )