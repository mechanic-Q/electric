"""
风/光功率独立预测模块
=====================

WindPowerForecaster / SolarPowerForecaster 复用 Tier1-4 特征
和 XGBoost 做新能源出力预测，指标包含 MAE/RMSE/nRMSE。

weather 不可用时降级到 Tier1-3。
"""

import logging
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np
import pandas as pd
import xgboost as xgb

from ellectric.config import TimeConfig

logger = logging.getLogger(__name__)


def _compute_metrics(actuals: np.ndarray, predictions: np.ndarray) -> dict:
    mae = float(mean_absolute_error(actuals, predictions))
    rmse = float(np.sqrt(mean_squared_error(actuals, predictions)))
    denom = float(np.max(actuals) - np.min(actuals))
    nrmse = rmse / denom if denom > 1e-6 else None
    return {"mae": mae, "rmse": rmse, "nrmse": nrmse}


class BaseRenewableForecaster:
    def __init__(self, target_col: str, baseline_col: str | None = None):
        self.target_col = target_col
        self.baseline_col = baseline_col
        self._model = None
        self._feature_cols = None
        self._scaler = None

    def train_evaluate(
        self, X: pd.DataFrame, y: pd.Series, n_splits: int = 5
    ) -> dict:
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

            model = xgb.XGBRegressor(
                n_estimators=100, max_depth=6, learning_rate=0.1,
                subsample=0.8, colsample_bytree=0.8, random_state=42,
                objective="reg:squarederror",
            )
            model.fit(X_train_s, y_train)
            y_pred = model.predict(X_test_s)
            all_preds.extend(y_pred.tolist())
            all_actuals.extend(y_test.tolist())

            fold_mae = mean_absolute_error(y_test, y_pred)
            logger.info(
                f"  Fold {fold+1}: MAE={fold_mae:.0f}, "
                f"train {len(train_idx)} rows → test {len(test_idx)} rows"
            )

        preds_arr = np.array(all_preds)
        actuals_arr = np.array(all_actuals)
        metrics = _compute_metrics(actuals_arr, preds_arr)
        self._model = model

        result = {
            "predictions": preds_arr,
            "actuals": actuals_arr,
            "metrics": metrics,
            "model": model,
        }
        if self.baseline_col is not None:
            baseline_preds = y.values[-len(preds_arr):] if len(y) >= len(preds_arr) else y.values
            if len(baseline_preds) > len(preds_arr):
                baseline_preds = baseline_preds[-len(preds_arr):]
            result["baseline_metrics"] = _compute_metrics(actuals_arr, baseline_preds)

        logger.info(
            f"{self.__class__.__name__} 训练完成: MAE={metrics['mae']:.0f}, "
            f"nRMSE={metrics['nrmse']:.4f}" if metrics['nrmse'] is not None
            else f"{self.__class__.__name__} 训练完成: MAE={metrics['mae']:.0f}"
        )
        return result

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("模型尚未训练。请先调用 train_evaluate()。")
        X_scaled = X[self._feature_cols].copy()
        if self._scaler is not None:
            X_scaled = pd.DataFrame(
                self._scaler.transform(X_scaled),
                columns=self._feature_cols, index=X_scaled.index,
            )
        return self._model.predict(X_scaled)


class WindPowerForecaster(BaseRenewableForecaster):
    def __init__(self):
        super().__init__(target_col="wind_actual_mw", baseline_col="wind_forecast_mw")


class SolarPowerForecaster(BaseRenewableForecaster):
    def __init__(self):
        super().__init__(target_col="solar_actual_mw", baseline_col="solar_forecast_mw")
