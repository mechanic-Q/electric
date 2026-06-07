"""
Phase 4 — Handler 函数：桥接 Pydantic Schema 到 Pipeline 模块
=============================================================

4 个业务函数：
- run_forecast():  负荷/电价预测
- run_simulate():   ASSUME 市场仿真
- run_backtest():   历史回测
- run_explain():    SHAP 模型可解释性

所有 pipeline 导入均为延迟导入（函数内部），避免模块级循环依赖。
"""

import csv
import json
import os
import re
import subprocess
import time

from ellectric.service.schemas import (
    ForecastRequest,
    ForecastResponse,
    ForecastMetrics,
    SimulateRequest,
    SimulateResponse,
    BacktestRequest,
    BacktestResponse,
    ExplainRequest,
    ExplainResponse,
    FeatureImportance,
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BASELINE_STRATEGIES = {"baseline_persistence", "baseline_mean", "oracle"}
_RL_STRATEGIES = {"ppo", "sac", "td3"}
_SUPPORTED_STRATEGIES = _BASELINE_STRATEGIES | _RL_STRATEGIES

_CONFIGURE_MAP = {
    "default": "ellectric/assume/configs/assume_china_config.yaml",
    "summer_peak": "ellectric/assume/configs/assume_china_summer_peak.yaml",
    "wind_high": "ellectric/assume/configs/assume_china_wind_high.yaml",
}


def _get_model_dir() -> str:
    return os.environ.get("ELLECTRIC_MODEL_DIR", "ellectric/models/")


def _get_data_dir() -> str:
    return os.environ.get("ELLECTRIC_DATA_DIR", "ellectric/data/")


# ═══════════════════════════════════════════════════════════════════
# 1. run_forecast
# ═══════════════════════════════════════════════════════════════════


def run_forecast(req: ForecastRequest) -> ForecastResponse:
    if req.model_type not in ("load", "price"):
        raise ValueError(
            f"Unsupported model_type: {req.model_type}. Valid: load, price"
        )
    if req.model_type == "load":
        return _run_load_forecast(req)
    return _run_price_forecast(req)


def _run_load_forecast(req: ForecastRequest) -> ForecastResponse:
    from ellectric.pipeline.forecaster import XGBoostForecaster
    from ellectric.pipeline.data_loader import OWIDChinaLoader
    from ellectric.pipeline.features import FeatureEngineer

    model_path = os.path.join(_get_model_dir(), "xgboost_model.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"XGBoost 模型文件未找到: {model_path}")

    forecaster = XGBoostForecaster()
    forecaster.load_model(model_path)

    loader = OWIDChinaLoader()
    df = loader.load_data()

    engineer = FeatureEngineer()
    df_feat = engineer.add_tier1_features(df)
    df_feat = engineer.add_tier2_features(df_feat)
    df_feat = engineer.add_tier3_features(df_feat)

    X = df_feat[forecaster._feature_cols].iloc[-req.horizon:]
    predictions = forecaster.predict(X)
    timestamps = df_feat["timestamp"].iloc[-req.horizon:].tolist()

    return ForecastResponse(
        timestamps=timestamps,
        predictions=predictions.tolist(),
        metrics=ForecastMetrics(),
    )


def _run_price_forecast(req: ForecastRequest) -> ForecastResponse:
    from ellectric.pipeline.price_forecaster import LEARForecaster
    from ellectric.pipeline.price_loader import PriceDataLoader

    model_path = os.path.join(_get_model_dir(), "lear_model.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"LEAR 模型文件未找到: {model_path}")

    forecaster = LEARForecaster()
    forecaster.load_model(model_path)

    xlsx_path = os.path.join(_get_data_dir(), "price_data.xlsx")
    loader = PriceDataLoader(xlsx_path)
    df = loader.load_data()

    df_feat = forecaster.add_price_features(df, "tier3")
    X = df_feat[forecaster._feature_cols].iloc[-req.horizon:]
    predictions = forecaster.predict(X)
    timestamps = df_feat["timestamp"].iloc[-req.horizon:].tolist()

    return ForecastResponse(
        timestamps=timestamps,
        predictions=predictions.tolist(),
        metrics=ForecastMetrics(),
    )


# ═══════════════════════════════════════════════════════════════════
# 2. run_simulate
# ═══════════════════════════════════════════════════════════════════


def run_simulate(req: SimulateRequest) -> SimulateResponse:
    config_path = _CONFIGURE_MAP.get(req.config)
    if config_path is None:
        raise ValueError(
            f"未知场景 '{req.config}'，可选: {list(_CONFIGURE_MAP.keys())}"
        )
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"场景配置文件未找到: {config_path}")

    output_dir = f"/tmp/assume_results_{req.config}_{int(time.time())}"

    result = subprocess.run(
        [
            "python", "ellectric/assume/run_simulation.py",
            "--config", config_path,
            "--output", output_dir,
            "--days", str(req.days),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ASSUME 仿真失败 (returncode={result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    import pandas as pd

    clearing_prices = []
    dispatch = []
    agent_profits = {}

    prices_path = os.path.join(output_dir, "clearing_prices.csv")
    if os.path.exists(prices_path):
        with open(prices_path) as f:
            for row in csv.DictReader(f):
                clearing_prices.append(float(row["clearing_price"]))

    dispatch_path = os.path.join(output_dir, "dispatch.csv")
    if os.path.exists(dispatch_path):
        dispatch = pd.read_csv(dispatch_path).to_dict(orient="records")

    profits_path = os.path.join(output_dir, "agent_profits.csv")
    if os.path.exists(profits_path):
        df_profits = pd.read_csv(profits_path)
        agent_profits = dict(zip(df_profits["agent"], df_profits["profit"]))

    return SimulateResponse(
        status="success",
        clearing_prices=clearing_prices,
        dispatch=dispatch,
        agent_profits=agent_profits,
        output_dir=output_dir,
    )


# ═══════════════════════════════════════════════════════════════════
# 3. run_backtest
# ═══════════════════════════════════════════════════════════════════


def run_backtest(req: BacktestRequest) -> BacktestResponse:
    if req.strategy not in _SUPPORTED_STRATEGIES:
        raise ValueError(
            f"未知策略 '{req.strategy}'，可选: {sorted(_SUPPORTED_STRATEGIES)}"
        )

    start = req.start_date.isoformat()
    end = req.end_date.isoformat()

    if not _DATE_PATTERN.match(start):
        raise ValueError(
            f"start_date 格式非法: {req.start_date}（应为 YYYY-MM-DD）"
        )
    if not _DATE_PATTERN.match(end):
        raise ValueError(
            f"end_date 格式非法: {req.end_date}（应为 YYYY-MM-DD）"
        )
    if req.start_date >= req.end_date:
        raise ValueError(
            f"start_date ({req.start_date}) 必须早于 end_date ({req.end_date})"
        )

    if req.strategy in _RL_STRATEGIES and not req.model_path:
        raise ValueError(
            f"RL 策略 '{req.strategy}' 需要提供 model_path 参数"
        )

    from ellectric.pipeline.backtester import BacktestRunner
    from ellectric.pipeline.data_loader import OWIDChinaLoader
    from ellectric.pipeline.price_loader import PriceDataLoader
    from ellectric.pipeline.trading_env import ElectricityMarketEnv

    loader = OWIDChinaLoader()
    load_df = loader.load_data()

    price_loader = PriceDataLoader(
        os.path.join(_get_data_dir(), "price_data.xlsx")
    )
    price_df = price_loader.load_data()

    env_factory = lambda: ElectricityMarketEnv(load_df, price_df, None, None)
    runner = BacktestRunner(env_factory)

    if req.strategy in _RL_STRATEGIES:
        from ellectric.pipeline.rl_trainer import RLAgentFactory

        agent = RLAgentFactory.load(req.strategy, req.model_path)
        replay_df = runner.replay(
            agent, load_df, price_df, start, end,
            strategy_name=req.strategy,
        )
    else:
        replay_df = runner.replay(
            None, load_df, price_df, start, end,
            strategy_name=req.strategy,
        )

    comparison_results = {req.strategy: replay_df}
    for baseline in ("baseline_persistence", "baseline_mean"):
        df_bs = runner.replay(
            None, load_df, price_df, start, end,
            strategy_name=baseline,
        )
        comparison_results[baseline] = df_bs

    comparison_df = runner.compare(comparison_results)

    cumulative_pnl = replay_df["pnl_cumulative"].tolist()

    comparison_dict = {
        row["策略"]: row["总收益"]
        for _, row in comparison_df.iterrows()
    }

    sharpe_row = comparison_df[comparison_df["策略"] == req.strategy]
    sharpe_val = (
        float(sharpe_row["夏普比率"].iloc[0])
        if len(sharpe_row) > 0 else None
    )

    return BacktestResponse(
        status="success",
        cumulative_pnl=cumulative_pnl,
        sharpe_ratio=sharpe_val,
        comparison=comparison_dict,
        plot_data=None,
    )


# ═══════════════════════════════════════════════════════════════════
# 4. run_explain
# ═══════════════════════════════════════════════════════════════════


def run_explain(req: ExplainRequest) -> ExplainResponse:
    if req.model_type == "xgboost":
        return _run_xgboost_explain(req)
    elif req.model_type == "lear":
        return _run_lear_explain(req)
    else:
        raise ValueError(
            f"不支持的 model_type '{req.model_type}'，可选: 'xgboost', 'lear'"
        )


def _run_xgboost_explain(req: ExplainRequest) -> ExplainResponse:
    from ellectric.pipeline.forecaster import XGBoostForecaster
    from ellectric.pipeline.data_loader import OWIDChinaLoader
    from ellectric.pipeline.features import FeatureEngineer
    from ellectric.pipeline.shap_explainer import (
        explain_xgboost_sample,
        feature_importance_ranking,
    )

    model_path = os.path.join(_get_model_dir(), "xgboost_model.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"XGBoost 模型文件未找到: {model_path}")

    forecaster = XGBoostForecaster()
    forecaster.load_model(model_path)

    loader = OWIDChinaLoader()
    df = loader.load_data()

    engineer = FeatureEngineer()
    df_feat = engineer.add_tier1_features(df)
    df_feat = engineer.add_tier2_features(df_feat)
    df_feat = engineer.add_tier3_features(df_feat)

    waterfall_fig = explain_xgboost_sample(
        forecaster, df_feat, req.sample_index, req.max_display
    )
    models = {"XGBoost": forecaster}
    importance_df = feature_importance_ranking(models, forecaster._feature_cols)

    return _build_explain_response(waterfall_fig, importance_df)


def _run_lear_explain(req: ExplainRequest) -> ExplainResponse:
    from ellectric.pipeline.price_forecaster import LEARForecaster
    from ellectric.pipeline.price_loader import PriceDataLoader
    from ellectric.pipeline.shap_explainer import (
        explain_lear_sample,
        feature_importance_ranking,
    )

    model_path = os.path.join(_get_model_dir(), "lear_model.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"LEAR 模型文件未找到: {model_path}")

    forecaster = LEARForecaster()
    forecaster.load_model(model_path)

    xlsx_path = os.path.join(_get_data_dir(), "price_data.xlsx")
    loader = PriceDataLoader(xlsx_path)
    df = loader.load_data()

    df_feat = forecaster.add_price_features(df, "tier3")

    waterfall_fig = explain_lear_sample(
        forecaster, df_feat, req.sample_index, req.max_display
    )
    models = {"LEAR": forecaster}
    importance_df = feature_importance_ranking(models, forecaster._feature_cols)

    return _build_explain_response(waterfall_fig, importance_df)


def _build_explain_response(waterfall_fig, importance_df) -> ExplainResponse:
    waterfall_json = json.loads(waterfall_fig.to_json())

    feature_importance_list = []
    for i, (_, row) in enumerate(importance_df.iterrows()):
        feature_importance_list.append(
            FeatureImportance(
                name=str(row["feature"]),
                importance=float(row["importance"]),
                rank=i + 1,
            )
        )

    return ExplainResponse(
        status="success",
        feature_importance=feature_importance_list,
        waterfall_json=waterfall_json,
    )
