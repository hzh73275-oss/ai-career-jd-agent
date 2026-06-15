# AI Career JD Agent / AI 求职 JD 分析助手

## 中文说明

AI Career JD Agent 是一个本地运行的 AI 求职决策工作台。它围绕“简历输入 -> 岗位输入 -> JD 解析 -> 简历匹配 -> 技能库 RAG -> 面试题与补强建议 -> 完整报告”形成闭环，帮助用户判断岗位匹配度、定位技能缺口，并准备简历优化和面试复盘。

本项目默认面向本地使用。API Key 只会从用户自己的 `.env` 文件读取，仓库中不包含任何真实密钥。

### 功能特性

- 本地 Web 工作台，包含 Vue 前端页面和 FastAPI 后端服务。
- 支持通过粘贴文本、本地 `resume.txt`、上传 TXT / DOCX / 文本型 PDF 读取简历。
- 配置 `TAVILY_API_KEY` 后，可通过 Tavily Search 搜索公开岗位。
- 未配置搜索 Key 时，仍可直接粘贴 JD 做本地分析。
- 支持提取岗位名称、公司、职责、要求、技能等结构化 JD 信息。
- 支持简历与 JD 的匹配评分、优势分析、短板分析、风险提示和行动建议。
- 支持生成逐项对照表，便于检查简历是否覆盖岗位要求。
- 内置本地技能库 / 面试题库，无 JD、无简历、无 API Key 时也能独立浏览。
- 支持 Chroma + 本地 BGE embedding 的技能库 hybrid RAG 检索。
- 支持普通 Workflow 和 LangGraph 两种匹配分析模式，LangGraph 模式会展示节点执行链路。
- 未配置大模型 Key 时，仍可使用规则版简历优化建议。
- 配置 `OPENAI_API_KEY` 后，可启用 OpenAI 或 OpenAI Compatible API 的大模型润色流程。

### 项目结构

```text
.
├── frontend/              # 静态 Web 前端
├── data/                  # 本地技能库，不提交向量索引缓存
├── src/
│   ├── api/               # FastAPI 本地 API
│   ├── core/              # 配置、数据结构、用户画像
│   ├── graphs/            # LangGraph 核心分析链路
│   ├── parsers/           # 简历和文档解析
│   ├── services/          # 搜索、匹配、翻译、格式化等服务
│   └── workflows/         # 简历/JD 工作流编排
├── run_app.py             # 一键启动本地应用
├── run_app.bat            # Windows 启动脚本
├── start_vue_ui.ps1       # PowerShell 启动脚本
├── pyproject.toml         # Python 依赖配置
├── .env.example           # 环境变量示例
└── README.md
```

### 环境要求

- Python 3.10 至 3.12
- Poetry，或其他可以安装 `pyproject.toml` 依赖的 Python 环境管理工具
- 可选：Tavily API Key，用于公开岗位搜索
- 可选：OpenAI 或 OpenAI Compatible API Key，用于大模型简历润色

### 安装与配置

安装依赖：

```powershell
cd path\to\agent-implementation
poetry install
```

复制环境变量示例文件：

```powershell
Copy-Item .env.example .env
```

然后只填写自己需要使用的 Key：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
MODEL_NAME=
TAVILY_API_KEY=
```

不配置 API Key 时，应用仍然可以进行本地简历/JD 分析。岗位搜索需要 `TAVILY_API_KEY`，大模型润色需要 `OPENAI_API_KEY`。

### 无 Key 模式

本项目支持无 Key 使用。不开通 Tavily / OpenAI Key 时，仍然可以完成核心流程：

- 手动去 Boss 直聘、实习僧、牛客、智联招聘、前程无忧、拉勾或公司官网搜索岗位。
- 复制岗位 JD，粘贴到项目“岗位搜索”页面的“手动粘贴 JD”入口。
- 点击“提取手动 JD”，生成结构化岗位信息。
- 上传或粘贴自己的简历。
- 继续生成简历与 JD 的匹配分析、逐项对照表、技能缺口、面试题和简历优化建议。
- 直接进入“技能库”页面，浏览本地技能卡、面试题和项目补强建议。

无 Key 模式下不可自动联网搜索岗位，但不影响本地 JD 分析、技能库 RAG、简历匹配、LangGraph 分析和规则版简历优化建议。

如果需要自动搜索公开岗位，可以配置自己的 `TAVILY_API_KEY`。Tavily 通常提供免费额度，但额度有限，深度搜索和多平台搜索会消耗更多 credits。

如果需要大模型润色，可以配置自己的 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `MODEL_NAME`。未配置时，项目会使用规则版简历优化建议。

### 本地运行

启动完整本地应用：

```powershell
python run_app.py
```

Windows 用户也可以运行：

```powershell
.\run_app.bat
```

启动后会打开两个本地服务：

- API 服务：`http://127.0.0.1:8765`
- Web 页面：`http://127.0.0.1:5175`

