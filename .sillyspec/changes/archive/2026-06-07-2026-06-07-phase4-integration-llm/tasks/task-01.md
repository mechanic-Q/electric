---
id: task-01
title: Phase 4 依赖声明
priority: P0
estimated_hours: 0.5
depends_on: []
blocks: [task-02]
allowed_paths:
  - ellectric/requirements-phase4.txt
  - ellectric/requirements.txt
---

# task-01: Phase 4 依赖声明

## 修改文件
- **新增**: `ellectric/requirements-phase4.txt`
- **修改**: `ellectric/requirements.txt` (末尾追加 Phase 4 依赖引用)

## 实现要求
1. 创建 `ellectric/requirements-phase4.txt`，声明 Phase 4 7 个依赖及其版本（>= pin，与 STACK.md / design.md 对齐）：
   - `fastapi>=0.136.1`
   - `uvicorn>=0.47.0`
   - `pydantic>=2.13.4`
   - `typer>=0.15`
   - `langchain>=1.3.1`
   - `langchain-openai>=0.3`
   - `httpx>=0.27`
2. 在 `ellectric/requirements.txt` 末尾追加：
   - 一行空行
   - 一行注释 `# ── Phase 4: API + CLI + LLM ──`
   - 一行 `-r requirements-phase4.txt`
3. 所有版本与 STACK.md 对齐（fastapi/uvicorn/pydantic/langchain 来自 STACK.md；typer/langchain-openai/httpx 来自 design.md）

## 边界处理（必填）
- 如果 `requirements.txt` 已包含 Phase 4 引用则跳过（幂等）
- 如果 STACK.md 或 design.md 有更高版本则用更高版本
- 文件必须 UTF-8 编码，LF 换行
- `requirements-phase4.txt` 不可为空（至少 5 行，含注释行）
- 不删除或移动已有 `requirements.txt` 内容

## 非目标（本任务不做的事）
- 不实际安装依赖（`pip install` 在 execute 阶段由 runner 执行）
- 不修改其他 requirements 文件（如 `requirements-assume.txt`）
- 不添加 `chromadb` 或 `sentence-transformers`（RAG 不在 Phase 4 MVP 范围）
- 不添加 `langchain-community`（使用 `langchain-openai` 直连 DeepSeek API）
- 不创建 `pyproject.toml` 或其他包管理文件

## TDD 步骤
1. **检查**: 读取 `requirements.txt` 末尾，确认无 Phase 4 引用 → 如有则跳过
2. **写入**: 创建 `requirements-phase4.txt`，包含 7 个依赖 + 文件头注释
3. **追加**: 在 `requirements.txt` 末尾追加 Phase 4 块（空行 + 注释 + `-r` 引用）
4. **验证语法**: `pip install -r ellectric/requirements-phase4.txt --dry-run` 或 `python -c "import re; [re.match(r'^[a-z][a-z0-9_-]*[><=]', l.strip()) for l in open('ellectric/requirements-phase4.txt') if l.strip() and not l.startswith('#')]"`
5. **确认 diff**: `git diff --stat` 验证只增不改原有内容

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| AC-01 | `cat ellectric/requirements-phase4.txt` | 包含 fastapi / uvicorn / pydantic / typer / langchain / langchain-openai / httpx 共 7 项，格式为 `package>=version` |
| AC-02 | `tail -5 ellectric/requirements.txt` | 包含空行、注释行 `# ── Phase 4: API + CLI + LLM ──`、以及 `-r requirements-phase4.txt` |
| AC-03 | `python -c "import re; lines=[l.strip() for l in open('ellectric/requirements-phase4.txt') if l.strip() and not l.startswith('#')]; assert all(re.match(r'^[a-z][a-z0-9_-]*[><=]', l) for l in lines), 'invalid format'; assert len(lines) == 7, f'expected 7 deps, got {len(lines)}'; print('OK: 7 valid deps')"` | 输出 `OK: 7 valid deps` |
| AC-04 | `git diff ellectric/requirements.txt` | 原文件内容无删除、无修改，仅末尾插入 ≤5 行 |
| AC-05 | `wc -l ellectric/requirements-phase4.txt` | 返回值 >= 5（至少 1 行注释 + 7 行依赖，预期 10-12 行） |
