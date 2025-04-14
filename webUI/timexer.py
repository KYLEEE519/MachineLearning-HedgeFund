import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader, WeightedRandomSampler
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix
import matplotlib.pyplot as plt
import io
from PIL import Image
import json
import os
import random
from datetime import datetime

class TimeXer(nn.Module):
    def __init__(self, d_en, d_ex, d_model=128, n_heads=4, n_layers=2, lookback=64, patch_size=8, dropout=0.2):
        super().__init__()
        self.lookback = lookback
        self.patch_size = patch_size
        self.patch_proj = nn.Sequential(
            nn.Linear(d_en, d_model),
            nn.Dropout(dropout)
        )
        self.global_token = nn.Parameter(torch.randn(1, 1, d_model))
        self.exo_proj = nn.Linear(lookback, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=256,
            batch_first=True, dropout=dropout, norm_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.cross_attn = nn.MultiheadAttention(embed_dim=d_model, num_heads=n_heads, batch_first=True, dropout=dropout)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

    def forward(self, x_en, x_ex):
        B = x_en.size(0)
        num_patches = self.lookback // self.patch_size
        x_en = x_en[:, :num_patches * self.patch_size, :].view(B, num_patches, self.patch_size, -1).mean(dim=2)
        x_en = self.patch_proj(x_en)
        g = self.global_token.expand(B, -1, -1)
        x_with_g = torch.cat([x_en, g], dim=1)
        x_encoded = self.encoder(x_with_g)
        x_ex = x_ex.permute(0, 2, 1)
        v_tokens = self.exo_proj(x_ex)
        g_token = x_encoded[:, -1:, :]
        g_updated, _ = self.cross_attn(g_token, v_tokens, v_tokens)
        logits = self.classifier(g_updated.squeeze(1))
        return logits


def fig_to_image(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    return Image.open(buf)


def focal_loss(logits, targets, alpha=0.25, gamma=2.0):
    BCE_loss = nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction='none')
    probs = torch.sigmoid(logits)
    pt = torch.where(targets == 1, probs, 1 - probs)
    loss = alpha * (1 - pt) ** gamma * BCE_loss
    return loss.mean()


def train_timexer_model(df, lookback=64, patch_size=8, epochs=10, batch_size=64, lr=1e-3,
                        d_model=128, n_heads=4, n_layers=2, dropout=0.2, pos_weight_auto=True):

    endogenous_cols = ["open", "high", "low", "close", "vol"]
    exo_cols = [col for col in df.columns if col not in endogenous_cols + ["timestamp", "target"]]
    df["target"] = df["target"].bfill()

    X_en = df[endogenous_cols].replace([np.inf, -np.inf], 0).ffill().bfill()
    X_ex = df[exo_cols].replace([np.inf, -np.inf], 0).ffill().bfill()
    y = df["target"].values

    X_en_scaled = StandardScaler().fit_transform(X_en)
    X_ex_scaled = StandardScaler().fit_transform(X_ex)

    X_en_seq, X_ex_seq, y_seq = [], [], []
    for i in range(len(df) - lookback):
        X_en_seq.append(X_en_scaled[i:i + lookback])
        X_ex_seq.append(X_ex_scaled[i:i + lookback])
        y_seq.append(y[i + lookback])

    X_en_seq = np.array(X_en_seq, dtype=np.float32)
    X_ex_seq = np.array(X_ex_seq, dtype=np.float32)
    y_seq = np.array(y_seq, dtype=np.float32).reshape(-1, 1)

    split_idx = int(0.8 * len(y_seq))
    X_en_train, X_en_test = X_en_seq[:split_idx], X_en_seq[split_idx:]
    X_ex_train, X_ex_test = X_ex_seq[:split_idx], X_ex_seq[split_idx:]
    y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]

    train_ds = TensorDataset(torch.tensor(X_en_train), torch.tensor(X_ex_train), torch.tensor(y_train))
    test_ds = TensorDataset(torch.tensor(X_en_test), torch.tensor(X_ex_test), torch.tensor(y_test))

    weights = np.ones_like(y_train.flatten(), dtype=np.float32)
    sampler = WeightedRandomSampler(torch.tensor(weights), num_samples=len(weights), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler)
    test_loader = DataLoader(test_ds, batch_size=batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TimeXer(X_en_train.shape[2], X_ex_train.shape[2], d_model, n_heads, n_layers, lookback, patch_size, dropout).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=lr)

    loss_curve, val_loss_curve = [], []
    acc_curve, val_acc_curve = [], []

    for epoch in range(epochs):
        model.train()
        losses = []
        for x_en, x_ex, labels in train_loader:
            x_en, x_ex, labels = x_en.to(device), x_ex.to(device), labels.to(device)
            optimizer.zero_grad()
            logits = model(x_en, x_ex)
            loss = focal_loss(logits, labels)
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        loss_curve.append(np.mean(losses))

        model.eval()
        val_losses, preds, trues = [], [], []
        with torch.no_grad():
            for x_en, x_ex, labels in test_loader:
                x_en, x_ex, labels = x_en.to(device), x_ex.to(device), labels.to(device)
                logits = model(x_en, x_ex)
                val_losses.append(focal_loss(logits, labels).item())
                probs = torch.sigmoid(logits).cpu().numpy().flatten()
                preds.extend((probs > 0.5).astype(int))
                trues.extend(labels.cpu().numpy().flatten())
        val_loss_curve.append(np.mean(val_losses))
        val_acc_curve.append(accuracy_score(trues, preds))
        acc_curve.append(accuracy_score(trues, preds))

    cm = confusion_matrix(trues, preds)
    fig_cm, ax_cm = plt.subplots()
    ax_cm.matshow(cm, cmap='Blues')
    for (i, j), val in np.ndenumerate(cm):
        ax_cm.text(j, i, f'{val}', ha='center', va='center')
    ax_cm.set_xlabel("Predicted")
    ax_cm.set_ylabel("Actual")
    cm_img = fig_to_image(fig_cm)
    plt.close(fig_cm)

    fig_loss, ax_loss = plt.subplots()
    ax_loss.plot(loss_curve, label="Train Loss")
    ax_loss.plot(val_loss_curve, label="Val Loss")
    ax_loss.set_title("Loss Curve")
    ax_loss.set_xlabel("Epoch")
    ax_loss.set_ylabel("Loss")
    ax_loss.legend()
    loss_img = fig_to_image(fig_loss)
    plt.close(fig_loss)

    fig_acc, ax_acc = plt.subplots()
    ax_acc.plot(acc_curve, label="Train Acc", color='green')
    ax_acc.plot(val_acc_curve, label="Val Acc", color='orange')
    ax_acc.set_title("Accuracy over Epochs")
    ax_acc.set_xlabel("Epoch")
    ax_acc.set_ylabel("Accuracy")
    ax_acc.legend()
    acc_img = fig_to_image(fig_acc)
    plt.close(fig_acc)

    acc = accuracy_score(trues, preds)
    prec = precision_score(trues, preds, zero_division=0)
    rec = recall_score(trues, preds, zero_division=0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = f"timexer_{timestamp}"
    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), f"models/{model_name}.pt")
    with open(f"models/{model_name}_config.json", "w") as f:
        json.dump({"lookback": lookback, "patch_size": patch_size, "epochs": epochs,
                   "batch_size": batch_size, "lr": lr, "d_model": d_model, "dropout": dropout,
                   "n_heads": n_heads, "n_layers": n_layers}, f, indent=4)

    return loss_img, acc_img, cm_img, f"Acc: {acc:.4f}, Prec: {prec:.4f}, Rec: {rec:.4f}", f"模型已保存至: models/{model_name}.pt"


def random_search_timexer(df, param_grid, n_trials=10):
    results = []
    for _ in range(n_trials):
        params = {key: random.choice(values) for key, values in param_grid.items()}
        try:
            _, _, _, metric_str, _ = train_timexer_model(df, **params)
            acc = float(metric_str.split("Acc:")[1].split(",")[0])
        except Exception:
            acc = 0.0
        results.append((params, acc))
    results.sort(key=lambda x: x[1], reverse=True)
    best_params, best_score = results[0]
    return best_params, best_score
