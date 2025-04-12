import datetime
import pandas as pd
import okx.MarketData as MarketData

def fetch_kline_df(days, bar, instId, flag="0"):
    """
    获取最近 days 天的K线数据，并转换为 pandas DataFrame

    参数:
        days (int): 需要的数据天数（例如最近7天）
        bar (str): 时间粒度，如 "1m", "5m", "1H" 等（注意：1s仅支持最近3个月数据）
        instId (str): 产品ID，如 "BTC-USDT"
        flag (str): 实盘："0"，模拟盘："1"

    返回:
        df (DataFrame): 包含字段 ['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'volCcyQuote', 'confirm'] 的 DataFrame，
                        ts 已转换为 datetime 类型，其他数值型字段已转换为 float
    """
    # 实例化市场数据API对象
    marketDataAPI = MarketData.MarketAPI(flag=flag)
    
    # 当前时间和起始时间（毫秒）
    now = datetime.datetime.now()
    now_ms = int(now.timestamp() * 1000)
    start_ms = now_ms - days * 24 * 3600 * 1000
    
    all_data = []  # 用于存放所有K线数据
    pagination_ts = None  # 分页参数，初始无值表示获取最新100条数据
    
    while True:
        # 构造请求参数
        params = {
            "instId": instId,
            "bar": bar,
            "limit": "100"  # 每次最多返回100条数据
        }
        if pagination_ts is not None:
            params["after"] = pagination_ts
        
        # 调用接口获取历史K线数据
        result = marketDataAPI.get_history_candlesticks(**params)
        
        if result.get("code") != "0":
            print("Error:", result.get("msg"))
            break
        
        data = result.get("data", [])
        if not data:
            break
        
        all_data.extend(data)
        
        # 获取最旧的时间戳
        oldest_ts = int(data[-1][0])
        if oldest_ts <= start_ms:
            break
        
        # 更新分页参数，继续获取更早的数据
        pagination_ts = data[-1][0]
    
    if not all_data:
        print("未获取到数据")
        return pd.DataFrame()
    
    columns = ["ts", "o", "h", "l", "c", "vol", "volCcy", "volCcyQuote", "confirm"]
    df = pd.DataFrame(all_data, columns=columns)
    
    # 使用 pd.to_numeric 避免 int 溢出问题
    df["ts"] = pd.to_datetime(pd.to_numeric(df["ts"]), unit="ms")
    
    # 转换其他数值型字段为浮点数
    for col in ["o", "h", "l", "c", "vol", "volCcy", "volCcyQuote"]:
        df[col] = pd.to_numeric(df[col])
    
    # 过滤出最近 days 天的数据
    df = df[df["ts"] >= pd.to_datetime(start_ms, unit="ms")]
    df = df.sort_values("ts").reset_index(drop=True)
    # 重命名并只保留需要的字段
    df = df.rename(columns={
        "ts": "timestamp",
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "vol": "vol"
    })
    df = df[["timestamp", "open", "high", "low", "close", "vol"]]
    return df


