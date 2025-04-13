import numpy as np
import pandas as pd
import json
from sklearn.model_selection import RandomizedSearchCV
import xgboost as xgb

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

    # 数据检查
    if target_col not in df.columns:
        return "目标列不存在，请检查！"
    if not all([col in df.columns for col in feature_cols]):
        return "部分特征列不存在，请检查！"
    if df[feature_cols].select_dtypes(include=["number"]).shape[1] != len(feature_cols):
        return "存在非数值型特征列，XGBoost 仅支持数值特征！"
    if df[target_col].nunique() < 2:
        return "目标列类别数不足，请检查！"

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