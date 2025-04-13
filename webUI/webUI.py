import gradio as gr
import pandas as pd
import json
from okx_fetch_data import fetch_kline_df
from indicators import indicator_registry, indicator_params
import os
from datetime import datetime
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

# =====================================
# 1. 数据加载与展示
# =====================================
def show_data(days, bar, instId):
    global df_cache
    df_cache = fetch_kline_df(days=days, bar=bar, instId=instId)
    if df_cache.empty:
        return "未获取到数据，请检查参数！", ""
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 2. 单指标生成 —— 生成 JSON 参数及参数说明
# =====================================
def update_param_inputs_json(indicator_name):
    """
    根据所选指标，从 indicator_params 中取出该指标所需参数，
    生成：
      1. 默认的 JSON 字符串（例如 {"window": ""}）
      2. 参数说明的 Markdown 文本（例如：- **window** (`int`): 窗口长度，建议取5~20）
    """
    params = indicator_params.get(indicator_name, [])
    default_dict = {}
    for p in params:
        default_dict[p["name"]] = ""
    json_str = json.dumps(default_dict, indent=4)
    
    # 生成说明文档，每个参数一行
    doc_lines = []
    for p in params:
        doc_lines.append(f"- **{p['name']}** (`{p['type']}`): {p['desc']}")
    doc_text = "\n".join(doc_lines)
    
    return gr.update(value=json_str, visible=True), doc_text

# =====================================
# 3. 单指标生成 —— 解析 JSON 参数并生成指标
# =====================================
def add_indicator_json(indicator_name, column, new_col_name, param_json_str):
    global df_cache
    if df_cache is None:
        return "请先获取数据！", ""
    if indicator_name not in indicator_registry:
        return "❌ 未找到该指标，请检查输入是否正确！", ""
    try:
        param_json = json.loads(param_json_str)
    except Exception as e:
        return f"JSON 格式错误: {e}", ""
    
    func = indicator_registry[indicator_name]
    param_info = indicator_params[indicator_name]
    kwargs = {"column": column}
    for p in param_info:
        name = p["name"]
        value = param_json.get(name, "")
        if p["type"] == "int":
            kwargs[name] = int(value) if value else 0
        elif p["type"] == "float":
            kwargs[name] = float(value) if value else 0.0

    df_cache = func(df_cache, **kwargs)
    if new_col_name:
        df_cache.rename(columns={df_cache.columns[-1]: new_col_name}, inplace=True)
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 4. 批量生成特征 —— 通过 JSON 配置一次性生成多个指标特征
# =====================================
def generate_features_by_json(json_str):
    global df_cache
    if df_cache is None:
        return "请先获取数据！", ""
    try:
        feature_config = json.loads(json_str)
    except Exception as e:
        return f"JSON 格式错误：{e}", ""
    
    for indicator_name, config in feature_config.items():
        if not config.get("enable", False):
            continue
        if indicator_name not in indicator_registry:
            continue
        func = indicator_registry[indicator_name]
        param_dict = config.get("params", {})
        kwargs = {"column": "close"}  # 默认作用于 close 列
        kwargs.update(param_dict)
        
        new_col_name = indicator_name + "_" + "_".join(str(v) for v in param_dict.values())
        if new_col_name in df_cache.columns:
            continue
        df_cache = func(df_cache, **kwargs)
        df_cache.rename(columns={df_cache.columns[-1]: new_col_name}, inplace=True)
    
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 5. 生成 Target 列
# =====================================
def generate_target(target_type):
    global df_cache
    if df_cache is None:
        return "请先获取数据！", ""
    if target_type == "涨跌（1为涨，0为跌）":
        df_cache['target'] = (df_cache['close'].shift(-1) > df_cache['close']).astype(float)  # 保留 NaN
    elif target_type == "涨跌幅":
        df_cache['target'] = df_cache['close'].shift(-1) / df_cache['close'] - 1
    else:
        return "未知的 target 类型", ""
    # 最后一行不需要预测
    df_cache.loc[df_cache.index[-1], 'target'] = None
    return df_cache.head().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 6. 数据清理
