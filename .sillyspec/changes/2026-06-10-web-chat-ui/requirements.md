---
author: lmr
created_at: 2026-06-10 16:25:35
---

# Requirements — Web Chat UI

## 角色

| 角色 | 说明 |
|------|------|
| 终端用户 | 通过浏览器访问聊天界面，用自然语言与 AI 电力交易助手对话 |
| 开发者 | 维护和扩展后端 SSE 流式逻辑、前端 UI |

## 功能需求

### FR-01: 流式对话

Given 用户已在聊天页面
When 用户输入问题并点击发送
Then 系统通过 SSE 流式返回 AI 回复，token 逐字出现在聊天区域

Given 用户在 AI 回复期间
When AI 正在生成回复
Then 用户看到闪烁光标指示生成中，发送按钮禁用

Given AI 回复完成
When 最后一个 token 返回
Then 光标消失，Markdown 最终渲染完成，发送按钮恢复

### FR-02: 工具调用状态可见

Given 用户的提问触发 Agent 调用工具（如 run_simulation）
When Agent 开始执行工具调用
Then 聊天区域显示黄色标签 "TOOL_NAME" + spinner 动画

Given 工具调用执行完成
When Agent 收到工具返回结果
Then 对应标签变为绿色 "TOOL_NAME · 完成"

Given 工具调用失败
When HTTP 请求超时或返回错误
Then Agent 在回复中说明错误原因，工具标签不出现

### FR-03: Markdown 渲染

Given AI 回复中包含 Markdown 格式内容（表格、代码块、列表）
When 回复渲染到聊天区域
Then 内容按 Markdown 语法正确格式化
- 代码块有语法高亮
- 表格有边框和 header 样式
- 数值数据使用等宽字体 (JetBrains Mono)

### FR-04: 快捷键

Given 用户光标在输入框中
When 用户按下 Enter（非 Shift 组合）
Then 发送当前消息

Given 用户光标在输入框中
When 用户按下 Shift+Enter
Then 插入换行符，不发送

### FR-05: 建议快捷按钮

Given 用户首次打开聊天页面（无历史消息）
When 页面加载完成
Then 显示 4 个建议快捷按钮：「负荷预测」「市场仿真」「策略回测」「模型解释」

Given 用户点击建议快捷按钮
When 按钮被点击
Then 对应问题文本自动填入输入框并发送

### FR-06: 响应式布局

Given 用户在移动设备上访问（屏幕宽度 < 640px）
When 页面渲染
Then 聊天界面全宽显示，消息气泡占 88% 宽度，输入区域调整间距

### FR-07: API 向后兼容

Given 现有 API 端点 `/predict` `/simulate` `/backtest` `/explain` `/health`
When 部署新版本后
Then 所有现有端点行为不变，请求/响应格式不变

## 非功能需求

- **兼容性**：零新 Python 依赖包，仅使用 FastAPI 内置 `StreamingResponse` 和标准库 `asyncio`
- **可回退**：删除 `ellectric/chat/` 目录 + `server.py` 新增行即可完全移除，现有功能不受影响
- **浏览器兼容性**：支持 Chrome/Firefox/Safari/Edge 最近 2 个主版本
- **性能**：SSE 连接延迟 < 1s（从 POST 到首个 token），消息渲染不阻塞 UI 线程
- **安全性**：API Key 保留在服务端，前端不暴露；用户输入做 HTML 转义防 XSS
