---
id: task-04
title: 搭建独立 epftoolbox venv + 下载 5 个基准数据集
author: lmr
created_at: 2026-06-06T19:36:10+08:00
priority: P1
estimated_hours: 2
depends_on: [task-03]
blocks: [task-05]
allowed_paths:
  - ellectric/install_epftoolbox.sh
  - ellectric/.venv_epftoolbox/
  - ellectric/.gitignore
---

# task-04: 搭建独立 epftoolbox venv + 下载 5 个基准数据集

## 修改文件

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `ellectric/install_epftoolbox.sh` | 独立 venv 安装脚本，包含数据集下载 + 统计输出 |
| 新增 | `ellectric/.venv_epftoolbox/` | epftoolbox 独立虚拟环境（gitignored，脚本自动创建） |
| 修改 | `ellectric/.gitignore` | 追加 `.venv_epftoolbox/` 条目 |

## 实现要求

### 1. install_epftoolbox.sh 脚本

```bash
# 功能: 创建 .venv_epftoolbox → pip install tensorflow + epftoolbox → 下载 5 数据集 → 输出统计
# 位置: ellectric/install_epftoolbox.sh
# 特性: 幂等（已安装则跳过）、网络容错（镜像源切换）、进度输出
```

脚本行为规范:

1. **Python 检查**: 同 setup.sh 风格，检测 Python 3.11+
2. **Venv 管理**: 检查 `.venv_epftoolbox/` 是否存在，存在则提示跳过或重新安装
3. **安装**:
   - 先装 `tensorflow`（epftoolbox 硬依赖）
   - 再装 `git+https://github.com/jeslago/epftoolbox.git`
   - 网络探测：PyPI 不可达时自动切清华镜像
4. **数据集下载**: 调用 epftoolbox 的 `epftoolbox.datasets` 模块下载 5 个数据集
   - 目标目录: `ellectric/data/epftoolbox_datasets/`
   - 数据集列表:

| 数据集 | 市场 | 文件命名 |
|--------|------|----------|
| EPEX-BE | Belgium day-ahead | `epex_be.csv` |
| EPEX-FR | France day-ahead | `epex_fr.csv` |
| EPEX-DE | Germany day-ahead | `epex_de.csv` |
| NordPool | Nordic day-ahead | `nordpool.csv` |
| PJM | US Pennsylvania-Jersey-Maryland | `pjm.csv` |

5. **统计输出**: 对每个数据集打印:

```
Dataset: EPEX-BE
  Rows: 29224  |  Columns: 6  |  Date range: 2017-01-01 ~ 2020-12-31
  Price (€/MWh):
    Mean:   42.31
    Median: 38.12
    Std:    28.94
    Min:    -500.00
    Max:    3000.00
    Missing: 12 (0.04%)
  Year: 2023  |  Week: 22  |  Hour: 0
  ---
```

## 接口定义

### epftoolbox 数据加载接口（仅读取，不训练）

```python
# 后续 task-05/06 通过此方式读取已下载数据：

import pandas as pd

def load_epftoolbox_dataset(name: str) -> pd.DataFrame:
    """从本地加载 epftoolbox 基准数据集。

    Args:
        name: 数据集名称，可选 'epex_be', 'epex_fr', 'epex_de', 'nordpool', 'pjm'

    Returns:
        DataFrame with columns: [year, month, day, hour, price, load]
        索引为 DatetimeIndex (UTC)

    Raises:
        FileNotFoundError: 数据集未下载（提示运行 install_epftoolbox.sh）
        ValueError: name 不在支持列表中
    """
    path = f"../data/epftoolbox_datasets/{name}.csv"
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df[['year', 'month', 'day', 'hour']])
    df = df.set_index('timestamp').drop(columns=['year', 'month', 'day', 'hour'])
    return df
```

### install_epftoolbox.sh 接口

```bash
# 命令行接口
./install_epftoolbox.sh                    # 完整安装 + 下载 + 统计
./install_epftoolbox.sh --skip-download    # 仅安装依赖，跳过数据集下载
./install_epftoolbox.sh --reinstall        # 强制重建 venv + 重新安装
./install_epftoolbox.sh --dataset-only     # 仅下载/刷新数据集
```

## 边界处理

