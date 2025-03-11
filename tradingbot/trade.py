import time
import okx.Account as Account
import okx.Trade as Trade
from Strategies.bollinger import BollingerStrategy  # ✅ 直接调用策略函数
import time
import ujson  # 更快的 JSON 解析库

# **API 初始化**
apikey = "df95c4bf-60e4-43b7-bc11-e2685f608605"
secretkey = "3B0DBD08C69C46C4C39AEB36B46A1731"
passphrase = "Qinmeng123@"

flag = "0"  # 实盘: 0, 模拟盘: 1
accountAPI = Account.AccountAPI(apikey, secretkey, passphrase, False, flag)
tradeAPI = Trade.TradeAPI(apikey, secretkey, passphrase, False, flag)

def get_account_balance():
    """获取 USDT 可用保证金"""
    result = accountAPI.get_account_balance()
    result = ujson.loads(ujson.dumps(result))  # 更快的 JSON 解析

    # **查找 USDT 可用保证金**
    usdt_avail_eq = next(
        (float(asset["availEq"]) for account in result.get("data", [])
         for asset in account.get("details", []) if asset.get("ccy") == "USDT"),
        0.0
    )
    return usdt_avail_eq

def get_positions():
    """获取 DOGE 永续合约持仓信息"""
    result = accountAPI.get_positions({"instType": "SWAP", "instId": "DOGE-USDT-SWAP"})
    result = ujson.loads(ujson.dumps(result))  # 更快的 JSON 解析

    # **查找 DOGE-USDT-SWAP 持仓信息**
    doge_position = next(
        (position for position in result.get("data", []) if position.get("instId") == "DOGE-USDT-SWAP"),
        None
    )

    return bool(doge_position)  # **返回是否持仓**
def execute_trade():
    """
    1. 调用 `BollingerStrategy()` 获取交易信号
    2. 如果已有持仓，不执行交易
    3. 根据信号执行交易（开多 / 开空）
    4. 该函数仅执行一次，循环逻辑在 `main()` 里
    """
    usdt_avail_eq = get_account_balance()  # **查询可用保证金**
    has_position = get_positions()  # **查询是否持仓**
    signal, tpTriggerPx, slTriggerPx, size = BollingerStrategy()

    # **如果已有持仓，不执行交易**
    if has_position:
        print("已有持仓，跳过交易。")
        return

    # **如果信号为 0，不交易**
    if signal == 0:
        print("无交易信号，跳过交易。")
        return

    # **计算实际交易量**
    sz = round(size / 1000, 6)  # 交易数量 / 1000，并四舍五入

    # **设置交易方向**
    side = "buy" if signal == 1 else "sell"
    posSide = "long" if signal == 1 else "short"

    print(f"执行交易 - 方向: {side}, 持仓方向: {posSide}, 交易量: {sz}")
    print(f"止盈触发价格: {tpTriggerPx}, 止损触发价格: {slTriggerPx}")

    # **第一步：设置持仓模式（开平仓模式）**
    accountAPI.set_position_mode(posMode="long_short_mode")

    # **第二步：设置杠杆倍数（10倍）**
    accountAPI.set_leverage(
        instId="DOGE-USDT-SWAP",
        lever="10",
        mgnMode="cross"
    )

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

    print(f"下单结果: {order_result}")

# **主循环**
def main():
    while True:
        execute_trade()  # **执行交易**
        time.sleep(0.3)  # **每 0.3 秒执行一次**

# **运行交易任务**
if __name__ == "__main__":
    main()
