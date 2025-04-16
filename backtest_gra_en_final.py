import gradio as gr
import pandas as pd
import json
import importlib
import plotly.graph_objs as go
from waibu.init_waibu import SimulatedExchange
from Data.okx_fetch_data import fetch_kline_df

with open("Strategies/strategies.json", "r", encoding="utf-8") as f:
    STRATEGY_CONFIGS = json.load(f)

def load_strategy_class(class_path: str):
    module_name, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)

def extract_trade_points(trade_log):
    opens, closes, transitions, balance_curve = [], [], [], []
    balance = 0
    for i, trade in enumerate(trade_log):
        timestamp = trade["timestamp"]
        price = trade.get("price") or trade.get("exit_price")
        direction = trade["direction"]
        action = trade["action"]
        balance = balance + trade.get("profit", 0) if action == "close" else balance
        if action == "close":
            balance_curve.append({"timestamp": timestamp, "balance": balance})
        point = {"timestamp": timestamp, "price": price, "direction": direction, "action": action}
        if action == "open":
            if i > 0 and trade_log[i - 1]["action"] == "close" and trade_log[i - 1]["timestamp"] == timestamp:
                transitions.append(point)
            else:
                opens.append(point)
        elif action == "close":
            if i + 1 < len(trade_log) and trade_log[i + 1]["action"] == "open" and trade_log[i + 1]["timestamp"] == timestamp:
                continue
            closes.append(point)
    return opens, closes, transitions, balance_curve

def format_positions(positions):
    lines = []
    for symbol, pos_list in positions.items():
        for pos in pos_list:
            line = f"{symbol} | {['空','多'][pos['direction']>0]}仓 | 数量: {pos['size']:.4f} @ 价格: {pos['entry_price']:.2f}"
            lines.append(line)
    return "\n".join(lines) if lines else "No Positions"

def build_additional_charts(trade_log):
    df = pd.DataFrame(trade_log)
    charts = []
    if df.empty:
        return charts

    df_close = df[df['action'] == 'close'].copy()
    df_close['timestamp'] = pd.to_datetime(df_close['timestamp'])
    df_close['open_timestamp'] = pd.to_datetime(df_close['open_timestamp'])

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=df_close['timestamp'],
        y=df_close['profit'],
        marker_color=['green' if p > 0 else 'red' for p in df_close['profit']],
        name="Profit per Trade"
    ))
    fig1.update_layout(title="Each Trade Profit", xaxis_title="Time", yaxis_title="Profit")
    charts.append(fig1)

    df_close['cumsum'] = df_close['profit'].cumsum()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_close['timestamp'], y=df_close['cumsum'], mode="lines+markers", name="累计Profit"))
    fig2.update_layout(title="累计Profit曲线", xaxis_title="Time", yaxis_title="累计Profit")
    charts.append(fig2)

    peak = df_close['cumsum'].cummax()
    drawdown = peak - df_close['cumsum']
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df_close['timestamp'], y=drawdown, fill='tozeroy', name="Drawdown"))
    fig3.update_layout(title="Drawdown曲线", xaxis_title="Time", yaxis_title="最大Drawdown")
    charts.append(fig3)

    df_close['type'] = df_close['direction'].map({1: 'Long', -1: 'Short'})
    grouped = df_close.groupby('type')['profit'].sum()
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(x=grouped.index, y=grouped.values, marker_color=['blue', 'orange']))
    fig4.update_layout(title="Long vs Short Profit Comparison", xaxis_title="Direction", yaxis_title="总Profit")
    charts.append(fig4)

    df_close['duration'] = (df_close['timestamp'] - df_close['open_timestamp']).dt.total_seconds() / 60
    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(
        x=df_close['duration'], y=df_close['profit'], mode='markers', name="持仓时长vsProfit",
        marker=dict(size=8, color='purple')
    ))
    fig5.update_layout(title="持仓时长 vs Profit", xaxis_title="Minutes", yaxis_title="Profit")
    charts.append(fig5)

    return charts

