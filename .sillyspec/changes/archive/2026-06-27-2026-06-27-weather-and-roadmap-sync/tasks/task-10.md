---
author: lmr
created_at: 2026-06-27 19:12:11
id: task-10
title: 运行文档/wiki 对账检查并更新任务勾选
priority: P0
depends_on:
  - task-04
  - task-05
  - task-06
  - task-07
  - task-08
  - task-09
blocks: []
requirement_ids:
  - FR-005
  - FR-006
decision_ids:
  - D-001@v1
  - D-002@v1
  - D-003@v1
  - D-004@v1
  - D-005@v1
  - D-006@v2
  - D-007@v2
  - D-008@v1
  - D-009@v1
allowed_paths:
  - ".sillyspec/changes/2026-06-27-weather-and-roadmap-sync/tasks.md"
  - ".sillyspec/changes/2026-06-27-weather-and-roadmap-sync/plan.md"
  - "ellectric/README.md"
  - ".planning/ROADMAP.md"
  - ".planning/REQUIREMENTS.md"
  - "docs/Ellectric/scan/ARCHITECTURE.md"
  - "docs/Ellectric/modules/feature-engineer.md"
  - "docs/Ellectric/modules/_module-map.yaml"
  - "wiki/synthesis/electric-phase4-closeout-20260627.md"
  - "wiki/entities/lmr-electric.md"
  - "wiki/synthesis/electric-data-requirements-vs-tuji-20260622.md"
  - "wiki/index.md"
  - "wiki/log.md"
---

# Task-10: 运行文档/wiki 对账检查并更新任务勾选

## 修改文件

| 操作 | 文件路径 | 说明 |
|---|---|---|
| 修改 | `.sillyspec/changes/2026-06-27-weather-and-roadmap-sync/tasks.md` | task-10 条目改为 `[x]`，被 task-04~09 blocks 的依赖检查确认后一并标注 |
| 修改 | `.sillyspec/changes/2026-06-27-weather-and-roadmap-sync/plan.md` | Wave 4 task-10 从 `[ ]` 改为 `[x]`；全局验收标准所有项改为 `[x]`（若对应证据存在） |

其余修改文件为**只读 grep 检查**：不写入内容，仅 grep 确认文档对账结果。

## 覆盖来源

| 需求/决策 | 覆盖方式 |
|---|---|
| FR-005 | grep 确认 README、ROADMAP、REQUIREMENTS、scan ARCHITECTURE、module docs 与当前山东 15min + Phase 4 状态一致 |
| FR-006 | grep 确认 LLM Wiki 新增/更新页面符合 `schema.md` frontmatter、wikilink、index、log 规则 |
| D-001@v1 | grep 确认所有文档记录"不做准实时"决策 |
| D-002@v1 | grep 确认所有文档记录"不做中长期合约"决策 |
| D-003@v1 | grep 确认文档保持单省山东 MVP 口径 |
| D-004@v1 | grep 确认文档保持学习原型、非真实交易口径 |
| D-005@v1 | 本轮变更完整覆盖确认（所有 task 勾选） |
| D-006@v2 | grep 确认 Tier4 API 兼容旧 `prepare_features(df, tiers=...)` 签名 |
| D-007@v2 | grep 确认 cache 策略与 safe ffill 对齐描述 |
| D-008@v1 | wiki 页面 schema 检查通过 |
| D-009@v1 | grep 确认 ARCHITECTURE.md 旧事实已清理 |

## 实现要求

### 1. 验收代码测试结果（确认 task-09 证据）

在运行文档 grep 之前，先确认 task-09 的输出存在：

```bash
# 检查 weather 测试全部通过
pytest tests/test_weather_features.py -v 2>&1 | tail -20
# 确认 12 个测试通过，无 FAIL/ERROR

# 检查旧 API 兼容
python -c "
from ellectric.pipeline.features import prepare_features
import pandas as pd
df = pd.DataFrame({'timestamp': pd.date_range('2024-01-01', periods=96, freq='15min', tz='UTC'), 'load_mw': [100]*96})
df2 = prepare_features(df, tiers=['tier1'])
# 应不含 weather 列
weather_cols = [c for c in df2.columns if any(w in c for w in ['temp_','ghi_','wind_speed_','precip_','humidity_','cloud_'])]
assert len(weather_cols) == 0, f'旧签名不应含 weather 列: {weather_cols}'
print('旧 API 兼容验证通过')
"

# 检查 Tier1-3 回归
pytest tests/ -x --timeout=60 -k "not weather" 2>&1 | tail -5
```

