from src.core.schemas import RoleProfile


AI_INTERN_PROFILE = RoleProfile(
  name="ai_intern",
  display_name="人工智能 / 大模型 / 智能体实习",
  keywords=[
    "大模型", "LLM", "Agent", "RAG", "Prompt", "提示词", "微调", "SFT",
    "LoRA", "QLoRA", "LangChain", "LangGraph", "MCP", "Python", "PyTorch",
    "Transformer", "Qwen", "LLaMA", "DeepSeek", "Docker", "Linux", "SQL",
    "评估", "数据集", "知识库", "检索", "多模态", "实习", "硕士",
  ],
  strong_resume_signals=[
    "LLaMA-Factory", "Qwen2-7B", "Prompt", "Kimi", "Agent", "Python",
    "Docker", "JSON", "Tavily", "OpenAI Compatible API",
  ],
  gap_project_templates=[
    "RAG 知识库问答项目：覆盖文档切分、向量检索、Prompt 拼接和答案生成。",
    "LangGraph 多节点 Agent 项目：覆盖计划、工具调用、结果校验和状态流转。",
    "模型评测项目：覆盖数据集构造、指标设计、结果对比和报告输出。",
  ],
)

GENERAL_PROFILE = RoleProfile(
  name="general",
  display_name="通用实习岗位",
  keywords=[
    "实习", "本科", "硕士", "沟通", "项目", "数据", "分析", "协作", "文档",
    "执行", "学习能力", "Excel", "Python", "SQL", "产品", "运营", "开发",
  ],
  strong_resume_signals=["项目", "实习", "Python", "SQL", "Git", "沟通", "协作"],
  gap_project_templates=[
    "岗位相关小项目：围绕 JD 中最高频职责做一个可展示的完整案例。",
    "数据分析案例：覆盖数据清洗、分析结论和可视化报告。",
  ],
)

PROFILES = {
  AI_INTERN_PROFILE.name: AI_INTERN_PROFILE,
  GENERAL_PROFILE.name: GENERAL_PROFILE,
}


def get_profile(name: str = "ai_intern") -> RoleProfile:
  return PROFILES.get(name, AI_INTERN_PROFILE)
