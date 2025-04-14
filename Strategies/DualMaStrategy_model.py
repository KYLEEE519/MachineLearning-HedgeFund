import pandas as pd
import ta
import pickle
import numpy as np


class DualMaStrategy_model:
    def __init__(self,
                 df: pd.DataFrame,
                 fast_ma: int=5,
                 slow_ma: int=10,
                 position_ratio: float=0.7,
                 tp_rate: float=0.03,
                 sl_rate: float=0.01):
        """
        参数:
          - fast_ma: 快速均线周期
          - slow_ma: 慢速均线周期
          - position_ratio: 开仓所用资金比例
          - tp_rate: 止盈比例
          - sl_rate: 止损比例
          - model_path: pkl 模型路径
          - feature_cols: 特征列名列表 (必须和模型训练时一致)
        """
        self.df = df.copy()
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.position_ratio = position_ratio
        self.tp_rate = tp_rate
        self.sl_rate = sl_rate
        self.model = self._load_model()

        # 均线特征
        self.df["fast_ma"] = self.df["close"].rolling(fast_ma).mean()
        self.df["slow_ma"] = self.df["close"].rolling(slow_ma).mean()

        # RSI(3)
        self.df['rsi3'] = ta.momentum.RSIIndicator(close=self.df['close'], window=3).rsi()

        # 模型预测
        self.df["predict"] = self._generate_model_predict()

        # warmup
        self.warmup_period = max(fast_ma, slow_ma, 3)

    def _load_model(self):
        model_path = r"C:\Users\qianz\Desktop\Untitled Folder\COIN\webUI\models\xgboost_20250414_134129.pkl"
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        return model

    def _generate_model_predict(self):
        feature_cols = ["open", "high", "low", "close", "vol", "rsi3"]
        df_feat = self.df[feature_cols].fillna(method='bfill').fillna(method='ffill')
        preds = self.model.predict(df_feat)
        return preds

    def generate_signal(self, index: int, current_balance: float, leverage: float = 1.0, current_position: int = 0):
        if index < self.warmup_period:
            return (0, None, None, 0, False)

        row = self.df.iloc[index]
        prev = self.df.iloc[index - 1]

        if pd.isna(row["fast_ma"]) or pd.isna(row["slow_ma"]) or pd.isna(prev["fast_ma"]) or pd.isna(prev["slow_ma"]):
            return (0, None, None, 0, False)

        long_condition = prev["fast_ma"] <= prev["slow_ma"] and row["fast_ma"] > row["slow_ma"]
        short_condition = prev["fast_ma"] >= prev["slow_ma"] and row["fast_ma"] < row["slow_ma"]

        model_predict = row["predict"]

        if long_condition and model_predict == 1:
            direction = 1
        elif short_condition and model_predict == 0:
            direction = -1
        else:
            return (0, None, None, 0, False)

        if direction == current_position:
            return (0, None, None, 0, False)

        entry_price = row["close"]
        nominal_value = current_balance * self.position_ratio * leverage
        position_size = nominal_value / entry_price

        if direction == 1:
            take_profit = entry_price * (1 + self.tp_rate)
            stop_loss = entry_price * (1 - self.sl_rate)
        else:
            take_profit = entry_price * (1 - self.tp_rate)
            stop_loss = entry_price * (1 + self.sl_rate)

        return (direction, take_profit, stop_loss, position_size, False)
