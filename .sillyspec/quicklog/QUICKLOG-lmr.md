## ql-20260607-001-3f2a | 2026-06-07 16:18:30 | 修复 predict() 缺少 scaler 转换 + backtester env_factory 绕过
状态：已完成
文件：forecaster.py, price_forecaster.py, backtester.py, trading_env.py, rl_trainer.py, notebook 10

修改摘要:
- forecaster.py: 新增 self._scaler, save/load/predict 支持 scaler
- price_forecaster.py: 同上
- backtester.py: replay() 改用 env_factory 直接创建 env
- trading_env.py: wind/solar lag_24h 从单值改为 24 步窗口
- rl_trainer.py: _compute_final_reward 后 reset() 清理 env 状态
- notebook 10: 结尾打印 "Notebook 07" → "Notebook 10"
