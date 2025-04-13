import pandas as pd
from .data_loader import df_cache

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
