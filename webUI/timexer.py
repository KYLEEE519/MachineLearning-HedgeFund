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

class TimeXer(nn.Module):
    def __init__(self, d_en, d_ex, d_model=128, n_heads=4, n_layers=2, lookback=64, patch_size=8):
        super().__init__()
        self.lookback = lookback
        self.patch_size = patch_size
        self.patch_proj = nn.Linear(d_en, d_model)
        self.global_token = nn.Parameter(torch.randn(1, 1, d_model))
        self.exo_proj = nn.Linear(lookback, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=256, batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.cross_attn = nn.MultiheadAttention(embed_dim=d_model, num_heads=n_heads, batch_first=True)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.ReLU(),
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

def train_timexer_model(df,
                        lookback=64,
                        patch_size=8,
                        epochs=10,
                        batch_size=64,
                        lr=1e-3,
                        d_model=128,
                        n_heads=4,
                        n_layers=2,
                        pos_weight_auto=True):

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
        X_en_seq.append(X_en_scaled[i:i+lookback])
        X_ex_seq.append(X_ex_scaled[i:i+lookback])
        y_seq.append(y[i+lookback])

    X_en_seq = np.array(X_en_seq, dtype=np.float32)
    X_ex_seq = np.array(X_ex_seq, dtype=np.float32)
    y_seq = np.array(y_seq, dtype=np.float32).reshape(-1, 1)

    split_idx = int(0.8 * len(y_seq))
    X_en_train, X_en_test = X_en_seq[:split_idx], X_en_seq[split_idx:]
    X_ex_train, X_ex_test = X_ex_seq[:split_idx], X_ex_seq[split_idx:]
    y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]

    train_ds = TensorDataset(torch.tensor(X_en_train), torch.tensor(X_ex_train), torch.tensor(y_train))
    test_ds = TensorDataset(torch.tensor(X_en_test), torch.tensor(X_ex_test), torch.tensor(y_test))

    pos_count = (y_train.flatten() == 1).sum()
    neg_count = (y_train.flatten() == 0).sum()
    pos_weight_value = neg_count / pos_count if pos_weight_auto and pos_count > 0 else 1.0
    weights = np.array([1/pos_count if y == 1 else 1/neg_count for y in y_train.flatten()], dtype=np.float32)
    sampler = WeightedRandomSampler(torch.tensor(weights), num_samples=len(weights), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler)
    test_loader = DataLoader(test_ds, batch_size=batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TimeXer(X_en_train.shape[2], X_ex_train.shape[2], d_model, n_heads, n_layers, lookback, patch_size).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight_value], device=device))
    optimizer = optim.AdamW(model.parameters(), lr=lr)

    loss_curve = []
    acc_curve = []

    for epoch in range(epochs):
        model.train()
        losses = []
        for x_en, x_ex, labels in train_loader:
            x_en, x_ex, labels = x_en.to(device), x_ex.to(device), labels.to(device)
            optimizer.zero_grad()
            logits = model(x_en, x_ex)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        loss_curve.append(np.mean(losses))

        model.eval()
        preds, trues = [], []
        with torch.no_grad():
            for x_en, x_ex, labels in test_loader:
                logits = model(x_en.to(device), x_ex.to(device))
                probs = torch.sigmoid(logits).cpu().numpy().flatten()
                preds.extend((probs > 0.5).astype(int))
                trues.extend(labels.numpy().flatten())
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
    ax_loss.plot(loss_curve, label="Loss")
    ax_loss.set_title("Loss Curve")
    ax_loss.set_xlabel("Epoch")
    ax_loss.set_ylabel("Loss")
    loss_img = fig_to_image(fig_loss)
    plt.close(fig_loss)

    fig_acc, ax_acc = plt.subplots()
    ax_acc.plot(acc_curve, label="Accuracy", color='green')
    ax_acc.set_title("Accuracy over Epochs")
    ax_acc.set_xlabel("Epoch")
    ax_acc.set_ylabel("Accuracy")
    acc_img = fig_to_image(fig_acc)
    plt.close(fig_acc)

    acc = accuracy_score(trues, preds)
    prec = precision_score(trues, preds, zero_division=0)
    rec = recall_score(trues, preds, zero_division=0)

    return loss_img, acc_img, cm_img, f"Final Acc: {acc:.4f}, Prec: {prec:.4f}, Rec: {rec:.4f}"