def run_backtest_ui(strategy_key, strategy_param_json, days, bar, initial_balance, instId, show_charts,
                    open_fee_rate, close_fee_rate, leverage, maintenance_margin_rate, min_unit):
    config = STRATEGY_CONFIGS[strategy_key]
    strategy_class = load_strategy_class(config["class_path"])
    use_strategy_exit = config["use_strategy_exit"]
    try:
        strategy_kwargs = json.loads(strategy_param_json)
    except json.JSONDecodeError:
        return "Invalid JSON format for parameters", None, None, [], None

    df = fetch_kline_df(days=days, bar=bar, instId=instId)
    if df.empty:
        return "Failed to fetch K-line data", None, None, [], None

    strategy = strategy_class(df=df, **strategy_kwargs)
    exchange = SimulatedExchange(
        initial_balance=initial_balance,
        open_fee_rate=open_fee_rate,
        close_fee_rate=close_fee_rate,
        leverage=leverage,
        position_ratio=0.1,
        maintenance_margin_rate=maintenance_margin_rate,
        min_unit=min_unit
    )   

    for i in range(strategy.warmup_period, len(df)):
        kline = df.iloc[i]
        if use_strategy_exit:
            current_pos = exchange.positions.get(instId, [{}])
            current_dir = current_pos[0].get("direction", 0) if current_pos else 0
            raw_signal = strategy.generate_signal(i, exchange.balance, exchange.leverage, current_dir)
            exchange.process_closing(instId, kline, raw_signal)
            current_pos = exchange.positions.get(instId, [{}])
            current_dir = current_pos[0].get("direction", 0) if current_pos else 0
            new_signal = strategy.generate_signal(i, exchange.balance, exchange.leverage, 0)
        else:
            new_signal = strategy.generate_signal(i, exchange.balance, exchange.leverage, 0)
            new_signal = new_signal[:4] + (False,)
            exchange.process_closing(instId, kline, new_signal)
        exchange.process_opening(instId, kline, new_signal)

    final_price = df.iloc[-1]["close"]
    total_balance, roi, total_trades = exchange.calculate_total_balance_and_roi(final_price)
    opens, closes, transitions, balance_curve = extract_trade_points(exchange.trade_log)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["close"], mode="lines", name="Close"))
    if opens:
        fig.add_trace(go.Scatter(x=[pt["timestamp"] for pt in opens], y=[pt["price"] for pt in opens], mode="markers", marker=dict(color="green", size=10, symbol="triangle-up"), name="Open"))
    if closes:
        fig.add_trace(go.Scatter(x=[pt["timestamp"] for pt in closes], y=[pt["price"] for pt in closes], mode="markers", marker=dict(color="red", size=10, symbol="x"), name="Close"))
    if transitions:
        fig.add_trace(go.Scatter(x=[pt["timestamp"] for pt in transitions], y=[pt["price"] for pt in transitions], mode="markers", marker=dict(color="orange", size=12, symbol="star"), name="Open+Close"))

    fig2 = go.Figure()
    if balance_curve:
        fig2.add_trace(go.Scatter(x=[pt["timestamp"] for pt in balance_curve], y=[initial_balance + pt["balance"] for pt in balance_curve], mode="lines+markers", name="Balance Curve"))
        fig2.update_layout(title="平仓后账户余额变化", xaxis_title="Time", yaxis_title="Account Balance")

    summary = f"""
--- Backtest Result汇总 ---
Final Account Balance: {exchange.balance:.2f}
Remaining Positions:\n{format_positions(exchange.positions)}
Total Account Balance: {total_balance:.2f}
ROI: {roi:.2f}%
Total Number of Trades: {total_trades} 笔
"""
    trade_df = pd.DataFrame(exchange.trade_log)
    extra_charts = build_additional_charts(exchange.trade_log) if show_charts else []
    return summary, fig, trade_df, [fig2] + extra_charts, trade_df

with gr.Blocks(title="Strategy Backtest Platform") as demo:
    gr.Markdown("## 📈 Multi-strategy Backtester")
    strategy_keys = list(STRATEGY_CONFIGS.keys())
    default_key = strategy_keys[0]
    default_config = STRATEGY_CONFIGS[default_key]
    default_json = json.dumps(default_config["default_params"], indent=2)

    with gr.Row():
        strategy_choice = gr.Dropdown(choices=strategy_keys, value=default_key, label="Select Strategy")
        days = gr.Slider(1, 30, value=10, step=1, label="Backtest Days")
        bar = gr.Dropdown(
            choices=["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"],
            value="5m",
            label="K-line Interval"
        )

        initial_balance = gr.Slider(1000, 20000, value=10000, step=500, label="Initial Balance")
        open_fee_rate = gr.Slider(0, 0.01, value=0.0001, step=0.0001, label="Open Fee Rate")
        close_fee_rate = gr.Slider(0, 0.01, value=0.0001, step=0.0001, label="Close Fee Rate")
        leverage = gr.Slider(1, 20, value=1.0, step=0.5, label="Leverage")
        maintenance_margin_rate = gr.Slider(0, 0.1, value=0.005, step=0.001, label="Maintenance Margin Rate")
        min_unit = gr.Number(value=10, label="Minimum Order Unit")

        instId = gr.Textbox(label="Symbol (e.g. BTC-USDT)", value="BTC-USDT")
    json_editor = gr.Code(label="Strategy Parameter JSON", language="json", value=default_json)
    show_charts = gr.Checkbox(label="Show All Charts", value=True)

    btn = gr.Button("Start Backtest")
    output_summary = gr.Textbox(label="Backtest Result")
    output_plot = gr.Plot(label="Price + Trades")
    chart_boxes = [gr.Plot(visible=False) for _ in range(10)]
    output_trades = gr.Dataframe(label="Trade Log")

    def update_json(strategy_key):
        cfg = STRATEGY_CONFIGS[strategy_key]
        return json.dumps(cfg["default_params"], indent=2)

    def run_and_return(strategy_key, strategy_param_json, days, bar,initial_balance, instId, show_charts,
                   open_fee_rate, close_fee_rate, leverage, maintenance_margin_rate, min_unit):

        summary, main_fig, trades, other_figs, df = run_backtest_ui(
            strategy_key, strategy_param_json, days,  bar,initial_balance, instId, show_charts,
            open_fee_rate, close_fee_rate, leverage, maintenance_margin_rate, min_unit
        )

        # 如果少于 10 张图，补 None
        padded_figs = other_figs[:10] + [None] * (10 - len(other_figs))

        # 用 gr.update(value=..., visible=True) 包装返回
        updated_figs = []
        for fig in padded_figs:
            if fig is not None:
                updated_figs.append(gr.update(value=fig, visible=True))
            else:
                updated_figs.append(gr.update(visible=False))

        return [summary, main_fig] + updated_figs + [df]


    strategy_choice.change(fn=update_json, inputs=strategy_choice, outputs=json_editor)
    btn.click(
        fn=run_and_return,
        inputs=[strategy_choice, json_editor, days,bar, initial_balance, instId, show_charts,
                open_fee_rate, close_fee_rate, leverage, maintenance_margin_rate, min_unit],
        outputs=[output_summary, output_plot] + chart_boxes + [output_trades]
    )

if __name__ == "__main__":
    demo.launch()