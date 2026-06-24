#!/usr/bin/env python3
"""verify_fetch_shanxi.py — task-04 验证脚本.

不实际调用网络（防 cookie 失效/反爬）。
仅验证: import / 类签名 / snapshot 目录逻辑 / cookie env 加载."""

import os, sys, tempfile, shutil, json
sys.path.insert(0, '.')

PASS = 0; FAIL = 0
def chk(label, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label} {detail}")

print("=" * 60)
print("fetch_shanxi 验证")
print("=" * 60)

# 1. 可 import
print("\n── 模块 import ──")
try:
    from ellectric.fetch import ShanxiFetcher
    chk("from ellectric.fetch import ShanxiFetcher", True)
except Exception as e:
    chk("import 失败", False, str(e)[:80])
    sys.exit(1)

try:
    from ellectric.fetch.shanxi import ShanxiFetcher as SF2, ALL_APIS, BASE_URL
    chk("ALL_APIS 18 个", len(ALL_APIS) == 18, f"got {len(ALL_APIS)}")
    chk("BASE_URL 正确", "pmos.sx.sgcc.com.cn" in BASE_URL)
except Exception as e:
    chk("ALL_APIS import", False, str(e)[:80])

# 2. cookie env 测试
print("\n── cookie 外部化 ──")
old_cookie = os.environ.pop("SHANXI_COOKIE", None)
try:
    try:
        ShanxiFetcher()
        chk("缺 cookie 应抛 ValueError", False, "未抛异常")
    except ValueError:
        chk("缺 cookie 抛 ValueError", True)

    os.environ["SHANXI_COOKIE"] = "test-token"
    f = ShanxiFetcher()
    chk("SHANXI_COOKIE env 读取", f.cookie == "test-token")
finally:
    if old_cookie:
        os.environ["SHANXI_COOKIE"] = old_cookie

# 3. 显式传 cookie
print("\n── 显式 cookie ──")
f = ShanxiFetcher(cookie="explicit-token")
chk("显式 cookie 优先", f.cookie == "explicit-token")

# 4. data_dir + snapshots 目录创建
print("\n── 目录自动创建 ──")
tmp = tempfile.mkdtemp()
try:
    f = ShanxiFetcher(cookie="t", data_dir=tmp + "/data")
    chk("data_dir 自动创建", os.path.isdir(tmp + "/data"))
    chk("snapshots 目录自动创建", os.path.isdir(tmp + "/data/snapshots"))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 5. snapshot 写入测试（不联网）
print("\n── snapshot 双输出 ──")
tmp = tempfile.mkdtemp()
try:
    f = ShanxiFetcher(cookie="t", data_dir=tmp)
    data = {"msg": "test", "code": 200, "data": [{"x": 1}]}
    snap = f._save_snapshot("spot_da", "2026-06", "2026-06-24", data)
    latest = f._save_latest("spot_da", "2026-06", data)
    chk("snapshot 文件存在", snap.exists())
    chk("latest 文件存在", latest.exists())
    chk("snapshot 路径含 2026-06-24", "2026-06-24" in str(snap))
    chk("latest 路径不含 snapshots", "snapshots" not in str(latest))
    # 第二次写 → 应追加 .1 后缀
    snap2 = f._save_snapshot("spot_da", "2026-06", "2026-06-24", data)
    chk("snapshot 第二次写入不覆盖", snap2 != snap)
    # 读回验证
    saved = json.loads(snap.read_text())
    chk("snapshot 内容正确", saved.get("code") == 200)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 6. 不影响现有 verify_shanxi_loader
print("\n── 现有 loader 不受影响 ──")
try:
    from ellectric.pipeline.data_loader import create_loader
    chk("data_loader 仍可 import", callable(create_loader))
except Exception as e:
    chk("data_loader import", False, str(e)[:80])

# 7. fetch_one source 校验
print("\n── source 校验 ──")
f = ShanxiFetcher(cookie="t")
try:
    f.fetch_one("invalid_source", "2026-06")
    chk("非法 source 应抛", False)
except ValueError as e:
    chk("非法 source 抛 ValueError", "未知" in str(e) or "unknown" in str(e).lower())

print(f"\n✅ {PASS} 通过 / ❌ {FAIL} 失败")
sys.exit(0 if FAIL == 0 else 1)
