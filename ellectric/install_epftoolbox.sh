#!/usr/bin/env bash
#
# install_epftoolbox.sh — epftoolbox 独立虚拟环境安装 + 5 个基准数据集下载
#
# 用法:
#   ./install_epftoolbox.sh                     # 完整安装 + 下载 + 统计
#   ./install_epftoolbox.sh --skip-download     # 仅安装依赖，跳过数据集下载
#   ./install_epftoolbox.sh --reinstall         # 强制重建 venv + 重新安装
#   ./install_epftoolbox.sh --dataset-only      # 仅下载/刷新数据集（假设 venv 已存在）
#
# 功能:
#   1. 创建 .venv_epftoolbox 虚拟环境
#   2. 安装 tensorflow + epftoolbox (git source)
#   3. 下载 5 个基准数据集 (EPEX-BE/FR/DE, NordPool, PJM)
#   4. 输出每个数据集的统计信息 (mean, median, std, min, max, missing%)
#   5. 将 .venv_epftoolbox/ 添加到 .gitignore
#
# 预期时间: 15-30 分钟（取决于网络速度，主要是 TF wheel 包下载）
# 国内网络: 自动检测并使用清华 PyPI 镜像

set -euo pipefail

# ── 颜色定义 (同 setup.sh) ─────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── 默认值 ─────────────────────────────────────────────────────
SKIP_DOWNLOAD=false
REINSTALL=false
DATASET_ONLY=false

# ── 命令行参数解析 ─────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-download) SKIP_DOWNLOAD=true; shift ;;
        --reinstall) REINSTALL=true; shift ;;
        --dataset-only) DATASET_ONLY=true; shift ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            echo "用法: $0 [--skip-download] [--reinstall] [--dataset-only]"
            exit 1
            ;;
    esac
done

# ── Banner ─────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  epftoolbox 独立环境安装"
echo "  基准数据集: EPEX-BE  EPEX-FR  EPEX-DE  NordPool  PJM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 脚本目录检测 ──────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ "$(basename "$SCRIPT_DIR")" != "ellectric" ]]; then
    echo -e "${YELLOW}警告: 脚本应在 ellectric/ 目录运行${NC}"
    echo "  当前目录: $SCRIPT_DIR"
    echo "  请从项目根目录运行: ./ellectric/install_epftoolbox.sh"
    exit 1
fi

VENV_DIR="$SCRIPT_DIR/.venv_epftoolbox"
DATA_DIR="$SCRIPT_DIR/data/epftoolbox_datasets"

# ── 检查 Python 版本 ──────────────────────────────────────────
echo "→ 检查 Python 版本..."
PYTHON=""
for cmd in python3.12 python3.11 python3; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        if [ -n "$ver" ]; then
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                PYTHON="$cmd"
                break
            fi
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}错误: 需要 Python 3.9+，未找到。${NC}"
    echo "  epftoolbox 依赖 TensorFlow，TF 2.16+ 已停止支持 Python 3.8。"
    echo "  请安装 Python 3.9 或以上版本: https://www.python.org/downloads/"
    exit 1
fi

if [ "$minor" -lt 11 ]; then
    echo -e "${YELLOW}警告: 推荐 Python 3.11+，当前为 $($PYTHON --version)${NC}"
    echo "  epftoolbox 在 Python 3.9/3.10 上可能功能受限。"
fi
echo -e "  ${GREEN}✓${NC} 找到 $PYTHON ($($PYTHON --version))"

# ── 确定脚本用 Python ─────────────────────────────────────────
if [ -f "$VENV_DIR/bin/python" ]; then
    VENV_PYTHON="$VENV_DIR/bin/python"
else
    VENV_PYTHON=""
fi

