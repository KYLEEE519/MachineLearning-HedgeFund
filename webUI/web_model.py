from timexer import train_timexer_model
import gradio as gr
import pandas as pd
import json
# from okx_fetch_data import fetch_kline_df
# from indicators import indicator_registry, indicator_params
import os
from datetime import datetime
import xgboost as xgb
import matplotlib.pyplot as plt
import pickle
import numpy as np
# from sklearn.model_selection import train_test_split
# from okx_fetch_data import fetch_kline_df
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import accuracy_score, mean_squared_error, roc_auc_score, roc_curve, precision_score, recall_score, f1_score

# def get_columns():
#     global df_csv
#     if df_csv is None or df_csv.empty:
#         return gr.update(choices=[]), gr.update(choices=[])
#     cols = df_csv.columns.tolist()
#     return gr.update(choices=cols), gr.update(choices=cols)


# =====================================
# 新增函数: 加载 CSV 数据
# =====================================
df_csv = None    # 加载的 CSV 数据

def load_csv(csv_path):
    global df_csv
    if not os.path.exists(csv_path):
        return "路径不存在，请检查！", "", gr.update(choices=[]), gr.update(choices=[])

    df_csv = pd.read_csv(csv_path)
    cols = df_csv.columns.tolist()
    
    # 注意：这里返回的是固定的 ['target'] 而不是列名
    return (
        df_csv.head().to_markdown(), 
        ", ".join(cols), 
        gr.update(choices=cols), 
        gr.update(choices=["target"], value="target")  # 固定唯一选项
    )


# def validate_data(df, feature_cols, target_col):
#     # 检查特征列和目标列是否存在
#     for col in feature_cols:
#         if col not in df.columns:
#             return False, f"特征列 {col} 不存在"

#     if target_col not in df.columns:
#         return False, f"目标列 {target_col} 不存在"

#     # 检查目标列类别数
#     y = df[target_col]
#     if y.nunique() <= 1:
#         return False, f"目标列 {target_col} 类别数 <= 1，不满足分类或回归任务要求"

#     # 检查特征列是否为数值类型
#     for col in feature_cols:
#         if not pd.api.types.is_numeric_dtype(df[col]):
#             return False, f"特征列 {col} 存在非数值类型数据"

#     return True, "数据检查通过"

# 检查数据合法性函数
def check_data_validity(feature_cols, target_col):
    global df_csv
    if df_csv is None or df_csv.empty:
        return "❌ 未加载数据，请先读取 CSV 文件"

    df = df_csv

    # 检查目标列
    if target_col not in df.columns:
        return f"❌ 目标列 {target_col} 不存在，请检查！"

    # 检查特征列
    missing_cols = [col for col in feature_cols if col not in df.columns]
    if missing_cols:
        return f"❌ 以下特征列不存在: {missing_cols}"

    # 检查特征列是否全为数值型
    non_numeric_cols = df[feature_cols].select_dtypes(exclude=["number"]).columns.tolist()
    if non_numeric_cols:
        return f"❌ 以下特征列存在非数值类型数据，仅支持数值特征: {non_numeric_cols}"

    # 检查 target 列类别数
    unique_num = df[target_col].nunique()
    if unique_num < 2:
        return f"❌ 目标列 {target_col} 类别数不足，仅有 {unique_num} 类"

    if unique_num > 10:
        return f"❌ 目标列 {target_col} 类别数过多，有 {unique_num} 类，不推荐"

    return "✅ 数据检查通过！"


