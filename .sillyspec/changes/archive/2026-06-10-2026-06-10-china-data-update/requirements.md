---
author: lmr
created_at: 2026-06-10 13:30:00
---

# Requirements — 中国电力数据更新

## 角色

| 角色 | 说明 |
|------|------|
| 开发者 | 运行 notebook/CLI 进行数据分析和模型训练 |
| 数据使用者 | 依赖 DataLoader 接口的下游模块（cleaner/features/forecaster） |

## 功能需求

### FR-01: OWID 多级回退拉取

Given OWIDChinaLoader 已初始化
When 调用 load_data()
Then 按优先级尝试拉取：OWID CDN → GitHub raw → 本地缓存
And 第一个成功的源返回数据
And 日志记录使用的数据源

#### 边界条件

Given OWID CDN 返回 HTTP 200
When 拉取成功
Then 直接返回数据，不尝试后续源
And 自动写本地缓存

Given OWID CDN 超时或返回非 200
When 回退到 GitHub raw
Then 日志输出 WARNING "OWID CDN 不可用，回退到 GitHub raw"
And 继续尝试 GitHub raw

Given GitHub raw 也失败
When 回退到本地缓存
Then 日志输出 WARNING "网络源均不可用，使用本地缓存"
And 返回缓存数据

Given 本地缓存也不存在
When 全部源失败
Then raise RuntimeError，日志输出 ERROR

### FR-02: 本地缓存机制

Given load_data() 从网络成功拉取
When 数据加载完成
Then 自动写入 `ellectric/data/owid_china_cache.parquet`
And 缓存包含 data_version 列（记录拉取时间戳）

Given load_data(refresh=True)
When 调用
Then 跳过缓存，强制从网络拉取

Given load_data(refresh=False)（默认）
When 网络全部不可用
Then 使用缓存数据（如有）

### FR-03: Ember 数据加载器

Given create_loader(source="ember")
When 返回 EmberLoader 实例
Then 实现 DataLoader ABC 接口
And load_data() 返回符合 Data Contract 的 DataFrame

Given Ember API 不可用
When load_data() 调用失败
Then logger.warning 降级通知
And 不阻断管道（调用方自行决定是否终止）

### FR-04: 工厂函数扩展

Given create_loader(source="owid")
When 调用
Then 返回 OWIDChinaLoader，行为与变更前相同

Given create_loader(source="manual"|"file")
When 调用
Then 返回 ChineseDataLoader，行为不变

Given create_loader(source="ember")
When 调用
Then 返回 EmberLoader 实例

### FR-05: 文档更新

Given 数据源变更完成
When 开发者查阅文档
Then README 包含数据更新说明
And INTEGRATIONS.md 包含 Ember 条目
And docs/data-sources.md 列出所有可用数据源及获取方式

## 非功能需求

- **兼容性**：create_loader 所有现有签名不变；load_data() 返回格式不变；下游模块零修改
- **可回退**：删除 `ember_loader.py` + 还原 `data_loader.py` 即可完全回退
- **可测试**：notebook 01→05 全流程作为 smoke test
- **网络容忍**：CDN 15s 超时、GitHub 30s 超时，总等待不超过 45s
- **缓存可靠性**：缓存写入前用 validate_schema() 校验，避免写入损坏数据