**若上述测试未全部通过**：记录失败项到文档，但继续执行 grep 检查（grep 检查独立于测试结果）。task-10 的勾选标记改为 `[~]`（部分通过）并在备注中注明。

### 2. 仓库文档 grep 对账清单

以下每条必须给出 `rg` 命令和输出摘要。输出结果记录到文档或终端，不修改目标文件。

#### 2.1 README.md 检查 (ellectric/README.md)

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| R1 | WeatherFetcher 气象特征标记为 `[x]` | `rg 'WeatherFetcher.*\[x\]|\[x\].*WeatherFetcher|气象特征.*\[x\]'` | 至少 1 匹配 |
| R2 | 包含四个 out-of-scope 决策 | `rg -i '准实时|中长期合约|多省|多节点|真实交易|付费数据'` | 每条短语至少 1 匹配 |
| R3 | 项目结构 features.py 标注已更新 | `rg 'features.py.*渐进式'` 或等价特征层描述 | 匹配含"4" |
| R4 | weather.py 在 fetch/ 下 | `rg 'weather.py.*WeatherFetcher'` | 匹配存在 |
| R5 | 无 Phase 状态矛盾（如 Phase 4 标记 `[ ]` 但实际上所有项已实现） | `rg '### Phase 4' -A 5` | 检查后续行状态合理 |

#### 2.2 ROADMAP.md 检查 (.planning/ROADMAP.md)

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| M1 | Phase 4 状态为 `[x]` / `[~]` 非 `[ ]` | `rg 'Phase 4.*\[[~x]\]'` | 至少 1 匹配 |
| M2 | Progress 表格 Phase 4 非 `Not started` | `rg -A 5 'Phase 4'` 在 Progress 表格中 | "In progress" 或 "Shipped" |
| M3 | 包含四个 out-of-scope 决策 | `rg -i '准实时|中长期合约|多省|多节点|真实交易'` | 每条至少 1 匹配 |
| M4 | Weather Tier4 在已完成的持续改进清单中 | `rg -i 'Weather.*Tier|Tier4.*weather|WeatherFetcher.*已完成'` | 至少 1 匹配 |
| M5 | Phase 1-3 状态不变 | `rg 'Phase [1-3]:'` | `[x]` 状态与变更前一致 |

#### 2.3 REQUIREMENTS.md 检查 (.planning/REQUIREMENTS.md)

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| Q1 | Phase 1 需求状态"已完成" | `rg 'ENV-01|ENV-02|ENV-03|DATA-01|DATA-02|DATA-03|DATA-04|PRED-01|VIZ-01'` | 对应的状态列含"已完成" |
| Q2 | Phase 2/3/4 需求保持"待开始" | `rg 'SIM-01|AGENT-01|INTG-01'` | 状态列含"待开始" |
| Q3 | 不在范围内新增准实时/中长期合约两行 | `rg -i '准实时.*T\+15|中长期合约.*增强'` | 至少 1 匹配 |
| Q4 | 页脚日期含 2026-06-27 | `rg '2026-06-27'` | 至少 1 匹配 |
| Q5 | 脚注说明 REQUIREMENTS 仅记录原始状态 | `rg '仅记录各 Phase 原始需求'` 或等效 | 至少 1 匹配 |

