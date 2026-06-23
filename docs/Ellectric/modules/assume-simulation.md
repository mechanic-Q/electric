---
schema_version: 1
doc_type: module-card
module_id: assume-simulation
---
# assume-simulation
## 定位
ASSUME 7 天仿真运行 + 结果验证
## 契约摘要
- `run_simulation.py --config <yaml> --output <dir>` — 运行仿真, 输出4个文件
- `verify_simulation.py --input <dir>` — 验证输出完整性和合理性
## 关键逻辑
- 168 小时仿真周期
- 输出: clearing_prices.csv, dispatch.csv, agent_profits.csv, metadata.json
- 含内置回退 (ASSUME 不可用时用 merit-order 模拟)
## 注意事项
- --seed 保证可复现 (默认42)
- 信号中断时保存部分结果
