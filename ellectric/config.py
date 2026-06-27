"""
电力时间分辨率全局配置 — Electric Time Resolution Config
==========================================================

TimeConfig 是 Electric 项目中所有时间维度参数的**唯一来源（Single Source of Truth）**。
所有 pipeline 模块不再硬编码点数或频率字符串，而是通过 `from ellectric.config import TimeConfig`
引用配置值，由此实现一处修改即全面切换。

设计理念 (Design Philosophy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- 配置是模块级类属性，不是环境变量 — 简单、无外部依赖
- 默认值对应山东 15min 现货数据：points_per_day=96, points_per_week=672, freq="15min"
- 无需外部配置文件或环境变量，修改类属性即可切换频率

为什么不用 dataclass / Pydantic？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- 不需要运行时校验、JSON 序列化或环境变量读取
- 类属性比 dataclass 实例更简洁（不需要 `TimeConfig()` 实例化）
- 保持依赖最小化（不引入 pydantic / attrs 等新依赖）
"""


class TimeConfig:
    """
    电力时间分辨率全局配置。

    Attributes:
        points_per_day: 每天时间点数。当前默认 96（15 分钟级）。
        points_per_week: 每周时间点数。
            等于 points_per_day × 7。存为独立字段避免每个模块自己算术。
        freq: pandas 频率字符串。当前默认 "15min"。
    """

    # ── 默认 15 分钟级配置（山东 Shandong 96 点/日）──
    points_per_day: int = 96
    points_per_week: int = 672
    freq: str = "15min"