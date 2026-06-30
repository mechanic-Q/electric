#!/usr/bin/env python3
"""Compare price forecasting models on Shandong data.

Usage:
    python -m ellectric.scripts.compare_price_models --dry-run
    python -m ellectric.scripts.compare_price_models --tier tier3 \\
        --start 2024-06 --end 2024-08
"""
import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Generator, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from ellectric.config import TimeConfig
from ellectric.pipeline.price_forecaster import LEARForecaster
from ellectric.pipeline.price_forecaster_dnn import DNNPriceForecaster
from ellectric.pipeline.shandong_loader import ShandongDataLoader

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Result schema
# ═══════════════════════════════════════════════════════════════


@dataclass
class ComparisonResult:
    """Canonical result container for price model comparison."""
    metadata: dict = field(default_factory=dict)
    models: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    statistical_tests: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


def create_comparison_result(metadata: dict) -> dict:
    """Return the canonical comparison result dict schema."""
    return {
        "metadata": metadata,
        "models": {},
        "metrics": {},
        "statistical_tests": {},
        "artifacts": {},
        "notes": [],
    }


# ═══════════════════════════════════════════════════════════════
# Data preparation
# ═══════════════════════════════════════════════════════════════


def _rename_for_lear(df: pd.DataFrame) -> pd.DataFrame:
    """Rename Shandong column names to LEARForecaster convention."""
    renames = {
        "da_price": "price_da",
        "wind_actual_mw": "wind_mw",
        "solar_actual_mw": "solar_mw",
    }
    existing = {k: v for k, v in renames.items() if k in df.columns}
    return df.rename(columns=existing)


def prepare_data(
    df: pd.DataFrame,
    tier: str = "tier3",
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, LEARForecaster]:
    """Build features via LEARForecaster, return X, y, feature_df, forecaster.

    Args:
        df: DataFrame with timestamp, price_da (after _rename_for_lear).
        tier: Feature tier 'tier1' | 'tier2' | 'tier3'.

    Returns:
        (X, y, df_feat, forecaster)
    """
    _validate_required_columns(df, {"timestamp", "price_da"}, "prepare_data")

    forecaster = LEARForecaster()
    df_feat = forecaster.add_price_features(df, tier)
    feature_cols = forecaster.get_feature_columns(tier)

    missing = [c for c in feature_cols if c not in df_feat.columns]
    if missing:
        raise ValueError(
            f"Feature columns missing after add_price_features: {missing}"
        )

    df_feat = df_feat.dropna(subset=feature_cols + ["price_da"]).reset_index(drop=True)

    X = df_feat[feature_cols]
    y = df_feat["price_da"]

    logger.info(
        "prepare_data(%s): X %s, y %s, date [%s, %s]",
        tier, X.shape, y.shape,
        df_feat["timestamp"].min(), df_feat["timestamp"].max(),
    )
    return X, y, df_feat, forecaster


def create_folds(
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
    gap: Optional[int] = None,
) -> Generator[tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series], None, None]:
    """Yield (X_train, X_test, y_train, y_test) per TimeSeriesSplit fold.

    Uses gap=TimeConfig.points_per_day by default to prevent look-ahead bias.
    """
    gap = int(TimeConfig.points_per_day if gap is None else gap)

    if len(X) <= n_splits + gap:
        raise ValueError(
            f"Not enough rows ({len(X)}) for {n_splits}-fold split with "
            f"gap={gap}. Need at least {n_splits + gap + 1}."
        )

    tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]
        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]
        logger.info(
            "Fold %d: train %d rows, test %d rows, gap=%d",
            fold + 1, len(X_train), len(X_test), gap,
        )
        yield X_train, X_test, y_train, y_test


