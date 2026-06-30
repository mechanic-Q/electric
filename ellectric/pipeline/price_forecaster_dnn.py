"""
PyTorch DNN 电价预测器（轻量 baseline）
========================================

三层 MLP，feature 对齐 LEAR 的滞后 + 日历特征。
不调参，不做超参数搜索，只作为 DNN baseline 用于对比。
"""

import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

from ellectric.config import TimeConfig

logger = logging.getLogger(__name__)


def _compute_metrics(actuals: np.ndarray, predictions: np.ndarray) -> dict:
    mae = float(mean_absolute_error(actuals, predictions))
    rmse = float(np.sqrt(mean_squared_error(actuals, predictions)))
    mask = actuals != 0
    mape = float(
        np.mean(np.abs((actuals[mask] - predictions[mask]) / actuals[mask])) * 100
    ) if mask.any() else None
    return {"mae": mae, "rmse": rmse, "mape": mape}


class _PriceMLP(nn.Module):
    """小 MLP: input -> 128 -> dropout -> 64 -> output"""
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


class DNNPriceForecaster:
    def __init__(self, input_dim: int = 30, lr: float = 1e-3, epochs: int = 50):
        self.input_dim = input_dim
        self.lr = lr
        self.epochs = epochs
        self._model: nn.Module | None = None
        self._feature_cols: list[str] | None = None
        self._scaler: StandardScaler | None = None

    def _build_model(self) -> nn.Module:
        return _PriceMLP(self.input_dim)

    def train_evaluate(self, X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> dict:
        self._feature_cols = list(X.columns)
        tscv = TimeSeriesSplit(n_splits=n_splits, gap=TimeConfig.points_per_day)

        all_preds, all_actuals = [], []

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
            X_train = X.iloc[train_idx]
            X_test = X.iloc[test_idx]
            y_train = y.iloc[train_idx]
            y_test = y.iloc[test_idx]

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)
            self._scaler = scaler

            model = self._build_model()
            opt = torch.optim.AdamW(model.parameters(), lr=self.lr)
            loss_fn = nn.MSELoss()

            X_t = torch.tensor(X_train_s, dtype=torch.float32)
            y_t = torch.tensor(y_train.values, dtype=torch.float32)
            X_v = torch.tensor(X_test_s, dtype=torch.float32)
            y_v = torch.tensor(y_test.values, dtype=torch.float32)

            model.train()
            for _ in range(self.epochs):
                opt.zero_grad()
                pred = model(X_t)
                loss = loss_fn(pred, y_t)
                loss.backward()
                opt.step()

            model.eval()
            with torch.no_grad():
                preds = model(X_v).numpy()
            all_preds.extend(preds.tolist())
            all_actuals.extend(y_test.tolist())

            fold_mae = mean_absolute_error(y_test, preds)
            logger.info(f"  Fold {fold+1}: MAE={fold_mae:.2f}, train {len(train_idx)} rows")

        preds_arr = np.array(all_preds)
        actuals_arr = np.array(all_actuals)
        metrics = _compute_metrics(actuals_arr, preds_arr)
        self._model = model

        return {"predictions": preds_arr, "actuals": actuals_arr, "metrics": metrics}

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not trained. Call train_evaluate first.")
        X_s = X[self._feature_cols].copy()
        if self._scaler is not None:
            X_s = pd.DataFrame(
                self._scaler.transform(X_s),
                columns=self._feature_cols, index=X_s.index,
            )
        self._model.eval()
        with torch.no_grad():
            return self._model(torch.tensor(X_s.values, dtype=torch.float32)).numpy()
