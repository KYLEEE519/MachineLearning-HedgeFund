import pandas as pd
# 注意：请确保你在 BollingerStrategy 的文件中，已经把资金相关的参数/属性迁移到外部
# 下面 import 的 BollingerStrategy 即为改造后的版本
from Strategies.bollinger import BollingerStrategy  
from fashuju.init_fashuju import get_recent_kline_data
from waibu.init_waibu import SimulatedExchange

def main():
    # 1. 读取历史数据（CSV 文件），并确保时间戳转换为 datetime 类型
    df = pd.read_csv("Data/merged_kline_1year.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # 按时间排序，确保时间顺序正确
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    
    # 2. 初始化策略对象
    #   去掉了 initial_balance, leverage, position_ratio 等资金相关参数
    strategy = BollingerStrategy(
        df=df,
        open_fee_rate=0.0005,
        close_fee_rate=0.0005,
        take_profit_ratio=0.01,
        stop_loss_ratio=0.01,
        bb_window=20,
        bb_std_mult=3
    )
    
    # 3. 初始化模拟交易所对象
    exchange = SimulatedExchange(
        initial_balance=10000,
        fee_rate=0.001,
        leverage=10,
        position_ratio=0.1,
        maintenance_margin_rate=0.005,
        min_unit=10,
        allow_multiple_positions=False
    )

    
    # 4. 发数据机器人参数，取最近 n 个时间段的数据
    n = 20  # 例如取最近20根K线作为数据发送窗口
    
    # 从能够计算布林带开始（bb_window）遍历
    for idx in range(strategy.bb_window, len(df)):
        # 当前时间
        current_time = df.loc[idx, "timestamp"]
        
        # （可选）数据发送机器人：获取截止到当前时间点的最近 n 条K线数据
        recent_data = get_recent_kline_data(df, current_time, n)
        # 如果需要在策略里用 recent_data 做更多逻辑，可以在这里处理
        
        # 5. 生成交易信号：
        #   这里把“当前余额/杠杆/仓位比例” 作为参数传给策略
        signal = strategy.generate_signal(
            index=idx,
            current_balance=exchange.balance,
            leverage=exchange.leverage,
            position_ratio=exchange.position_ratio
        )
        
        # 当前K线数据，转换为字典格式传递给模拟交易所
        current_kline = df.loc[idx].to_dict()
        
        # 6. 模拟交易所处理当前K线数据和交易信号
        exchange.process_kline(symbol="DOGE", kline=current_kline, signal=signal)
    
    # 7. 输出最终结果
    print("\n--- 回测结果汇总 ---")
    print("最终账户余额:", exchange.balance)
    print("剩余持仓:", exchange.positions)
    print("交易日志:")
    for log in exchange.trade_log:
        print(log)

if __name__ == "__main__":
    main()
