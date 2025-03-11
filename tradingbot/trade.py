import time
import okx.Account as Account
import okx.Trade as Trade
from bollinger import BollingerStrategy  # ✅ 直接调用策略函数
import time
import ujson  # 更快的 JSON 解析库
from okx import MarketData 
import pandas as pd
# **API 初始化**
apikey = "df95c4bf-60e4-43b7-bc11-e2685f608605"
secretkey = "3B0DBD08C69C46C4C39AEB36B46A1731"
passphrase = "Qinmeng123@"

flag = "0"  # 实盘: 0, 模拟盘: 1
accountAPI = Account.AccountAPI(apikey, secretkey, passphrase, False, flag)
tradeAPI = Trade.TradeAPI(apikey, secretkey, passphrase, False, flag)
market = MarketData.MarketAPI(api_key="", api_secret_key="", passphrase="", flag="0")

def get_latest_5m_kline(instId="DOGE-USDT-SWAP", num_bars=22):
    """
    直接请求最近 num_bars (默认22) 根 5 分钟 K 线数据，并返回 DataFrame
    """
    # market = MarketData.MarketAPI(api_key="", api_secret_key="", passphrase="", flag="0")

    try:
        params = {"instId": instId, "bar": "5m", "limit": num_bars}
        resp = market.get_candlesticks(**params)

        if resp.get("code") != "0":
            raise RuntimeError(f"❌ get_candlesticks/API 请求失败: {resp.get('msg')} (code={resp.get('code')})") 
        all_data = resp.get("data", [])
        if not all_data:
            raise RuntimeError(f"❌ get_candlesticks/API 请求失败: {resp.get('msg')} (code={resp.get('code')})") 
        columns = ["timestamp", "open", "high", "low", "close", "vol", "volCcy", "volCcyQuote", "confirm"]
        full_df = pd.DataFrame(all_data, columns=columns)
        df = full_df[["timestamp", "open", "high", "low", "close", "vol"]].copy()
        numeric_cols = ["open", "high", "low", "close", "vol"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True).dt.tz_convert(None)
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        return df

    except Exception:
        raise RuntimeError(f"❌ get_candlesticks/API 请求失败: {resp.get('msg')} (code={resp.get('code')})") 

def get_account_balance():
    """获取 USDT 可用保证金"""
    result = accountAPI.get_account_balance()
    result = ujson.loads(ujson.dumps(result))  # 更快的 JSON 解析
    if result.get("code") != "0":
        raise RuntimeError(f"❌ get_account_balance/API 请求失败: {result.get('msg')} (code={result.get('code')})")
    # **查找 USDT 可用保证金**
    usdt_avail_eq = next(
        (float(asset["availEq"]) for account in result.get("data", [])
         for asset in account.get("details", []) if asset.get("ccy") == "USDT"),
        0.0
    )
    return usdt_avail_eq

def check_get_positions():
    """检查是否有 DOGE 永续合约持仓 (无论是 long 还是 short)"""
    result = accountAPI.get_positions()
    result = ujson.loads(ujson.dumps(result))  # 解析 JSON
    if result.get("code") != "0":
        raise RuntimeError(f"❌ get_positions/API 请求失败: {result.get('msg')} (code={result.get('code')})")
    for position in result["data"]:
        if position.get("instId") == "DOGE-USDT-SWAP" and float(position.get("pos", 0)) > 0:
            return True  # **找到持仓，返回 True**

    return False  # **未找到持仓**

def execute_trade():
    """
    1. 调用 `BollingerStrategy()` 获取交易信号
    2. 如果已有持仓，不执行交易
    3. 根据信号执行交易（开多 / 开空）
    4. 该函数仅执行一次，循环逻辑在 `main()` 里
    """
    df = get_latest_5m_kline()
    print(df.tail(2))
    usdt_avail_eq = get_account_balance()  # **查询可用保证金**
    has_position = check_get_positions()  # **查询是否持仓**
    strategy = BollingerStrategy(df=df, initial_balance=usdt_avail_eq)
    signal, tpTriggerPx, slTriggerPx, size = strategy.generate_signal(len(df) - 1)
    print(signal, tpTriggerPx, slTriggerPx, size)
    # **如果已有持仓，不执行交易**
    if has_position:
        print("已有持仓，跳过交易。")
        return

    # **如果信号为 0，不交易**
    if signal == 0:
        print("无交易信号，跳过交易。")
        return

    # **计算实际交易量**
    sz = round(size / 1000, 2)  # 交易数量 / 1000，并四舍五入

    # **设置交易方向**
    side = "buy" if signal == 1 else "sell"
    posSide = "long" if signal == 1 else "short"

    print(f"执行交易 - 方向: {side}, 持仓方向: {posSide}, 交易量: {sz}")
    print(f"止盈触发价格: {tpTriggerPx}, 止损触发价格: {slTriggerPx}")

    # **第一步：设置持仓模式（开平仓模式）**
    result = accountAPI.set_position_mode(posMode="long_short_mode")
    if result.get("code") != "0":
        raise RuntimeError(f"❌ set_position_mode/API 请求失败: {result.get('msg')} (code={result.get('code')})")
    # **第二步：设置杠杆倍数（10倍）**
    result = accountAPI.set_leverage(
        instId="DOGE-USDT-SWAP",
        lever="10",
        mgnMode="cross"
    )
    if result.get("code") != "0":
        raise RuntimeError(f"❌ set_leverage/API 请求失败: {result.get('msg')} (code={result.get('code')})")
    # **第三步：市价买入 / 卖出 + 止盈止损**
    order_result = tradeAPI.place_order(
        instId="DOGE-USDT-SWAP",  # 交易对
        tdMode="cross",  # **全仓模式**
        side=side,  # **买入 or 卖出**
        posSide=posSide,  # **开多 or 开空**
        ordType="market",  # **市价单**
        sz=str(sz),  # **交易数量**
        ccy="USDT",  # **保证金币种**
        attachAlgoOrds=[  # **止盈止损**
            {
                "tpTriggerPx": str(tpTriggerPx),  # **止盈触发价格**
                "tpOrdPx": "-1",  # **市价止盈**
            },
            {
                "slTriggerPx": str(slTriggerPx),  # **止损触发价格**
                "slOrdPx": "-1",  # **市价止损**
            }
        ]
    )
    if order_result.get("code") != "0":
        raise RuntimeError(f"❌ place_order/API 请求失败: {order_result.get('msg')} (code={order_result.get('code')})")
    print(f"下单结果: {order_result}")

# **主循环**
def main():
    try:
        while True:
            execute_trade()  # **执行交易**
            time.sleep(0.4)  # **每 0.4 秒执行一次**
    except RuntimeError as e:
        print(f"🚨 交易中断: {e}")  # **API 错误，立即停止交易**
        exit(1)
    except Exception as e:
        print(f"⚠️ 未知错误: {e}")  # **捕获其他错误**
        exit(1)

# **运行交易任务**
if __name__ == "__main__":
    main()
