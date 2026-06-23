---
id: task-06
title: 修改 pipeline/data_loader.py create_loader 添加 3 个 shanxi source
priority: P0
depends_on: [task-02, task-03, task-04, task-05]
blocks: []
requirement_ids: [FR-007, FR-008]
decision_ids: [D-004@v1]
author: lmr
created_at: 2026-06-23T15:10:00+08:00
allowed_paths:
  - ellectric/pipeline/data_loader.py
---

# task-06: 修改 pipeline/data_loader.py create_loader 添加 3 个 shanxi source

## 修改文件 (必填)

- `ellectric/pipeline/data_loader.py` — 仅修改 `create_loader()` 工厂函数（在 `elif source == "ember"` 分支之后追加 3 个 elif 分支 + 同步更新该函数 docstring + 同步更新最后兜底 `ValueError` 的错误信息列表）。**严禁修改**该文件的其他任何函数 / 类 / 顶层 import / 常量。

## 覆盖来源

- Requirements: FR-007（工厂扩展）、FR-008（现有 API 兼容性）
- Decisions: D-004@v1（create_loader 使用延迟导入）

## 实现要求

### 1. 定位修改点

打开 `ellectric/pipeline/data_loader.py`，定位到 `create_loader()` 函数当前末尾：

```python
elif source == "ember":
    # 延迟导入 — EmberLoader 是可选模块
    from ellectric.pipeline.ember_loader import EmberLoader
    return EmberLoader()
else:
    raise ValueError(f"未知数据源: {source}. 可选: 'owid', 'manual', 'file', 'ember'")
```

### 2. 在 `elif source == "ember"` 与 `else` 之间插入 3 个新 elif 分支

```python
elif source == "shanxi_spot_da":
    # 延迟导入 — ShanxiSpotDaLoader 位于独立模块（参照 D-005@v1）
    from ellectric.pipeline.shanxi_loader import ShanxiSpotDaLoader
    return ShanxiSpotDaLoader(**kwargs)
elif source == "shanxi_spot_rt":
    from ellectric.pipeline.shanxi_loader import ShanxiSpotRtLoader
    return ShanxiSpotRtLoader(**kwargs)
elif source == "shanxi_month_settle":
    from ellectric.pipeline.shanxi_loader import ShanxiMonthSettleLoader
    return ShanxiMonthSettleLoader(**kwargs)
```

### 3. 同步更新 `else` 分支错误信息

把原 `ValueError` 消息中的可选列表扩展为 7 项：

```python
else:
    raise ValueError(
        f"未知数据源: {source}. 可选: 'owid', 'manual', 'file', 'ember', "
        f"'shanxi_spot_da', 'shanxi_spot_rt', 'shanxi_month_settle'"
    )
```

### 4. 同步更新 `create_loader()` docstring 的 `source` 参数说明

在 Args 块中已有四行（owid / manual / file / ember）之后追加三行：

```
- "shanxi_spot_da"     : 山西日前出清价（15min 粒度，2022-04~2026-05）
- "shanxi_spot_rt"     : 山西实时出清电量（15min 粒度，2022-04~2026-05）
- "shanxi_month_settle": 山西月度结算电价（逐日分时，2018-01~2026-12）
```

可在 Example 块末尾追加（可选，但推荐）：

```
>>> loader = create_loader("shanxi_spot_da")
>>> df = loader.load_data(start="2022-04", end="2026-05")
```

### 5. 严格不动的部分

- 不动顶层 `import` 区块（不在文件头新增 `from ellectric.pipeline.shanxi_loader import ...`）
- 不动 `DataLoader` 抽象基类
- 不动 `OWIDChinaLoader`、`ChineseDataLoader` 任何方法体
- 不动 `_safe_float`、`_twh_to_daily_mw`、`_standardize_columns` 等工具函数
- 不动 `OWID_*` 常量
- 不动 `create_loader()` 函数签名 `def create_loader(source: str = "owid", **kwargs) -> DataLoader:`

## 接口定义 (代码类任务必填)

### `create_loader()` 完整目标签名

