---
schema_version: 1
doc_type: module-card
module_id: assume-configs
---
# assume-configs
## 定位
ASSUME 中国省间现货市场 YAML 配置
## 契约摘要
- 基准: `assume_china_config.yaml` (煤50/风20/光15/气10/储5 GW)
- 高风电: `assume_china_wind_high.yaml` (风30GW, 煤40GW)
- 夏季高峰: `assume_china_summer_peak.yaml` (需求96GW, 气15GW)
## 关键逻辑
- 中国省间规则: 报价0-1500元/MWh, 偏差考核, 新能源优先
- YAML anchors 继承 (`&defaults`, `<<:`)
## 注意事项
- 边际成本为元/MWh
- 智能体类型: learning(PPO), naive, strategic