# ================================================================
#  数据集下载 + 统计函数（嵌入 Python）
# ================================================================
download_datasets() {
    local py_interp="$1"
    local data_dir="$2"

    echo ""
    echo "→ 检查磁盘空间..."
    mkdir -p "$data_dir"
    local available_kb
    available_kb=$(df "$data_dir" | awk 'NR==2 {print $4}')
    if [ "$available_kb" -lt 512000 ]; then
        echo -e "${YELLOW}警告: $data_dir 所在分区可用空间不足 500MB${NC}"
        echo "  当前可用: $(( available_kb / 1024 )) MB"
        echo "  继续下载可能导致磁盘满。按 Ctrl+C 取消..."
    else
        echo -e "  ${GREEN}✓${NC} 磁盘空间充足 ($(( available_kb / 1024 )) MB 可用)"
    fi

    echo ""
    echo "→ 下载数据集..."
    echo "  目标目录: $data_dir"
    echo ""

    _DATA_DIR="$data_dir" "$py_interp" << 'PYEOF'
import os
import sys
import urllib.request
import time
import pandas as pd

data_dir = os.environ["_DATA_DIR"]
os.makedirs(data_dir, exist_ok=True)

DATASETS = [
    {
        "key": "EPEX_BE",
        "url": "https://raw.githubusercontent.com/jeslago/epftoolbox/master/epftoolbox/data/EPEX_BE.csv",
        "file": "epex_be.csv",
        "name": "EPEX-BE",
        "market": "Belgium day-ahead",
        "currency": "\u20ac/MWh"
    },
    {
        "key": "EPEX_FR",
        "url": "https://raw.githubusercontent.com/jeslago/epftoolbox/master/epftoolbox/data/EPEX_FR.csv",
        "file": "epex_fr.csv",
        "name": "EPEX-FR",
        "market": "France day-ahead",
        "currency": "\u20ac/MWh"
    },
    {
        "key": "EPEX_DE",
        "url": "https://raw.githubusercontent.com/jeslago/epftoolbox/master/epftoolbox/data/EPEX_DE.csv",
        "file": "epex_de.csv",
        "name": "EPEX-DE",
        "market": "Germany day-ahead",
        "currency": "\u20ac/MWh"
    },
    {
        "key": "NordPool",
        "url": "https://raw.githubusercontent.com/jeslago/epftoolbox/master/epftoolbox/data/NordPool.csv",
        "file": "nordpool.csv",
        "name": "NordPool",
        "market": "Nordic day-ahead",
        "currency": "\u20ac/MWh"
    },
    {
        "key": "PJM",
        "url": "https://raw.githubusercontent.com/jeslago/epftoolbox/master/epftoolbox/data/PJM.csv",
        "file": "pjm.csv",
        "name": "PJM",
        "market": "US Pennsylvania-Jersey-Maryland",
        "currency": "$/MWh"
    }
]

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"

def download_file(url, filepath, timeout=30):
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Ellectric/1.0 (learning platform)"
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            with open(filepath, "wb") as f:
                f.write(raw)
            return True, None
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2)
            else:
                return False, str(e)

results = {}
for ds in DATASETS:
    filepath = os.path.join(data_dir, ds["file"])
    print(f"  [{ds['name']}] {ds['market']}")
    print(f"    源: {ds['url']}")

    success, err = download_file(ds["url"], filepath)
    results[ds["key"]] = success

    if success:
        size = os.path.getsize(filepath)
        print(f"    {GREEN}\u2713{NC} {ds['file']}  ({size:,} bytes)")
    else:
        print(f"    {RED}\u2717{NC} 下载失败: {err}")
    print()

# ── 统计输出 ──────────────────────────────────────
separator = "\u2501" * 70
print(separator)
print("  数据集统计")
print(separator)
print()

for ds in DATASETS:
    filepath = os.path.join(data_dir, ds["file"])
    status = "\u2713" if results.get(ds["key"]) else "\u2717"
    print(f"Dataset: {ds['name']} [{status}]")

    if not results.get(ds["key"]):
        print(f"  {RED}下载失败，跳过统计{NC}")
        print("  ---")
        print()
        continue

    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig", encoding_errors="replace")
        rows, cols = df.shape
        has_price = "price" in df.columns
        has_year = "year" in df.columns

        if has_year:
            ymin = int(df["year"].min())
            ymax = int(df["year"].max())
            drange = f"{ymin}-01-01 ~ {ymax}-12-31"
        else:
            drange = "N/A"

        print(f"  Rows: {rows:<7} | Columns: {cols:<6} | Date range: {drange}")

        if has_price:
            p = df["price"].dropna()
            missing = int(df["price"].isna().sum())
            rate = missing / rows * 100 if rows > 0 else 0.0
            print(f"  Price ({ds['currency']}):")
            print(f"    Mean:   {p.mean():>10.2f}")
            print(f"    Median: {p.median():>10.2f}")
            print(f"    Std:    {p.std():>10.2f}")
            print(f"    Min:    {p.min():>10.2f}")
            print(f"    Max:    {p.max():>10.2f}")
            print(f"    Missing: {missing} ({rate:.2f}%)")
        else:
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                col = numeric_cols[0]
                vals = df[col].dropna()
                missing = int(df[col].isna().sum())
                rate = missing / rows * 100 if rows > 0 else 0.0
                print(f"  Column '{col}' ({ds['currency']}):")
                print(f"    Mean:   {vals.mean():>10.2f}")
                print(f"    Median: {vals.median():>10.2f}")
                print(f"    Std:    {vals.std():>10.2f}")
                print(f"    Min:    {vals.min():>10.2f}")
                print(f"    Max:    {vals.max():>10.2f}")
                print(f"    Missing: {missing} ({rate:.2f}%)")

        print(f"  Columns: {', '.join(df.columns.tolist())}")

    except Exception as e:
        print(f"  {RED}统计计算失败: {e}{NC}")

    print("  ---")
    print()
