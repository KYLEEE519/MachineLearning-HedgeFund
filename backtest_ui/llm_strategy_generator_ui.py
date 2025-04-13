import gradio as gr
from openai import OpenAI
import os

# 请确保设置了环境变量 OPENAI_API_KEY，或者直接写在这里（⚠️不推荐硬编码）
client = OpenAI(api_key=os.getenv("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"))
# -------- 第一阶段：翻译用户自然语言为结构化描述 --------
def translate_user_intent(user_text):
    system_prompt = (
        "你是一个策略设计专家，请将用户描述的自然语言交易策略，翻译成结构化、明确、具备参数信息的格式，请务必回答中文"
        "该格式用于后续生成 Python 策略类。语言应简洁明了，描述应包含买入/卖出逻辑、涉及的指标、参数。"
        "请只输出策略相关信息，请不要输出任何其他的与用户互动的信息，这很重要。"
        "如果用户说的不是策略相关的东西，那么我们就回答“这不是一个策略。”"
        "这是用户的问题："
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # 可替换为gpt-3.5-turbo
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ 翻译失败：{str(e)}"
# -------- 第二阶段：结构化描述转策略代码 --------
def generate_strategy_code(description_text):
    system_prompt = (
        "你是一个专业的金融量化工程师，目标是根据用户的自然语言策略意图，生成一份符合严格规范的 Python 策略类代码。该策略类将在一个量化回测系统中运行，必须满足以下要求：\n\n"

        "【类结构要求】\n"
        "- 必须定义一个类，类名自定义；\n"
        "- 类必须包含两个方法：\n"
        "  1. __init__(self, df: pd.DataFrame, ...): 初始化方法，接收一个 DataFrame 和其他参数；\n"
        "  2. generate_signal(self, index: int, current_balance: float, leverage: float = 1.0, current_position: int = 0): 信号生成方法。\n\n"

        "【generate_signal 的返回格式】\n"
        "必须返回一个 长度为 5 的元组 (direction, take_profit, stop_loss, position_size, exit_signal)：\n"
        "- direction: int 类型，只能是 -1, 0, 1；\n"
        "- take_profit: 止盈价格，float 或 None；\n"
        "- stop_loss: 止损价格，float 或 None；\n"
        "- position_size: float 类型，非负数；\n"
        "- exit_signal: bool 类型。\n\n"

        "【策略类型规范】\n"
        "你生成的策略必须属于以下两种类型之一：\n"
        "1. 设置止盈止损策略：tp 和 sl 均为非 None，exit_signal 必须是 False；\n"
        "2. 不设置止盈止损策略：tp 和 sl 必须为 None，exit_signal 可为 True 或 False。\n\n"

        "【上下文说明】\n"
        "- self.df 是 pd.DataFrame，包含至少 'timestamp', 'open', 'high', 'low', 'close' 五列；\n"
        "- 所有技术指标只能使用 pandas 完成；不能使用 ta-lib 或其他库；\n"
        "- __init__ 方法中需计算策略所需字段，并设置 self.warmup_period（如 ma_length 等）；\n"
        "- 所有变量命名清晰、函数结构合理。\n\n"

        "【输入示例】：用户输入：'我想要一个RSI策略，RSI小于30做多，大于70做空，开仓比例为0.5，不设置止盈止损'\n\n"

        "【输出格式】：你输出的内容应仅为完整的 Python 策略类定义代码，不包含解释文字，不加```python标记。\n"
        "必须结构清晰、无语法错误、可以直接写入 .py 文件运行。\n\n"
    "模板一（无止盈止损策略）\n"
    "import pandas as pd"
    "class Ma20Strategy:"
    "    def __init__(self, df: pd.DataFrame, ma_length: int = 20, position_ratio: float = 0.5):"
    "        self.df = df.copy()"
    "        self.ma_length = ma_length"
    "        self.warmup_period = ma_length"
    "        self.position_ratio = position_ratio"
    "        self.df['ma'] = self.df['close'].rolling(self.ma_length).mean()"
    "    def generate_signal(self, index: int, current_balance: float, leverage: float = 1.0, current_position: int = 0):"
    "        if index < self.ma_length:"
    "            return (0, None, None, 0, False)"
    "        row = self.df.iloc[index]"
    "        prev = self.df.iloc[index - 1]"
    "        if pd.isna(row['ma']) or pd.isna(prev['ma']):"
    "            return (0, None, None, 0, False)"
    "        long_condition = (prev['low'] <= prev['ma']) and (row['low'] > row['ma'])"
    "        short_condition = (prev['high'] >= prev['ma']) and (row['high'] < row['ma'])"
    "        if long_condition:"
    "            direction = 1"
    "            exit_signal = True"
    "        elif short_condition:"
    "            direction = -1"
    "            exit_signal = True"
    "        else:"
    "            return (0, None, None, 0, False)"
    "        if current_position == direction:"
    "            return (0, None, None, 0, False)"
    "        entry_price = row['close']"
    "        nominal_value = current_balance * self.position_ratio * leverage"
    "        position_size = nominal_value / entry_price"
    "        return (direction, None, None, position_size, exit_signal)"
    "模板二（有止盈止损策略）\n"
    "import pandas as pd"
    "class DualMaStrategy:"
    "    def __init__(self, df: pd.DataFrame, fast_ma: int, slow_ma: int, position_ratio: float, tp_rate: float, sl_rate: float):"
    "        self.df = df.copy()"
    "        self.fast_ma = fast_ma"
    "        self.slow_ma = slow_ma"
    "        self.position_ratio = position_ratio"
    "        self.tp_rate = tp_rate"
    "        self.sl_rate = sl_rate"
    "        self.df['fast_ma'] = self.df['close'].rolling(fast_ma).mean()"
    "        self.df['slow_ma'] = self.df['close'].rolling(slow_ma).mean()"
    "        self.warmup_period = max(fast_ma, slow_ma)"
    "    def generate_signal(self, index: int, current_balance: float, leverage: float = 1.0, current_position: int = 0):"
    "        if index < self.slow_ma:"
    "            return (0, None, None, 0, False)"
    "        row = self.df.iloc[index]"
    "        prev = self.df.iloc[index - 1]"
    "        if pd.isna(row['fast_ma']) or pd.isna(row['slow_ma']) or pd.isna(prev['fast_ma']) or pd.isna(prev['slow_ma']):"
    "            return (0, None, None, 0, False)"
    "        long_condition = prev['fast_ma'] <= prev['slow_ma'] and row['fast_ma'] > row['slow_ma']"
    "        short_condition = prev['fast_ma'] >= prev['slow_ma'] and row['fast_ma'] < row['slow_ma']"
    "        if long_condition:"
    "            direction = 1"
    "        elif short_condition:"
    "            direction = -1"
    "        else:"
    "            return (0, None, None, 0, False)"
    "        if direction == current_position:"
    "            return (0, None, None, 0, False)"
    "        entry_price = row['close']"
    "        nominal_value = current_balance * self.position_ratio * leverage"
    "        position_size = nominal_value / entry_price"
    "        if direction == 1:"
    "            take_profit = entry_price * (1 + self.tp_rate)"
    "            stop_loss = entry_price * (1 - self.sl_rate)"
    "        else:"
    "            take_profit = entry_price * (1 - self.tp_rate)"
    "            stop_loss = entry_price * (1 + self.sl_rate)"
    "        return (direction, take_profit, stop_loss, position_size, False)"


        "请根据用户的策略意图，严格按上述规范生成代码。注意，指输出代码，请不要输出任何其他的用户互动自然语言，这很重要。"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": description_text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ 代码生成失败：{str(e)}"
# -------- 创建页面 --------
def create_llm_strategy_generator_ui():
    with gr.Blocks(title="💡 策略生成器（基于大模型）") as demo:
        gr.Markdown("## 🎯 自然语言策略生成器\n通过自然语言描述你的交易策略，我们将自动帮你生成符合标准格式的策略类代码")

        user_input = gr.Textbox(lines=5, label="📝 你想要的策略（自然语言）")
        translated_output = gr.Textbox(lines=10, label="📄 结构化策略描述", interactive=True)
        code_output = gr.Code(label="🧠 生成的策略代码", language="python")

        with gr.Row():
            translate_btn = gr.Button("🔁 翻译策略意图")
            generate_btn = gr.Button("🧪 生成策略代码")

        translate_btn.click(fn=translate_user_intent, inputs=[user_input], outputs=[translated_output])
        generate_btn.click(fn=generate_strategy_code, inputs=[translated_output], outputs=[code_output])

    return demo
