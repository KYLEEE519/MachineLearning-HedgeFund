import pandas as pd
from Strategies.bollinger import BollingerStrategy
from fashuju.init_fashuju import get_recent_kline_data
from waibu.init_waibu import SimulatedExchange

def main():
    # 1. 读取历史数据（CSV文件），并确保时间戳转换为 datetime 类型
    df = pd.read_csv("Data/merged_kline_1year.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # 按时间排序，确保时间顺序正确
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    
    # 2. 初始化策略对象，传入历史数据和相关参数
    strategy = BollingerStrategy(
        df=df,
        initial_balance=10000,
        leverage=10,
        position_ratio=0.1,
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
        maintenance_margin_rate=0.005,  # 维持保证金率：0.5%
        min_unit=10
    )
    
    # 4. 定义数据发送机器人参数，取最近 n 个时间段的数据
    n = 20  # 例如取最近20根K线作为数据发送窗口
    
    # 从策略允许计算信号的索引开始遍历（确保有足够历史数据计算指标）
    for idx in range(strategy.bb_window, len(df)):
        # 当前时间步 t
        current_time = df.loc[idx, "timestamp"]
        
        # 数据发送机器人：获取截止到当前时间点的最近 n 条K线数据
        recent_data = get_recent_kline_data(df, current_time, n)
        # 此处 recent_data 可用于策略更复杂的计算或展示
        
        # 同步最新的余额到策略中
        strategy.update_balance(exchange.balance)
        
        # 策略生成交易信号（格式： (signal, take_profit, stop_loss, position_size)）
        signal = strategy.generate_signal(idx)
        
        # 当前K线数据，转换为字典格式传递给模拟交易所
        current_kline = df.loc[idx].to_dict()
        
        # 模拟交易所处理当前K线数据和交易信号
        exchange.process_kline(symbol="DOGE", kline=current_kline, signal=signal)
    
    # 5. 输出最终结果
    print("\n最终账户余额:", exchange.balance)
    print("剩余持仓:", exchange.positions)
    print("交易日志:")
    for log in exchange.trade_log:
        print(log)

if __name__ == "__main__":
    main()