PYEOF

    local py_exit=$?
    if [ $py_exit -ne 0 ]; then
        echo -e "${RED}数据集下载脚本执行失败 (退出码: $py_exit)${NC}"
        return 1
    fi
    return 0
}

# ================================================================
#  仅数据集模式
# ================================================================
if [ "$DATASET_ONLY" = true ]; then
    echo "→ 仅数据集模式..."

    # 找可用的 Python
    DS_PYTHON=""
    if [ -n "$VENV_PYTHON" ]; then
        DS_PYTHON="$VENV_PYTHON"
        echo -e "  ${GREEN}✓${NC} 使用 venv Python"
    elif command -v python3 &>/dev/null; then
        if python3 -c "import pandas" &>/dev/null 2>&1; then
            DS_PYTHON="python3"
            echo -e "  ${YELLOW}⚠${NC} .venv_epftoolbox 不存在，使用系统 python3"
        else
            echo -e "${RED}错误: 系统 python3 缺少 pandas。${NC}"
            echo "  请先运行 ./install_epftoolbox.sh 创建完整环境。"
            exit 1
        fi
    else
        echo -e "${RED}错误: 找不到 Python 解释器${NC}"
        exit 1
    fi

    download_datasets "$DS_PYTHON" "$DATA_DIR"

    echo "→ 更新 .gitignore..."
    update_gitignore "$SCRIPT_DIR"

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  数据集处理完成！${NC}"
    echo "  目录: $DATA_DIR"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
fi

# ================================================================
#  Venv 管理
# ================================================================
echo ""
echo "→ 管理虚拟环境..."

if [ "$REINSTALL" = true ]; then
    if [ -d "$VENV_DIR" ]; then
        echo "  删除现有 venv (--reinstall)..."
        rm -rf "$VENV_DIR"
        echo -e "  ${GREEN}✓${NC} 已删除旧环境"
    fi
fi

INSTALL_DEPS=true
if [ -d "$VENV_DIR" ]; then
    if "$VENV_DIR/bin/python" -c "import epftoolbox" &>/dev/null 2>&1; then
        echo -e "  ${YELLOW}epftoolbox 已安装，跳过安装步骤${NC}"
        INSTALL_DEPS=false
    else
        echo -e "  ${YELLOW}.venv_epftoolbox 存在但 epftoolbox 不可用${NC}"
        echo "  提示: 如需重建请使用 --reinstall"
        echo "  继续尝试安装依赖..."
    fi
else
    echo "  创建虚拟环境..."
    $PYTHON -m venv "$VENV_DIR"
    echo -e "  ${GREEN}✓${NC} 虚拟环境创建完成"
    VENV_PYTHON="$VENV_DIR/bin/python"
fi

# ── 激活虚拟环境 ───────────────────────────────────────────────
source "$VENV_DIR/bin/activate"

