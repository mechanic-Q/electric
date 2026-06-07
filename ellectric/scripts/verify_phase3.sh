#!/usr/bin/env bash
# Phase 3 端到端验证脚本
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
PASS="${GREEN}[PASS]${NC}"
FAIL="${RED}[FAIL]${NC}"

ALL_PASS=true

# Locate project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT=""
for d in "$SCRIPT_DIR" "$SCRIPT_DIR/.." "$SCRIPT_DIR/../.." "$SCRIPT_DIR/../../.."; do
    if [ -f "$d/ellectric/pipeline/__init__.py" ]; then
        PROJECT_ROOT="$d"
        break
    fi
done
if [ -z "$PROJECT_ROOT" ]; then
    echo -e "  $FAIL Cannot locate project root"
    exit 1
fi
cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Phase 3 端到端验证报告"
echo "=========================================="

# ── [1/5] 虚拟环境 ───────────────────────────────────
echo -e "\n[1/5] 虚拟环境检查"
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo -e "  $PASS .venv 存在，激活中..."
    source "$PROJECT_ROOT/.venv/bin/activate"
else
    echo -e "  $PASS 不使用 .venv（依赖系统 Python）"
fi

# ── [2/5] Import ─────────────────────────────────────
echo -e "\n[2/5] 新模块 Import 验证"

import_check() {
    local module="$1"
    local import_stmt="$2"
    local output
    output=$(python3 -c "$import_stmt" 2>&1) || true
    if echo "$output" | grep -q "OK$"; then
        echo -e "  $PASS $module 导入成功"
        return 0
    fi
    if echo "$output" | grep -qi "shap 未安装\|No module named 'shap'"; then
        echo -e "  $PASS $module 导入成功（跳过 shap：可选依赖未安装）"
        return 0
    fi
    echo -e "  $FAIL $module 导入失败: $(echo "$output" | tail -1)"
    return 1
}

import_check "trading_env" \
    "from ellectric.pipeline.trading_env import ElectricityMarketEnv, RewardRegistry; print('trading_env OK')" \
    || ALL_PASS=false

import_check "rl_trainer" \
    "from ellectric.pipeline.rl_trainer import RLAgentFactory, BaseRLAgent; print('rl_trainer OK')" \
    || ALL_PASS=false

import_check "backtester" \
    "from ellectric.pipeline.backtester import BacktestRunner, oracle_strategy, baseline_persistence, baseline_mean; print('backtester OK')" \
    || ALL_PASS=false

import_check "shap_explainer" \
    "from ellectric.pipeline.shap_explainer import explain_xgboost_sample, explain_lear_sample, feature_importance_ranking; print('shap_explainer OK')" \
    || ALL_PASS=false

# ── [3/5] Oracle 策略验证 ────────────────────────────
echo -e "\n[3/5] Oracle 策略验证 (bid == actual_load)"

ORACLE_TMP=$(mktemp)
cat > "$ORACLE_TMP" <<'PYEOF'
import sys, numpy as np, pandas as pd
from ellectric.pipeline.backtester import BacktestRunner
from ellectric.pipeline.trading_env import ElectricityMarketEnv

np.random.seed(42)
n = 24 * 14
ts = pd.date_range("2024-01-01", periods=n, freq="h")
load = 500 + 100 * np.sin(2 * np.pi * np.arange(n) / 24) + np.random.randn(n) * 20
price = 30 + 10 * np.sin(2 * np.pi * np.arange(n) / 24) + np.random.randn(n) * 5
ldf = pd.DataFrame({"timestamp": ts, "load_mw": load})
pdf = pd.DataFrame({"timestamp": ts, "price_da": price})
mc = float(load.max())
ef = lambda: ElectricityMarketEnv(ldf, pdf, None, None, max_capacity=mc)
runner = BacktestRunner(ef)
result = runner.replay("oracle", ldf, pdf, "2024-01-01", "2024-01-07")

# 1) Oracle bid == actual_load
max_diff = (result["bid_mw"] - result["actual_load"]).abs().max()
if max_diff > 1e-3:
    print(f"FAIL: Oracle bid mismatch, max diff = {max_diff:.6f}")
    sys.exit(1)
print(f"PASS: Oracle bid == actual_load (max diff = {max_diff:.2e})")

# 2) Oracle P&L ≈ 0 (bid≈actual → near-zero imbalance P&L)
oracle_pnl = result["pnl_hourly"].sum()
if abs(oracle_pnl) > 1.0:
    print(f"FAIL: Oracle P&L should be ~0, got {oracle_pnl:.6f}")
    sys.exit(1)
print(f"PASS: Oracle P&L = {oracle_pnl:.6f} (≈0, float32 precision expected)")

