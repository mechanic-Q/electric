"""
SHAP 模型可解释性 — TreeExplainer (XGBoost) + LinearExplainer (LEAR)
====================================================================

本模块提供三个函数:
1. explain_xgboost_sample() — XGBoost 单样本 SHAP waterfall 图
2. explain_lear_sample()    — LEAR Lasso 单样本 SHAP waterfall 图
3. feature_importance_ranking() — 跨模型特征重要性排名表

为什么需要 SHAP？
~~~~~~~~~~~~~~~~
SHAP (SHapley Additive exPlanations) 基于博弈论中的 Shapley 值，
将模型预测分解为各个特征的边际贡献。

- TreeExplainer: 适用于树模型（XGBoost），精确计算 Shapley 值
- LinearExplainer: 适用于线性模型（Lasso），利用系数直接计算

SHAP 的核心思想:
对于每个样本，SHAP 计算:
  prediction = base_value + Σ shap_value_i
其中 base_value 是模型在所有训练样本上的平均输出，
shap_value_i 是第 i 个特征对这个样本的"贡献"（可正可负）。
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def _get_shap():
    """惰性导入 shap，避免 shap 未安装时整个模块不可用。"""
    try:
        import shap
        return shap
    except ImportError:
        raise RuntimeError(
            "shap 未安装。请运行: pip install shap\n"
            "注意: feature_importance_ranking() 不需要 shap，仍可使用。"
        )


def explain_xgboost_sample(
    model: Any,
    X: pd.DataFrame,
    sample_idx: int = 0,
    max_display: int = 15,
) -> go.Figure:
    """
    XGBoost 单样本 SHAP waterfall 图。

    使用 shap.TreeExplainer 计算单个样本的 Shapley 值，
    返回 plotly 水平柱状图显示特征贡献排序。

    Args:
        model:       XGBoostForecaster 实例（_model 属性为 XGBRegressor）
        X:           特征 DataFrame（含 _feature_cols 列）
        sample_idx:  解释哪一行（默认 0）
        max_display: 最多显示的特征数（默认 15，小于 1 时使用 10）

    Returns:
        plotly Figure — 水平柱状图（特征贡献排序）

    Raises:
        RuntimeError: shap 未安装 或 模型未训练
        IndexError:   sample_idx 越界
        ValueError:   X 为空 DataFrame

    Example:
        >>> fig = explain_xgboost_sample(forecaster, X_test, sample_idx=5)
        >>> fig.show()
    """
    _validate_inputs(model, X, sample_idx)
    if model._model is None:
        raise RuntimeError("模型未训练: model._model 为 None")
    max_display = _resolve_max_display(max_display)

    X_sub = X[model._feature_cols].copy()

    try:
        shap = _get_shap()
        explainer = shap.TreeExplainer(model._model)
        shap_values = explainer.shap_values(X_sub)
    except Exception as e:
        logger.error(f"SHAP TreeExplainer 计算失败: {e}")
        raise RuntimeError(f"SHAP 计算失败: {e}") from e

    return _build_waterfall(
        shap_values=shap_values,
        feature_names=model._feature_cols,
        X_row=X_sub.iloc[sample_idx],
        sample_idx=sample_idx,
        base_value=explainer.expected_value,
        max_display=max_display,
        model_name="XGBoost",
    )


def explain_lear_sample(
    model: Any,
    X: pd.DataFrame,
    sample_idx: int = 0,
    max_display: int = 15,
) -> go.Figure:
    """
    LEAR 单样本 SHAP waterfall 图。

    使用 shap.LinearExplainer 计算单个样本的 Shapley 值，
    返回 plotly 水平柱状图显示特征贡献排序。

    Args:
        model:       LEARForecaster 实例（_model 属性为 Lasso）
        X:           特征 DataFrame（含 _feature_cols 列）
        sample_idx:  解释哪一行（默认 0）
        max_display: 最多显示的特征数（默认 15，小于 1 时使用 10）

    Returns:
        plotly Figure — 水平柱状图（特征贡献排序）

    Raises:
        RuntimeError: shap 未安装 或 模型未训练
        IndexError:   sample_idx 越界
        ValueError:   X 为空 DataFrame

    Example:
        >>> fig = explain_lear_sample(forecaster, X_test, sample_idx=3)
        >>> fig.show()
    """
    _validate_inputs(model, X, sample_idx)
    if model._model is None:
        raise RuntimeError("模型未训练: model._model 为 None")
    max_display = _resolve_max_display(max_display)

    X_sub = X[model._feature_cols].copy()

    try:
        shap = _get_shap()
        explainer = shap.LinearExplainer(model._model, X_sub)
        shap_values = explainer.shap_values(X_sub)
    except Exception as e:
        logger.error(f"SHAP LinearExplainer 计算失败: {e}")
        raise RuntimeError(f"SHAP 计算失败: {e}") from e

    return _build_waterfall(
        shap_values=shap_values,
        feature_names=model._feature_cols,
        X_row=X_sub.iloc[sample_idx],
        sample_idx=sample_idx,
        base_value=explainer.expected_value,
        max_display=max_display,
        model_name="LEAR",
    )


def feature_importance_ranking(
    models: dict[str, Any],
    feature_names: list[str],
) -> pd.DataFrame:
    """
    跨模型特征重要性排名表。

    遍历所有模型，提取特征重要性或系数绝对值，
    返回统一的 DataFrame 用于对比。

    - XGBoost: model._model.feature_importances_
    - LEAR:    model._model.coef_（取绝对值）
    - 其他模型: 尝试 model._model.feature_importances_，
               再尝试 coef_，都没有则记录 warning

    Args:
        models:        {"XGBoost": xgb_forecaster, "LEAR": lear_forecaster}
        feature_names: 所有特征名列表（必须与模型的特征列顺序一致）

    Returns:
        DataFrame[model, feature, importance] — 按 importance 降序排列

    Raises:
        RuntimeError: 存在未训练的模型

    Example:
        >>> ranking = feature_importance_ranking(
        ...     {"XGBoost": xgb, "LEAR": lear},
        ...     ["hour", "lag_24h", ...]
        ... )
        >>> ranking.head()
    """
    rows = []

    for name, forecaster in models.items():
        if forecaster._model is None:
            raise RuntimeError(f"模型 '{name}' 未训练: _model 为 None")

        internal = forecaster._model
        if hasattr(internal, "feature_importances_") and internal.feature_importances_ is not None:
            importances = internal.feature_importances_
        elif hasattr(internal, "coef_") and internal.coef_ is not None:
            importances = np.abs(internal.coef_)
        else:
            logger.warning(f"模型 '{name}' 不支持特征重要性提取（无 feature_importances_ 或 coef_）")
            continue

        n_feat = min(len(importances), len(feature_names))
        for i in range(n_feat):
            rows.append({
                "model": name,
                "feature": feature_names[i],
                "importance": float(importances[i]),
            })

        if n_feat < len(feature_names):
            logger.warning(
                f"模型 '{name}' 有 {len(importances)} 个重要性值，"
                f"但提供了 {len(feature_names)} 个特征名"
            )

    df = pd.DataFrame(rows, columns=["model", "feature", "importance"])
    df = df.sort_values("importance", ascending=False).reset_index(drop=True)
    logger.info(f"特征重要性排名: {df['model'].nunique()} 个模型, {len(df)} 行")
    return df


# ════════════════════════════════════════════════════════════════
# 内部辅助函数
# ════════════════════════════════════════════════════════════════


def _validate_inputs(model: Any, X: pd.DataFrame, sample_idx: int) -> None:
    """统一校验：检查 X 是否为空、sample_idx 是否越界。"""
    if X.empty:
        raise ValueError("X is empty")
    if sample_idx < 0 or sample_idx >= len(X):
        raise IndexError(
            f"sample_idx {sample_idx} 超出范围 [0, {len(X) - 1}]"
        )
    # 检查特征列是否存在
    feature_cols = getattr(model, "_feature_cols", None)
    if feature_cols is None:
        raise RuntimeError("模型缺少 _feature_cols 属性，请先训练模型")
    missing = [c for c in feature_cols if c not in X.columns]
    if missing:
        raise ValueError(
            f"X 中缺少特征列: {missing}。请确保输入数据包含所有训练时使用的特征列。"
        )


def _resolve_max_display(max_display: int) -> int:
    """如果 max_display < 1 则返回默认值 10。"""
    return max_display if max_display >= 1 else 10


def _build_waterfall(
    shap_values: np.ndarray,
    feature_names: list[str],
    X_row: pd.Series,
    sample_idx: int,
    base_value: float,
    max_display: int,
    model_name: str,
) -> go.Figure:
    """
    构建 SHAP waterfall 水平柱状图。

    从 shap_values 中提取指定样本行，按 |SHAP 值| 排序，
    取 top max_display 个特征，用蓝/红柱表示正/负贡献。
    """
    sv = shap_values[sample_idx]
    fv = X_row.values
    names = list(feature_names)

    # 按 |SHAP 值| 降序排列
    sorted_idx = np.argsort(np.abs(sv))[::-1][:max_display]
    top_names = [names[i] for i in sorted_idx]
    top_shap = [float(sv[i]) for i in sorted_idx]
    top_feat_vals = [float(fv[i]) for i in sorted_idx]

    colors = ["#1f77b4" if s >= 0 else "#d62728" for s in top_shap]

    pred_value = float(base_value + sv.sum())
    pred_label = f"预测值: {pred_value:.3f}"

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=top_shap,
            y=top_names,
            orientation="h",
            marker_color=colors,
            text=[f"{s:+.4f}  (val={v:.2f})" for s, v in zip(top_shap, top_feat_vals)],
            textposition="outside",
            name="SHAP 值",
        )
    )

    fig.update_layout(
        title=dict(
            text=(
                f"{model_name} SHAP Waterfall — 样本 #{sample_idx}<br>"
                f"<sup>base={base_value:.3f}, {pred_label}</sup>"
            ),
            font=dict(size=16),
        ),
        xaxis=dict(title="SHAP 值 (特征对预测的贡献)"),
        yaxis=dict(title="特征", autorange="reversed"),
        height=min(100 + 30 * max_display, 800),
        margin=dict(l=120, r=40, t=80, b=40),
        hovermode="y unified",
        showlegend=False,
    )

    # 在 x=0 处添加一条参考线
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="gray")

    return fig
