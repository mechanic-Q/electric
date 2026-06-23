---
schema_version: 1
doc_type: module-card
module_id: epftoolbox-install
---
# epftoolbox-install
## 定位
epftoolbox 独立 venv 安装脚本
## 契约摘要
- `install_epftoolbox.sh` — 创建 venv + 安装 + 下载 5 数据集 + 输出统计
- Flags: `--skip-download`, `--reinstall`, `--dataset-only`
## 关键逻辑
- 独立 venv 隔离 TensorFlow/PyTorch 冲突
- 自动检测国内 PyPI 镜像
## 注意事项
- Python ≥3.11 推荐
- 数据集下载后缓存于 data/epftoolbox_datasets/
