import gradio as gr
import pandas as pd
import traceback
import ta

# 主执行函数（绑定按钮）
def run_user_indicator_code(user_code_str, df_raw):
    if df_raw is None:
        return "❌ 请先加载数据再运行指标函数。", "", "", df_raw

    # Step 1: 过滤出最基础的 K 线列
    base_cols = ["timestamp", "open", "high", "low", "close", "vol"]
    df_base = df_raw[[col for col in df_raw.columns if col in base_cols]].copy()

    # 注册用户函数用的 registry
    local_registry = {}

    def register_indicator(name):
        def decorator(func):
            local_registry[name] = func
            return func
        return decorator

    # 安全执行用户代码
    exec_globals = {
        "register_indicator": register_indicator,
        "ta": ta,
        "__builtins__": __builtins__,  # 开放基本内建函数
    }

    try:
        exec(user_code_str, exec_globals)

        if not local_registry:
            return "⚠️ 未找到通过 `@register_indicator(...)` 定义的函数。", "", "", df_raw

        new_cols_added = []
        for name, func in local_registry.items():
            result_df = func(df_base.copy())
            if result_df is None or not isinstance(result_df, pd.DataFrame):
                return f"⚠️ 指标 `{name}` 未返回有效 DataFrame。", "", "", df_raw

            new_cols = [col for col in result_df.columns if col not in df_base.columns]
            if not new_cols:
                return f"⚠️ 指标 `{name}` 未生成任何新列。", "", "", df_raw

            # 合并新列到原始 df（按 timestamp 对齐）
            df_raw = pd.merge(df_raw, result_df[["timestamp"] + new_cols], on="timestamp", how="left")
            new_cols_added.extend(new_cols)

        return "✅ 自定义指标添加成功！", df_raw.tail().to_markdown(), ", ".join(df_raw.columns), df_raw

    except Exception:
        return f"""❌ 错误发生:\n```\n{traceback.format_exc()}\n```""", "", "", df_raw


# 构建 UI Tab
def build_custom_indicator_tab():
    with gr.Tab("自定义指标"):
        gr.Markdown("## 自定义指标生成")
        gr.Markdown(
            "请定义你的指标函数，必须使用 `@register_indicator(\"名字\")` 装饰器。\n"
            "函数必须返回包含新列的 DataFrame，新列将自动合并进主数据。\n"
            "你可以一次定义多个函数，每个函数都需用 `@register_indicator`。"
        )

        example_code = '''# ✅ 示例模板（你可以一次写多个函数）
@register_indicator("Stoch")
def calculate_stoch(df, column='close', window=14):
    stoch = ta.momentum.StochasticOscillator(
        high=df['high'],
        low=df['low'],
        close=df[column],
        window=window
    )
    df[f'Stoch_{window}'] = stoch.stoch()
    return df
'''

        user_code = gr.Code(label="自定义指标代码", value=example_code, language="python", lines=20)
        run_button = gr.Button("运行自定义指标")

        error_display = gr.Markdown()
        df_tail_preview = gr.Markdown()
        df_column_list = gr.Markdown(label="全部列名")

        df_state = gr.State()

        run_button.click(
            fn=run_user_indicator_code,
            inputs=[user_code, df_state],
            outputs=[error_display, df_tail_preview, df_column_list, df_state]
        )

        return df_state  # 用于上层主程序控制状态共享
