---
author: lmr
created_at: 2026-06-10T13:30:00+08:00
---

# Design — 中国电力数据更新

## 背景

Ellectric 项目使用 OWID (Our World in Data) 作为中国电力数据源，硬编码使用 `raw.githubusercontent.com`（GitHub raw）URL。该域名在国内网络环境下经常被阻断或超时，导致数据拉取失败。用户实际使用时数据停留在 2017 年，无法获取最新数据。

OWID 上游数据实际上已更新到 **2025 年**（Ember 2026-04-27 更新），但项目缺少：
- 多级回退机制
- 本地缓存
- 网络超时重试
- 小时级数据源

## 设计目标

1. OWID 中国数据可靠拉取到 2025 年最新
2. 国内网络环境下自动回退，不丢数据
3. 新增 Ember 小时级数据探索能力
4. 数据合约 `{timestamp, load_mw}` 不变，下游零修改
5. 文档更新，标注数据源和使用方法

## 非目标

- 不引入 PUDL/ENTSO-E/pypsa 等重型专业库
- 不修改 cleaner/features/forecaster 下游模块
- 不新增 CLI/API 接口
- 不修改 ChineseDataLoader 现有逻辑
- 不做数据版本对比/数据质量评分（后续变更）

## 拆分判断

单模块变更，3 个 Wave 独立可交付，任务数 < 10，无批量模式需求。不拆分。

## 总体方案

### Wave 1: OWID 3 级回退 + 缓存

修改 `OWIDChinaLoader.load_data()` 实现拉取链路：

```
优先级 1: OWID 官方 CDN (owid-public.owid.io)
    → 超时 15s / HTTP != 200
    → 优先级 2: GitHub raw (raw.githubusercontent.com)
        → 超时 30s / HTTP != 200
        → 优先级 3: 本地 Parquet 缓存 (ellectric/data/owid_china_cache.parquet)
            → 缓存也无 → raise RuntimeError
```

关键设计：
- 成功后自动写本地缓存（data_version 增加拉取时间戳）
- 缓存路径：`ellectric/data/owid_china_cache.parquet`
- `load_data()` 签名不变，新增可选 `refresh=False` 参数跳过缓存
- 日志分级：INFO 成功 + 数据源、WARNING 回退触发、ERROR 全部失败

### Wave 2: Ember 数据加载器（新增）

新增 `ember_loader.py`，继承 `DataLoader` ABC：
- 从 Ember Climate API 拉取小时级/日级中国电力数据
- `create_loader(source="ember")` 工厂支持
- try/except 容错 — Ember API 可能需要 key，缺失时降级不阻断管道

### Wave 3: 验证 + 文档

- notebook 01→05 全流程验证
- 更新 README/INTEGRATIONS.md
- 新增 `docs/data-sources.md`

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `ellectric/pipeline/data_loader.py` | OWIDChinaLoader: 新增 3 级回退链路 + 本地缓存；新增 OWID_CDN_URL 常量；create_loader 注册 ember |
| 新增 | `ellectric/pipeline/ember_loader.py` | EmberLoader 类，继承 DataLoader ABC，小时级数据探索 |
| 修改 | `ellectric/README.md` | 数据源说明 + 更新方法 |
| 修改 | `.sillyspec/docs/Ellectric/scan/INTEGRATIONS.md` | Ember 数据源条目 |
| 新增 | `docs/data-sources.md` | 所有可用数据源一览 |
| 修改 | `.sillyspec/docs/Ellectric/modules/_module-map.yaml` | 新增 ember-loader 模块条目 |

## 接口定义

### OWIDChinaLoader（修改）

```python
class OWIDChinaLoader(DataLoader):
    OWID_CDN_URL = "https://owid-public.owid.io/data/energy/owid-energy-data.csv"
    OWID_GITHUB_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
    CACHE_PATH = Path("ellectric/data/owid_china_cache.parquet")

    def load_data(self, start=None, end=None, refresh=False) -> pd.DataFrame:
        """3 级回退拉取中国电力数据。refresh=True 跳过缓存强制拉取。"""
        ...

    def _fetch_from_url(self, url: str, timeout: int) -> list[dict]:
        """从指定 URL 拉取并解析 OWID CSV，返回 rows。失败 raise。"""
        ...

    def _load_from_cache(self) -> pd.DataFrame:
        """从本地 Parquet 缓存加载数据。无缓存 raise FileNotFoundError。"""
        ...

    def _save_cache(self, df: pd.DataFrame) -> None:
        """保存 DataFrame 到本地 Parquet 缓存。"""
        ...
```

### EmberLoader（新增）

```python
class EmberLoader(DataLoader):
    EMBER_API_URL = "https://api.ember-energy.org/v1/..."

    def load_data(self, start=None, end=None) -> pd.DataFrame:
        """从 Ember API 拉取中国小时级电力数据。返回 Data Contract。"""
        ...
```

### create_loader（修改）

```python
def create_loader(source="owid", **kwargs) -> DataLoader:
    # source 新增 "ember" 选项
    ...
```

## 数据模型

无新增数据表。新增本地缓存文件：
- `ellectric/data/owid_china_cache.parquet` — OWID 拉取成功后写入，schema 同 Data Contract + 额外字段（year, generation_twh, demand_twh, solar_twh, wind_twh, coal_twh, region, source, data_version）

## 兼容策略

- **未配置缓存行为不变**：首次运行无缓存时从网络拉取，行为等同于原有逻辑
- **合约不变**：load_data() 返回 `DataFrame[timestamp, load_mw, ...]`，下游零修改
- **create_loader() 向后兼容**：`source="owid"` / `"manual"` / `"file"` 行为不变
- **Ember 失败不阻断**：`source="ember"` 仅新增选项，不设默认值

## 风险登记

| 编号 | 风险 | 等级 | 应对策略 |
|------|------|------|---------|
| R-01 | OWID CDN URL 未来迁移 | P1 | 保留 GitHub raw 作为备用；CDN URL 失败时自动回退 |
| R-02 | GitHub raw 在国内持续不可用 | P1 | 本地 Parquet 缓存兜底；即使网络全断也能用上次数据 |
| R-03 | Ember API 需要 key 且获取困难 | P2 | try/except ImportError 容错；logger.warning 降级 |
| R-04 | 25MB CSV 下载超时 | P1 | 超时从 30s 缩短到 15s（CDN）+ 30s（GitHub）；失败立即回退 |
| R-05 | 本地缓存格式与合约不一致 | P2 | _save_cache 写入前用 validate_schema() 校验 |

## 自审

- [x] 需求覆盖：3 项核心需求全部覆盖（OWID 回退、Ember 探索、文档验证）
- [x] 约束一致性：不改 ABC/工厂/合约模式，与 CONVENTIONS.md 的 "依赖倒置" 原则一致
- [x] 真实性：OWID_ENERGY_CSV_URL 来自代码第 66-69 行；REQUIRED_COLUMNS 来自 cleaner.py 第 42 行；类名/方法名均来自真实代码
- [x] YAGNI：不引入专业库、不加数据质量评分、不加 API 接口
- [x] 验收标准：notebook 01→05 全流程跑通 + 2025 年数据出现
- [x] 非目标清晰：明确 5 项不做的
- [x] 兼容策略：3 级回退保证向后兼容
- [x] 风险识别：5 项风险全部有应对
