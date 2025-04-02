from Data.okx_fetch_data import fetch_kline_df
from Strategies.BTC_DOGE import SpreadArbitrageStrategy
import pandas as pd
from waibu.init_waibu_multi import SimulatedExchange


def main():
    days = 40
    bar = "15m"
    btc_df = fetch_kline_df(days=days, bar=bar, instId="BTC-USDT", flag="0") 
    doge_df = fetch_kline_df(days=days, bar=bar, instId="DOGE-USDT", flag="0") 

    strategy = SpreadArbitrageStrategy(doge_df, btc_df, position_ratio=0.1)

    exchange = SimulatedExchange(
        initial_balance=10000,
        open_fee_rate=0.0002,
        close_fee_rate=0.0002,
        leverage=1,  # ⚠️ 默认值仍需要设定，但每笔可覆盖
        position_ratio=0.1,
        maintenance_margin_rate=0.005,
        min_unit=0.01,
        allow_multiple_positions=False
    )

    in_position = False
    for i in range(len(strategy.df)):
        row = strategy.df.loc[i]
        timestamp = row['timestamp']

        doge_kline = {
            'timestamp': timestamp,
            'open': row['doge_open'],
            'high': row['doge_high'],
            'low': row['doge_low'],
            'close': row['doge_close']
        }
        btc_kline = {
            'timestamp': timestamp,
            'open': row['btc_open'],
            'high': row['btc_high'],
            'low': row['btc_low'],
            'close': row['btc_close']
        }

        # 🧠 第一次信号（用于平仓）
        doge_sig, btc_sig = strategy.generate_signal(i, exchange.balance, in_position)

        if len(doge_sig) == 6 and doge_sig[4]:  # exit_flag
            exchange.process_closing("DOGEUSDT", doge_kline, doge_sig)
        if len(btc_sig) == 6 and btc_sig[4]:
            exchange.process_closing("BTCUSDT", btc_kline, btc_sig)

        # 更新 in_position
        in_position = (
            'DOGEUSDT' in exchange.positions and len(exchange.positions['DOGEUSDT']) > 0 and
            'BTCUSDT' in exchange.positions and len(exchange.positions['BTCUSDT']) > 0
        )

        # 第二次信号（用于重新开仓）
        doge_sig, btc_sig = strategy.generate_signal(i, exchange.balance, in_position)

        # 开仓
        if doge_sig[0] != 0 and len(doge_sig) == 6:
            exchange.process_opening("DOGEUSDT", doge_kline, doge_sig)
        if btc_sig[0] != 0 and len(btc_sig) == 6:
            exchange.process_opening("BTCUSDT", btc_kline, btc_sig)

        # 再次更新持仓状态
        in_position = (
            'DOGEUSDT' in exchange.positions and len(exchange.positions['DOGEUSDT']) > 0 and
            'BTCUSDT' in exchange.positions and len(exchange.positions['BTCUSDT']) > 0
        )

    # === 最后计算总资产 ===
    symbol_prices = {
        'DOGEUSDT': strategy.df.iloc[-1]['doge_close'],
        'BTCUSDT': strategy.df.iloc[-1]['btc_close']
    }
    total_balance, roi, total_trades = exchange.calculate_total_balance_and_roi(symbol_prices)

    print("\n--- 回测结果 ---")
    print(f"账户余额: {exchange.balance:.2f}")
    print(f"总余额: {total_balance:.2f}")
    print(f"ROI: {roi:.2f}%")
    print(f"交易次数: {total_trades}")


if __name__ == "__main__":
    main()
