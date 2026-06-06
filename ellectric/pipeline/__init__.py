# ellectric — pipeline 模块
# Phase 1: 负荷数据管道 + XGBoost 预测
# Phase 2: 电价数据管道 + LEAR 预测

from ellectric.pipeline.price_forecaster import LEARForecaster
from ellectric.pipeline.statistical_tests import run_statistical_tests

try:
    from ellectric.pipeline.price_loader import PriceDataLoader
except ImportError:
    # price_loader.py 由 task-01 创建，导入失败是预期行为
    PriceDataLoader = None

__all__ = [
    "LEARForecaster",
    "PriceDataLoader",
    "run_statistical_tests",
]