#### 2.4 ARCHITECTURE.md 检查 (docs/Ellectric/scan/ARCHITECTURE.md)

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| A1 | 无 `OWID` 作为 primary 数据源 | `rg 'OWID.*(urllib|GitHub|raw|主数据源|primary)'` | 仅出现在历史参考/副线标注中 |
| A2 | ShandongDataLoader 在模块职责中 | `rg 'ShandongDataLoader'` | 至少 1 匹配 |
| A3 | `prepare_features` 签名使用 `tiers` 列表形式 | `rg 'prepare_features\(.*tiers='` | 至少 1 匹配 |
| A4 | `add_tier4_weather_features` 或 Tier4 出现 | `rg 'add_tier4_weather_features|Tier4'` | 至少 1 匹配 |
| A5 | `TimeSeriesSplit(gap=` 值为 96 而非 24 | `rg 'TimeSeriesSplit'` | gap 值为 96 或 TimeConfig.points_per_day |
| A6 | `Box` 动作空间更新为 `(96,)` | `rg 'Box\(0.*1.*\(96'` | 至少 1 匹配 |
| A7 | `updated_at` 为 2026-06-27 | `rg 'updated_at'` | 更新后的日期 |
| A8 | 无残留 `gap=24` 作为当前事实 | `rg 'gap=24'` | 0 匹配（允许历史注释中提及） |
| A9 | 无残留 `Box\(0, 1, \(24` 作为当前事实 | `rg 'Box\(0.*1.*\(24,' | 0 匹配 |
| A10 | Phase 边界表数据源含山东 15min | `rg -i 'Phase 1.*数据源|山东.*canonical|15min.*canonical'` | 山东 15min 出现在数据源位置 |

#### 2.5 feature-engineer.md 检查 (docs/Ellectric/modules/feature-engineer.md)

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| F1 | 定位段含"4层"而非"3层" | `rg '4层|Tier4|tier4'` | 至少 1 匹配 |
| F2 | 契约摘要含 `add_tier4_weather_features` | `rg 'add_tier4_weather_features'` | 至少 1 匹配 |
| F3 | 关键逻辑含 weather cache/降级说明 | `rg 'cache|降级|ffill|safe ffill'` | 至少 1 匹配 |
| F4 | 注意事项含 weather 相关说明 | `rg -i 'weather.*注意|气象.*注意|小时级.*ffill|cache.*派生'` | 至少 1 匹配 |

#### 2.6 _module-map.yaml 检查 (docs/Ellectric/modules/_module-map.yaml)

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| Y1 | feature-engineer tags 含 weather/tier4 | `rg -A 30 'feature-engineer:' docs/Ellectric/modules/_module-map.yaml \| rg 'tags' -A 5` | 含 `weather` / `weather-features` / `tier4` |
| Y2 | feature-engineer entrypoints 含 `add_tier4_weather_features` | `rg -A 20 'feature-engineer:' \| rg 'entrypoints' -A 3` | 含该方法 |
| Y3 | feature-engineer depends_on 含 `weather-fetcher` | `rg -A 15 'feature-engineer:' \| rg 'depends_on' -A 2` | 含 `weather-fetcher` |
| Y4 | 新增 `weather-fetcher` 模块条目 | `rg 'weather-fetcher:'` | 至少 1 匹配 |
| Y5 | weather-fetcher 条目含 paths/aliases/entrypoints | `rg -A 20 'weather-fetcher:'` | paths、tags、aliases、entrypoints、main_symbols、depends_on 均有值 |

### 3. LLM Wiki grep 对账清单

wiki 目录位于 `/mnt/e/Agent_memory/wiki_nashsu/wiki_nashsu/`（根据 D-008@v1 上下文）。

#### 3.1 closeout synthesis 检查

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| W1 | 新增 `electric-phase4-closeout-20260627.md` 存在 | `ls wiki/synthesis/electric-phase4-closeout-20260627.md` | 文件存在 |
| W2 | frontmatter 含 `type/title/tags/related/created/updated` | `head -15 wiki/synthesis/electric-phase4-closeout-20260627.md \| rg '^(type|title|tags|related|created|updated):'` | 六项都存在 |
| W3 | 文件名 kebab-case | 目视文件名 | 无大写/空格/下划线 |
| W4 | 含 `[[wikilink]]` 连接 | `rg '\[\[.*\]\]' wiki/synthesis/electric-phase4-closeout-20260627.md` | 至少 1 个 wikilink |
| W5 | 记录 out-of-scope 决策 | `rg -i 'out.of.scope|准实时|中长期合约|多省|真实交易'` | 至少 1 匹配 |

#### 3.2 entity/lmr-electric.md 检查

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| E1 | 更新 Phase 4 状态 | `rg -i 'Phase 4|p4.*weather|weather.*tier4' wiki/entities/lmr-electric.md` | 含当前的 Phase 4 进展 |

#### 3.3 旧 synthesis 更新检查

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| S1 | `electric-data-requirements-vs-tuji-20260622.md` 含 2026-06-27 状态段 | `rg '2026-06-27' wiki/synthesis/electric-data-requirements-vs-tuji-20260622.md` | 至少 1 匹配 |

#### 3.4 index.md 检查

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| I1 | 含指向新 closeout synthesis 的 wikilink | `rg 'electric-phase4-closeout' wiki/index.md` | 至少 1 匹配 |

#### 3.5 log.md 检查

| # | 检查项 | grep 命令 | 预期结果 |
|---|---|---|---|
| L1 | 含 2026-06-27 条目 | `rg '2026-06-27' wiki/log.md` | 至少 1 匹配 |
| L2 | 条目格式符合 schema（逆时间） | 目视最上方条目日期 | 最新日期在最前 |

### 4. 更新 tasks.md 勾选

读取当前 `.sillyspec/changes/2026-06-27-weather-and-roadmap-sync/tasks.md`，将所有 task 条目 `[ ]` 改为 `[x]`。

将 `T-010` 条目改为 `[x]`：

```
- [x] T-001 — 扩展 FeatureEngineer Tier4 weather API (ellectric/pipeline/features.py) — 覆盖 FR-001, FR-003, FR-004, D-006@v2
- [x] T-002 — 实现 weather parquet cache 读取/抓取/写入与降级路径 (ellectric/pipeline/features.py, ellectric/fetch/weather.py) — 覆盖 FR-002, FR-003, D-007@v2
- [x] T-003 — 修正或规避 WeatherFetcher.align_to_15min() 30min 容差边界 (ellectric/fetch/weather.py) — 覆盖 FR-003, D-007@v2
- [x] T-004 — 增加 weather feature 测试 (tests/test_weather_features.py) — 覆盖 FR-001~FR-004, D-006@v2, D-007@v2
- [x] T-005 — 更新 feature-engineer 模块文档与 module-map (docs/Ellectric/modules/feature-engineer.md, docs/Ellectric/modules/_module-map.yaml) — 覆盖 FR-005, D-009@v1
- [x] T-006 — 更新 scan 架构文档旧事实 (docs/Ellectric/scan/ARCHITECTURE.md) — 覆盖 FR-005, D-009@v1
- [x] T-007 — 更新 README/ROADMAP/REQUIREMENTS 状态 (ellectric/README.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md) — 覆盖 FR-005, D-001@v1~D-005@v1
- [x] T-008 — 新增 LLM Wiki closeout synthesis (wiki/synthesis/electric-phase4-closeout-20260627.md) — 覆盖 FR-006, D-008@v1
- [x] T-009 — 更新 LLM Wiki 现有 entity/synthesis/index/log (wiki/entities/lmr-electric.md, wiki/synthesis/electric-data-requirements-vs-tuji-20260622.md, wiki/index.md, wiki/log.md) — 覆盖 FR-006, D-008@v1
- [x] T-010 — 验证与对账：运行 weather tests、旧 API 兼容测试、文档 grep、wiki schema 检查 — 覆盖 FR-001~FR-006
```

### 5. 更新 plan.md 勾选

读取当前 `.sillyspec/changes/2026-06-27-weather-and-roadmap-sync/plan.md`，更新：

**Wave 4**（第29行）：
```
- [x] task-09: 运行代码测试与旧 API 兼容检查（覆盖：FR-001, FR-002, FR-003, FR-004）
- [x] task-10: 运行文档/wiki 对账检查并更新任务勾选（覆盖：FR-005, FR-006, D-001@v1~D-009@v1）
```

**全局验收标准**（第62-71行）— 所有项改为 `[x]`：

```
- [x] `tests/test_weather_features.py` 覆盖 Tier4、cache 命中、cache 缺失降级、15min safe ffill、旧 `prepare_features(df, tiers=...)` 兼容。
- [x] 不真实调用 Open-Meteo 的测试全部通过。
- [x] `prepare_features(df, tiers=["tier1"])` 与 Tier1~Tier3 旧调用行为不变。
- [x] `get_feature_columns("tier4")` 只返回实际存在的天气列，不包含缺失列。
- [x] `WeatherFetcher.align_to_15min()` 或 Tier4 对齐逻辑覆盖 `00:45` 边界。
- [x] README、ROADMAP、REQUIREMENTS、scan ARCHITECTURE、module docs 与当前山东 15min + Phase 4 状态一致。
- [x] LLM Wiki 新增/更新页面符合 `schema.md` frontmatter、wikilink、index、log 规则。
- [x] D-001@v1~D-005@v1、D-006@v2、D-007@v2、D-008@v1、D-009@v1 均有任务和验收证据覆盖。
- [x] local.yaml 已读取；若仍无启用 lint/test 命令，则使用 targeted pytest 与静态 grep 作为验证证据。
```

## 接口定义

N/A。本任务为验证与对账任务，只运行 grep/pytest 命令并更新勾选框状态。不涉及 Python 代码接口。

验证接口定义为：`tasks.md` 勾选标记、`plan.md` 勾选标记、grep 命令返回值、pytest 退出码。

## 边界处理

1. **grep 结果不符合预期**（某条检查失败）：不修改被检查的目标文档，只记录到 task-10 执行输出中。在 tasks.md 和 plan.md 中标记 `[~]`（部分通过），并在备注行列出失败的检查项编号（如 "R2 缺失 out-of-scope"）。不允许为了通过检查而修改目标文档——grep 是只读审计。

2. **pytest 测试未全部通过**：如上所述，测试结果独立于 grep 对账。在 plan.md 全局验收标准中标记具体失败项为 `[~]`，task-10 整体标记 `[~]`。不阻止 tasks.md 勾选（task-10 作为验证步骤已执行，只是结果有缺陷）。

3. **wiki 文件路径不存在**：D-008@v1 上下文中 wiki 位于 `/mnt/e/Agent_memory/wiki_nashsu/wiki_nashsu/`。若该路径不存在，则 wiki 对账部分标注 N/A 并注明原因。主仓库的 `.planning/` 文档对账仍然照常执行。

4. **plan.md 全局验收标准中部分项已被前序 task 部分勾选**：task-10 只做最终全量确认，不重复勾选。若前序 task 已将部分标准标记为 `[x]`，保留已有标记，只将未勾选的改为 `[x]`。

5. **tasks.md 中 T-010 条目标注与 task-10 不一致**：tasks.md 中 T-010 的描述可能简化（"验证与对账"），task-10.md 必须与之保持一致。最终的 tasks.md 更新仅将 `[ ]` 改为 `[x]`，不修改描述文本。

6. **plan.md 中 Wave 4 的 task-09 和 task-10 同时更新**：先更新 task-09（假设它已完成），再更新 task-10（本任务）。若 task-09 未完成，task-10 标记 `[~]` 并在备注说明。

7. **部分文档已在前序 task 中被修改并更新了勾选**：task-10 不重复检查 task-04~06 是否已标记（它们已有自己的 task 文件）。task-10 的 grep 检查是独立的最终确认，与 task-04~06 的勾选状态无关。

8. **grep 命令因路径问题失败**：若某个目标文件被提前删除或移动，grep 命令返回 1（无匹配）。在 grep 检查记录中标注该文件缺失，并对该项标注 N/A，继续执行其余检查。

9. **多个 out-of-scope 决策在同一文件中表述不一致**：四个决策（D-001@v1~D-004@v1）在 README、ROADMAP、REQUIREMENTS 中可能出现不同措辞。task-10 不要求完全一致的模板文本，只要求每份文档覆盖了"不做准实时/中长期合约/多省/真实交易"的核心语义。

10. **`generated_at`/`source_commit` 在 `_module-map.yaml` 中被前序 task 意外更新**：若发现这些元数据被更新，记录为审计发现，但不回滚。本 task 不修改 `_module-map.yaml`。

## 非目标

- 不修改除 `tasks.md` 和 `plan.md` 之外的任何文件
- 不修改被 grep 检查的任何文档内容（只读审计）
- 不运行 Open-Meteo 网络测试（task-01 和 task-09 覆盖）
- 不重新执行 task-01~09（验证结果来自前序 task 的输出）
- 不改动代码、测试、模块文档、scan 文档、路线图、需求文档
- 不改动 wiki 文件
- 不生成对账报告文件（grep 结果输出到终端）
- 不提交 git commit

## 参考

| 来源 | 内容 | 用途 |
|---|---|---|
| `design.md:64-80` | Wave 4 文档/wiki 对账设计 | 文档对账范围 |
| `design.md:25-26` | FR-005, FR-006 定义 | grep 检查目标 |
| `design.md:172-183` | D-001@v1~D-009@v1 决策描述 | grep 检查出站依据 |
| `plan.md:62-71` | 全局验收标准 | 勾选更新依据 |
| `plan.md:27-29` | Wave 4 task-09/task-10 定义 | 勾选更新依据 |
| `plan.md:43-45` | 任务总表 task-10 条目 | 行为约束 |
| `requirements.md:70-92` | FR-005/FR-006 验收条件 | grep 检查验收标准 |
| `decisions.md` | D-001@v1~D-009@v1 全文 | 决策覆盖证据 |
| `tasks/task-06.md` | README/ROADMAP/REQUIREMENTS 变更设计 | 确认 task-06 已修改的文档 |
| `tasks/task-04.md` | 模块文档与 module-map 变更 | 确认 task-04 已修改的文档 |
| `tasks/task-05.md` | ARCHITECTURE.md 变更 | 确认 task-05 已修改的文档 |

## TDD 步骤

1. **读取本地 yaml 配置**（如 `.opencode/local.yaml`）：确认 lint/test 命令可用；若无，确认使用 `pytest` + `rg` 作为验证工具链。

2. **确认 task-09 测试结果**：运行 pytest weather 测试套件（12 个测试）和旧 API 兼容脚本，确保 task-09 的输出存在。记录通过/失败状态。

3. **运行仓库文档 grep 检查**：按 2.1→2.6 顺序逐条执行 grep 命令。每条记录：命令输出、匹配次数、通过/失败。

4. **运行 wiki grep 检查**：按 3.1→3.5 顺序逐条执行 grep 命令。若 wiki 路径不存在，标注 N/A 并注明。

5. **记录审计结果**：汇总所有 grep 检查项的通过/失败计数。失败项保留为审计记录，不修改目标文档。

6. **更新 tasks.md**：将所有 `[ ]` 改为 `[x]`。若测试或 grep 有失败项，在 T-010 行末追加备注 `（部分通过，见审计记录）`。

7. **更新 plan.md**：更新 Wave 4 勾选和全局验收标准勾选。若某验收标准未通过（测试失败或 grep 失败），该标准保留为 `[~]`。

8. **交叉验证勾选一致性**：检查 tasks.md 和 plan.md 的勾选无矛盾（例如 plan.md 标注 task-10 失败但 tasks.md 标注完成）。

9. **最终 diff 确认**：`git diff --name-only` 确认只修改了 `tasks.md` 和 `plan.md`（及可能的其他 SillySpec 元数据文件）。

## 验收标准表格

| # | 标准 | 验证方式 | 覆盖 |
|---|---|---|---|
| 1 | 12 个 weather 测试全部通过 | `pytest tests/test_weather_features.py -v` 退出码 0 | FR-001~FR-004 |
| 2 | 旧 `prepare_features(df, tiers=['tier1'])` 调用不含 weather 列 | python 脚本 assert | D-006@v2 |
| 3 | README.md 中 Weather 特征标记 `[x]` 或 `[~]` 且包含 out-of-scope 决策 | grep R1-R2 均通过 | FR-005, D-001@v1~D-004@v1 |
| 4 | ROADMAP.md Phase 4 状态非 `[ ]`，含 out-of-scope 和 Weather 已完成项 | grep M1-M4 均通过 | FR-005, D-001@v1~D-004@v1 |
| 5 | REQUIREMENTS.md Phase 1 需求为"已完成"，新增 out-of-scope 行 | grep Q1-Q5 均通过 | FR-005 |
| 6 | ARCHITECTURE.md 无 `gap=24`/`Box(24,)`/OWID primary 旧事实；含 Tier4 | grep A1-A10 均通过 | FR-005, D-009@v1 |
| 7 | feature-engineer.md 含 Tier4 weather 契约 | grep F1-F4 均通过 | FR-005, D-009@v1 |
| 8 | `_module-map.yaml` 含 weather-fetcher 条目 + feature-engineer weather tags | grep Y1-Y5 均通过 | FR-005, D-009@v1 |
| 9 | 新增 wiki closeout synthesis 存在且含 frontmatter + wikilink | grep W1-W5 均通过 | FR-006, D-008@v1 |
| 10 | wiki entity/旧synthesis/index/log 已包含 2026-06-27 状态引用 | grep E1, S1, I1, L1-L2 均通过 | FR-006, D-008@v1 |
| 11 | `tasks.md` 所有条目为 `[x]` | 目视确认 | D-005@v1 |
| 12 | `plan.md` Wave 4 和全局验收标准所有项为 `[x]` 或有效的 `[~]` | 目视确认 | D-005@v1 |
| 13 | 除 `tasks.md` 和 `plan.md` 外无其他文件被修改 | `git diff --name-only` | — |
