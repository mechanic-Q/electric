---
id: task-04
title: 实现 `build_datasets` + rt_price→price_da 价格代理 + 时段切分 + null 填充
author: lmr
created_at: 2026-06-29 01:51:26
priority: P0
depends_on: [task-01]
blocks: [task-06, task-07, task-08]
requirement_ids: [FR-01]
decision_ids: [D-001@v1, D-006@v1]
allowed_paths:
  - ellectric/scripts/train_rl_full_dataset.py
goal: >
  把 ShandongDataLoader 输出转成 trading_env / backtester 所需的 (train_load, train_price, test_load, test_price) 四件，用 rt_price 重命名为 price_da 作为出清价代理。
implementation:
  - 用 `create_loader("shandong")` 调用 `ShandongDataLoader.load_data()` 拿到全量 DataFrame
  - 验证 `timestamp / load_mw / rt_price` 列存在；rt_price 用 `bfill().ffill()` 处理 null
  - 构造 price_df：拷贝 timestamp 列 + 新列 `price_da = df["rt_price"]`，保留 `is_holiday / is_weekend` 以便特征工程下游使用
  - 按 train_start/train_end/test_start/test_end 切分 load_df 与 price_df 各两份（边界含起含止用 timestamp 字符串比较 + tz-aware）
  - 返回 (train_load, train_price, test_load, test_price)；空切片抛 ValueError
  - 模块级常量 `PRICE_PROXY = "rt_price->price_da"` 用于报告 metadata
acceptance:
  - test_build_datasets_price_proxy_columns：返回 price_df 含 `price_da` 列且等于原 `rt_price`
  - test_build_datasets_split_disjoint：train/test 时间范围不重叠
  - test_build_datasets_null_filled：返回 price_df 的 `price_da` 列无 null
verify:
  - pytest tests/test_train_rl_full_dataset.py -q -k build_datasets
constraints:
  - 不修改 ShandongDataLoader 原始列名（只在脚本内拷贝重命名）
  - 不动 da_price 列（保留供未来切换）
  - 不依赖 holidays / 任何可选依赖
