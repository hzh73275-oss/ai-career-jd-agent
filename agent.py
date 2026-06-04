import re

from chat import Chat


class Agent:
  action_re = re.compile(r"^Action: (\w+): (.*)$")

  def __init__(self, tools, max_turns=8):
    self.tools = tools
    self.max_turns = max_turns
    self.prompt = self.get_agent_prompt(self.tools)
    self.chat = Chat(self.prompt)
    self.known_actions = self.get_actions(self.tools)

  def query(self, prompt):
    i = 0
    print(prompt)
    next_prompt = prompt
    action_re = self.__class__.action_re

    while i < self.max_turns:
      i += 1
      result = self.chat(next_prompt)
      print(result)
      actions = [action_re.match(a) for a in result.split("\n") if action_re.match(a)]

      if actions:
        groups = actions[0].groups()
        action = groups[0]
        action_input = groups[1] if len(groups) > 1 else None

        if action not in self.known_actions:
          raise Exception("Unknown action: {}: {}".format(action, action_input))

        if action_input:
          observation = self.known_actions[action](action_input)
        else:
          observation = self.known_actions[action]()

        print(observation)
        next_prompt = "Observation: {}".format(observation)
      else:
        return

  def get_agent_prompt(self, tools):
    tools_str = "\n".join([f"{tool.__doc__}\n" for tool in tools])
    print(tools_str)

    prompt = f"""
你是一个中文求职 Agent，帮助用户搜索公开实习岗位、分析简历匹配度、给出简历优化建议。

你必须用以下循环工作：
Thought: 简短说明下一步做什么
Action: 工具名: 工具输入
PAUSE

工具执行结果会以 Observation 返回。你拿到足够信息后，输出：
Answer: 中文最终答案

重要规则：
- 除工具名、代码、链接、英文技术名词外，所有内容必须使用中文。
- 不要编造岗位信息、薪资、地点、公司文化或录用概率。
- 如果网页无法读取或信息不足，请让用户粘贴完整 JD。
- 如果用户问实习、岗位、简历匹配、简历优化，优先使用岗位搜索和简历匹配工具。
- 一次只输出一个 Action。

可用工具：

{tools_str}

示例：
Question: 帮我找大模型 Agent 实习岗位，并分析我的简历是否匹配
Thought: 我需要先搜索公开岗位。
Action: search_jobs: 大模型 Agent 实习 北京 上海 武汉
PAUSE

Observation: 搜索到公开岗位候选。
Thought: 我需要提取第一个岗位信息。
Action: extract_job_info: 1
PAUSE

Observation: 已提取岗位信息。
Thought: 我需要读取简历并匹配。
Action: match_resume_to_job: none
PAUSE

Observation: 已生成匹配报告。
Answer: 这是匹配分析和建议。
""".strip()

    return prompt

  def get_actions(self, tools):
    return {tool.__name__: tool for tool in tools}