使用过程中请保持终端窗口打开。

### 操作说明

1. 打开 Web 页面 `http://127.0.0.1:5175`。
2. 在“简历”页面粘贴简历文本，或上传 TXT / DOCX / 文本型 PDF 简历文件。
3. 在“岗位搜索”页面选择岗位输入方式：配置 `TAVILY_API_KEY` 时可联网搜索；没有 Key 时可直接粘贴 JD。
4. 点击“提取岗位信息”或“提取手动 JD”，生成结构化 JD。
5. 选择一个岗位，进入岗位详情页，系统会提取岗位名称、职责、要求和技能点。
6. 进入“匹配分析”，选择普通 Workflow 或 LangGraph 模式，生成匹配报告。
7. 查看逐项对照表，检查简历中哪些经历已经覆盖岗位要求，哪些内容还需要补充。
8. 进入“技能库”页面，可独立搜索 `RAG`、`Agent`、`FastAPI`、`企业知识库问答` 等技能和面试题。
9. 在“简历润色”页面生成优化建议。未配置大模型 Key 时使用规则版建议；配置 `OPENAI_API_KEY` 后可启用大模型润色。
10. 根据报告修改自己的简历，再重新上传或粘贴，反复对比优化效果。

### 本地 RAG 与 LangGraph

- 技能库位于 `data/skill_library.json`，用于标准技能解释、JD 常见说法、简历证据模式、项目补强建议和面试题。
- 向量索引使用 Chroma，默认保存在 `data/vector_store/`，该目录不应提交到 Git。
- 本地 embedding 缓存默认放在项目上级目录的 `.cache/`，避免占用 C 盘。
- `/api/skills/search` 支持 `keyword`、`vector`、`hybrid` 三种模式，默认使用 hybrid。
- `/api/match` 是稳定的普通 Workflow 匹配链路。
- `/api/graph/match` 是 LangGraph 核心分析链路，会返回 `graph_trace`，用于查看节点执行过程。
- 技能库浏览、面试题查看、向量索引构建是独立工具模块，不进入 LangGraph，避免过度设计。


### Replit 配置

Replit 入口文件已配置为：

```text
run_app.py
```

### API 概览

本地 API 提供以下主要接口：

- `GET /api/health`：检查服务状态和 Key 配置情况。
- `POST /api/resume`：读取简历内容。
- `POST /api/search`：搜索公开岗位。
- `POST /api/job`：提取结构化 JD 信息。
- `POST /api/match`：生成简历与 JD 匹配分析报告。
- `POST /api/graph/match`：通过 LangGraph 生成匹配报告并返回执行链路。
- `POST /api/polish`：生成简历润色结果。
- `GET /api/skills`：读取本地技能库。
- `POST /api/skills/search`：本地关键词 / 向量 / 混合检索技能库。
- `POST /api/skills/reindex`：重建本地 Chroma 向量索引。

### 安全说明

- 不要提交 `.env`。
- 不要提交真实 API Key、访问令牌、Cookie 或其他私密凭据。
- `.gitignore` 已排除 `.env` 和 `.env.*`，但允许提交 `.env.example`。
- 所有第三方 API 调用额度和费用都由配置 Key 的使用者自行承担。
- 公开岗位搜索会消耗 Tavily credits，搜索范围越广或深度越高，消耗越多。
- 不要提交 `data/vector_store/`、模型缓存、`.cache/` 等本地生成文件。
- 如果 `resume.txt` 包含个人简历、手机号、邮箱、学校、公司等隐私信息，发布到 GitHub 前请不要提交它。

上传 GitHub 前建议执行：

```powershell
git status --short
git ls-files --others --exclude-standard
```

确认 `.env` 没有被暂存，也没有出现在待上传文件中。

### 开发说明

- `run_app.py` 会同时启动本地 API 和静态前端页面。
- 只需要 API 时，可以直接运行 `src.api.server`。
- 前端是静态页面，可直接从 `frontend/` 目录提供服务。
- 上传的简历文件会写入系统临时目录，不会写入仓库。

### 许可证

如果项目要公开发布，建议在上传前补充合适的开源许可证。

---

## English

AI Career JD Agent is a local resume and job-description analysis workbench. It helps users search public job postings, extract structured JD details, compare a resume against a selected role, and generate resume improvement suggestions.

The project is designed for local use. API keys are loaded only from the user's own `.env` file and are not included in this repository.

## Features

- Local web workbench with a Vue frontend and FastAPI backend.
- Resume loading from pasted text, local `resume.txt`, or uploaded TXT / DOCX / text-based PDF files.
- Public job search through Tavily Search when `TAVILY_API_KEY` is configured.
- Manual JD analysis when no search key is configured.
- Structured JD extraction for title, company, requirements, responsibilities, and skills.
- Resume-to-JD match scoring with gaps, strengths, risks, and recommended next actions.
- Resume comparison table for point-by-point review.
- Local skill-library analysis for normalized job skills, resume evidence, project suggestions, and interview questions.
- Rule-based resume polish suggestions without an LLM key.
- Optional OpenAI-compatible polish flow when `OPENAI_API_KEY` is configured.

