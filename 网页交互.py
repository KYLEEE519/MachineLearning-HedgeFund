import gradio as gr
import pandas as pd
import xgboost as xgb
import matplotlib.pyplot as plt
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle

def show_data(file):
    df = pd.read_csv(file.name)
    return df.head().to_markdown(), ", ".join(df.columns.tolist())

def get_columns(file):
    df = pd.read_csv(file.name)
    cols = df.columns.tolist()
    return gr.update(choices=cols), gr.update(choices=cols)





# 训练模型
def train_model(file, feature_cols, target_col, learning_rate, max_depth, n_estimators, save_path):
    df = pd.read_csv(file.name)

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

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=True
    )

    evals_result = model.evals_result() if hasattr(model, 'evals_result') else {}

    os.makedirs("result", exist_ok=True)

    loss_path = os.path.join("result", "loss.png")
    importance_path = os.path.join("result", "feature_importance.png")
    model_path = os.path.join(save_path, 'xgb_model.pkl')

    # 绘制 loss 曲线
    if evals_result:
        plt.figure()
        loss_key = list(evals_result['validation_0'].keys())[0]  # 自动找 logloss / rmse
        plt.plot(evals_result['validation_0'][loss_key])
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Validation Loss')
        plt.savefig(loss_path)
        plt.close()

    # 绘制特征重要性
    xgb.plot_importance(model)
    plt.savefig(importance_path)
    plt.close()

    if isinstance(model, xgb.XGBClassifier):
        y_pred = model.predict(X_val)
        from sklearn.metrics import accuracy_score
        acc = accuracy_score(y_val, y_pred)
    else:
        y_pred = model.predict(X_val)
        from sklearn.metrics import mean_squared_error
        import numpy as np
        acc = np.sqrt(mean_squared_error(y_val, y_pred))

    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    return loss_path, importance_path, acc, f"模型已保存到: {model_path}"





with gr.Blocks() as demo:
    gr.Markdown("# XGBoost 可视化训练工具")

    with gr.Row():
        file = gr.File(label="上传CSV数据")
        data_info = gr.Markdown()
        all_columns = gr.Markdown(label="全部列名")

    load_button = gr.Button("读取数据")

    feature_cols = gr.Dropdown(
        choices=[], label="选择特征列(可多选)", multiselect=True, allow_custom_value=False
    )
    target_col = gr.Dropdown(
        choices=[], label="选择目标列(单选)", multiselect=False, allow_custom_value=False
    )

    load_button.click(fn=show_data, inputs=file, outputs=[data_info, all_columns])
    load_button.click(fn=get_columns, inputs=file, outputs=[feature_cols, target_col])

    gr.Markdown("### 模型参数设置")
    learning_rate = gr.Slider(0.01, 1.0, 0.1, step=0.01, label="学习率")
    max_depth = gr.Slider(1, 15, 3, step=1, label="最大深度")
    n_estimators = gr.Slider(10, 500, 100, step=10, label="迭代次数")
    save_path = gr.Textbox(label="模型保存路径(需要提前存在)")

    train_button = gr.Button("开始训练")

    loss_img = gr.Image(label="Loss曲线")
    importance_img = gr.Image(label="特征重要性")
    acc = gr.Textbox(label="验证集准确率")
    save_info = gr.Textbox(label="模型保存信息")

    train_button.click(
        fn=train_model,
        inputs=[file, feature_cols, target_col, learning_rate, max_depth, n_estimators, save_path],
        outputs=[loss_img, importance_img, acc, save_info]
    )

demo.launch()
