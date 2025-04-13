import os
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn.metrics import accuracy_score, mean_squared_error, roc_auc_score, roc_curve, precision_score, recall_score, f1_score

def train_model(feature_cols, target_col,
                learning_rate, max_depth, n_estimators,
                subsample, colsample_bytree, gamma, reg_lambda, reg_alpha):
    global df_csv
    if df_csv is None or df_csv.empty:
        raise ValueError("未加载数据，请先读取 CSV 文件")

    df = df_csv

    # 检查数据合法性
    if target_col not in df.columns:
        return "", "", "", "目标列不存在，请检查！"
    if not all([col in df.columns for col in feature_cols]):
        return "", "", "", "部分特征列不存在，请检查！"
    if df[feature_cols].select_dtypes(include=["number"]).shape[1] != len(feature_cols):
        return "", "", "", "存在非数值型特征列，XGBoost 仅支持数值特征！"
    if df[target_col].nunique() < 2:
        return "", "", "", "目标列类别数不足，请检查！"

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