# =====================================
def clean_data(clean_type):
    global df_cache
    if df_cache is None:
        return "请先获取数据！", ""
    # 替换 inf 和 -inf 为 NaN
    df_cache.replace([float('inf'), float('-inf')], pd.NA, inplace=True)
    # 强制转换（非时间列）为数字
    for col in df_cache.columns:
        if col != "timestamp":
            df_cache[col] = pd.to_numeric(df_cache[col], errors='coerce')
    original_rows = df_cache.shape[0]
    # 删除全为 NaN 的列
    na_cols = df_cache.columns[df_cache.isna().all()].tolist()
    df_cache.drop(columns=na_cols, inplace=True)
    report = f"已删除全为 NaN 的列: {na_cols}\n"
    if clean_type == "中位数填充":
        df_cache.fillna(df_cache.median(), inplace=True)
        report += "已用列的中位数填充 NaN\n"
    elif clean_type == "均值填充":
        df_cache.fillna(df_cache.mean(), inplace=True)
        report += "已用列的均值填充 NaN\n"
    elif clean_type == "删除含NaN的行":
        df_cache.dropna(inplace=True)
        df_cache.reset_index(drop=True, inplace=True)
        report += "已删除包含 NaN 的行\n"
    else:
        report += "未知的清理类型\n"
    new_rows = df_cache.shape[0]
    report += f"\n数据清理前行数: {original_rows} 行，清理后行数: {new_rows} 行"
    return report + "\n\n" + df_cache.tail().to_markdown(), ", ".join(df_cache.columns.tolist())

# =====================================
# 7. 保存数据
# =====================================
def save_data(instId):
    global df_cache
    if df_cache is None:
        return "请先获取数据！"
    
    # 确保目录存在
    save_dir = "./data"
    os.makedirs(save_dir, exist_ok=True)

    # 文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{instId}_{timestamp}.csv"
    save_path = os.path.join(save_dir, filename)

    # 保存
    df_cache.to_csv(save_path, index=False)

    # 返回绝对路径
    abs_path = os.path.abspath(save_path)

    return f"数据已保存至: {abs_path}"

def get_columns():
    global df_csv
    if df_csv is None or df_csv.empty:
        return gr.update(choices=[]), gr.update(choices=[])
    cols = df_csv.columns.tolist()
    return gr.update(choices=cols), gr.update(choices=cols)


# =====================================
# 新增函数: 加载 CSV 数据
# =====================================
df_csv = None    # 加载的 CSV 数据

def load_csv(csv_path):
    global df_csv
    if not os.path.exists(csv_path):
        return "路径不存在，请检查！", ""

    df_csv = pd.read_csv(csv_path)
    return df_csv.head().to_markdown(), ", ".join(df_csv.columns.tolist())

def validate_data(df, feature_cols, target_col):
    # 检查特征列和目标列是否存在
    for col in feature_cols:
        if col not in df.columns:
            return False, f"特征列 {col} 不存在"

    if target_col not in df.columns:
        return False, f"目标列 {target_col} 不存在"

    # 检查目标列类别数
    y = df[target_col]
    if y.nunique() <= 1:
        return False, f"目标列 {target_col} 类别数 <= 1，不满足分类或回归任务要求"

    # 检查特征列是否为数值类型
    for col in feature_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            return False, f"特征列 {col} 存在非数值类型数据"

    return True, "数据检查通过"

# 检查数据合法性函数
def check_data_validity(feature_cols, target_col):
    global df_csv
    if df_csv is None or df_csv.empty:
        return "❌ 未加载数据，请先读取 CSV 文件"

    df = df_csv

    if target_col not in df.columns:
        return f"❌ 目标列 {target_col} 不存在，请检查！"

    if not all([col in df.columns for col in feature_cols]):
        return f"❌ 部分特征列不存在，请检查！"

    if df[feature_cols].select_dtypes(include=["number"]).shape[1] != len(feature_cols):
        return "❌ 存在非数值型特征列，XGBoost 仅支持数值特征！"

    if df[target_col].nunique() < 2:
        return "❌ 目标列类别数不足，请检查！"

    if df[target_col].nunique() > 10:
        return "❌ 目标列类别数过多，请检查！"

    return "✅ 数据检查通过！"


from sklearn.metrics import accuracy_score, mean_squared_error, roc_auc_score, roc_curve, precision_score, recall_score, f1_score

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

from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import accuracy_score, mean_squared_error
import numpy as np
import json

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



# =====================================
# 8. 构建 Gradio UI
# =====================================

from timexer import train_timexer_model
from PIL import Image
import pandas as pd


