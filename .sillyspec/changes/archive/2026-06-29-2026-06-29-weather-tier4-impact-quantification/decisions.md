---
author: lmr
created_at: 2026-06-29 20:40:04
---

# Weather Tier4 Impact Quantification 决策台账

## D-001@v1

- type: validation-policy
- status: accepted
- source: user-request + prior weather validation decision
- question: Weather Tier4 impact quantification 是否设置 MAE/RMSE/MAPE 改善硬阈值？
- answer: 不设置硬阈值，继续 report-only；指标改善或退化都作为事实输出。
- normalized_requirement: 报告必须给出 baseline vs weather 指标和 delta，但 `hard_threshold_applied=false`，不因 weather 未改善而失败。
- impacts: [design-goals, non-goals, Wave-2, R-05, tests-report-schema]
- evidence: `ellectric/scripts/validate_weather_tier4.py` 已有 `interpretation.hard_threshold_applied=False`；历史设计明确 Tier4 是可选增强。
- priority: P1

## D-002@v1

- type: experiment-design
- status: accepted
- source: code review of current `run_ablation_experiment()`
- question: Weather impact 实验中 weather 分支是否可以使用 feature_df 除 timestamp/load_mw 外的所有列？
- answer: 不可以。weather 分支只能使用 Tier3 baseline 列 + 实际 weather 列，禁止混入 raw Shandong columns。
- normalized_requirement: `X_weather.columns == tier3_cols + weather_cols_detected`；raw columns 如 `rt_price`、`da_price`、`wind_actual_mw` 不得进入 X_weather。
- impacts: [Wave-1, tests-raw-column-leakage, R-03, data-model]
- evidence: `ellectric/pipeline/shandong_loader.py` 输出 21 列扩展 schema；当前 `run_ablation_experiment()` 用除 timestamp/load_mw 外全部列会混入非 weather 信号。
- priority: P0

## D-003@v1

- type: evidence-storage
- status: accepted
- source: project memory + user request for automated verification
- question: Full-run 证据日志应存在哪里？
- answer: 写入 `ellectric/reports/weather_tier4/weather_tier4_impact.log`，不写 `/tmp`。
- normalized_requirement: 最终 full-run 命令输出必须 tee/redirect 到 reports 目录，报告 JSON/Markdown 同目录生成；metadata.log_path 记录该日志路径。
- impacts: [Wave-2, Wave-4, file-change-list, R-01]
- evidence: Project memory: full-run evidence logs should stay under `ellectric/reports/rl_full_dataset/*.log` rather than `/tmp`;同一原则适用于 weather_tier4。
- priority: P1

## D-004@v1

- type: reproducibility
- status: accepted
- source: local data inspection
- question: Full-run 验证默认是否允许联网抓取 weather？
- answer: 最终验证优先离线 cache，使用 `--no-fetch`；cache 缺失时报告 degraded 并提示，不依赖网络作为完成条件。
- normalized_requirement: 运行 `python ellectric/scripts/validate_weather_tier4.py --no-fetch --output-dir ellectric/reports/weather_tier4`；使用已有 `ellectric/data/shandong/weather_2024-2026.parquet`。
- impacts: [Wave-4, R-02, compatibility]
- evidence: 本地存在 `ellectric/data/shandong/weather_2024-2026.parquet`；项目约束强调公开数据和可复现学习流程。
- priority: P1