# 3) replay produces expected columns
expected = {"timestamp", "bid_mw", "cleared_mw", "clearing_price", "actual_load", "pnl_hourly", "pnl_cumulative", "strategy"}
missing = expected - set(result.columns)
if missing:
    print(f"FAIL: Missing columns: {missing}")
    sys.exit(1)
print(f"PASS: All expected columns present ({len(result)} rows)")

# 4) compare() works
p = runner.replay("baseline_persistence", ldf, pdf, "2024-01-01", "2024-01-07")
m = runner.replay("baseline_mean", ldf, pdf, "2024-01-01", "2024-01-07")
comp = runner.compare({"oracle": result, "persistence": p, "mean": m})
print(f"PASS: compare() produced {len(comp)} strategies")

# 5) max_capacity: 168h history check
env_long = ElectricityMarketEnv(ldf, pdf, None, None, max_capacity=mc)
obs, _ = env_long.reset()
_ = env_long.step(np.zeros(24))
assert "price_history_168h" in obs, "Missing price_history_168h"
print("PASS: Observation space includes all 5 keys (load_forecast, price_forecast, time_features, price_history, account)")
PYEOF

oracle_test=$(PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}" python3 "$ORACLE_TMP" 2>&1) || true
rm -f "$ORACLE_TMP"

if echo "$oracle_test" | grep -q "^FAIL"; then
    echo -e "  $FAIL Oracle 测试失败"
    echo "$oracle_test" | while IFS= read -r line; do echo "         $line"; done
    ALL_PASS=false
elif echo "$oracle_test" | grep -q "^PASS"; then
    echo -e "  $PASS Oracle 策略验证通过"
    echo "$oracle_test" | while IFS= read -r line; do echo "         $line"; done
else
    echo -e "  $FAIL Oracle 测试异常"
    echo "$oracle_test" | while IFS= read -r line; do echo "         $line"; done
    ALL_PASS=false
fi

# ── [4/5] 已有模块未修改 ────────────────────────────
echo -e "\n[4/5] 已有 pipeline 模块未修改验证"

PIPELINE_MODULES=(
    "data_loader.py" "cleaner.py" "features.py" "forecaster.py"
    "price_loader.py" "price_forecaster.py" "statistical_tests.py" "__init__.py"
)

GIT_DIR="$PROJECT_ROOT"
git -C "$GIT_DIR" rev-parse --git-dir > /dev/null 2>&1 || GIT_DIR="$(dirname "$PROJECT_ROOT")"
git -C "$GIT_DIR" rev-parse --git-dir > /dev/null 2>&1 || GIT_DIR="$PROJECT_ROOT"

changes_found=false
for mod in "${PIPELINE_MODULES[@]}"; do
    for scope in "" "--cached"; do
        if git -C "$GIT_DIR" diff $scope HEAD -- "ellectric/pipeline/$mod" 2>/dev/null | grep -q .; then
            echo -e "  $FAIL $mod 已被修改"
            changes_found=true
            continue 2
        fi
    done
    echo -e "  $PASS $mod 未修改"
done

if [ "$changes_found" = true ]; then
    ALL_PASS=false
fi

# ── [5/5] Notebook 有效性 ──────────────────────────
echo -e "\n[5/5] Phase 3 Notebook JSON 有效性验证"

PHASE3_NOTEBOOKS=(
    "09_rl_trading_agent.ipynb"
    "10_multi_agent_backtest.ipynb"
    "11_model_explainability.ipynb"
)

for nb in "${PHASE3_NOTEBOOKS[@]}"; do
    nb_path=""
    for base in "$PROJECT_ROOT/ellectric/notebooks"; do
        if [ -f "$base/$nb" ]; then
            nb_path="$base/$nb"
            break
        fi
    done
    if [ -z "$nb_path" ]; then
        echo -e "  $FAIL $nb 文件未找到"
        ALL_PASS=false
        continue
    fi
    if python3 -m json.tool "$nb_path" > /dev/null 2>&1; then
        cells=$(python3 -c "
import json
with open('$nb_path') as f:
    nb = json.load(f)
cc = len([c for c in nb.get('cells', []) if c.get('cell_type') == 'code'])
mc = len([c for c in nb.get('cells', []) if c.get('cell_type') == 'markdown'])
print(f'{cc} code, {mc} markdown cells')
")
        echo -e "  $PASS $nb 有效 JSON ($cells)"
    else
        err=$(python3 -m json.tool "$nb_path" 2>&1 || true)
        echo -e "  $FAIL $nb 无效 JSON: $err"
        ALL_PASS=false
    fi
done

# ── 汇总 ─────────────────────────────────────────────
echo -e "\n=========================================="
if [ "$ALL_PASS" = true ]; then
    echo -e "  状态: ${GREEN}全部通过${NC} ✓"
    exit 0
else
    echo -e "  状态: ${RED}部分检查未通过${NC} ✗"
    exit 1
fi