with gr.Blocks() as demo:
    with gr.Tab("数据处理与特征工程"):
        gr.Markdown("# XGBoost 可视化训练工具（完整功能版）")
        
        # ----- 数据获取 -----
        with gr.Row():
            days = gr.Number(label="获取最近几天数据（days）", info="例如7表示最近7天")
            bar = gr.Textbox(label="K线粒度（bar）", info="例如1m、5m、1H、4H")
            instId = gr.Textbox(label="交易对（instId）", info="例如BTC-USDT")
        data_info = gr.Markdown()
        all_columns = gr.Markdown(label="全部列名")
        load_button = gr.Button("获取并展示数据")
        load_button.click(fn=show_data, inputs=[days, bar, instId], outputs=[data_info, all_columns])
        
        # ----- 单指标生成 -----
        with gr.Tab("单指标生成"):
            gr.Markdown("## 单指标生成")
            indicator_name = gr.Dropdown(choices=list(indicator_registry.keys()), label="选择指标")
            column = gr.Textbox(label="作用列", value="close")
            confirm_param_button = gr.Button("确认生成参数输入框")
            json_params = gr.Textbox(label="请在此输入指标参数（JSON 格式）", visible=False, lines=10)
            # Markdown 组件，用于显示参数说明（instruction）
            param_instructions = gr.Markdown(label="参数说明")
            confirm_param_button.click(
                fn=update_param_inputs_json,
                inputs=[indicator_name],
                outputs=[json_params, param_instructions]
            )
            new_col_name = gr.Textbox(label="新列名（可选）")
            add_indicator_button = gr.Button("生成指标")
            add_indicator_button.click(
                fn=add_indicator_json,
                inputs=[indicator_name, column, new_col_name, json_params],
                outputs=[data_info, all_columns]
            )
        
        # ----- 批量生成特征 -----
        with gr.Tab("批量生成指标"):
            gr.Markdown("## 编辑 JSON 自动批量生成特征")
            json_editor = gr.Code(
                label="指标配置 JSON", language="json",
                value='''{
            "RSI": {"enable": true, "params": {"window": 14}},
            "MACD": {"enable": true, "params": {"window_fast": 12, "window_slow": 26, "window_sign": 9}},
            "BOLL": {"enable": false, "params": {"window": 20, "std": 2.0}},
            "EMA": {"enable": false, "params": {"window": 14}},
            "SMA": {"enable": false, "params": {"window": 14}},
            "ATR": {"enable": false, "params": {"window": 14}},
            "CCI": {"enable": false, "params": {"window": 14}},
            "Stoch": {"enable": false, "params": {"window": 14}},
            "WILLR": {"enable": false, "params": {"window": 14}},
            "ROC": {"enable": false, "params": {"window": 14}}
            }'''
            )
            new_data_info = gr.Markdown()
            new_all_columns = gr.Markdown(label="最新全部列名")
            generate_button = gr.Button("批量生成特征")
            generate_button.click(
                fn=generate_features_by_json,
                inputs=[json_editor],
                outputs=[new_data_info, new_all_columns]
            )
        with gr.Tab("自定义指标"):
            gr.Markdown("## 自定义指标")
        # ----- 生成 Target 列 -----
        gr.Markdown("## 选择 Target 列")
        target_type = gr.Dropdown(choices=["涨跌（1为涨，0为跌）", "涨跌幅"], label="选择 Target 类型")
        target_data_info = gr.Markdown()
        target_all_columns = gr.Markdown(label="最新全部列名")
        generate_target_button = gr.Button("生成 Target 列")
        generate_target_button.click(
            fn=generate_target,
            inputs=[target_type],
            outputs=[target_data_info, target_all_columns]
        )
        
        # ----- 数据清理 -----
        gr.Markdown("## 数据清理")
        clean_type = gr.Dropdown(choices=["中位数填充", "均值填充", "删除含NaN的行"], label="选择数据清理方式")
        clean_info = gr.Markdown()
        clean_cols = gr.Markdown(label="最新全部列名")
        clean_button = gr.Button("执行数据清理")
        clean_button.click(
            fn=clean_data,
            inputs=[clean_type],
            outputs=[clean_info, clean_cols]
        )
        gr.Markdown("## 数据保存")

        save_path_info = gr.Markdown()
        save_button = gr.Button("保存数据为 CSV")

        save_button.click(
            fn=save_data,
            inputs=[instId],
            outputs=[save_path_info]
        )
    with gr.Tab("XGBoost 训练"):
        gr.Markdown("# XGBoost 可视化训练")

        csv_path = gr.Textbox(label="输入 CSV 文件绝对路径")
        load_csv_button = gr.Button("读取 CSV")

        data_info = gr.Markdown()
        all_columns = gr.Markdown(label="全部列名")

        feature_cols = gr.Dropdown(choices=[], label="选择特征列(可多选)", multiselect=True)
        target_col = gr.Dropdown(choices=[], label="选择目标列(单选)", multiselect=False)

        load_csv_button.click(fn=load_csv, inputs=[csv_path], outputs=[data_info, all_columns])
        load_csv_button.click(fn=get_columns, inputs=[], outputs=[feature_cols, target_col])
        gr.Markdown("## 数据检查")

        check_info = gr.Markdown()  # 显示检查结果
        check_button = gr.Button("检查数据合法性")

        check_button.click(
            fn=check_data_validity,
            inputs=[feature_cols, target_col],
            outputs=[check_info]
        )
        with gr.Tab("模型训练"):
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







demo.launch()