```python
def create_loader(source: str = "owid", **kwargs) -> DataLoader:
    """
    创建数据加载器的工厂函数。

    Args:
        source: 数据源类型
            - "owid"               : OWID 中国年级数据（自动拉取，三级回退）
            - "manual"             : 手动下载的日/小时数据
            - "file"               : 同 manual，传 kwarg data_path
            - "ember"              : Ember Climate 中国小时级数据（探索性）
            - "shanxi_spot_da"     : 山西日前出清价（15min 粒度，2022-04~2026-05）
            - "shanxi_spot_rt"     : 山西实时出清电量（15min 粒度，2022-04~2026-05）
            - "shanxi_month_settle": 山西月度结算电价（逐日分时，2018-01~2026-12）
        **kwargs: 透传给具体子类构造器（如 data_path / data_dir）

    Returns:
        对应的 DataLoader 实例

    Example:
        >>> loader = create_loader("owid")
        >>> df = loader.load_data()
        >>> loader = create_loader("manual", data_path="data/guangdong_2023.csv")
        >>> df = loader.load_data(start="2023-01-01", end="2023-12-31")
        >>> loader = create_loader("ember")
        >>> df = loader.load_data(start="2024-01-01", end="2024-12-31")
        >>> loader = create_loader("shanxi_spot_da")
        >>> df = loader.load_data(start="2022-04", end="2026-05")
    """
    if source == "owid":
        return OWIDChinaLoader()
    elif source in ("manual", "file"):
        data_path = kwargs.get("data_path")
        if not data_path:
            raise ValueError("manual/file 模式需要指定 data_path 参数")
        return ChineseDataLoader(data_path=data_path)
    elif source == "ember":
        # 延迟导入 — EmberLoader 是可选模块
        from ellectric.pipeline.ember_loader import EmberLoader
        return EmberLoader()
    elif source == "shanxi_spot_da":
        # 延迟导入 — ShanxiSpotDaLoader 位于独立模块 shanxi_loader.py（D-004@v1, D-005@v1）
        from ellectric.pipeline.shanxi_loader import ShanxiSpotDaLoader
        return ShanxiSpotDaLoader(**kwargs)
    elif source == "shanxi_spot_rt":
        from ellectric.pipeline.shanxi_loader import ShanxiSpotRtLoader
        return ShanxiSpotRtLoader(**kwargs)
    elif source == "shanxi_month_settle":
        from ellectric.pipeline.shanxi_loader import ShanxiMonthSettleLoader
        return ShanxiMonthSettleLoader(**kwargs)
    else:
        raise ValueError(
            f"未知数据源: {source}. 可选: 'owid', 'manual', 'file', 'ember', "
            f"'shanxi_spot_da', 'shanxi_spot_rt', 'shanxi_month_settle'"
        )
```

### 控制流（伪代码）

```
INPUT  source: str  (默认 "owid")
INPUT  **kwargs    (data_path / data_dir 等)

IF source == "owid":             RETURN OWIDChinaLoader()
ELIF source in {"manual","file"}: VALIDATE data_path; RETURN ChineseDataLoader(data_path)
ELIF source == "ember":           LAZY-IMPORT EmberLoader;            RETURN EmberLoader()
ELIF source == "shanxi_spot_da":  LAZY-IMPORT ShanxiSpotDaLoader;     RETURN ShanxiSpotDaLoader(**kwargs)
ELIF source == "shanxi_spot_rt":  LAZY-IMPORT ShanxiSpotRtLoader;     RETURN ShanxiSpotRtLoader(**kwargs)
ELIF source == "shanxi_month_settle": LAZY-IMPORT ShanxiMonthSettleLoader; RETURN ShanxiMonthSettleLoader(**kwargs)
ELSE:                             RAISE ValueError(列出全部 7 个可选 source)
```

### 关键约束

- **延迟导入**：3 个新 elif 分支必须使用函数内 `from ellectric.pipeline.shanxi_loader import XxxLoader`，**禁止**在 `data_loader.py` 文件头 `import` 区块新增 shanxi_loader 引用
- **kwargs 透传**：3 个 shanxi 分支均使用 `**kwargs`（参照 EmberLoader 的不同点：EmberLoader 不接受 kwargs；shanxi loader 接受可选 `data_dir`，故必须透传）
- **错误信息**：`else` 分支错误信息中可选列表必须完整列出全部 7 个 source key

