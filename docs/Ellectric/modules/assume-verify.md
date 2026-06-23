---
schema_version: 1
doc_type: module-card
module_id: assume-verify
---
# assume-verify
## 定位
ASSUME 安装验证 — 确保框架可用
## 契约摘要
- `verify_assume.py` — 4 项检查: Python版本, 导入, 版本号, 最小仿真
- `requirements-assume.txt` — 锁定依赖
## 关键逻辑
- 4 项检查全部 PASS 标记安装完成
- 最小仿真 48h, SQLite 输出
## 注意事项
- 不依赖 Docker/Grafana (task-10 负责)
