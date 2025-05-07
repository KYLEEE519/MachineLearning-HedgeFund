import pandas as pd
import torch
import numpy as np
import ta
from sklearn.preprocessing import StandardScaler
from timexer import TimeXer  # 确保导入你定义的 TimeXer 类


class DualMaStrategy_timexer:
    def __init__(self,
                 df: pd.DataFrame,
                 model_path: str = None,
                 config_path: str = None,
                 fast_ma: int = 5,
                 slow_ma: int = 10,
                 position_ratio: float = 0.7,
                 tp_rate: float = 0.03,
                 sl_rate: float = 0.01):
        self.df = df.copy()
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.position_ratio = position_ratio
        self.tp_rate = tp_rate
        self.sl_rate = sl_rate
        self.model_path = model_path or self._get_latest_model()
        self.config_path = config_path or self.model_path.replace(".pt", "_config.json")
        self.model, self.config = self._load_model_and_config()

        self.df['fast_ma'] = self.df['close'].rolling(fast_ma).mean()
        self.df['slow_ma'] = self.df['close'].rolling(slow_ma).mean()
        self.df['rsi3'] = ta.momentum.RSIIndicator(close=self.df['close'], window=3).rsi()
        self.df['predict'] = self._generate_model_predict()

        self.warmup_period = max(self.config['lookback'], fast_ma, slow_ma, 3)

    def _get_latest_model(self):
        model_dir = "models"
        candidates = [f for f in os.listdir(model_dir) if f.endswith(".pt")]
        if not candidates:
            raise FileNotFoundError("No TimeXer model found in 'models' directory.")
        return os.path.join(model_dir, sorted(candidates)[-1])

    def _load_model_and_config(self):
        with open(self.config_path, "r") as f:
            config = json.load(f)
        model = TimeXer(5, 1, config['d_model'], config['n_heads'], config['n_layers'],
                        config['lookback'], config['patch_size'], config.get("dropout", 0.2))
        model.load_state_dict(torch.load(self.model_path, map_location=torch.device("cpu")))
        model.eval()
        return model, config

    def _generate_model_predict(self):
        endogenous_cols = ["open", "high", "low", "close", "vol"]
        exogenous_cols = ["rsi3"]
        df_feat = self.df[endogenous_cols + exogenous_cols].fillna(method='bfill').fillna(method='ffill')

        X_en = torch.tensor(StandardScaler().fit_transform(df_feat[endogenous_cols]), dtype=torch.float32)
        X_ex = torch.tensor(StandardScaler().fit_transform(df_feat[exogenous_cols]), dtype=torch.float32)

        X_en_seq, X_ex_seq = [], []
        for i in range(len(self.df) - self.config['lookback']):
            X_en_seq.append(X_en[i:i + self.config['lookback']])
            X_ex_seq.append(X_ex[i:i + self.config['lookback']])

        with torch.no_grad():
            logits = self.model(torch.stack(X_en_seq), torch.stack(X_ex_seq))
            probs = torch.sigmoid(logits).cpu().numpy().flatten()
        return np.concatenate([np.full(self.config['lookback'], np.nan), (probs > 0.5).astype(int)])

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
