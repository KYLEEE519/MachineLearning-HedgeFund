import gradio as gr
import pandas as pd
from okx_fetch_data import fetch_kline_df
from indicators import indicator_registry, indicator_params

df_cache = None  # 缓存数据
current_param_inputs = []  # 存储当前参数输入框组件

# 展示数据（保持不变）
def show_data(days, bar, instId):
    global df_cache
    df_cache = fetch_kline_df(days=days, bar=bar, instId=instId)
    if df_cache.empty:
        return "未获取到数据，请检查参数！", ""
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# 获取对应输入框（保持不变）
def get_params_ui(indicator_name):
    params = indicator_params.get(indicator_name, [])
    inputs = []
    for param in params:
        inputs.append(gr.Textbox(label=f"{param['name']} ({param['desc']})"))
    return inputs

# 更新参数输入框逻辑（已修改）
def update_param_inputs(indicator_name):
    global current_param_inputs
    if indicator_name not in indicator_registry:
        current_param_inputs = []
        return gr.Column([])
    
    current_param_inputs = get_params_ui(indicator_name)
    return gr.Column(current_param_inputs)

# 添加指标逻辑（已修改参数收集方式）
def add_indicator(indicator_name, column, new_col_name, *param_values):
    global df_cache
    if df_cache is None:
        return "请先获取数据！", ""

    if indicator_name not in indicator_registry:
        return "❌ 未找到该指标，请检查输入是否正确！", ""

    func = indicator_registry[indicator_name]
    param_info = indicator_params[indicator_name]

    kwargs = {"column": column}
    for i, param in enumerate(param_info):
        value = param_values[i]
        if param["type"] == "int":
            kwargs[param["name"]] = int(value) if value else 0
        elif param["type"] == "float":
            kwargs[param["name"]] = float(value) if value else 0.0

    df_cache = func(df_cache, **kwargs)

    if new_col_name:
        df_cache.rename(columns={df_cache.columns[-1]: new_col_name}, inplace=True)

    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

with gr.Blocks() as demo:
    gr.Markdown("# XGBoost 可视化训练工具（最新官方规范版）")

    with gr.Row():
        days = gr.Number(label="获取最近几天数据（days）", info="例如7表示最近7天")
        bar = gr.Textbox(label="K线粒度（bar）", info="例如1m、5m、1H、4H")
        instId = gr.Textbox(label="交易对（instId）", info="例如BTC-USDT")

    data_info = gr.Markdown()
    all_columns = gr.Markdown(label="全部列名")

    load_button = gr.Button("获取并展示数据")
    load_button.click(fn=show_data, inputs=[days, bar, instId], outputs=[data_info, all_columns])

    gr.Markdown("## 选择指标并生成参数输入框")
    indicator_name = gr.Dropdown(choices=list(indicator_registry.keys()), label="选择指标")
    column = gr.Textbox(label="作用列")

    confirm_param_button = gr.Button("确认生成参数输入框")
    param_inputs_area = gr.Column()  # 参数输入框容器
    confirm_param_button.click(fn=update_param_inputs, inputs=[indicator_name], outputs=param_inputs_area)

    new_col_name = gr.Textbox(label="新列名（可选）")

    add_indicator_button = gr.Button("生成指标")
    # 动态收集参数输入框的值（关键修改）
    add_indicator_button.click(
        fn=add_indicator,
        inputs=[indicator_name, column, new_col_name] + current_param_inputs,
        outputs=[data_info, all_columns]
    )

demo.launch()