| # | 边界场景 | 处理方式 |
|---|----------|----------|
| 1 | `epftoolbox` 安装失败（git clone 超时/网络不可达） | 脚本输出明确错误信息 + 退出码 1；提示用户手动尝试 `pip install git+https://github.com/jeslago/epftoolbox.git`；不自动切镜像（GitHub 无镜像） |
| 2 | 部分数据集下载失败（单个市场数据源中断） | 继续下载其余数据集；最终统计报告标注每个数据集下载状态（成功/失败）；不阻塞整体流程 |
| 3 | `.venv_epftoolbox/` 已存在但损坏 | `--reinstall` 标志删除并重建；无标志时检测关键包（`python -c "import epftoolbox"`），失败则报错提示加 `--reinstall` |
| 4 | 磁盘空间不足 | 下载前检查 `data/epftoolbox_datasets/` 所在分区可用空间 ≥ 500MB；不足时输出警告但不强制退出 |
| 5 | Python 版本不满足（< 3.9） | epftoolbox 依赖 TF 2.x，TF 2.16+ 已停止支持 Python 3.8；检测到 < 3.9 时报错退出，提示使用 Python 3.10+ |
| 6 | 脚本从错误目录运行 | 脚本自动检测 `ellectric/` 目录是否存在（通过自身路径 `$(dirname "$0")`），不存在则报错提示从项目根目录运行 |
| 7 | 重复安装（脚本第二次运行） | 检测 `.venv_epftoolbox/` 存在 + `epftoolbox` 可导入则跳过安装步骤，直接从数据集下载开始；`--reinstall` 覆盖此行为 |
| 8 | CSV 文件编码问题 | epftoolbox 部分数据集可能包含 BOM 或其他编码；使用 `utf-8-sig` 编码读取，`encoding_errors='replace'` 处理异常字符 |

## 非目标

- 不训练任何 epftoolbox 模型（epftoolbox 仅用作数据集来源和统计检验基准）
- 不修改主虚拟环境 `.venv/`（主环境只有 sklearn Lasso，不与 TF 冲突）
- 不在 `requirements.txt` 中添加 epftoolbox 或 tensorflow 依赖
- 不做 epftoolbox 的 DNN 模型对比（DM/GW 检验在 task-05 中进行）
- 不实现数据集缓存过期检测（数据集是静态的，不会更新）
- 不做 pandas 版本兼容性处理（epftoolbox 自身处理数据读取）

## 参考

- epftoolbox GitHub: https://github.com/jeslago/epftoolbox
- epftoolbox datasets: `epftoolbox.datasets` 模块（`_DATASETS` 字典包含 5 个市场配置）
- TF compatibility matrix: https://www.tensorflow.org/install/source#gpu
- 设计文档: `design.md` §Wave 2 — epftoolbox 安装策略
- 主 venv 安装脚本参考: `ellectric/setup.sh`（风格一致性）

## TDD 步骤

| 步骤 | 操作 | 验证方法 |
|------|------|----------|
| 1 | 编写 `install_epftoolbox.sh` 脚本框架（venv 创建 + 包安装） | `bash -n install_epftoolbox.sh` 语法检查通过 |
| 2 | 运行 `./install_epftoolbox.sh` 安装依赖 | 脚本退出码 0，控制台输出 "安装完成" |
| 3 | 激活 venv 并验证导入 | `.venv_epftoolbox/bin/python -c "import epftoolbox; print(epftoolbox.__version__)"` 无报错 |
| 4 | 运行 `./install_epftoolbox.sh --skip-download`（幂等验证） | 第二次运行 10 秒内完成，输出 "依赖已安装，跳过" |
| 5 | 添加数据集下载逻辑，下载 5 个数据集 | 5 个 CSV 文件存在于 `data/epftoolbox_datasets/` |
| 6 | 验证每个 CSV 文件完整性 | `wc -l` 每个文件 >= 1000 行（最小数据集 PJM 约 17000 行） |
| 7 | 添加统计输出逻辑 | 每个数据集输出 7 个统计值（mean, median, std, min, max, missing, missing_rate） |
| 8 | 按需运行 `--dataset-only` 测试 | 只下载数据集，不重复安装 |
| 9 | 按需运行 `--reinstall` 测试 | 删除旧 venv + 重建 + 重新安装 |
| 10 | 测试边界：在无网络环境运行 `--skip-download` | 只检查已安装部分，不尝试网络请求 |

## 验收标准

### 功能标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | 脚本在干净的 Python 3.11+ 环境中 15 分钟内完成安装 | 计时执行 `time ./install_epftoolbox.sh` |
| 2 | 5 个数据集文件均成功下载到 `data/epftoolbox_datasets/` | `ls -la data/epftoolbox_datasets/` 列出 5 个 CSV |
| 3 | 每个数据集文件行数 >= 1000 | `wc -l data/epftoolbox_datasets/*.csv` |
| 4 | 统计输出包含所有 7 个指标（mean, median, std, min, max, missing, missing_rate） | 控制台输出包含每个指标的标注行 |
| 5 | 主虚拟环境 `.venv/` 不受影响 | `source .venv/bin/activate && python -c "import epftoolbox"` 报错 ImportError（预期行为） |

### 幂等标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 6 | 脚本第二次运行快速完成（安装部分跳过） | 第二次运行 <= 30 秒（无网络依赖） |
| 7 | `--reinstall` 强制重建环境 | venv 目录 mtime 更新，epftoolbox 版本无变化 |
| 8 | `--skip-download` 不产生网络请求 | 断网运行通过，数据集文件不变 |

### 数据完整性标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 9 | 每个 CSV 包含 price 列，且无全空列 | `python -c "import pandas as pd; [print(pd.read_csv(f).isnull().all().any()) for f in glob('*.csv')]"` 均输出 False |
| 10 | 时间范围覆盖至少 2 年 | 加载每个数据集，检查 `year` 列 min/max 跨度 >= 2 |
