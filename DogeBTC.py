import pandas as pd
import datetime
import time
from httpx import RequestError
import csv

from Data.okx_fetch_data import fetch_kline_df
from Strategies.doge_btc_spread_strategy import DogeBTCSpreadStrategy
from waibu.init_waibu import SimulatedExchange
from fashuju.init_fashuju import get_recent_kline_data

def get_current_position(exchange, symbol):
    if symbol in exchange.positions and len(exchange.positions[symbol]) > 0:
        return exchange.positions[symbol][0]['direction']
    return 0

def safe_fetch_kline(instId, days, bar, retry=3):
    for attempt in range(retry):
        try:
            df = fetch_kline_df(days=days, bar=bar, instId=instId, flag="0")
            if not df.empty:
                return df
        except RequestError as e:
            print(f"请求失败（{instId}）第 {attempt+1}/{retry} 次: {e}")
        time.sleep(2)
    return pd.DataFrame()

def main():
    days = 4
    bar = "5m"
    df_btc = safe_fetch_kline("BTC-USDT", days, bar)
    df_doge = safe_fetch_kline("DOGE-USDT", days, bar)

    if df_btc.empty or df_doge.empty:
        print("获取BTC或DOGE的K线数据为空，无法继续回测")
        return

    df = pd.merge(df_btc[['timestamp', 'close']].rename(columns={'close': 'btc_close'}),
                  df_doge[['timestamp', 'close']].rename(columns={'close': 'doge_close'}),
                  on='timestamp', how='inner')

    strategy = DogeBTCSpreadStrategy(df=df, position_ratio=0.5)

    exchange = SimulatedExchange(
        initial_balance=10000,
        open_fee_rate=0.0001,
        close_fee_rate=0.0001,
        leverage=10,
        position_ratio=0.1,
        maintenance_margin_rate=0.005,
        min_unit=10,
        allow_multiple_positions=False
    )

    btc_entry_price = None
    entry_spread = None
    signal_count = {1: 0, -1: 0}
    entry_k = None

    log_path = "trade_log.csv"
    with open(log_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'doge_price', 'btc_price', 'direction'])

        for i in range(600, len(df)):
            ts = df.iloc[i]['timestamp']
            doge_price = df.iloc[i]['doge_close']
            btc_price = df.iloc[i]['btc_close']

            doge_kline = {
                'timestamp': ts,
                'open': doge_price,
                'high': doge_price,
                'low': doge_price,
                'close': doge_price
            }
            btc_kline = {
                'timestamp': ts,
                'open': btc_price,
                'high': btc_price,
                'low': btc_price,
                'close': btc_price
            }

            pos_doge = get_current_position(exchange, symbol="DOGE-USDT")
            pos_btc = get_current_position(exchange, symbol="BTC-USDT")

            signal = strategy.generate_signal(
                index=i,
                current_balance=exchange.balance,
                leverage=exchange.leverage,
                current_position=pos_doge
            )

            doge_pos = exchange.positions.get("DOGE-USDT", [])
            btc_pos = exchange.positions.get("BTC-USDT", [])

            if doge_pos and btc_pos and entry_spread is not None:
                doge_entry = doge_pos[0]['entry_price']
                doge_dir = doge_pos[0]['direction']
                btc_entry = btc_pos[0]['entry_price']
                btc_dir = btc_pos[0]['direction']

                doge_pnl = (doge_price - doge_entry) * doge_dir * doge_pos[0]['size']
                btc_pnl = (btc_price - btc_entry) * btc_dir * btc_pos[0]['size']
                total_pnl = doge_pnl + btc_pnl

                if total_pnl > entry_k * exchange.leverage * exchange.balance * strategy.position_ratio:
                    print(f"[{ts}] 满足收益条件，执行平仓")
                    exchange.process_closing("DOGE-USDT", doge_kline, signal)
                    exchange.process_closing("BTC-USDT", btc_kline, signal)
                    entry_spread = None
                    entry_k = None
                    btc_entry_price = None

            pos_doge = get_current_position(exchange, symbol="DOGE-USDT")
            pos_btc = get_current_position(exchange, symbol="BTC-USDT")

            signal = strategy.generate_signal(
                index=i,
                current_balance=exchange.balance,
                leverage=exchange.leverage,
                current_position=pos_doge
            )

            if signal[0] == 0:
                signal_count[1] = 0
                signal_count[-1] = 0
                continue
            else:
                signal_count[signal[0]] += 1
                signal_count[-signal[0]] = 0

            if signal_count[signal[0]] < 3:
                continue

            direction, _, _, _, exit_flag = signal

            total_funds = exchange.balance * strategy.position_ratio * exchange.leverage
            doge_usd = total_funds / 2
            btc_usd = total_funds / 2

            doge_units = doge_usd / doge_price
            btc_units = btc_usd / btc_price

            if direction == 1:
                print(f"[{ts}] 多DOGE空BTC, DOGE价格: {doge_price:.5f}, BTC价格: {btc_price:.2f}")
                btc_entry_price = btc_price
                doge_ret = 0
                btc_ret = 0
                entry_spread = abs((doge_price - doge_price) / doge_price - (btc_price - btc_entry_price) / btc_entry_price)
                entry_k = entry_spread
                exchange.process_opening("DOGE-USDT", doge_kline, (1, None, None, doge_units, exit_flag))
                exchange.process_opening("BTC-USDT", btc_kline, (-1, None, None, btc_units, exit_flag))
                writer.writerow([ts, doge_price, btc_price, 'long_doge'])
            elif direction == -1:
                print(f"[{ts}] 空DOGE多BTC, DOGE价格: {doge_price:.5f}, BTC价格: {btc_price:.2f}")
                btc_entry_price = btc_price
                entry_spread = abs((doge_price - doge_price) / doge_price - (btc_price - btc_entry_price) / btc_entry_price)
                entry_k = entry_spread
                exchange.process_opening("DOGE-USDT", doge_kline, (-1, None, None, doge_units, exit_flag))
                exchange.process_opening("BTC-USDT", btc_kline, (1, None, None, btc_units, exit_flag))
                writer.writerow([ts, doge_price, btc_price, 'short_doge'])

    print("\n--- 回测结果汇总 ---")
    print("最终账户余额:", exchange.balance)
    print("剩余持仓:", exchange.positions)
    final_price = df.iloc[-1]['doge_close']
    total_balance, roi, total_trades = exchange.calculate_total_balance_and_roi(final_price)
    print(f"总余额（账户余额 + 持仓价值）: {total_balance:.5f}")
    print(f"盈亏比（ROI）: {roi:.3f}%")
    print(f"总交易次数（开仓 + 平仓）: {total_trades} 笔")

if __name__ == "__main__":
    main()
