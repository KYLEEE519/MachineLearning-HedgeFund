# main.py

# main.py 最顶部添加以下几行
import sys
import os

# 添加项目根目录到sys.path，确保可以import waibu 等模块
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import gradio as gr
from backtest_ui import create_backtest_ui
from strategy_editor_ui import create_strategy_editor_ui
from llm_strategy_generator_ui import create_llm_strategy_generator_ui
with gr.Blocks(title="策略平台") as app:
    with gr.Tabs():
        with gr.Tab("策略回测器"):
            create_backtest_ui()
        with gr.Tab("代码执行器"):
            create_strategy_editor_ui()
        with gr.Tab("大模型生成器"):
            create_llm_strategy_generator_ui()

if __name__ == "__main__":
    app.launch()
