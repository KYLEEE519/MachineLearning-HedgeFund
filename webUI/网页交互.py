import gradio as gr
import pandas as pd
import xgboost as xgb
import matplotlib.pyplot as plt
import os
import pickle
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
from okx_fetch_data import fetch_kline_df

df_cache = None  # 全局数据缓存


def show_data(days, bar, instId):
    global df_cache
    df_cache = fetch_kline_df(days=days, bar=bar, instId=instId)
    if df_cache.empty:
        return "未获取到数据，请检查参数！", ""
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())


def get_columns():
    global df_cache
    if df_cache is None or df_cache.empty:
        return gr.update(choices=[]), gr.update(choices=[])
    cols = df_cache.columns.tolist()
    return gr.update(choices=cols), gr.update(choices=cols)


def train_model(feature_cols, target_col, learning_rate, max_depth, n_estimators, save_path):
    global df_cache
    if df_cache is None or df_cache.empty:
        raise ValueError("未获取到数据，请先点击读取数据")

    df = df_cache
    X = df[feature_cols]
    y = df[target_col]

    if y.nunique() > 10:
        model = xgb.XGBRegressor(
            learning_rate=learning_rate,
            max_depth=max_depth,
            n_estimators=n_estimators,
        )
    else:
        model = xgb.XGBClassifier(
            learning_rate=learning_rate,
            max_depth=max_depth,
            n_estimators=n_estimators,
            eval_metric='logloss'
        )

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=True)

    evals_result = model.evals_result() if hasattr(model, 'evals_result') else {}

    os.makedirs("result", exist_ok=True)
    loss_path = os.path.join("result", "loss.png")
    importance_path = os.path.join("result", "feature_importance.png")
    model_path = os.path.join(save_path, 'xgb_model.pkl')

    if evals_result:
        plt.figure()
        loss_key = list(evals_result['validation_0'].keys())[0]
        plt.plot(evals_result['validation_0'][loss_key])
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Validation Loss')
        plt.savefig(loss_path)
        plt.close()

    xgb.plot_importance(model)
    plt.savefig(importance_path)
    plt.close()

    if isinstance(model, xgb.XGBClassifier):
        y_pred = model.predict(X_val)
        acc = accuracy_score(y_val, y_pred)
    else:
        y_pred = model.predict(X_val)
        acc = np.sqrt(mean_squared_error(y_val, y_pred))

    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    return loss_path, importance_path, acc, f"模型已保存到: {model_path}"


# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("# XGBoost 可视化训练工具（仅支持OKX数据获取）")

    with gr.Row():
        days = gr.Number(label="获取最近几天数据（days）", info="例如7表示最近7天")
        bar = gr.Textbox(label="K线粒度（bar）", info="例如1m、5m、1H、4H")
        instId = gr.Textbox(label="交易对（instId）", info="例如BTC-USDT")

    data_info = gr.Markdown()
    all_columns = gr.Markdown(label="全部列名")

    load_button = gr.Button("获取并展示数据")

    feature_cols = gr.Dropdown(choices=[], label="选择特征列(可多选)", multiselect=True)
    target_col = gr.Dropdown(choices=[], label="选择目标列(单选)", multiselect=False)

    load_button.click(fn=show_data, inputs=[days, bar, instId], outputs=[data_info, all_columns])
    load_button.click(fn=get_columns, inputs=[], outputs=[feature_cols, target_col])

    gr.Markdown("### 模型参数设置")
    learning_rate = gr.Slider(0.01, 1.0, 0.1, step=0.01, label="学习率")
    max_depth = gr.Slider(1, 15, 3, step=1, label="最大深度")
    n_estimators = gr.Slider(10, 500, 100, step=10, label="迭代次数")
    save_path = gr.Textbox(label="模型保存路径(需要提前存在)")

    train_button = gr.Button("开始训练")

    loss_img = gr.Image(label="Loss曲线")
    importance_img = gr.Image(label="特征重要性")
    acc = gr.Textbox(label="验证集评估指标")
    save_info = gr.Textbox(label="模型保存信息")

    train_button.click(
        fn=train_model,
        inputs=[feature_cols, target_col, learning_rate, max_depth, n_estimators, save_path],
        outputs=[loss_img, importance_img, acc, save_info]
    )

demo.launch()
