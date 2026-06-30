#!/usr/bin/env python3
"""验证风/光功率预测器在山东全量数据上的表现。"""

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

from ellectric.pipeline.renewable_forecaster import (
    WindPowerForecaster,
    SolarPowerForecaster,
    _compute_metrics,
)
from ellectric.pipeline.shandong_loader import ShandongDataLoader
from ellectric.pipeline.features import FeatureEngineer

logger = logging.getLogger(__name__)


def run_validation(output_dir: str = "ellectric/reports/renewable_forecaster") -> dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    df = ShandongDataLoader().load_data()
    engineer = FeatureEngineer()
    df_feat = engineer.add_tier1_features(df)
    df_feat = engineer.add_tier2_features(df_feat)
    df_feat = engineer.add_tier3_features(df_feat)

    tier3_cols = engineer.get_feature_columns("tier3")
    weather_available = False
    try:
        df_feat = engineer.add_tier4_weather_features(df_feat, fetch_if_missing=False)
        weather_cols = [c for c in getattr(engineer, '_weather_columns', []) if c in df_feat.columns]
        if weather_cols:
            weather_available = True
    except Exception:
        weather_cols = []

    feature_cols = tier3_cols + (weather_cols if weather_available else [])

    experiments = {}

    for name, ForecasterCls in [("wind", WindPowerForecaster), ("solar", SolarPowerForecaster)]:
        forecaster = ForecasterCls()
        target = forecaster.target_col
        if target not in df_feat.columns:
            experiments[name] = {"status": "skipped", "reason": f"target column {target} not found"}
            continue
        X = df_feat[feature_cols].copy()
        y = df_feat[target].copy()
        result = forecaster.train_evaluate(X, y, n_splits=5)
        experiments[name] = {
            "status": "ok",
            "target": target,
            "feature_count": len(feature_cols),
            "weather_available": weather_available,
            "metrics": result["metrics"],
        }
        if "baseline_metrics" in result:
            experiments[name]["baseline_metrics"] = result["baseline_metrics"]

    metadata = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_source": "shandong",
        "input_rows": int(len(df)),
        "report_scope": "full_dataset",
        "weather_available": weather_available,
    }

    report = {
        "status": "ok",
        "metadata": metadata,
        "experiments": experiments,
    }

    json_path = output_path / "renewable_forecast_validation.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), "utf-8")

    md_lines = [
        f"# 风/光功率预测验证报告\n",
        f"*生成时间: {metadata['generated_at']}*\n",
        "## Metadata\n",
        f"- **data_source**: {metadata['data_source']}",
        f"- **input_rows**: {metadata['input_rows']}",
        f"- **weather_available**: {metadata['weather_available']}\n",
    ]
    for name, exp in experiments.items():
        md_lines.append(f"## {name.upper()}\n")
        if exp.get("status") == "skipped":
            md_lines.append(f"- **状态**: 跳过 ({exp['reason']})\n")
            continue
        md_lines.append(f"- **target**: {exp['target']}")
        m = exp["metrics"]
        md_lines.append(f"- **MAE**: {m['mae']:.2f}")
        md_lines.append(f"- **RMSE**: {m['rmse']:.2f}")
        md_lines.append(f"- **nRMSE**: {m['nrmse'] if m['nrmse'] is not None else 'N/A'}")
        if "baseline_metrics" in exp:
            bm = exp["baseline_metrics"]
            md_lines.append(f"- **Baseline MAE**: {bm['mae']:.2f}")
        md_lines.append("")

    md_path = output_path / "renewable_forecast_validation.md"
    md_path.write_text("\n".join(md_lines), "utf-8")

    logger.info("Reports generated in %s", output_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="验证风/光功率预测器")
    parser.add_argument("--output-dir", default="ellectric/reports/renewable_forecaster")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    result = run_validation(output_dir=args.output_dir)
    print(f"Validation status: {result['status']}")


if __name__ == "__main__":
    main()
