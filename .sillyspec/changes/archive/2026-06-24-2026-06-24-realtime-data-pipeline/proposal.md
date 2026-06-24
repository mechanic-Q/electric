---
author: lmr
created_at: 2026-06-24T15:00:00+08:00
---

# Proposal — 数据抓取管道

## 动机

上 3 个变更接入了山西 18 个 API 数据，但抓取是手动跑 `sx_pull_all.py`。一次抓完落盘后没有：
- 重复抓取的接口（每月新数据需重跑）
- 历史快照（重抓直接覆盖旧数据）
- 三明治集成（脚本不能被 API/LLM 调用）

## 关键问题

1. **数据老化**：山西月度曲线每月更新，手动重跑容易遗忘
2. **数据丢失**：没有 snapshots，无法对比上月抓取 vs 这次的差异
3. **不能 LLM/网站调用**：未来 ABCD 之后做 LLM 实时问答时，需要可程序化的 fetch API

## 变更范围

- ShanxiFetcher 模块（核心抓取类）
- CLI 薄壳（命令行抓取入口）
- snapshots 归档（按日期目录保留历史）
- latest 视图维护（兼容现有 loader）

## 不在范围内

- ❌ 不做调度（cron/airflow）— 手动按需运行
- ❌ 不接 FastAPI 或 LLM tool — 留给后续 web-chat-ui 之类变更
- ❌ 不抓广东 — 单独变更
- ❌ 不做实时推送（websocket 等）
- ❌ 不引入新依赖

## 成功标准

1. ShanxiFetcher 可被 import 使用
2. CLI 脚本 fetch_shanxi.py 可调
3. snapshots 目录按日期归档保留所有历史
4. 现有 ShanxiSpotDaLoader 等读取 latest 视图行为不变
5. 现有 verify_shanxi_loader 37/37 仍通过
6. 不引入新依赖
