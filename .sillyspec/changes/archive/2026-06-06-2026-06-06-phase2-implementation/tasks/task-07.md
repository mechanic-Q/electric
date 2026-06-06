---
id: task-07
title: 安装 ASSUME + 验证可运行
author: lmr
created_at: 2026-06-06T19:36:10+08:00
priority: P0
estimated_hours: 1
depends_on: []
blocks: [task-08]
allowed_paths:
  - ellectric/requirements-assume.txt
  - ellectric/scripts/verify_assume.py
  - ellectric/README.md
---

# Task-07: 安装 ASSUME + 验证可运行

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `ellectric/requirements-assume.txt` | 新增 | ASSUME + stable-baselines3 依赖锁定 |
| `ellectric/scripts/verify_assume.py` | 新增 | 验证脚本：导入检查 + 最小仿真运行 |
| `ellectric/README.md` | 修改 | 追加 ASSUME 安装说明 |
| `(跳过 docker-compose.yml — task-10 负责)` | — | — |

---

## 实现要求

### 1. 安装 ASSUME Core

```bash
pip install 'assume-framework==0.6.0[learning]'
```

- 安装核心包 + PyTorch (CPU) + stable-baselines3
- 不安装 `[network]` 或 `[all]`（PyPSA 非必需，Phase 3 需要时再装）
- Python 3.11+ 兼容性已验证

### 2. 锁定依赖到 `requirements-assume.txt`

生成可重现的锁定文件：

```bash
pip freeze | grep -E "assume|stable-baselines3|sb3|gymnasium|torch" > ellectric/requirements-assume.txt
```

必须包含的包：
- `assume-framework==0.6.0`
- `stable-baselines3>=2.0.0`
- `torch>=2.0.0` (CPU 版本)
- `gymnasium>=1.0.0`

### 3. 创建验证脚本 `verify_assume.py`

脚本必须完成以下验证：

1. **导入验证**: `from assume import World` 成功
2. **版本检查**: 打印 ASSUME 版本号
3. **最小仿真**: 调用 `World` 运行一个仿真实例（使用内建示例配置），验证仿真完成后输出结果
4. **错误处理**: 捕获所有异常，输出明确的诊断信息

### 4. docker-compose.yml

不修改 `docker-compose.yml` — task-10 负责启用 TimescaleDB + Grafana 服务。
task-07 的仿真验证使用 ASSUME 内建 CSV 输出即可。

### 5. 修改 README

在 README 中追加 ASSUME 安装验证章节，包括：
- 安装命令
- 验证命令
- 预期输出示例

---

## 接口定义

### `verify_assume.py`

```python
def check_imports() -> bool:
    """验证 ASSUME 和相关依赖可导入"""

def check_version() -> str:
    """返回 ASSUME 版本字符串"""

def run_minimal_simulation() -> dict:
    """
    运行 ASSUME 内建最小仿真。

    返回:
        {
            "status": "success" | "failure",
            "clearing_prices": list[float],
            "dispatch": dict[str, float],
            "total_profit": float,
            "error": str | None
        }
    """

def main():
    """主入口：顺序执行三个检查，输出报告"""
```

### 命令行调用

```bash
python ellectric/scripts/verify_assume.py
```

预期输出格式：

```
========================================
ASSUME 安装验证报告
========================================
[PASS] ASSUME 导入成功         -> 版本: 0.6.0
[PASS] stable-baselines3 导入成功 -> 版本: 2.8.0
[PASS] PyTorch 导入成功         -> 版本: 2.x.x
[PASS] 最小仿真运行成功
       - 出清时段: 168 小时
       - 平均出清价格: 234.56 元/MWh
       - 智能体数量: 5
========================================
状态: 全部通过 ✓
========================================
```

---

## 边界处理

1. **网络不可用**: 如果 pip 安装时网络超时，使用国内 PyPI 镜像 `-i https://pypi.tuna.tsinghua.edu.cn/simple` 重试；验证脚本不依赖网络
2. **Python 版本不兼容**: 安装前检查 `sys.version_info >= (3, 11)`；如果 Python < 3.11，打印明确的错误信息和升级指引，不执行安装
3. **依赖冲突**: 如果 `assume-framework` 与已安装包冲突，建议在独立 venv 中安装；验证脚本在运行时自动检测冲突并报告
4. **无 GPU/CUDA**: `assume-framework[learning]` 默认安装 CPU-only PyTorch；验证脚本在 `torch.cuda.is_available()` 为 False 时不报错，仅输出 INFO 信息
5. **docker-compose 不存在**: 如果用户环境中无 docker-compose，TimescaleDB + Grafana 标记为"可选跳过"，仿真使用内建 CSV 输出回退
6. **安装中断**: 如果 `pip install` 中途中断（Ctrl+C 或网络断开），再次运行应可安全重入；不留下损坏的 partial install
7. **已安装旧版本**: `pip install assume-framework` 默认覆盖升级；验证脚本打印已安装版本和最新版本的对比

