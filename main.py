from agent import Agent
from src.core.config import load_settings
from src.services.formatters import (
  format_job_info,
  format_match_report,
  format_resume_advice,
  format_search_results,
)
from src.services.job_search import SOURCE_GROUPS
from src.workflows.resume_jd_workflow import ResumeJDWorkflow
from tools import (
  extract_job_info,
  match_resume_to_job,
  read_resume,
  search_jobs,
  suggest_resume_edits,
)


def run_saver_flow():
  settings = load_settings()
  workflow = ResumeJDWorkflow(settings, profile_name="ai_intern")

  print("\n省额度模式：直接使用模块化 Python workflow，尽量少调用大模型。")
  query = input("请输入岗位搜索关键词，例如“大模型 Agent 实习 北京 上海 武汉”：").strip()
  if not query:
    query = "大模型 Agent 实习 北京 上海 武汉"

  max_results_text = input("候选数量 30/50/80/100，默认 80：").strip()
  max_results = int(max_results_text) if max_results_text in {"30", "50", "80", "100"} else 80

  print("搜索范围：1=全部，2=实习校招，3=通用招聘，4=公司官网")
  scope = input("请选择搜索范围，默认 1：").strip()
  scope_map = {
    "2": ["campus"],
    "3": ["general"],
    "4": ["company"],
  }
  source_keys = scope_map.get(scope, list(SOURCE_GROUPS.keys()))

  print("\n[1/5] 搜索公开岗位...")
  try:
    results = workflow.search_jobs(query, max_results=max_results, source_keys=source_keys)
    print(format_search_results(results))
  except Exception as exc:
    print(f"岗位搜索失败：{exc}")
    print("你仍然可以在下一步直接粘贴岗位 JD。")

  choice = input("\n请选择岗位编号，或直接粘贴岗位 JD / URL：").strip()
  if not choice:
    choice = "1"

  print("\n[2/5] 提取岗位信息...")
  job = workflow.extract_job(choice)
  print(format_job_info(job))

  print("\n[3/5] 读取简历...")
  resume_source = input("可直接回车读取 resume.txt，或输入 DOCX/PDF/TXT 路径：").strip()
  resume = workflow.load_resume(resume_source)
  print(resume[:800] + "\n...[简历内容已截断显示]")

  print("\n[4/5] 匹配岗位和简历...")
  report = workflow.match()
  print(format_match_report(report))

  print("\n[5/5] 生成简历优化建议和项目补强计划...")
  advice = workflow.advise()
  print(format_resume_advice(advice))


def run_agent_flow():
  agent_tools = [
    search_jobs,
    extract_job_info,
    read_resume,
    match_resume_to_job,
    suggest_resume_edits,
  ]
  agent = Agent(agent_tools)

  while True:
    user_query = input("请输入需求，或输入 exit 退出：")
    if user_query.lower() == "exit":
      print("已退出。")
      break
    agent.query(user_query)


def main():
  print("Resume-JD Match Skill 原型")
  print("1. 省额度模式（推荐）：模块化 workflow，适合本地使用和调试")
  print("2. Agent 模式：ReAct 多轮工具调用，会消耗更多模型额度")
  mode = input("请选择模式 1/2，默认 1：").strip()

  if mode == "2":
    run_agent_flow()
  else:
    run_saver_flow()


if __name__ == "__main__":
  main()