## Project Structure

```text
.
├── frontend/              # Static web UI
├── data/                  # Local skill library
├── src/
│   ├── api/               # FastAPI local API
│   ├── core/              # Configuration, schemas, profiles
│   ├── parsers/           # Resume/document parsing
│   ├── services/          # Search, matching, translation, formatting
│   └── workflows/         # Resume/JD workflow orchestration
├── run_app.py             # One-command local app launcher
├── run_app.bat            # Windows launcher
├── start_vue_ui.ps1       # PowerShell launcher
├── pyproject.toml         # Python dependencies
├── .env.example           # Example environment variables
└── README.md
```

## Requirements

- Python 3.10 to 3.12
- Poetry, or another Python environment manager that can install the dependencies in `pyproject.toml`
- Optional: Tavily API key for public job search
- Optional: OpenAI or OpenAI-compatible API key for LLM resume polish

## Setup

Install dependencies:

```powershell
cd path\to\agent-implementation
poetry install
```

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Then fill in only the keys you want to use:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
MODEL_NAME=
TAVILY_API_KEY=
```

The app still supports local resume/JD analysis without API keys. Job search requires `TAVILY_API_KEY`; LLM polish requires `OPENAI_API_KEY`.

## No-Key Mode

This project can be used without Tavily or OpenAI keys.

Without API keys, users can still:

- Search jobs manually on platforms such as Boss Zhipin, Shixiseng, Nowcoder, Zhaopin, 51Job, Lagou, or company career pages.
- Copy a job description and paste it into the app.
- Click "Extract manual JD" to generate structured job information.
- Upload or paste a resume.
- Generate resume-JD match analysis, comparison tables, local skill-library insights, and rule-based resume improvement suggestions.

No-key mode does not support automatic public job search, but it still supports local JD analysis, resume matching, and rule-based resume polish suggestions.

To enable automatic public job search, configure your own `TAVILY_API_KEY`. Tavily may provide free credits, but quota is limited, and broader or deeper search consumes more credits.

To enable LLM polish, configure your own `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `MODEL_NAME`. Without these settings, the app uses rule-based suggestions.

## Running Locally

Start the full local app:

```powershell
python run_app.py
```

On Windows, you can also run:

```powershell
.\run_app.bat
```

The launcher starts:

- API server: `http://127.0.0.1:8765`
- Web UI: `http://127.0.0.1:5175`

Keep the terminal open while using the app.

## How to Use

1. Open `http://127.0.0.1:5175`.
2. Paste resume text or upload a TXT / DOCX / text-based PDF resume.
3. Search for a job keyword, such as `AI intern`, `machine learning engineer`, or `data analyst intern`.
4. If `TAVILY_API_KEY` is configured, use public job search. Without it, paste a JD manually.
5. Select a job and let the app extract structured responsibilities, requirements, and skills.
6. Run the match analysis to review score, strengths, gaps, risks, and improvement suggestions.
7. Check the comparison table to see which JD requirements are already covered by the resume.
8. Generate resume polish suggestions. The rule-based version works without an LLM key; the LLM flow requires `OPENAI_API_KEY`.
9. Revise the resume and run the analysis again to compare improvements.

如果这个项目对你有帮助，欢迎自愿打赏支持后续维护。打赏完全自愿，不影响任何功能使用。

<img src="docs/wechat-reward.jpg" alt="WeChat reward QR code" width="120">

## Replit

The Replit entrypoint is configured to run:

```text
run_app.py
```

## API Overview

The local API exposes these main routes:

- `GET /api/health` checks service status and key availability.
- `POST /api/resume` loads resume content.
- `POST /api/search` searches public job postings.
- `POST /api/job` extracts structured JD details.
- `POST /api/match` builds the resume/JD analysis report.
- `/api/match` also returns `skill_insights` for local skill-library analysis.
- `POST /api/polish` generates resume polish output.

## Security Notes

- Do not commit `.env`.
- Do not commit real API keys, access tokens, cookies, or private credentials.
- `.gitignore` excludes `.env` and `.env.*` while allowing `.env.example`.
- All third-party API usage is paid for by the user configuring their own keys.
- Public job search can consume Tavily credits, especially in broader or deeper search modes.

Before pushing to GitHub, run:

```powershell
git status --short
git ls-files --others --exclude-standard
```

Confirm that `.env` is not staged or listed as an upload candidate.

## Development Notes

- `run_app.py` starts both the FastAPI backend and the static Vue frontend.
- `src.api.server` can be run directly when only the API is needed.
- The frontend is static and can be served from the `frontend/` directory.
- Uploaded resume files are written to the system temporary directory, not to the repository.

## License

Add a license before publishing if this project will be shared publicly.
