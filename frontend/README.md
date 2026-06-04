# Vue 前端说明

这是 AI 求职决策工作台的 Vue 版页面，采用“左侧导航 + 顶部栏 + 多页面工作台”的产品化布局。

## 一键启动

在项目根目录运行：

```powershell
cd path\to\agent-implementation
powershell -ExecutionPolicy Bypass -File .\start_vue_ui.ps1
```

脚本会启动两个服务：

- 本地 API：http://127.0.0.1:8765
- Vue 页面：http://127.0.0.1:5175

## 手动启动

如果一键脚本不能用，可以手动开两个终端。

终端 1：启动本地 API：

```powershell
cd path\to\agent-implementation
python -B -m src.api.server
```

终端 2：启动 Vue 页面：

```powershell
cd path\to\agent-implementation
python -m http.server 5175 --bind 127.0.0.1 --directory frontend
```

然后打开：

```text
http://127.0.0.1:5175
```

## 当前能力

- 简历读取：支持粘贴文本，也支持上传 TXT / DOCX / 文本型 PDF。
- 岗位搜索：调用本地 API，再由 Python 侧使用 Tavily 搜索公开岗位。
- 岗位详情：选择岗位后提取结构化 JD。
- 匹配分析：生成匹配分、推荐等级、点对点对比表。
- 简历润色：支持规则版建议，也支持大模型润色版。
- 详细报告：集中展示完整匹配分析、点对点对比、润色建议和补强计划。

## API 规则

- 前端不会保存任何 API Key。
- 后端只读取使用者自己本地 `.env` 中的 Key。
- 开源版本不内置任何真实 Key。
- 未启动本地 API 时，页面会显示示例数据，并提示接口未连接。
- 联网岗位搜索需要使用者自己的 `TAVILY_API_KEY`；未配置时可以粘贴 JD 做本地分析。
- 大模型润色需要使用者自己的 `OPENAI_API_KEY`；未配置时仍可使用规则版润色。
- 多平台搜索会消耗 Tavily credits，深度搜索覆盖更广，也会消耗更多额度。
