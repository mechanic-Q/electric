---
author: lmr
created_at: 2026-06-24T15:00:00+08:00
---

# Decisions — 数据抓取管道

## D-001@v1 — 模块+脚本双模式（方案C）

**决策**：核心逻辑在 `ellectric/fetch/shanxi.py` 类，scripts 只做参数转发

**备选**：A(Typer CLI 子命令)/B(独立脚本)

**理由**：满足三明治架构 — 未来网站/LLM 可 import 调用，不依赖 shell

## D-002@v1 — Snapshots 归档策略

**决策**：双输出：snapshots/<today>/ 历史快照（永不覆盖） + latest 视图（可被覆盖）

**理由**：留下可追溯痕迹，同时保持现有 loader 兼容

## D-003@v1 — Cookie 外部化

**决策**：cookie 默认从 SHANXI_COOKIE 环境变量读，或构造时传入

**理由**：cookie 是凭证，不能 commit 到代码