# ── 安装依赖 ───────────────────────────────────────────────────
if [ "$INSTALL_DEPS" = true ]; then
    echo ""
    echo "→ 升级 pip..."
    pip install --quiet --upgrade pip
    echo -e "  ${GREEN}✓${NC} pip 已升级"

    # 镜像源检测
    echo ""
    echo "→ 测试 PyPI 网络连通性..."
    PIP_INDEX=""
    if curl -s --connect-timeout 3 https://pypi.org > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} PyPI 官方源可达"
    else
        PIP_INDEX="-i https://pypi.tuna.tsinghua.edu.cn/simple"
        echo -e "  ${YELLOW}!${NC} PyPI 不可达，使用清华镜像源"
    fi

    # 安装 tensorflow
    echo ""
    echo "→ 安装 tensorflow（epftoolbox 硬依赖，可能需要较长时间）..."
    if pip install $PIP_INDEX tensorflow; then
        echo -e "  ${GREEN}✓${NC} tensorflow 安装成功"
    else
        echo -e "${YELLOW}tensorflow 官方包安装失败，尝试 tensorflow-cpu...${NC}"
        if pip install $PIP_INDEX tensorflow-cpu; then
            echo -e "  ${GREEN}✓${NC} tensorflow-cpu 安装成功"
        else
            echo -e "${RED}错误: tensorflow 安装失败，请检查网络连接。${NC}"
            exit 1
        fi
    fi

    # 安装 epftoolbox（GitHub 直连，无镜像）
    echo ""
    echo "→ 安装 epftoolbox (git+https://github.com/jeslago/epftoolbox.git)..."
    if pip install git+https://github.com/jeslago/epftoolbox.git; then
        echo -e "  ${GREEN}✓${NC} epftoolbox 安装成功"
    else
        echo -e "${RED}错误: epftoolbox 安装失败。${NC}"
        echo "  GitHub 直连无镜像可用，请检查网络连接后重试:"
        echo "  pip install git+https://github.com/jeslago/epftoolbox.git"
        exit 1
    fi

    # 验证安装
    echo ""
    echo "→ 验证安装..."
    if python -c "import epftoolbox; print(f'  epftoolbox 版本: {epftoolbox.__version__}')" 2>&1; then
        echo -e "  ${GREEN}✓${NC} 安装验证通过"
    else
        echo -e "${RED}错误: epftoolbox 导入失败，环境可能损坏。${NC}"
        echo "  请使用 --reinstall 重建环境"
        exit 1
    fi
fi

# ================================================================
#  数据集下载
# ================================================================
if [ "$SKIP_DOWNLOAD" = false ]; then
    download_datasets "$VENV_DIR/bin/python" "$DATA_DIR"
else
    echo ""
    echo -e "  ${YELLOW}跳过数据集下载 (--skip-download)${NC}"
fi

# ================================================================
#  更新 .gitignore
# ================================================================
update_gitignore() {
    local dir="$1"
    local gitignore="$dir/.gitignore"
    local entry=".venv_epftoolbox/"
    if [ -f "$gitignore" ]; then
        if ! grep -qF "$entry" "$gitignore" 2>/dev/null; then
            echo "" >> "$gitignore"
            echo "# epftoolbox 独立虚拟环境" >> "$gitignore"
            echo "$entry" >> "$gitignore"
            echo -e "  ${GREEN}✓${NC} 已将 $entry 添加到 .gitignore"
        else
            echo -e "  ${YELLOW}$entry 已在 .gitignore 中${NC}"
        fi
    else
        echo "# epftoolbox 独立虚拟环境" > "$gitignore"
        echo "$entry" >> "$gitignore"
        echo -e "  ${GREEN}✓${NC} 已创建 .gitignore 并添加 $entry"
    fi
}

echo ""
echo "→ 更新 .gitignore..."
update_gitignore "$SCRIPT_DIR"

# ================================================================
#  完成
# ================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}  安装完成！${NC}"
echo ""
echo "  epftoolbox 环境: $VENV_DIR"
echo "  数据集目录:      $DATA_DIR"
echo ""
echo "  使用方式:"
echo "    source .venv_epftoolbox/bin/activate"
echo "    python -c \"from epftoolbox.datasets import load_EPEX_BE_dataset\""
echo ""
echo "  数据集文件:"
for ds in epex_be epex_fr epex_de nordpool pjm; do
    f="$DATA_DIR/$ds.csv"
    if [ -f "$f" ]; then
        size=$(wc -c < "$f" | tr -d ' ')
        rows=$(wc -l < "$f" | tr -d ' ')
        echo "    $ds.csv  ($size bytes, $rows 行)"
    else
        echo -e "    ${YELLOW}$ds.csv  (未下载)${NC}"
    fi
done
echo ""
echo "  再次运行可跳过已安装依赖:"
echo "    $0"
echo "  强制重建:"
echo "    $0 --reinstall"
echo "  仅下载数据集:"
echo "    $0 --dataset-only"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
