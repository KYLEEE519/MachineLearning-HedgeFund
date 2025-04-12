from Data.okx_fetch_data import fetch_kline_df
from waibu.init_waibu import SimulatedExchange
from fashuju.init_fashuju import get_recent_kline_data

def get_current_position(exchange, symbol):
    if symbol in exchange.positions and len(exchange.positions[symbol]) > 0:
        return exchange.positions[symbol][0]['direction']
    return 0

def run_backtest(
    strategy_class,
    strategy_kwargs,
    instId,
    days,
    bar,
    use_strategy_exit,
    exchange_kwargs,
    verbose=False
):
    df = fetch_kline_df(days=days, bar=bar, instId=instId)
    if df.empty:
        print("K线数据为空")
        return

    strategy = strategy_class(df=df, **strategy_kwargs)

    exchange = SimulatedExchange(**exchange_kwargs)

    for i in range(strategy.warmup_period, len(df)):
        kline = df.iloc[i]

        if use_strategy_exit:
            current_pos = get_current_position(exchange, instId)
            raw_signal = strategy.generate_signal(
                index=i,
                current_balance=exchange.balance,
                leverage=exchange.leverage,
                current_position=current_pos
            )
            exchange.process_closing(instId, kline, raw_signal)

            updated_pos = get_current_position(exchange, instId)
            new_signal = strategy.generate_signal(
                index=i,
                current_balance=exchange.balance,
                leverage=exchange.leverage,
                current_position=updated_pos
            )
            exchange.process_opening(instId, kline, new_signal)

        else:
            signal = strategy.generate_signal(
                index=i,
                current_balance=exchange.balance,
                leverage=exchange.leverage,
                current_position=get_current_position(exchange, instId)
            )
            signal = signal[:4] + (False,)
            exchange.process_closing(instId, kline, signal)
            exchange.process_opening(instId, kline, signal)

    final_price = df.iloc[-1]["close"]
    total_balance, roi, total_trades = exchange.calculate_total_balance_and_roi(final_price)

    print("\n--- 回测结果汇总 ---")
    print("最终账户余额:", exchange.balance)
    print("剩余持仓:", exchange.positions)
    print(f"总余额: {total_balance:.2f}")
    print(f"ROI: {roi:.2f}%")
    print(f"总交易次数: {total_trades} 笔")
