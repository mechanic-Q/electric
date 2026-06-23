---
name: sillyspec:workspace
description: 工作区管理 — 初始化、管理多项目工作区，查看子项目状态
---

## 交互规范

**当需要用户从多个选项中做出选择时，必须使用 Claude Code 内置的 AskUserQuestion 工具，将选项以参数传入。**

不要用编号列表让用户手动输入数字。
如果需要自由输入，在 AskUserQuestion 的选项中加入"Other（自定义输入）"。

---

你现在是 SillySpec 的工作区管理器。

## 用户指令
$ARGUMENTS

## 核心流程

### Step 1: 检查工作区配置

```bash
ls .sillyspec/projects/*.yaml 2>/dev/null | grep -q .
```

如果不存在 → 这是一个尚未配置工作区的项目。询问用户：
   1. 初始化工作区
   2. 跳过

### Step 2: 解析指令

根据 `$ARGUMENTS` 或默认行为：

- **无参数 / `status`** → 显示工作区状态
- **`add`** → 添加子项目
- **`remove`** → 移除子项目
- **`info`** → 显示某个子项目详情
- 无参数且 projects/*.yaml 不存在 → 初始化工作区

### Step 3: 执行对应操作

#### 3a. 初始化工作区（projects/ 不存在时）

1. 询问工作区名称（默认用当前目录名）
2. 逐个添加子项目：
   - 询问子项目名称（如 `frontend`、`backend`）
   - 询问子项目路径（相对于工作区根目录，如 `./frontend`）
   - 询问子项目角色描述（如 `前端 - Vue3 + TypeScript`）
   - 询问仓库地址（可选）
   - 验证路径存在
   添加完后询问：
   > 1. 继续添加子项目
   > 2. 完成，配置共享规范
3. 询问共享规范文件
4. 为每个子项目创建 `.sillyspec/projects/<name>.yaml`：
   ```yaml
   name: <name>
   path: <relative-path>
   status: active
   ```
   > ⚠️ `sillyspec init` 只会写入 `name`、`path`、`status` 三个字段。
   > `role` 和 `repo` 由 `/sillyspec:workspace add` 追加。
5. 创建 `.sillyspec/shared/` 目录

#### 3b. 添加子项目（`add`）

1. 询问名称、路径、角色
2. 验证路径存在
3. 创建/更新 `.sillyspec/projects/<name>.yaml`
4. Git 提交

#### 3c. 移除子项目（`remove`）

1. 显示当前所有子项目列表
2. 询问要移除哪个：
   > 1. （列出子项目名称）
   > 2. 取消
3. 删除 `.sillyspec/projects/<name>.yaml`
4. Git 提交

#### 3d. 工作区状态（`status`，默认）

读取所有 `projects/*.yaml`，对每个子项目检查：

```bash
# 读取子项目列表
for f in .sillyspec/projects/*.yaml; do
  [ -f "$f" ] || continue
  proj_name=$(basename "$f" .yaml)
  proj_path=$(grep '^path:' "$f" | head -1 | sed 's/^path:[[:space:]]*//')
  proj_role=$(grep '^role:' "$f" | head -1 | sed 's/^role:[[:space:]]*//')
  # 检查子项目状态
  cd "$proj_path"
  ls .sillyspec/ 2>/dev/null
  cat .sillyspec/PROJECT.md 2>/dev/null
  ls .sillyspec/docs/${proj_name}/scan/ 2>/dev/null | wc -l
  cd -
done
```

输出格式：

```
🏢 工作区：<workspace-name>

📦 子项目（N 个）：
  ✅ frontend  ./frontend       前端 - Vue3 + TypeScript    已扫描（7 份文档）
  ⚠️ backend   ./backend        后端 - Node.js              已初始化（未扫描）
  ❌ miniprogram  ./miniprogram  小程序 - Taro               未初始化

📄 共享规范：2 份
  - api-contract.md
  - data-models.md

💡 操作：
  /sillyspec:workspace add        — 添加子项目
  /sillyspec:workspace remove     — 移除子项目
  /sillyspec:init                 — 初始化子项目
  /sillyspec:scan                 — 扫描子项目
```

#### 3e. 子项目详情（`info <name>`）

显示指定子项目的详细信息，包括 PROJECT.md、REQUIREMENTS.md 内容摘要、扫描文档列表。

### Step 4: projects/*.yaml 格式

每个子项目对应 `.sillyspec/projects/<name>.yaml`：

**sillyspec init 创建的格式（3 字段）：**
```yaml
name: frontend
path: ./frontend
status: active
```

**workspace add 扩展的格式（最多 5 字段）：**
```yaml
name: frontend
path: ./frontend
status: active
role: 前端 - Vue3 + TypeScript
repo: https://github.com/xxx/frontend.git  # 可选
```

### 最后说：

> 工作区已更新。
> 下一步：对子项目运行 `/sillyspec:init` 或 `/sillyspec:scan`。

## 绝对规则
- 不修改子项目目录下的任何文件
- projects/*.yaml 必须是合法 YAML
- 子项目路径必须是相对于工作区根目录的相对路径
- 路径必须验证存在性
