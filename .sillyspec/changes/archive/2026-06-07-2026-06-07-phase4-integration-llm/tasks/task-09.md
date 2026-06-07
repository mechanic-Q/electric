---
author: lmr
created_at: 2026-06-07 23:55:29
id: task-09
title: 交互式终端对话循环 (LLM Chat)
priority: P1
estimated_hours: 1
depends_on: [task-08]
blocks: [task-10]
allowed_paths:
  - ellectric/llm/chat.py
---

# task-09: 交互式终端对话循环 (LLM Chat)

## 修改文件
- **新增**: `ellectric/llm/chat.py`

## 实现要求
1. 创建 `ellectric/llm/chat.py`，实现交互式终端对话循环入口函数 `main()`
2. `main()` 签名无参数，通过 `ellectric.llm.agent.create_agent` 获取 agent 实例
3. 启动时检查 `DEEPSEEK_API_KEY` 环境变量，缺失时打印友好中文错误信息并 return，不崩溃
4. 进入 `while True` 循环：
   - 提示符 `"你: "`，使用 `input()`
   - 空输入 → `continue` (静默跳过)
   - `/exit` → 打印 `"再见!"` → `break`
   - Ctrl+C (`KeyboardInterrupt`) → 捕获并打印 `"\n再见!"` → `break`
   - 调用 `agent.invoke({"input": user_input})`，打印 `"助手: {result['output']}"`
   - API 异常 (`Exception`) → 捕获并打印 `"错误: {e}"`，继续循环
5. 文件最末添加 `if __name__ == "__main__": main()` 入口
6. 无其他命令行参数解析（无 argparse/typer），保持 importable

## 边界处理（必填）
- `DEEPSEEK_API_KEY` 未设置 → 打印中文错误，不调用 agent，不触发异常
- 空输入 → 静默跳过，不打印任何内容
- Ctrl+C → 优雅退出，不打印 traceback
- `/exit` → 正常退出，不打印 traceback
- agent.invoke 任何异常 → 打印 `"错误: {e}"`，不退出循环，用户可以继续提问
- 输入首尾空白字符 → `.strip()` 处理，全空白按空输入处理

## 非目标（本任务不做的事）
- 不实现 agent 本身（由 task-08 提供 `create_agent`）
- 不实现 LangChain tools（由 task-07 提供）
- 不处理多轮对话记忆（agent.invoke 处理）
- 不实现流式输出（streaming）
- 不实现历史记录持久化
- 不实现 `/help` 等额外命令（仅 `/exit`）

## TDD 步骤
1. **检查**: 确认 `ellectric/llm/` 目录存在（由 task-08 创建），不存在则不执行
2. **写入**: 创建 `ellectric/llm/chat.py`，包含 `main()` 和 `if __name__` 块
3. **语法验证**: `python -c "import ast; ast.parse(open('ellectric/llm/chat.py').read()); print('OK')"` 输出 `OK`
4. **导入验证**: `python -c "from ellectric.llm.chat import main; print('OK')"` 输出 `OK`（即使 agent 因缺少 key 不可用，import 也不应失败——因 import 在函数内部）
5. **手工测试（可选）**: `DEEPSEEK_API_KEY=test python -c "from ellectric.llm.chat import main; main()"` 应进入循环（实际 agent 初始化可能失败，但脚本应正确处理）

## 验收标准
| # | 验证步骤 | 通过标准 |
|---|---------|---------|
| AC-01 | `python -c "import ast; ast.parse(open('ellectric/llm/chat.py').read()); print('OK')"` | 输出 `OK` |
| AC-02 | `unset DEEPSEEK_API_KEY && python -c "from ellectric.llm.chat import main; main()"` | 输出包含 `错误` 或 `未设置` 的中文错误信息，正常退出（不抛异常） |
| AC-03 | `python -c "from ellectric.llm.chat import main; print('OK')"` | 输出 `OK`（import 不依赖环境变量） |
| AC-04 | `grep -c 'def main' ellectric/llm/chat.py` | 返回值 >= 1 |
| AC-05 | `grep '/exit' ellectric/llm/chat.py` | 包含 `/exit` 命令处理逻辑 |
| AC-06 | `grep 'KeyboardInterrupt' ellectric/llm/chat.py` | 包含 Ctrl+C 异常捕获 |
| AC-07 | `grep 'if __name__' ellectric/llm/chat.py` | 包含脚本入口守卫 |
