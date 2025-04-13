from .data_loader import df_cache

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