## 边界处理 (至少 5 条)

1. **未知 source 字符串**：传入既不是 7 个合法 source key 也不是空串时，原 `else` 分支抛 `ValueError`，错误信息列举全部 7 个可选值（含新增 3 个），不静默返回 None。

2. **空字符串 / None**：传入 `""` 或 `None` 时同样落到 `else` 抛 `ValueError`；不在 elif 内做特殊处理（保持与既有 owid/manual/ember 同样行为，避免误兼容）。

3. **shanxi 分支 kwargs 异常**：用户传入 `create_loader("shanxi_spot_da", data_dir="/不存在/路径")` 时，`create_loader()` 本身不校验，原样透传给 `ShanxiSpotDaLoader(**kwargs)`；任何文件不存在的报错/警告由 task-02 实现的 `ShanxiBaseLoader.load_data()` 在 `load_data()` 时输出 WARNING，**不**由本任务的 `create_loader()` 提前拦截（保持工厂函数职责单一）。

4. **延迟导入失败**：若 `ellectric/pipeline/shanxi_loader.py` 不存在或 import 报错（如 task-02 尚未完成），分支内 `from ... import ...` 会自然抛 `ImportError`，**不** try/except 静默吞掉；让错误向上冒泡以便定位（与 EmberLoader 一致）。

5. **现有 source 不变**：`create_loader("owid")`、`create_loader("manual", data_path=p)`、`create_loader("file", data_path=p)`、`create_loader("ember")` 四种调用的返回类型、构造参数、副作用、抛错条件**完全保持现状**；新增 elif 分支放在 `elif source == "ember"` 之后、`else` 之前，不调整既有 if/elif 顺序。

6. **大小写敏感**：source 字符串保持大小写敏感（`"Shanxi_Spot_Da"` 不命中），与现有 owid/manual 行为一致；不引入 `.lower()` 之类的归一化。

7. **不修改全局状态**：本任务只新增 3 个 elif 分支，绝不在模块级别注入 import、修改 logger、添加全局缓存或注册表。

## 非目标 (本任务不做的事)

- ❌ 不实现 `ShanxiBaseLoader` / `ShanxiSpotDaLoader` / `ShanxiSpotRtLoader` / `ShanxiMonthSettleLoader` 类本身（由 task-02、task-03、task-04、task-05 完成）
- ❌ 不创建 `ellectric/pipeline/shanxi_loader.py` 文件（由 task-02 完成）
- ❌ 不修改 `OWIDChinaLoader` 或 `ChineseDataLoader`
- ❌ 不修改 `DataLoader` 抽象基类的方法签名或 `get_metadata()` 实现
- ❌ 不修改顶层 import（即不在 `data_loader.py` 文件头新增 shanxi 相关 import）
- ❌ 不实现验证脚本（由 task-07 完成）
- ❌ 不写 README（由 task-01 完成）
- ❌ 不写自动化测试用例（项目无 pytest 套件，验证走 task-07 verify 脚本）

## 参考

- 参考 `ellectric/pipeline/data_loader.py:512-515` 的 EmberLoader 延迟导入模式（本任务 3 个分支严格照抄此模式）
- 参考 `.sillyspec/changes/2026-06-22-shanxi-spot-data-access/design.md` 「IV. 工厂扩展」与「接口定义 → 工厂扩展」章节
- 参考 `.sillyspec/changes/2026-06-22-shanxi-spot-data-access/decisions.md` 「D-004@v1」决策完整理由
- 参考 `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md` 中关于 docstring 中英双语 / 段落分隔 / 类型标注的规范
- 参考 CLAUDE.md 「延迟导入」「可选依赖防护」段落

## TDD 步骤

1. **步骤 1（最小可解析）**：仅追加 3 个 elif 分支，暂不更新 docstring 与 else 错误信息；运行 `python -c "from ellectric.pipeline.data_loader import create_loader; print(create_loader)"` 确认模块仍可 import（顶层 import 没被污染）。