def _validate_required_columns(
    df: pd.DataFrame,
    required: set,
    context: str = "",
) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"[{context}] Missing required columns: {missing}. "
            f"Available: {list(df.columns)}"
        )


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare price forecasting models on Shandong data.",
    )
    parser.add_argument(
        "--dataset",
        default="shandong",
        choices=["shandong"],
        help="Dataset to use (default: shandong)",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Start date (YYYY-MM-DD or YYYY-MM, optional)",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="End date (YYYY-MM-DD or YYYY-MM, optional)",
    )
    parser.add_argument(
        "--tier",
        default="tier3",
        choices=["tier1", "tier2", "tier3"],
        help="Feature tier (default: tier3)",
    )
    parser.add_argument(
        "--output-dir",
        default="ellectric/reports/price_comparison",
        help="Output directory for results "
             "(default: ellectric/reports/price_comparison)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load data, build features, print metadata, exit without training",
    )
    return parser.parse_args(argv)


def build_metadata(
    df: pd.DataFrame,
    df_feat: pd.DataFrame,
    X: pd.DataFrame,
    args: argparse.Namespace,
) -> dict:
    return {
        "dataset": args.dataset,
        "tier": args.tier,
        "n_splits": 5,
        "n_rows_raw": len(df),
        "n_rows_clean": len(df_feat),
        "n_features": X.shape[1],
        "n_target": 1,
        "date_range": (
            f"{df_feat['timestamp'].min()} ~ {df_feat['timestamp'].max()}"
        ),
        "args": vars(args),
    }


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(message)s",
    )
    logger.info(
        "Starting price model comparison (dataset=%s, tier=%s)",
        args.dataset, args.tier,
    )

    # ── Load data ──────────────────────────────────────────
    loader = ShandongDataLoader()
    df = loader.load_data(args.start, args.end)
    logger.info("Loaded %d rows, columns: %s", len(df), list(df.columns))

    # Rename for LEAR compat
    df = _rename_for_lear(df)

    logger.info(
        "Dataset summary: %d rows, %.1f%% price_da non-null, "
        "range [%s, %s]",
        len(df),
        100 * df["price_da"].notna().sum() / max(len(df), 1),
        df["timestamp"].min(),
        df["timestamp"].max(),
    )

    # ── Build features ─────────────────────────────────────
    X, y, df_feat, forecaster = prepare_data(df, args.tier)
    metadata = build_metadata(df, df_feat, X, args)

    logger.info(
        "Features built: %d rows x %d cols, tier=%s",
        X.shape[0], X.shape[1], args.tier,
    )
    logger.info("Feature columns: %s", list(X.columns))

    # ── Dry-run: print metadata and exit ───────────────────
    if args.dry_run:
        print("=" * 56)
        print("  Dry-Run Metadata")
        print("=" * 56)
        for k, v in metadata.items():
            if k == "args":
                continue
            print(f"  {k:<22}: {v}")
        print(f"  {'feature_cols':<22}: {list(X.columns)}")
        print(f"  {'target':<22}: price_da")
        print("=" * 56)
        logger.info("Dry-run complete. Exiting.")
        return

    # ── Setup logging to file ──────────────────────────────
    os.makedirs(args.output_dir, exist_ok=True)
    log_path = _setup_logging(args.output_dir)
    logger.info("Full comparison run starting...")

    # ── Train all models ───────────────────────────────────
    models_result = evaluate_all_models(df, tier=args.tier, n_splits=5)
    metric_summary = {name: res["metrics"] for name, res in models_result.items()}
    logger.info("Model evaluation complete. Metrics: %s", metric_summary)

    # ── DM/GW pairwise tests ───────────────────────────────
    st = run_dm_gw_pairwise(models_result, h=96, crit="MAE")
    logger.info("Statistical tests complete.")

    # ── Build result ───────────────────────────────────────
    result = create_comparison_result(metadata)
    result["models"] = {
        name: {
            "metrics": res["metrics"],
            "predictions": res["predictions"].tolist() if hasattr(res["predictions"], "tolist") else list(res["predictions"]),
            "actuals": res["actuals"].tolist() if hasattr(res["actuals"], "tolist") else list(res["actuals"]),
        }
        for name, res in models_result.items()
    }
    result["statistical_tests"] = st
    result["notes"] = ["DNN is PyTorch MLP baseline, not epftoolbox DNN"]
    logger.info("Result container built.")

    # ── Generate reports ───────────────────────────────────
    artifacts = generate_report(result, args.output_dir)
    result["artifacts"] = artifacts
    logger.info("Reports saved to %s", args.output_dir)


