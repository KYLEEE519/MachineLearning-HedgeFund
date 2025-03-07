# grid_search_main.py
import pandas as pd
import itertools
from Strategies.backtest_martingale import MartingaleBacktest

# 1. 定义参数网格范围
short_window_range = [5, 10, 15, 20, 25]
long_window_range = [50, 60, 80, 100, 120]
atr_tp_range = [1.5, 2, 2.5, 3]
atr_sl_range = [1, 1.5, 2]
breakout_period_range = [10, 15, 20, 30]

# 2. 生成所有有效参数组合（短期小于长期）
param_grid = list(itertools.product(
    short_window_range,
    long_window_range,
    atr_tp_range,
    atr_sl_range,
    breakout_period_range
))
param_grid = [p for p in param_grid if p[0] < p[1]]

# 3. 读取历史数据
df = pd.read_csv('historical_data.csv')  # 替换成你的数据文件

# 4. 记录所有回测结果
results = []

# 5. 遍历网格组合，逐一回测
for params in param_grid:
    short_window, long_window, atr_tp, atr_sl, breakout_period = params

    print(f"回测参数: 短期={short_window}, 长期={long_window}, TP={atr_tp}, SL={atr_sl}, 突破周期={breakout_period}")

    backtest = MartingaleBacktest(
        df=df,
        short_window=short_window,
        long_window=long_window,
        atr_tp_multiplier=atr_tp,
        atr_sl_multiplier=atr_sl,
        breakout_period=breakout_period,
        leverage_list=[5, 10, 20, 30, 50],
        position_list=[0.05, 0.11, 0.22, 0.35, 0.5]
    )

    final_balance, max_drawdown, sharpe = backtest.run()

    results.append({
        'short_window': short_window,
        'long_window': long_window,
        'atr_tp_multiplier': atr_tp,
        'atr_sl_multiplier': atr_sl,
        'breakout_period': breakout_period,
        'final_balance': final_balance,
        'max_drawdown': max_drawdown,
        'sharpe': sharpe
    })

# 6. 保存并打印结果
results_df = pd.DataFrame(results)
results_df.to_csv('grid_search_results.csv', index=False)

best_params = results_df.sort_values(by='sharpe', ascending=False).iloc[0]
print("\n最优参数组合:")
print(best_params)