---

## 非目标

- ❌ 不配置中国省间市场 YAML（task-08 负责）
- ❌ 不修改 ASSUME 源代码
- ❌ 不运行 7 天长仿真（task-09 负责）
- ❌ 不训练 RL 智能体
- ❌ 不安装 Grafana 仪表板面板（task-10 负责）
- ❌ 不修改 `requirements.txt`（独立 `requirements-assume.txt`）
- ❌ 不部署到生产环境

---

## 参考

| 来源 | 链接 |
|------|------|
| ASSUME GitHub | https://github.com/assume-framework/assume |
| ASSUME PyPI | https://pypi.org/project/assume-framework/ |
| ASSUME 文档 | https://assume.readthedocs.io/en/latest/ |
| ASSUME 安装指南 | https://assume.readthedocs.io/en/latest/installation.html |
| stable-baselines3 | https://github.com/DLR-RM/stable-baselines3 |
| 国内 PyPI 镜像 | https://pypi.tuna.tsinghua.edu.cn/simple |
| AGENTS.md | `/mnt/e/Ellectric/AGENTS.md` — 项目技术栈定义 |
| STACK.md | `/mnt/e/Ellectric/research/STACK.md` — ASSUME 0.6.0 技术选型 |
| design.md Wave 3 | `../design.md` — 中国省间现货规则配置基线 |
| plan.md 任务表 | `../plan.md` — 依赖关系: task-07 → task-08 → task-09 → task-10 |

---

## TDD 步骤

### 步骤 1: 安装 ASSUME

```bash
# 激活项目 venv
source ellectric/.venv/bin/activate
# 安装
pip install 'assume-framework==0.6.0[learning]'
# 锁定依赖
pip freeze | grep -E "assume|stable-baselines3|sb3|gymnasium|torch" > ellectric/requirements-assume.txt
```

**验证**: `pip list | grep assume` → `assume-framework 0.6.0`

### 步骤 2: 编写验证脚本

创建 `ellectric/scripts/verify_assume.py`，包含 `check_imports()`、`check_version()`、`run_minimal_simulation()`。

**验证**: `python ellectric/scripts/verify_assume.py` 退出码 0，所有检查 PASS。

### 步骤 3: 运行最小仿真

在验证脚本中调用 ASSUME 内建示例配置（如 `example_01a` 或 `World` 的默认初始化），等待仿真完成。

**验证**: 输出包含 `clearing_prices` 和 `dispatch`，`status` 为 `"success"`。

### 步骤 4: docker-compose.yml

不修改 docker-compose.yml — task-10 负责 TimescaleDB + Grafana 配置。

**验证**: verify_assume.py 不依赖 Docker，全部 PASS 即完成。

### 步骤 5: 更新 README

在 `ellectric/README.md` 追加 ASSUME 安装验证章节。

**验证**: README 包含"安装 ASSUME"和"验证安装"子章节。

### 步骤 6: 清理

```bash
rm -f assume_framework-0.6.0-py3-none-any.whl
```

---

## 验收标准

| 编号 | 标准 | 验证方式 | P/F |
|------|------|----------|-----|
| AC-01 | `pip install 'assume-framework==0.6.0[learning]'` 成功 | 安装命令退出码 0 | |
| AC-02 | `from assume import World` 无报错 | `python -c "from assume import World; print(World)"` 输出类信息 | |
| AC-03 | `from stable_baselines3 import PPO` 无报错 | `python -c "from stable_baselines3 import PPO; print(PPO)"` 输出类信息 | |
| AC-04 | `verify_assume.py` 全部 4 项 PASS | 执行脚本，退出码 0，检查点全部 [PASS] | |
| AC-05 | 最小仿真完成，输出出清价格列表 | `verify_assume.py` 输出包含 `clearing_prices` 非空列表 | |
| AC-06 | （跳过 — task-10 负责 Docker Compose 配置） | — | |
| AC-07 | README 包含 ASSUME 安装章节 | `grep -c "安装 ASSUME\|Installing ASSUME" ellectric/README.md` ≥ 1 | |
| AC-08 | `requirements-assume.txt` 存在且非空 | `wc -l ellectric/requirements-assume.txt` ≥ 5 | |
| AC-09 | Python < 3.11 时给出明确错误 | 脚本中 `sys.version_info` 检查逻辑存在（代码审查） | |
| AC-10 | 无 GPU 时不报错，仅 INFO | 脚本在不带 CUDA 的环境中运行，无 Error 日志 | |

### Wave 3 集成验收

| 编号 | 标准 | 关联 |
|------|------|------|
| AC-W3-01 | task-07 完成 → task-08 可开始 | 依赖 `pip install assume-framework` 成功 |
| AC-W3-02 | ASSUME 安装状态在 progress.json 记录 | `progress.json` 中 task-07 标记为 done |