# ════════════════════════════════════════════════════════════════
# Task-04: 4-model unified evaluation (LEAR, DNN, persistence, weekly avg)
# ════════════════════════════════════════════════════════════════


def _finite_pairs(actuals: np.ndarray, predictions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    actuals = np.asarray(actuals, dtype=float)
    predictions = np.asarray(predictions, dtype=float)
    mask = np.isfinite(actuals) & np.isfinite(predictions)
    return actuals[mask], predictions[mask]


def compute_metrics(actuals: np.ndarray, predictions: np.ndarray) -> dict:
    actuals, predictions = _finite_pairs(actuals, predictions)
    if len(actuals) == 0:
        return {"mae": None, "rmse": None, "mape": None}
    mae = float(np.mean(np.abs(actuals - predictions)))
    rmse = float(np.sqrt(np.mean((actuals - predictions) ** 2)))
    mask = actuals != 0
    mape = float(
        np.mean(np.abs((actuals[mask] - predictions[mask]) / actuals[mask])) * 100
    ) if mask.any() else None
    return {"mae": mae, "rmse": rmse, "mape": mape}


def train_and_evaluate_lear(
    df: pd.DataFrame,
    tier: str = "tier3",
    n_splits: int = 5,
) -> dict:
    forecaster = LEARForecaster(alpha=0.01)
    df_feat = forecaster.add_price_features(df, tier)
    result = forecaster.train_evaluate(df_feat, tier, n_splits=n_splits)
    mape_metrics = compute_metrics(result["actuals"], result["predictions"])
    result["metrics"]["mape"] = mape_metrics["mape"]
    result["model"] = forecaster
    return result


def train_and_evaluate_dnn(
    df: pd.DataFrame,
    tier: str = "tier3",
    n_splits: int = 5,
) -> dict:
    forecaster = LEARForecaster(alpha=0.01)
    df_feat = forecaster.add_price_features(df, tier)
    feature_cols = forecaster.get_feature_columns(tier)

    X = df_feat[feature_cols].copy()
    y = df_feat["price_da"].copy()

    from ellectric.pipeline.price_forecaster import _filter_nan_inf
    X, y = _filter_nan_inf(X, y, "price_da", logger)

    nan_mask = X.isna().any(axis=1) | np.isinf(X).any(axis=1)
    if nan_mask.any():
        X = X[~nan_mask]
        y = y[~nan_mask]

    dnn = DNNPriceForecaster(input_dim=len(feature_cols), epochs=30)
    result = dnn.train_evaluate(X, y, n_splits=n_splits)
    result["model"] = dnn
    return result


def train_and_evaluate_persistence(df: pd.DataFrame) -> dict:
    split = int(len(df) * 0.8)
    test = df.iloc[split:].copy()
    train = df.iloc[:split].copy()

    preds = train["price_da"].iloc[-TimeConfig.points_per_day:].values
    preds = np.tile(preds, int(np.ceil(len(test) / TimeConfig.points_per_day)))[:len(test)]
    actuals = test["price_da"].values

    preds = preds[:len(actuals)]
    metrics = compute_metrics(actuals, preds)
    return {"predictions": preds, "actuals": actuals, "metrics": metrics, "model": None}


def train_and_evaluate_weekly_avg(df: pd.DataFrame) -> dict:
    split = int(len(df) * 0.8)
    train = df.iloc[:split].copy()
    test = df.iloc[split:].copy()

    all_data = pd.concat([train, test]).reset_index(drop=True)
    n = len(all_data)

    preds = np.full(n, np.nan)
    for i in range(n):
        indices = []
        for k in range(1, 8):
            idx = i - k * TimeConfig.points_per_day
            if idx >= 0:
                indices.append(idx)
        if indices:
            values = all_data["price_da"].iloc[indices].values
            values = values[np.isfinite(values)]
            if len(values) > 0:
                preds[i] = float(np.mean(values))

    test_start = len(train)
    preds_test = preds[test_start:]
    actuals_test = all_data["price_da"].iloc[test_start:].values

    metrics = compute_metrics(actuals_test, preds_test)
    return {"predictions": preds_test, "actuals": actuals_test, "metrics": metrics, "model": None}


def evaluate_all_models(
    df: pd.DataFrame,
    tier: str = "tier3",
    n_splits: int = 5,
) -> dict:
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    results = {
        "lear": train_and_evaluate_lear(df_sorted, tier=tier, n_splits=n_splits),
        "dnn": train_and_evaluate_dnn(df_sorted, tier=tier, n_splits=n_splits),
        "persistence": train_and_evaluate_persistence(df_sorted),
        "weekly_avg": train_and_evaluate_weekly_avg(df_sorted),
    }
    return results


# ════════════════════════════════════════════════════════════════
# Task-05: DM/GW pairwise statistical tests
# ════════════════════════════════════════════════════════════════

try:
    from epftoolbox.evaluation import dm_test as _epf_dm, gw_test as _epf_gw
    _HAS_EPFTOOLBOX = True
except ImportError:
    _HAS_EPFTOOLBOX = False
    logger.info("epftoolbox not available; DM/GW will use MOCK values")


def _clip_pval(p: float) -> float:
    return max(0.0, min(1.0, p))


def _fmt_pval(p: float) -> str:
    if p is None:
        return "N/A"
    if p < 0.001:
        return "< 0.001"
    return f"{p:.3f}"


def _validate_error_series(e: np.ndarray, name: str) -> str | None:
    if e is None or len(e) == 0:
        return f"SKIP — no data"
    if not np.all(np.isfinite(e)):
        return f"SKIP — contains NaN/Inf"
    if np.allclose(e, 0):
        return f"SKIP — zero error"
    return None


def _tail_align(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    min_len = min(len(a), len(b))
    if len(a) != len(b):
        logger.warning(
            f"Error series lengths differ: {len(a)} vs {len(b)}, "
            f"truncating to {min_len}"
        )
    return a[-min_len:], b[-min_len:]


def _mock_dm_gw(rng: np.random.RandomState) -> tuple[float, float, float, float]:
    """Deterministic mock DM/GW values when epftoolbox absent."""
    dm_stat = float(rng.randn())
    dm_pval = float(rng.uniform(0, 1))
    gw_stat = float(rng.randn())
    gw_pval = float(rng.uniform(0, 1))
    return dm_stat, dm_pval, gw_stat, gw_pval


def _sig_marker(p_value: float | None) -> str:
    if p_value is None:
        return "—"
    if p_value < 0.001:
        return "Yes***"
    if p_value < 0.01:
        return "Yes**"
    if p_value < 0.05:
        return "Yes*"
    return "No"


def _pairwise_dm(
    e1: np.ndarray,
    e2: np.ndarray,
    h: int = 96,
    crit: str = "MAE",
) -> dict:
    skip = _validate_error_series(e1, "e1")
    if skip is None:
        skip = _validate_error_series(e2, "e2")
    if skip is not None:
        return {"dm_stat": None, "p_value": None, "significant": False, "skip_reason": skip}

    e1, e2 = _tail_align(e1, e2)
    if len(e1) < h:
        return {"dm_stat": None, "p_value": None, "significant": False,
                "skip_reason": f"SKIP — aligned length {len(e1)} < h={h}"}

    if not _HAS_EPFTOOLBOX:
        rng = np.random.RandomState(42)
        dm_s, dm_p, _, _ = _mock_dm_gw(rng)
        return {"dm_stat": dm_s, "p_value": _clip_pval(dm_p),
                "significant": dm_p < 0.05,
                "skip_reason": "MOCK — epftoolbox not installed"}

    try:
        dm_stat, dm_pval = _epf_dm(e1, e2, h=h, crit=crit)
        dm_pval = _clip_pval(dm_pval)
        return {"dm_stat": float(dm_stat), "p_value": dm_pval,
                "significant": dm_pval < 0.05, "skip_reason": None}
    except Exception as exc:
        return {"dm_stat": None, "p_value": None, "significant": False,
                "skip_reason": f"DM failed: {exc}"}


def _pairwise_gw(
    e1: np.ndarray,
    e2: np.ndarray,
    h: int = 96,
    crit: str = "MAE",
) -> dict:
    skip = _validate_error_series(e1, "e1")
    if skip is None:
        skip = _validate_error_series(e2, "e2")
    if skip is not None:
        return {"gw_stat": None, "p_value": None, "significant": False, "skip_reason": skip}

    e1, e2 = _tail_align(e1, e2)
    if len(e1) < h:
        return {"gw_stat": None, "p_value": None, "significant": False,
                "skip_reason": f"SKIP — aligned length {len(e1)} < h={h}"}

    if not _HAS_EPFTOOLBOX:
        rng = np.random.RandomState(42)
        _, _, gw_s, gw_p = _mock_dm_gw(rng)
        return {"gw_stat": gw_s, "p_value": _clip_pval(gw_p),
                "significant": gw_p < 0.05,
                "skip_reason": "MOCK — epftoolbox not installed"}

    try:
        gw_stat, gw_pval = _epf_gw(e1, e2, h=h, crit=crit)
        gw_pval = _clip_pval(gw_pval)
        return {"gw_stat": float(gw_stat), "p_value": gw_pval,
                "significant": gw_pval < 0.05, "skip_reason": None}
    except Exception as exc:
        return {"gw_stat": None, "p_value": None, "significant": False,
                "skip_reason": f"GW failed: {exc}"}


def _build_pairwise_table(pairwise_results: list) -> str:
    lines = []
    lines.append("### DM/GW Pairwise Test Results")
    lines.append("")
    lines.append("| Model 1 | Model 2 | DM stat | DM p-value | GW stat | GW p-value | Notes |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in pairwise_results:
        dm = r["dm"]
        gw = r["gw"]
        dm_stat = f"{dm['dm_stat']:.3f}" if dm["dm_stat"] is not None else "N/A"
        dm_p = _fmt_pval(dm["p_value"])
        gw_stat = f"{gw['gw_stat']:.3f}" if gw["gw_stat"] is not None else "N/A"
        gw_p = _fmt_pval(gw["p_value"])
        dm_sig = _sig_marker(dm["p_value"])
        gw_sig = _sig_marker(gw["p_value"])
        note = dm.get("skip_reason") or gw.get("skip_reason") or "—"
        lines.append(
            f"| {r['model_1']} | {r['model_2']} | "
            f"{dm_stat} ({dm_sig}) | {dm_p} | "
            f"{gw_stat} ({gw_sig}) | {gw_p} | {note} |"
        )
    return "\n".join(lines)


def run_dm_gw_pairwise(
    model_results: dict,
    h: int = 96,
    crit: str = "MAE",
) -> dict:
    """Run DM/GW tests for every pair of models.

    Args:
        model_results: {"name": {"predictions": ndarray, "actuals": ndarray}, ...}
        h: Forecast horizon (96 steps for 15min data)
        crit: Loss criterion "MAE" or "MSE"

    Returns:
        {"pairwise_results": [...], "summary": str}
    """
    errors = {}
    for name, res in model_results.items():
        preds = np.asarray(res.get("predictions", []))
        actuals = np.asarray(res.get("actuals", []))
        if len(preds) == 0 or len(actuals) == 0:
            logger.warning("Model %s has no predictions/actuals, skipping", name)
            continue
        actuals, preds = _finite_pairs(actuals, preds)
        if len(preds) == 0 or len(actuals) == 0:
            logger.warning("Model %s has no finite prediction/actual pairs, skipping", name)
            continue
        errors[name] = actuals - preds

    model_names = list(errors.keys())
    pairwise_results = []

    for i in range(len(model_names)):
        for j in range(i + 1, len(model_names)):
            m1, m2 = model_names[i], model_names[j]
            dm = _pairwise_dm(errors[m1], errors[m2], h=h, crit=crit)
            gw = _pairwise_gw(errors[m1], errors[m2], h=h, crit=crit)
            pairwise_results.append({
                "model_1": m1,
                "model_2": m2,
                "dm": dm,
                "gw": gw,
            })

    summary = _build_pairwise_table(pairwise_results)
    return {"pairwise_results": pairwise_results, "summary": summary}


# ════════════════════════════════════════════════════════════════
# Task-06: Report generation (JSON, Markdown, HTML, logging)
# ════════════════════════════════════════════════════════════════


def _setup_logging(output_dir: str) -> str:
    log_path = os.path.join(output_dir, "comparison.log")
    fh = logging.FileHandler(log_path, mode="w")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
    logging.getLogger().addHandler(fh)
    return log_path


def _write_json(result: dict, output_dir: str) -> str:
    path = os.path.join(output_dir, "comparison.json")
    with open(path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("JSON report saved to %s", path)
    return path


def _write_markdown(result: dict, output_dir: str) -> str:
    path = os.path.join(output_dir, "comparison.md")
    meta = result.get("metadata", {})
    models = result.get("models", {})
    tests = result.get("statistical_tests", {})

    lines = []
    lines.append("---")
    lines.append("author: lmr")
    lines.append(f"created_at: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("---")
    lines.append("")
    lines.append("# Price Model Comparison Report")
    lines.append("")
    lines.append(f"- **Dataset**: {meta.get('dataset', 'N/A')}")
    lines.append(f"- **Feature tier**: {meta.get('tier', 'N/A')}")
    lines.append(f"- **Date range**: {meta.get('date_range', 'N/A')}")
    lines.append(f"- **Splits**: {meta.get('n_splits', 'N/A')}-fold TimeSeriesSplit")
    lines.append(f"- **Samples (clean)**: {meta.get('n_rows_clean', 'N/A')}")
    lines.append(f"- **Features**: {meta.get('n_features', 'N/A')}")
    lines.append("")
    lines.append("## Metrics Summary")
    lines.append("")
    lines.append("| Model | MAE | RMSE | MAPE (%) |")
    lines.append("|---|---|---|---|")

    for name, res in sorted(models.items()):
        m = res.get("metrics", {})
        mae_v = m.get("mae")
        rmse_v = m.get("rmse")
        mape_v = m.get("mape")
        mae_s = f"{mae_v:.2f}" if isinstance(mae_v, (int, float)) else "N/A"
        rmse_s = f"{rmse_v:.2f}" if isinstance(rmse_v, (int, float)) else "N/A"
        mape_s = f"{mape_v:.2f}" if isinstance(mape_v, (int, float)) else "N/A"
        lines.append(f"| {name} | {mae_s} | {rmse_s} | {mape_s} |")

    lines.append("")

    summary = tests.get("summary", "")
    if summary:
        lines.append("## Statistical Tests")
        lines.append("")
        lines.append(summary)
        lines.append("")

    lines.append("## Residual Interpretation")
    lines.append("")
    lines.append("- Lower MAE/RMSE indicates better point forecast accuracy.")
    lines.append("- MAPE should be interpreted with caution near zero prices.")
    lines.append("- Statistically significant DM p-value (< 0.05) indicates the ")
    lines.append("  forecast errors differ meaningfully between the two models.")
    lines.append("- GW test extends DM to nested model comparisons.")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append("- DNN is a PyTorch MLP baseline, NOT the epftoolbox DNN implementation.")

    for note in result.get("notes", []):
        lines.append(f"- {note}")

    has_mock = any(
        r.get("dm", {}).get("skip_reason", "").startswith("MOCK")
        or r.get("gw", {}).get("skip_reason", "").startswith("MOCK")
        for pr in tests.get("pairwise_results", [])
        for r in [pr.get("dm", {}), pr.get("gw", {})]
    )
    if has_mock:
        lines.append("- DM/GW tests use MOCK values because epftoolbox is not installed.")

    lines.append("")

    md = "\n".join(lines)
    with open(path, "w") as f:
        f.write(md)
    logger.info("Markdown report saved to %s", path)
    return path


def _write_html(result: dict, output_dir: str) -> str:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    path = os.path.join(output_dir, "residuals.html")
    models = result.get("models", {})

    colors = {
        "lear": "#1f77b4",
        "dnn": "#ff7f0e",
        "persistence": "#2ca02c",
        "weekly_avg": "#d62728",
    }

    residuals = {}
    for name, res in models.items():
        preds = np.asarray(res.get("predictions", []))
        actuals = np.asarray(res.get("actuals", []))
        if len(preds) > 0 and len(actuals) > 0:
            residuals[name] = actuals[:len(preds)] - preds[:len(actuals)]

    if not residuals:
        logger.warning("No model residuals to plot; skipping HTML report")
        return path

    has_timestamps = any(
        "timestamps" in res and len(res["timestamps"]) > 0
        for res in models.values()
    )
    n_rows = 3 if has_timestamps else 2

    titles = [
        "Residual Time Series",
        "Residual Distribution",
    ]
    if has_timestamps:
        titles.append("Error Heatmap by Hour")

    fig = make_subplots(
        rows=n_rows, cols=1,
        subplot_titles=titles,
        vertical_spacing=0.12 if n_rows == 3 else 0.15,
    )

    for name, res in residuals.items():
        color = colors.get(name, "#333333")
        fig.add_trace(
            go.Scatter(y=res, mode="lines", name=name,
                       line=dict(color=color, width=1)),
            row=1, col=1,
        )

    for name, res in residuals.items():
        color = colors.get(name, "#333333")
        fig.add_trace(
            go.Histogram(x=res, name=name, opacity=0.5,
                         marker=dict(color=color),
                         histnorm="probability density"),
            row=2, col=1,
        )

    if has_timestamps:
        hourly_errors = {}
        for name in models:
            ts = models[name].get("timestamps", [])
            if len(ts) == 0:
                continue
            err = residuals.get(name)
            if err is None or len(err) == 0:
                continue
            min_len = min(len(ts), len(err))
            if min_len == 0:
                continue
            ts_arr = np.asarray(ts[:min_len])
            err_arr = err[:min_len]
            if not np.issubdtype(ts_arr.dtype, np.datetime64):
                continue
            hours = pd.Series(ts_arr).dt.hour.values
            hourly_df = pd.DataFrame({"hour": hours, "error": np.abs(err_arr)})
            hourly_errors[name] = hourly_df.groupby("hour")["error"].mean().to_dict()

        if hourly_errors:
            all_hours = sorted(
                set().union(*[set(e.keys()) for e in hourly_errors.values()])
            )
            for name, hourly_dict in hourly_errors.items():
                color = colors.get(name, "#333333")
                values = [hourly_dict.get(h, 0) for h in all_hours]
                fig.add_trace(
                    go.Scatter(x=all_hours, y=values,
                               mode="lines+markers",
                               name=name, line=dict(color=color)),
                    row=3, col=1,
                )
            fig.update_xaxes(title_text="Hour of Day", row=3, col=1)
            fig.update_yaxes(title_text="Mean |Residual|", row=3, col=1)

    fig.update_layout(
        title="Price Model Residual Analysis",
        height=300 * n_rows,
        showlegend=True,
        template="plotly_white",
    )
    fig.update_xaxes(title_text="Sample Index", row=1, col=1)
    fig.update_yaxes(title_text="Residual (Actual - Predicted)", row=1, col=1)
    fig.update_xaxes(title_text="Residual Value", row=2, col=1)
    fig.update_yaxes(title_text="Density", row=2, col=1)

    fig.write_html(path)
    logger.info("HTML residual report saved to %s", path)
    return path


def generate_report(result: dict, output_dir: str) -> dict:
    paths = {
        "json": _write_json(result, output_dir),
        "md": _write_markdown(result, output_dir),
        "html": _write_html(result, output_dir),
    }
    logger.info("All reports generated: %s", paths)
    return paths


if __name__ == "__main__":
    main()
