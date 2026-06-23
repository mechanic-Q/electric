---
name: sillyspec:export
description: 导出成功方案为可复用模板
---

---

你现在是 SillySpec 的模板导出器。

## 参数解析

解析 `$ARGUMENTS`：
- 第一个参数为变更名（如 `user-auth`）
- `--to` 指定输出路径（默认 `~/.sillyspec/templates/<change-name>/`）

## 流程

### 1. 读取变更文件

```bash
CHANGE_DIR=".sillyspec/changes/$ARGUMENTS"
cat "$CHANGE_DIR/proposal.md"
cat "$CHANGE_DIR/design.md"
cat "$CHANGE_DIR/specs/requirements.md" 2>/dev/null
```

如果变更不存在 → 告诉用户"变更不存在，请确认变更名"

### 2. 清理为通用模板

读取文件后，进行清理：
- 移除项目特定的信息（具体类名、路径、端口号）
- 保留通用的设计方案、架构决策、需求场景
- 添加一个 `notes.md`，记录使用建议和适配要点

### 3. 导出到模板目录

```bash
mkdir -p ~/.sillyspec/templates/<change-name>
cp 清理后的文件到该目录
```

### 4. 确认

展示导出内容摘要，告知模板路径。

### 最后说：

> ✅ 方案已导出到 `~/.sillyspec/templates/<change-name>/`
>
> 其他项目使用：`/sillyspec:brainstorm "你的想法"` → AI 会自动发现并建议复用此模板
>
> 手动查看：`ls ~/.sillyspec/templates/<change-name>/`
