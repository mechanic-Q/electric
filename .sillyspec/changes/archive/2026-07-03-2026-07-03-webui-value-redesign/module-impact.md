---
author: lmr
created_at: 2026-07-03 19:39:32
---

# Module Impact — WebUI Value Redesign

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| *(新)* WebUI Frontend | 新增 | ellectric/web/ | Vite+React+TS Dashboard-first 前端源码 | false |
| *(新)* WebUI Tests | 新增 | tests/test_web_static.py | 静态页面和路由 smoke test | false |
| service-api | 调用关系变更 | ellectric/web/src/api.ts | 前端新增 API client 消费现有 backend 端点；server.py 0 行修改 | false |
| service-api | 配置变更 | README.md | 更新启动/构建说明；不改变后端配置 | false |

## 未匹配文件

| 文件 | 原因 |
|------|------|
| ellectric/api/static/index.html | 构建产物，非源文件 |
| ellectric/api/static/assets/* | 构建产物，非源文件 |

## 影响分析

- 无后端模块逻辑变更
- 无数据结构或接口变更（前端 TypeScript 类型仅镜像后端 JSON）
- server.py 0 行修改
- 所有后端模块保持活跃（active）状态
- 建议后续 scan 新增 `web-frontend` 模块
