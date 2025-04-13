# code_executor_ui.py
# strategy_editor_ui.py
import gradio as gr
import ast
import os

STRATEGY_DIR = "Strategies"

def is_valid_strategy_code(code: str):
    try:
        tree = ast.parse(code)
        class_nodes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
        if not class_nodes:
            return False, "❌ 未定义类"

        for cls in class_nodes:
            method_names = [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
            if "__init__" not in method_names:
                return False, f"❌ 类 {cls.name} 缺少 __init__ 方法"
            if "generate_signal" not in method_names:
                return False, f"❌ 类 {cls.name} 缺少 generate_signal 方法"
        return True, f"✅ 检测通过，类名：{class_nodes[0].name}"

    except Exception as e:
        return False, f"❌ 检测失败：{str(e)}"

def save_strategy_file(code: str, filename: str):
    if not filename.endswith(".py"):
        filename += ".py"
    filepath = os.path.join(STRATEGY_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    return f"✅ 策略已保存到 {filepath}"

def create_strategy_editor_ui():
    with gr.Blocks(title="策略代码编辑器") as editor_ui:
        gr.Markdown("## 🧠 策略代码编辑器\n编写自定义策略类（必须包含 `__init__` 和 `generate_signal` 方法）")

        code_editor = gr.Code(language="python", lines=25, label="策略代码")
        filename_input = gr.Textbox(label="保存的策略文件名（不带后缀）")
        check_btn = gr.Button("🧪 检查是否合规")
        save_btn = gr.Button("💾 保存策略文件", visible=False)

        check_output = gr.Textbox(label="合规性检查结果")
        save_output = gr.Textbox(label="保存状态")

        def check_and_show_save_button(code):
            is_valid, msg = is_valid_strategy_code(code)
            return msg, gr.update(visible=is_valid)

        def save_code(code, filename):
            return save_strategy_file(code, filename)

        check_btn.click(fn=check_and_show_save_button, inputs=[code_editor], outputs=[check_output, save_btn])
        save_btn.click(fn=save_code, inputs=[code_editor, filename_input], outputs=save_output)

    return editor_ui