2. **步骤 2（已知 source 不变）**：运行 `python -c "from ellectric.pipeline.data_loader import create_loader; print(type(create_loader('owid')).__name__)"`，期望输出 `OWIDChinaLoader`；确认现有分支零行为变化。

3. **步骤 3（新 source 路由）**：假设 task-02~05 已完成 shanxi_loader.py，运行 `python -c "from ellectric.pipeline.data_loader import create_loader; print(type(create_loader('shanxi_spot_da')).__name__)"`，期望输出 `ShanxiSpotDaLoader`；对 `shanxi_spot_rt`、`shanxi_month_settle` 同样验证。

4. **步骤 4（kwargs 透传）**：运行 `create_loader("shanxi_spot_da", data_dir="ellectric/data/raw/shanxi")`，确认 `loader.data_dir == Path("ellectric/data/raw/shanxi")`（依赖 task-02 实现）。

5. **步骤 5（错误信息完整）**：运行 `create_loader("nonexistent")` 应抛 `ValueError`，且消息字符串中能 `grep` 到 7 个 source key 全部出现（'owid', 'manual', 'file', 'ember', 'shanxi_spot_da', 'shanxi_spot_rt', 'shanxi_month_settle'）。

6. **步骤 6（docstring 同步）**：`python -c "from ellectric.pipeline.data_loader import create_loader; print(create_loader.__doc__)"` 输出中应能找到 `shanxi_spot_da` / `shanxi_spot_rt` / `shanxi_month_settle` 三个字符串。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `git diff ellectric/pipeline/data_loader.py` 统计修改行数 | 新增行数 ≤ 30（仅 docstring 增 3-5 行 + 3 个 elif 共 9 行 + ValueError 信息扩展 1-2 行） |
| AC-02 | `grep -nE "^(import\|from)" ellectric/pipeline/data_loader.py \| grep -i shanxi` | 退出码非 0 或返回空（顶层 import 区块不含 shanxi_loader 引用） |
| AC-03 | `grep -c "from ellectric.pipeline.shanxi_loader import" ellectric/pipeline/data_loader.py` | 输出 `3`（3 个 elif 分支各一次延迟导入） |
| AC-04 | `python -c "from ellectric.pipeline.data_loader import create_loader; print(type(create_loader('owid')).__name__)"` | 输出 `OWIDChinaLoader`，退出码 0 |
| AC-05 | `python -c "from ellectric.pipeline.data_loader import create_loader; print(type(create_loader('shanxi_spot_da')).__name__)"`（需 task-02~05 已完成） | 输出 `ShanxiSpotDaLoader`，退出码 0 |
| AC-06 | `python -c "from ellectric.pipeline.data_loader import create_loader; print(type(create_loader('shanxi_spot_rt')).__name__)"` | 输出 `ShanxiSpotRtLoader`，退出码 0 |
| AC-07 | `python -c "from ellectric.pipeline.data_loader import create_loader; print(type(create_loader('shanxi_month_settle')).__name__)"` | 输出 `ShanxiMonthSettleLoader`，退出码 0 |
| AC-08 | `python -c "from ellectric.pipeline.data_loader import create_loader; create_loader('bogus')"` | 抛 `ValueError`，错误信息字符串同时包含 `'owid'`、`'manual'`、`'file'`、`'ember'`、`'shanxi_spot_da'`、`'shanxi_spot_rt'`、`'shanxi_month_settle'` 共 7 个子串 |
| AC-09 | `python -c "from ellectric.pipeline.data_loader import create_loader; assert 'shanxi_spot_da' in create_loader.__doc__ and 'shanxi_spot_rt' in create_loader.__doc__ and 'shanxi_month_settle' in create_loader.__doc__"` | 退出码 0（docstring 包含 3 个新 source 说明） |
| AC-10 | `git diff ellectric/pipeline/data_loader.py -- :^create_loader` 检查除 `create_loader` 函数体与其 docstring 外是否有改动 | 无任何其他函数/类/常量被改动（应只有 `create_loader` 一个函数内部 + 其 docstring 出现 diff） |
