## ql-20260606-001-a3f2 | 2026-06-06 14:56:13 | Phase 1计划偏差修正：forecaster(gap=24/MAE-only/save/plot)+DataLoader+Cleaner+CONVENTIONS符号注册表+Notebooks思考题
状态：已完成
文件：ellectric/pipeline/forecaster.py, ellectric/pipeline/data_loader.py, ellectric/pipeline/cleaner.py, .sillyspec/docs/Ellectric/scan/CONVENTIONS.md, ellectric/notebooks/*.ipynb
结果：
- forecaster.py: gap 0→24, MAE-only, 新增save_model/load_model(joblib), 新增plot_forecast(叠加图+误差直方图)
- data_loader.py: 新增get_metadata(), OWIDChinaLoader/ChineseDataLoader元数据属性, load_hourly_demand()
- cleaner.py: 新增detect_timezone(), standardize_frequency(), get_data_quality_score()
- CONVENTIONS.md: 新增符号注册表(列名合约/预测器接口/DataLoader/Cleaner命名/禁止事项)
- 5个notebook: 各新增3道思考题, JSON格式修复
