from Strategies.ma20_strategy import Ma20Strategy
from waibu.core_backtester import run_backtest
from Strategies.DualMaStrategy import DualMaStrategy
# ===== 策略配置 =====
# strategy_class = Ma20Strategy
# strategy_kwargs = {
#     "ma_length": 20,
#     "position_ratio": 0.5
# }
strategy_class = DualMaStrategy
strategy_kwargs = {
    "fast_ma": 5,
    "slow_ma": 30,
    "position_ratio": 0.7,
    "tp_rate": 0.03,
    "sl_rate": 0.015
}
# ===== 交易系统配置 =====
exchange_kwargs = {
    "initial_balance": 10000,
    "open_fee_rate": 0.0001,
    "close_fee_rate": 0.0001,
    "leverage": 1.0,
    "position_ratio": 0.1,
    "maintenance_margin_rate": 0.005,
    "min_unit": 10,
    "allow_multiple_positions": False
}

# ===== 执行回测 =====
run_backtest(
    strategy_class=strategy_class,
    strategy_kwargs=strategy_kwargs,
    instId="BTC-USDT",
    days=10,
    bar="5m",
    use_strategy_exit=False,
    exchange_kwargs=exchange_kwargs,  # ✅ 传入交易所参数
    verbose=True
)