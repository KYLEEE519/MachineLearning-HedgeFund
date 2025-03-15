import pandas as pd

def get_recent_kline_data(df: pd.DataFrame, current_time, n: int) -> pd.DataFrame:
    """
    返回历史数据中截止到 current_time 最近 n 个时间段的数据

    参数:
      - df: 包含历史K线数据的DataFrame，必须包含'timestamp'列（已转换为datetime格式）
      - current_time: 当前时间点，可以是字符串或datetime对象
      - n: 要返回的时间段数量

    返回:
      - 最近 n 个时间段的数据（DataFrame）
    """
    # 确保 current_time 为 datetime 类型
    if isinstance(current_time, str):
        current_time = pd.to_datetime(current_time)
    
    # 过滤出截止到 current_time 的数据
    df_filtered = df[df['timestamp'] <= current_time]
    
    # 取最后 n 条记录
    recent_data = df_filtered.tail(n)
    
    return recent_data

# 示例使用：
if __name__ == "__main__":
    # 构造示例历史数据
    data = {
        'timestamp': pd.date_range(start='2025-03-12 10:35', periods=10, freq='5T'),
        'open': [0.16557, 0.16595, 0.16587, 0.16654, 0.16638, 0.17099, 0.17067, 0.17027, 0.17037, 0.16994],
        'high': [0.16601, 0.16595, 0.16667, 0.16660, 0.16674, 0.17129, 0.17071, 0.17067, 0.17043, 0.16995],
        'low':  [0.16546, 0.16539, 0.16586, 0.16616, 0.16623, 0.17062, 0.17007, 0.17017, 0.16962, 0.16989],
        'close':[0.16595, 0.16587, 0.16656, 0.16637, 0.16667, 0.17067, 0.17028, 0.17037, 0.16993, 0.16991],
        'vol':  [8204.21, 6539.07, 10941.35, 7001.35, 5116.67, 4001.12, 12703.64, 4723.44, 31827.95, 281.91]
    }
    df = pd.DataFrame(data)
    
    # 假设当前时间点 t 为数据中的第7个时间点
    current_time = df.loc[6, 'timestamp']
    
    # 取从 t- n 到 t 的数据，比如 n=5
    n = 5
    recent_k_data = get_recent_kline_data(df, current_time, n)
    
    print("当前时间点:", current_time)
    print("从t-n到t的数据：")
    print(recent_k_data)
