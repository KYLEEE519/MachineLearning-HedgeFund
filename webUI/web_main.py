import gradio as gr
from web_data import build_data_process_ui
from web_model import build_model_train_ui

with gr.Blocks() as demo:
    build_data_process_ui()
    build_model_train_ui()

demo.launch()