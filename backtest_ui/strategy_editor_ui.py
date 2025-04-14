# code_executor_ui.py
# strategy_editor_ui.py
import gradio as gr
import os

STRATEGY_DIR = "Strategies"
import ast
import tempfile
import importlib.util
import uuid
import traceback
import pandas as pd
from pathlib import Path
import json
def is_valid_strategy_code(code: str):
    import ast, tempfile, importlib.util, uuid, traceback, pandas as pd, inspect

    # ---------- 静态分析 ----------
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

        class_name = class_nodes[0].name

    except Exception as e:
        return False, f"❌ 静态检测失败：{str(e)}"

    # ---------- 动态执行并测试 ----------
    try:
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".py")
        temp_path.write(code.encode())
        temp_path.close()

        module_name = f"user_strategy_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, temp_path.name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        StrategyClass = getattr(module, class_name)

        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=50, freq="5min"),
            "open": [100] * 50,
            "high": [101] * 50,
            "low": [99] * 50,
            "close": [100] * 50,
            "vol":[100] *50
        })

        init_args = inspect.signature(StrategyClass.__init__).parameters
        init_kwargs = {k: 10 for k in init_args if k not in ['self', 'df']}
        init_kwargs['df'] = df
        strategy = StrategyClass(**init_kwargs)

        result = strategy.generate_signal(index=30, current_balance=10000, leverage=1.0, current_position=0)

        if not isinstance(result, tuple) or len(result) != 6:
            return False, f"❌ 返回值必须是长度为6的tuple，而不是：{result}"

        direction, tp, sl, size, exit_signal, exit_ratio = result

        if direction not in [-1, 0, 1]:
            return False, f"❌ direction 取值必须是 -1, 0, 1：当前是 {direction}"
        if not isinstance(size, (int, float)) or size < 0:
            return False, f"❌ position_size 应该是非负数：当前是 {size}"
        if exit_signal not in [-1, 0, 1]:
            return False, f"❌ exit_signal 应为 -1, 0 或 1：当前是 {exit_signal}"
        if not isinstance(exit_ratio, (int, float)) or not (0 <= exit_ratio <= 1):
            return False, f"❌ exit_ratio 应为 0 到 1 之间的浮点数：当前是 {exit_ratio}"

        return True, f"✅ 检测通过，类名：{class_name}"

    except Exception as e:
        tb = traceback.format_exc()
        return False, f"❌ 动态执行失败：\n{str(e)}\n{tb}"

import inspect
def extract_default_params_from_code(code: str):
    try:
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".py")
        temp_path.write(code.encode())
        temp_path.close()

        module_name = f"user_strategy_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, temp_path.name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class_nodes = [n for n in ast.parse(code).body if isinstance(n, ast.ClassDef)]
        class_name = class_nodes[0].name
        StrategyClass = getattr(module, class_name)

        sig = inspect.signature(StrategyClass.__init__)
        default_params = {}
        for name, param in sig.parameters.items():
            if name in ("self", "df"):
                continue
            default = param.default
            default_params[name] = default if default != inspect.Parameter.empty else 10
        return class_name, default_params

    except Exception as e:
        raise RuntimeError(f"提取参数失败: {e}")
def save_code(code, filename):
    if not filename.endswith(".py"):
        filename += ".py"
    filepath = os.path.join(STRATEGY_DIR, filename)
    
    # 保存文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

    # 更新 strategies.json
    try:
        class_name, default_params = extract_default_params_from_code(code)

        strategy_key = filename.replace(".py", "")
        class_path = f"Strategies.{strategy_key}.{class_name}"

        strategies_path = Path(STRATEGY_DIR) / "strategies.json"
        with open(strategies_path, "r", encoding="utf-8") as f:
            strategies = json.load(f)

        strategies[strategy_key] = {
            "name": class_name,
            "class_path": class_path,
            "use_strategy_exit": default_params.get("tp_rate") is None,  # 自动判断策略类型
            "default_params": default_params
        }

        with open(strategies_path, "w", encoding="utf-8") as f:
            json.dump(strategies, f, indent=2, ensure_ascii=False)

        return f"✅ 策略已保存到 {filepath}，并已更新 strategies.json"

    except Exception as e:
        return f"⚠️ 策略保存成功，但更新 strategies.json 失败：{e}"

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


        check_btn.click(fn=check_and_show_save_button, inputs=[code_editor], outputs=[check_output, save_btn])
        save_btn.click(fn=save_code, inputs=[code_editor, filename_input], outputs=save_output)

    return editor_ui