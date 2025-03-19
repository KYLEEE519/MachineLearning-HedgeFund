import time
import subprocess
import ujson  # 更快的 JSON 解析库
import pandas as pd
import okx.Account as Account
import okx.Trade as Trade
from Strategies.bollinger import BollingerStrategy  # 直接调用策略函数
from okx import MarketData 

# 接收用户输入
apikey = input("请输入 API Key: ").strip()
secretkey = input("请输入 Secret Key: ").strip()
passphrase = input("请输入 Passphrase: ").strip()
instId = input("请输入币种 (例如 DOGE-USDT-SWAP): ").strip()

# 标记：实盘: 0, 模拟盘: 1
flag = "0"  
accountAPI = Account.AccountAPI(apikey, secretkey, passphrase, False, flag)
tradeAPI = Trade.TradeAPI(apikey, secretkey, passphrase, False, flag)
market = MarketData.MarketAPI(api_key="", api_secret_key="", passphrase="", flag="0")

def get_latest_5m_kline(instId=instId, num_bars=22):
    """
    请求最近 num_bars (默认22) 根 5 分钟 K 线数据，并返回 DataFrame
    """
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

    except Exception as e:
        raise RuntimeError(f"❌ get_candlesticks/API 请求失败: {e}")

def get_account_balance():
    """获取 USDT 可用保证金"""
    result = accountAPI.get_account_balance()
    result = ujson.loads(ujson.dumps(result))  # 更快的 JSON 解析
    if result.get("code") != "0":
        raise RuntimeError(f"❌ get_account_balance/API 请求失败: {result.get('msg')} (code={result.get('code')})")
    # 查找 USDT 可用保证金
    usdt_avail_eq = next(
        (float(asset["availEq"]) for account in result.get("data", [])
         for asset in account.get("details", []) if asset.get("ccy") == "USDT"),
        0.0
    )
    return usdt_avail_eq

def check_get_positions():
    """检查是否有指定币种的永续合约持仓 (无论是 long 还是 short)"""
    result = accountAPI.get_positions()
    result = ujson.loads(ujson.dumps(result))  # 解析 JSON
    if result.get("code") != "0":
        raise RuntimeError(f"❌ get_positions/API 请求失败: {result.get('msg')} (code={result.get('code')})")
    for position in result["data"]:
        if position.get("instId") == instId and float(position.get("pos", 0)) > 0:
            return True  # 找到持仓，返回 True
    return False  # 未找到持仓

def execute_trade():
    """
    1. 调用 BollingerStrategy 获取交易信号；
    2. 如果已有持仓，不执行交易；
    3. 根据信号执行交易（开多 / 开空）。
       该函数仅执行一次，循环逻辑在 main_trade_loop() 中
    """
    usdt_avail_eq = get_account_balance()  # 查询可用保证金
    has_position = check_get_positions()  # 查询是否持仓
    df = get_latest_5m_kline()
    print("最近几根K线数据：")
    print(df.tail(2))
    strategy = BollingerStrategy(df=df, initial_balance=usdt_avail_eq)
    signal, tpTriggerPx, slTriggerPx, size = strategy.generate_signal(len(df) - 1)
    print(f"信号: {signal}, 止盈触发价格: {tpTriggerPx}, 止损触发价格: {slTriggerPx}, 预计算量: {size}")
    
    # 如果已有持仓或无交易信号，则跳过交易
    if has_position:
        print("已有持仓，跳过交易。")
        return
    if signal == 0:
        print("无交易信号，跳过交易。")
        return

    sz = round(size / 1000, 2)  # 实际交易数量（转换并四舍五入）
    side = "buy" if signal == 1 else "sell"
    posSide = "long" if signal == 1 else "short"

    print(f"执行交易 - 方向: {side}, 持仓方向: {posSide}, 交易量: {sz}")
    print(f"止盈触发价格: {tpTriggerPx}, 止损触发价格: {slTriggerPx}")

    # 设置持仓模式
    result = accountAPI.set_position_mode(posMode="long_short_mode")
    if result.get("code") != "0":
        raise RuntimeError(f"❌ set_position_mode/API 请求失败: {result.get('msg')} (code={result.get('code')})")
    # 设置杠杆倍数（10倍）
    result = accountAPI.set_leverage(
        instId=instId,
        lever="10",
        mgnMode="cross"
    )
    if result.get("code") != "0":
        raise RuntimeError(f"❌ set_leverage/API 请求失败: {result.get('msg')} (code={result.get('code')})")
    # 市价单下单 + 止盈止损
    order_result = tradeAPI.place_order(
        instId=instId,  # 交易对
        tdMode="cross",  # 全仓模式
        side=side,       # 买入或卖出
        posSide=posSide, # 开多或开空
        ordType="market",  # 市价单
        sz=str(sz),        # 交易数量
        ccy="USDT",        # 保证金币种
        attachAlgoOrds=[   # 止盈止损
            {
                "tpTriggerPx": str(tpTriggerPx),
                "tpOrdPx": str(tpTriggerPx),
                "tpOrdKind": "limit",
                "tpTriggerPxType": "last"
            },
            {
                "slTriggerPx": str(slTriggerPx),
                "slOrdPx": str(slTriggerPx),
                "slOrdKind": "limit",
                "slTriggerPxType": "last"
            }
        ]
    )
    if order_result.get("code") != "0":
        raise RuntimeError(f"❌ place_order/API 请求失败: {order_result.get('msg')} (code={order_result.get('code')})")
    print(f"下单结果: {order_result}")

def main_trade_loop():
    """
    交易主循环，每 0.4 秒执行一次交易任务
    """
    while True:
        execute_trade()
        time.sleep(0.4)

if __name__ == "__main__":
    max_restarts = 50  # 设置最大重启次数
    restart_count = 0

    while restart_count < max_restarts:
        try:
            print("🚀 启动交易任务...")
            main_trade_loop()
        except RuntimeError as e:
            restart_count += 1
            print(f"🚨 交易任务异常中断: {e}")
            print(f"⚠️ 正在尝试第 {restart_count} 次重启...")
            time.sleep(1)
        except Exception as e:
            restart_count += 1
            print(f"⚠️ 未知错误: {e}")
            print(f"⚠️ 正在尝试第 {restart_count} 次重启...")
            time.sleep(1)

    print("❌ 交易任务多次失败，停止自动重启！")
