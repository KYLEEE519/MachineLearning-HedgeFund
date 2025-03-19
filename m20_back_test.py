import pandas as pd
import datetime

# 1) 从 OKX 接口获取数据的函数
from Data.okx_fetch_data import fetch_kline_df

# 2) 策略: Ma20Strategy
from Strategies.ma20_strategy import Ma20Strategy

# 3) 模拟交易所（带区分开/平仓手续费版本）
from waibu.init_waibu import SimulatedExchange

# 4) 发数据机器人
from fashuju.init_fashuju import get_recent_kline_data
def get_current_position(exchange, symbol):
    """ 获取当前持仓方向 """
    if symbol in exchange.positions and len(exchange.positions[symbol]) > 0:
        return exchange.positions[symbol][0]['direction']  # 获取第一个持仓方向
    return 0  # 无持仓

def main():
    # ========== A. 从OKX接口获取最近 14 天的 5分钟K线，BTC-USDT为例 ==========
    days = 7
    bar = "5m"
    instId = "BTC-USDT"
    df = fetch_kline_df(days=days, bar=bar, instId=instId, flag="0")  # "0"实盘
    if df.empty:
        print("获取K线数据为空，无法继续回测")
        return
    
    # print("获取到的K线数据最后5行:")
    # print(df.head(5))
    
    # ========== B. 初始化策略与交易所 ==========
    strategy = Ma20Strategy(df=df, ma_length=20, position_ratio=0.5)
    
    exchange = SimulatedExchange(
        initial_balance=10000,
        open_fee_rate=0.0001,   # 开仓费率
        close_fee_rate=0.0001,  # 平仓费率
        leverage=10,
        position_ratio=0.1,
        maintenance_margin_rate=0.005,
        min_unit=10,
        allow_multiple_positions=False
    )

    # 定义发数据机器人参数
    n = 20  # 例如每次获取最近20条K线
    
    # ========== C. 回测循环 ==========
    for i in range(strategy.ma_length, len(df)):
        current_kline = df.iloc[i]
        current_time = current_kline["timestamp"]
        
        # 1) 发数据机器人（可选）
        recent_data = get_recent_kline_data(df, current_time, n)
        current_position = get_current_position(exchange, symbol="BTC-USDT")
        # 2) 先生成初始信号（但不执行开仓）
        raw_signal = strategy.generate_signal(
            index=i,
            current_balance=exchange.balance,  # **当前 balance**
            leverage=exchange.leverage,
            current_position=current_position
        )
        # 3) 先处理平仓
        exchange.process_closing(symbol="BTC-USDT", kline=current_kline, signal=raw_signal)
        # 4) 重新获取持仓方向（防止平仓后持仓方向变化）
        updated_position = get_current_position(exchange, symbol="BTC-USDT")
        # 5) 重新获取新的 balance，计算新的开仓信号
        new_signal = strategy.generate_signal(
            index=i,
            current_balance=exchange.balance,  # **使用更新后的 balance**
            leverage=exchange.leverage,
            current_position=updated_position
        )

        # >>>>>>>>>>>>>>>>>>>>>> DEBUG 打印开始 <<<<<<<<<<<<<<<<<<<<<<
        # 你可以在这里把当前K线信息，以及策略返回的信号都打印出来
        # 这样就能看到每根K线策略输出了什么
        # print(f"[DEBUG] i={i}, TS={current_time}, "
        #       f"O={current_kline['open']}, H={current_kline['high']}, "
        #       f"L={current_kline['low']}, C={current_kline['close']} => signal={signal}")
        # >>>>>>>>>>>>>>>>>>>>>> DEBUG 打印结束 <<<<<<<<<<<<<<<<<<<<<<
        
        # 6) 处理开仓
        exchange.process_opening(symbol="BTC-USDT", kline=current_kline, signal=new_signal)
        # print('time',i, exchange.balance)

    # ========== D. 输出回测结果 ==========
    print("\n--- 回测结果汇总 ---")
    print("最终账户余额:", exchange.balance)
    print("剩余持仓:", exchange.positions)
    # 获取最后一根K线的收盘价
    final_price = df.iloc[-1]["close"]
    total_balance, roi, total_trades = exchange.calculate_total_balance_and_roi(final_price)
    print(f"总余额（账户余额 + 持仓价值）: {total_balance:.5f}")
    print(f"盈亏比（ROI）: {roi:.3f}%")
    print(f"总交易次数（开仓 + 平仓）: {total_trades} 笔")
    # for log in exchange.trade_log:
    #     print(log)

if __name__ == "__main__":
    main()
