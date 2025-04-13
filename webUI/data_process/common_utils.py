import pandas as pd
import gradio as gr

def get_columns():
    global df_csv
    if df_csv is None or df_csv.empty:
        return gr.update(choices=[]), gr.update(choices=[])
    cols = df_csv.columns.tolist()
    return gr.update(choices=cols), gr.update(choices=cols)

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