def train_model(feature_cols, target_col,
                learning_rate, max_depth, n_estimators,
                subsample, colsample_bytree, gamma, reg_lambda, reg_alpha):
    global df_csv
    if df_csv is None or df_csv.empty:
        raise ValueError("未加载数据，请先读取 CSV 文件")

    df = df_csv
    
    X = df[feature_cols]
    y = df[target_col]

    is_classification = y.nunique() <= 10
    if is_classification:
        model = xgb.XGBClassifier(
            learning_rate=learning_rate,
            max_depth=max_depth,
            n_estimators=n_estimators,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            gamma=gamma,
            reg_lambda=reg_lambda,
            reg_alpha=reg_alpha,
            eval_metric='logloss'
        )
    else:
        model = xgb.XGBRegressor(
            learning_rate=learning_rate,
            max_depth=max_depth,
            n_estimators=n_estimators,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            gamma=gamma,
            reg_lambda=reg_lambda,
            reg_alpha=reg_alpha,
        )

    split_index = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_val = y.iloc[:split_index], y.iloc[split_index:]

    model.fit(X_train, y_train, eval_set=[(X_train, y_train), (X_val, y_val)], verbose=True)

    evals_result = model.evals_result()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = f"xgboost_{timestamp}"
    os.makedirs("models", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    model_path = os.path.join("models", model_name + ".pkl")
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    if evals_result:
        plt.figure()
        plt.plot(evals_result['validation_0']['logloss'], label='Train Loss')
        plt.plot(evals_result['validation_1']['logloss'], label='Val Loss')
        plt.xlabel('Estimator')
        plt.ylabel('Loss')
        plt.title('Train vs Val Loss')
        plt.legend()
        plt.savefig(f"results/{model_name}_loss.png")
        plt.close()

    xgb.plot_importance(model)
    plt.savefig(f"results/{model_name}_importance.png")
    plt.close()

    roc_path = ""
    auc = "N/A"
    if is_classification:
        y_pred = model.predict(X_val)
        y_pred_proba = model.predict_proba(X_val)[:, 1]

        acc = accuracy_score(y_val, y_pred)
        precision = precision_score(y_val, y_pred, zero_division=0)
        recall = recall_score(y_val, y_pred, zero_division=0)
        f1 = f1_score(y_val, y_pred, zero_division=0)
        auc = roc_auc_score(y_val, y_pred_proba)

        acc_info = f"ACC: {acc:.4f}  Precision: {precision:.4f}  Recall: {recall:.4f}  F1: {f1:.4f}"

        fpr, tpr, _ = roc_curve(y_val, y_pred_proba)
        plt.figure()
        plt.plot(fpr, tpr)
        plt.xlabel('FPR')
        plt.ylabel('TPR')
        plt.title('ROC Curve')
        roc_path = f"results/{model_name}_roc.png"
        plt.savefig(roc_path)
        plt.close()
    else:
        y_pred = model.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        acc_info = f"RMSE: {rmse:.4f}"

    return (f"results/{model_name}_loss.png",
            f"results/{model_name}_importance.png",
            acc_info,
            f"模型已保存至: {os.path.abspath(model_path)}\nAUC: {auc}",
            roc_path)



def hyperparameter_search(feature_cols, target_col, n_iter,
                          lr_min, lr_max, lr_step,
                          n_min, n_max, n_step,
                          depth_min, depth_max, depth_step,
                          subsample_min, subsample_max, subsample_step,
                          colsample_min, colsample_max, colsample_step,
                          gamma_min, gamma_max, gamma_step,
                          lambda_min, lambda_max, lambda_step,
                          alpha_min, alpha_max, alpha_step):
    global df_csv
    if df_csv is None or df_csv.empty:
        return "未加载数据，请先读取 CSV 文件"

    df = df_csv


    X = df[feature_cols]
    y = df[target_col]

    # 按时间顺序划分 8:2
    split_index = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_val = y.iloc[:split_index], y.iloc[split_index:]

    # 判断分类 or 回归
    is_classification = y.nunique() <= 10

    if is_classification:
        model = xgb.XGBClassifier(eval_metric='logloss', use_label_encoder=False)
        scoring = "accuracy"
    else:
        model = xgb.XGBRegressor()
        scoring = "neg_root_mean_squared_error"

    # 构造 param_grid
    param_grid = {
        "learning_rate": list(np.arange(lr_min, lr_max + lr_step, lr_step)),
        "n_estimators": list(range(n_min, n_max + n_step, n_step)),
        "max_depth": list(range(depth_min, depth_max + depth_step, depth_step)),
        "subsample": list(np.arange(subsample_min, subsample_max + subsample_step, subsample_step)),
        "colsample_bytree": list(np.arange(colsample_min, colsample_max + colsample_step, colsample_step)),
        "gamma": list(np.arange(gamma_min, gamma_max + gamma_step, gamma_step)),
        "reg_lambda": list(np.arange(lambda_min, lambda_max + lambda_step, lambda_step)),
        "reg_alpha": list(np.arange(alpha_min, alpha_max + alpha_step, alpha_step)),
    }

    search = RandomizedSearchCV(
        estimator=model,
        param_distributions=param_grid,
        n_iter=n_iter,
        scoring=scoring,
        cv=3,
        verbose=2,
        n_jobs=-1,
        random_state=42
    )

    search.fit(X_train, y_train)

    best_params = search.best_params_
    best_score = search.best_score_

    return f"超参数搜索完毕！\n\n最佳参数:\n{json.dumps(best_params, indent=4)}\n\n最佳得分: {best_score:.4f}"

def build_model_train_ui():
    with gr.Tab("XGBoost 训练"):
        gr.Markdown("# XGBoost 可视化训练")

        csv_path = gr.Textbox(label="输入 CSV 文件绝对路径")
        load_csv_button = gr.Button("读取 CSV")

        data_info = gr.Markdown()
        all_columns = gr.Markdown(label="全部列名")

        feature_cols = gr.Dropdown(choices=[], label="选择特征列(可多选)", multiselect=True)
        target_col = gr.Dropdown(choices=[], label="选择目标列(单选)", multiselect=False)

        load_csv_button.click(
                        fn=load_csv,
                        inputs=[csv_path],
                        outputs=[data_info, all_columns, feature_cols, target_col]
                    )
        gr.Markdown("## 数据检查")

        check_info = gr.Markdown()  # 显示检查结果
        check_button = gr.Button("检查数据合法性")

        check_button.click(
            fn=check_data_validity,
            inputs=[feature_cols, target_col],
            outputs=[check_info]
        )
        with gr.Tab("模型训练"):
            with gr.Tab("手动调整参数"):
                gr.Markdown("### 模型参数设置")

                learning_rate = gr.Slider(0.001, 1.0, 0.1, step=0.001, label="学习率")
                n_estimators = gr.Slider(10, 500, 50, step=10, label="迭代次数")
                max_depth = gr.Slider(1, 15, 3, step=1, label="最大深度")
                subsample = gr.Slider(0.6, 0.9, 0.8, step=0.1, label="subsample（行采样比例）")
                colsample_bytree = gr.Slider(0.6, 1.0, 0.8, step=0.1, label="colsample_bytree（列采样比例）")
                gamma = gr.Slider(0.0, 0.5, 0.1, step=0.1, label="gamma（最小损失减少）")
                reg_lambda = gr.Slider(0.0, 10.0, 1.0, step=0.5, label="reg_lambda（L2 正则）")
                reg_alpha = gr.Slider(0.0, 10.0, 1.0, step=0.5, label="reg_alpha（L1 正则）")

                train_button = gr.Button("开始训练")

                loss_img = gr.Image(label="Train vs Val Loss 曲线")
                importance_img = gr.Image(label="特征重要性图")
                acc = gr.Textbox(label="验证集评估指标")
                save_info = gr.Textbox(label="模型保存信息")
                roc_img = gr.Image(label="ROC 曲线图（分类任务）")

                train_button.click(
                    fn=train_model,
                    inputs=[
                        feature_cols, target_col,
                        learning_rate, max_depth, n_estimators,
                        subsample, colsample_bytree, gamma, reg_lambda, reg_alpha
                    ],
                    outputs=[loss_img, importance_img, acc, save_info, roc_img]
                )
            with gr.Tab("通过json调整参数"):
                gr.Markdown("### 使用 JSON 输入训练参数")

                json_input = gr.Code(label="输入参数 JSON", language="json", value='''{
                "subsample": 0.6,
                "reg_lambda": 1.0,
                "reg_alpha": 0.0,
                "n_estimators": 100,
                "max_depth": 2,
                "learning_rate": 0.002,
                "gamma": 0.1,
                "colsample_bytree": 0.6
            }''')

                json_train_button = gr.Button("使用 JSON 参数开始训练")

                json_loss_img = gr.Image(label="Train vs Val Loss 曲线")
                json_importance_img = gr.Image(label="特征重要性图")
                json_acc = gr.Textbox(label="验证集评估指标")
                json_save_info = gr.Textbox(label="模型保存信息")
                json_roc_img = gr.Image(label="ROC 曲线图（分类任务）")

                def train_with_json_params(params_json, feature_cols, target_col):
                    try:
                        params = json.loads(params_json)
                    except json.JSONDecodeError as e:
                        return "", "", "", f"JSON 解析错误: {e}", ""

                    keys = ["learning_rate", "max_depth", "n_estimators", "subsample", "colsample_bytree", "gamma", "reg_lambda", "reg_alpha"]
                    for k in keys:
                        if k not in params:
                            return "", "", "", f"缺少参数: {k}", ""

                    return train_model(
                        feature_cols, target_col,
                        params["learning_rate"],
                        params["max_depth"],
                        params["n_estimators"],
                        params["subsample"],
                        params["colsample_bytree"],
                        params["gamma"],
                        params["reg_lambda"],
                        params["reg_alpha"]
                    )

                json_train_button.click(
                    fn=train_with_json_params,
                    inputs=[json_input, feature_cols, target_col],
                    outputs=[json_loss_img, json_importance_img, json_acc, json_save_info, json_roc_img]
                )


        with gr.Tab("超参数搜索"):
            gr.Markdown("# XGBoost 超参数搜索（RandomizedSearchCV）")



            gr.Markdown("### 超参数范围设置（最大范围固定，可缩小范围 & 调整步长）")

            # 每个超参数范围设置
            lr_min = gr.Slider(0.001, 1.0, 0.001, step=0.001, label="learning_rate 最小值")
            lr_max = gr.Slider(0.001, 1.0, 0.1, step=0.001, label="learning_rate 最大值")
            lr_step = gr.Slider(0.001, 1.0, 0.001, step=0.001, label="learning_rate 步长")

            n_min = gr.Slider(10, 500, 10, step=10, label="n_estimators 最小值")
            n_max = gr.Slider(10, 500, 100, step=10, label="n_estimators 最大值")
            n_step = gr.Slider(10, 500, 10, step=10, label="n_estimators 步长")

            depth_min = gr.Slider(1, 15, 1, step=1, label="max_depth 最小值")
            depth_max = gr.Slider(1, 15, 3, step=1, label="max_depth 最大值")
            depth_step = gr.Slider(1, 15, 1, step=1, label="max_depth 步长")

            subsample_min = gr.Slider(0.6, 0.9, 0.6, step=0.1, label="subsample 最小值")
            subsample_max = gr.Slider(0.6, 0.9, 0.8, step=0.1, label="subsample 最大值")
            subsample_step = gr.Slider(0.1, 0.3, 0.1, step=0.1, label="subsample 步长")

            colsample_min = gr.Slider(0.6, 1.0, 0.6, step=0.1, label="colsample_bytree 最小值")
            colsample_max = gr.Slider(0.6, 1.0, 0.8, step=0.1, label="colsample_bytree 最大值")
            colsample_step = gr.Slider(0.1, 0.3, 0.1, step=0.1, label="colsample_bytree 步长")

            gamma_min = gr.Slider(0.0, 0.5, 0.0, step=0.1, label="gamma 最小值")
            gamma_max = gr.Slider(0.0, 0.5, 0.1, step=0.1, label="gamma 最大值")
            gamma_step = gr.Slider(0.1, 0.3, 0.1, step=0.1, label="gamma 步长")

            lambda_min = gr.Slider(0.0, 10.0, 0.0, step=0.5, label="reg_lambda 最小值")
            lambda_max = gr.Slider(0.0, 10.0, 1.0, step=0.5, label="reg_lambda 最大值")
            lambda_step = gr.Slider(0.5, 5.0, 0.5, step=0.5, label="reg_lambda 步长")

            alpha_min = gr.Slider(0.0, 10.0, 0.0, step=0.5, label="reg_alpha 最小值")
            alpha_max = gr.Slider(0.0, 10.0, 1.0, step=0.5, label="reg_alpha 最大值")
            alpha_step = gr.Slider(0.5, 5.0, 0.5, step=0.5, label="reg_alpha 步长")

            n_iter = gr.Slider(5, 100, 20, step=1, label="采样超参数组合的次数")

            search_result = gr.Markdown(label="搜索结果")

            search_button = gr.Button("开始超参数搜索")

            # 按钮逻辑
            search_button.click(
                fn=hyperparameter_search,
                inputs=[
                    feature_cols, target_col, n_iter,
                    lr_min, lr_max, lr_step,
                    n_min, n_max, n_step,
                    depth_min, depth_max, depth_step,
                    subsample_min, subsample_max, subsample_step,
                    colsample_min, colsample_max, colsample_step,
                    gamma_min, gamma_max, gamma_step,
                    lambda_min, lambda_max, lambda_step,
                    alpha_min, alpha_max, alpha_step,
                ],
                outputs=[search_result]
            )

    with gr.Tab("TimeXer 模型训练"):
        gr.Markdown("# TimeXer 模型 - 基于 Transformer 的涨跌预测")

        # ===== CSV 数据输入 =====
        timexer_csv_path = gr.Textbox(label="输入 CSV 文件路径（含所有特征+target）")
        timexer_load_btn = gr.Button("加载数据")

        timexer_data_preview = gr.Markdown(label="预览数据")

        def load_csv_for_timexer(path):
            if not os.path.exists(path):
                return "路径不存在，请检查！", None
            df = pd.read_csv(path)
            return df.head().to_markdown(), df

        timexer_df_state = gr.State()
        timexer_load_btn.click(fn=load_csv_for_timexer, inputs=[timexer_csv_path],
                            outputs=[timexer_data_preview, timexer_df_state])

        # ===== 参数设置区 =====
        gr.Markdown("## 模型参数设置")
        with gr.Row():
            lookback = gr.Slider(16, 128, value=64, step=8, label="LOOKBACK 序列长度")
            patch_size = gr.Slider(4, 32, value=8, step=4, label="PATCH_SIZE")
            d_model = gr.Slider(32, 256, value=128, step=32, label="d_model (Transformer hidden dim)")
        with gr.Row():
            n_heads = gr.Slider(1, 8, value=4, step=1, label="多头注意力头数")
            n_layers = gr.Slider(1, 6, value=2, step=1, label="Transformer 层数")
        with gr.Row():
            epochs = gr.Slider(1, 50, value=10, step=1, label="训练轮数 (Epochs)")
            batch_size = gr.Slider(16, 256, value=64, step=16, label="Batch Size")
            lr = gr.Slider(1e-5, 1e-2, value=1e-3, step=1e-5, label="学习率")

        # ===== 训练与可视化输出 =====
        train_timexer_btn = gr.Button("开始训练 TimeXer 模型")

        loss_img = gr.Image(label="Loss 曲线")
        acc_img = gr.Image(label="Accuracy 曲线")
        cm_img = gr.Image(label="混淆矩阵")
        metric_info = gr.Textbox(label="最终指标 (Acc / Prec / Rec)")

        def run_timexer(df, lookback, patch_size, epochs, batch_size, lr, d_model, n_heads, n_layers):
            if df is None or not isinstance(df, pd.DataFrame):
                return None, None, None, "请先加载合法的 CSV 数据"
            return train_timexer_model(df,
                                    lookback=int(lookback),
                                    patch_size=int(patch_size),
                                    epochs=int(epochs),
                                    batch_size=int(batch_size),
                                    lr=float(lr),
                                    d_model=int(d_model),
                                    n_heads=int(n_heads),
                                    n_layers=int(n_layers))

        train_timexer_btn.click(
            fn=run_timexer,
            inputs=[timexer_df_state, lookback, patch_size, epochs, batch_size, lr, d_model, n_heads, n_layers],
            outputs=[loss_img, acc_img, cm_img, metric_info]
        )
