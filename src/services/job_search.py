from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import httpx

from src.core.schemas import SearchResult
from src.services.text_utils import clip_text


@dataclass(frozen=True)
class SourceGroup:
  key: str
  name: str
  domains: list[str]


@dataclass(frozen=True)
class SourceTarget:
  key: str
  name: str
  domain: str
  group_key: str
  group_name: str
  base_quota: int


SOURCE_GROUPS = {
  "campus": SourceGroup(
    key="campus",
    name="实习校招平台",
    domains=[
      "site:shixiseng.com",
      "site:yingjiesheng.com",
      "site:xiaoyuan.zhaopin.com",
      "site:campus.51job.com",
      "site:campus.lagou.com",
      "site:nowcoder.com",
    ],
  ),
  "general": SourceGroup(
    key="general",
    name="通用招聘平台",
    domains=[
      "site:zhipin.com",
      "site:zhaopin.com",
      "site:51job.com",
      "site:liepin.com",
      "site:lagou.com",
    ],
  ),
  "company": SourceGroup(
    key="company",
    name="公司官网",
    domains=[
      "site:careers.tencent.com",
      "site:jobs.bytedance.com",
      "site:campus.alibaba.com",
      "site:talent.baidu.com",
      "site:hr.xiaomi.com",
      "site:campus.meituan.com",
      "site:campus.jd.com",
      "site:campus.163.com",
      "site:career.huawei.com",
      "site:zhaopin.kuaishou.cn",
    ],
  ),
}


DEFAULT_SOURCE_KEYS = ["campus", "general", "company"]


COMPANY_DOMAINS = [
  "site:careers.tencent.com",
  "site:jobs.bytedance.com",
  "site:campus.alibaba.com",
  "site:talent.baidu.com",
  "site:hr.xiaomi.com",
  "site:campus.meituan.com",
  "site:campus.jd.com",
  "site:campus.163.com",
  "site:career.huawei.com",
  "site:zhaopin.kuaishou.cn",
]


SOURCE_TARGETS = [
  SourceTarget("company", "公司官网", "", "company", "公司官网", 18),
  SourceTarget("shixiseng", "实习僧", "site:shixiseng.com", "campus", "实习校招平台", 12),
  SourceTarget("nowcoder", "牛客", "site:nowcoder.com", "campus", "实习校招平台", 10),
  SourceTarget("yingjiesheng", "应届生求职网", "site:yingjiesheng.com", "campus", "实习校招平台", 8),
  SourceTarget("zhaopin_campus", "智联校园", "site:xiaoyuan.zhaopin.com", "campus", "实习校招平台", 8),
  SourceTarget("job51_campus", "前程无忧校园", "site:campus.51job.com", "campus", "实习校招平台", 8),
  SourceTarget("zhaopin", "智联招聘", "site:zhaopin.com", "general", "通用招聘平台", 10),
  SourceTarget("job51", "前程无忧", "site:51job.com", "general", "通用招聘平台", 10),
  SourceTarget("lagou", "拉勾", "site:lagou.com", "general", "通用招聘平台", 7),
  SourceTarget("liepin", "猎聘", "site:liepin.com", "general", "通用招聘平台", 7),
  SourceTarget("boss", "Boss 直聘", "site:zhipin.com", "general", "通用招聘平台", 6),
]


BOSS_SOURCE = "Boss 直聘"
BOSS_RESULT_RATIO = 0.2


def build_query_variants(query: str, mode: str = "fast") -> list[str]:
  base = query.strip()
  if mode == "fast":
    return [base]

  expansions = [
    "大模型 实习",
    "LLM 实习",
    "Agent 实习",
    "RAG 实习",
    "AI 应用开发 实习",
    "Prompt 工程 实习",
    "Python AI 实习",
    "大模型应用开发 实习",
  ]
  variants = [base]
  for item in expansions:
    if item.lower() not in base.lower():
      variants.append(f"{base} {item}")
  return variants[:5]


def selected_source_targets(source_keys: list[str]) -> list[SourceTarget]:
  selected = set(source_keys or DEFAULT_SOURCE_KEYS)
  return [target for target in SOURCE_TARGETS if target.group_key in selected]


def build_platform_search_queries(query: str, source_keys: list[str], mode: str) -> list[tuple[str, str, str]]:
  variants = build_query_variants(query, mode=mode)
  targets = selected_source_targets(source_keys)
  queries: list[tuple[str, str, str]] = []

  for target in targets:
    target_variants = variants if mode == "deep" else variants[:2]
    if target.key == "company":
      company_domains = COMPANY_DOMAINS if mode == "deep" else COMPANY_DOMAINS[:6]
      for domain in company_domains:
        for variant in target_variants:
          queries.append((f"{variant} 招聘 岗位职责 任职要求 {domain}", target.name, target.key))
      continue

    for variant in target_variants:
      queries.append((f"{variant} 招聘 岗位职责 任职要求 {target.domain}", target.name, target.key))

  return queries


def infer_source(url: str, group_name: str) -> str:
  mapping = {
    "shixiseng.com": "实习僧",
    "yingjiesheng.com": "应届生求职网",
    "xiaoyuan.zhaopin.com": "智联校园",
    "zhaopin.com": "智联招聘",
    "campus.51job.com": "前程无忧校园",
    "51job.com": "前程无忧",
    "campus.lagou.com": "拉勾校招",
    "lagou.com": "拉勾",
    "nowcoder.com": "牛客",
    "zhipin.com": "Boss 直聘",
    "liepin.com": "猎聘",
    "careers.tencent.com": "腾讯招聘",
    "jobs.bytedance.com": "字节招聘",
    "campus.alibaba.com": "阿里校园",
    "talent.baidu.com": "百度招聘",
    "hr.xiaomi.com": "小米招聘",
    "campus.meituan.com": "美团校园",
    "campus.jd.com": "京东校园",
    "campus.163.com": "网易校园",
    "career.huawei.com": "华为招聘",
    "zhaopin.kuaishou.cn": "快手招聘",
  }
  for domain, name in mapping.items():
    if domain in url:
      return name
  return group_name


def classify_result(title: str, summary: str, source: str) -> tuple[str, str]:
  text = f"{title} {summary} {source}".lower()
  reject_words = ["销售", "电销", "客服", "运营专员", "标注", "审核", "博士", "顶会", "全职", "社招"]
  if any(word.lower() in text for word in reject_words):
    return "不建议", "岗位职责或硬性要求与当前实习目标偏离较大。"

  big_company_words = [
    "腾讯", "字节", "阿里", "百度", "小米", "美团", "京东", "网易", "快手", "华为",
    "microsoft", "amazon", "sap", "ibm",
  ]
  hard_words = ["强化学习", "顶会", "论文", "博士", "research", "算法研究"]
  if any(word.lower() in text for word in big_company_words) or any(word.lower() in text for word in hard_words):
    return "冲刺岗", "公司或岗位要求较高，适合少量冲刺投递。"

  main_words = ["大模型", "llm", "agent", "rag", "ai", "python", "应用开发", "工程", "实习"]
  if sum(1 for word in main_words if word.lower() in text) >= 2:
    return "主投岗", "方向与目标较接近，适合作为重点候选。"

  return "保底岗", "岗位要求可能相对宽泛，可作为扩大机会的候选。"


def _search_once(query: str, tavily_api_key: str, max_results: int) -> list[dict]:
  payload = {
    "api_key": tavily_api_key,
    "query": query,
    "search_depth": "basic",
    "include_answer": False,
    "max_results": max_results,
  }
  response = httpx.post("https://api.tavily.com/search", json=payload, timeout=25)
  response.raise_for_status()
  return response.json().get("results", [])


def build_search_queries(query: str, source_keys: list[str], mode: str) -> list[tuple[str, str]]:
  selected_groups = [SOURCE_GROUPS[key] for key in source_keys if key in SOURCE_GROUPS]
  variants = build_query_variants(query, mode=mode)

  queries: list[tuple[str, str]] = []
  if mode == "fast":
    for group in selected_groups:
      domain_query = " OR ".join(group.domains)
      queries.append((f"{variants[0]} 招聘 岗位职责 任职要求 {domain_query}", group.name))
    return queries

  for group in selected_groups:
    domain_query = " OR ".join(group.domains)
    for variant in variants:
      queries.append((f"{variant} 招聘 岗位职责 任职要求 {domain_query}", group.name))
  return queries


def _prepare_results(raw_results: list[dict]) -> list[SearchResult]:
  seen = set()
  prepared: list[SearchResult] = []
  for item in raw_results:
    url = item.get("url", "").strip()
    title = item.get("title", "无标题").strip()
    summary = clip_text(item.get("content", ""), 360)
    source = infer_source(url, item.get("_source_group", "公开网页"))
    title_key = "".join(title.lower().split())[:80]
    summary_key = "".join(summary.lower().split())[:80]
    key = url or f"{source}:{title_key}:{summary_key}"
    weak_key = f"{source}:{title_key}"
    if not key or key in seen or weak_key in seen:
      continue
    seen.add(key)
    seen.add(weak_key)

    tier, reason = classify_result(title, summary, source)
    prepared.append(SearchResult(
      index=0,
      title=title,
      url=url,
      summary=summary,
      source=source,
      tier=tier,
      tier_reason=reason,
    ))
  return prepared


def build_source_stats(results: list[SearchResult]) -> dict[str, int]:
  stats: dict[str, int] = {}
  for result in results:
    stats[result.source] = stats.get(result.source, 0) + 1
  return dict(sorted(stats.items(), key=lambda item: item[1], reverse=True))


def build_platform_notices(results: list[SearchResult], source_keys: list[str]) -> list[str]:
  stats = build_source_stats(results)
  targets = selected_source_targets(source_keys)
  notices: list[str] = []
  for target in targets:
    if target.key == "boss":
      continue
    expected_names = [target.name]
    if target.key == "company":
      expected_names = [
        "腾讯招聘", "字节招聘", "阿里校园", "百度招聘", "小米招聘",
        "美团校园", "京东校园", "网易校园", "华为招聘", "快手招聘",
      ]
    count = sum(stats.get(name, 0) for name in expected_names)
    if count == 0:
      notices.append(f"{target.name}公开搜索结果较少，可能需要登录或页面未被搜索引擎收录，可手动粘贴 JD。")
  return notices[:8]


TIER_QUOTAS = {
  "冲刺岗": 20,
  "主投岗": 50,
  "保底岗": 10,
  "不建议": 10,
}


def _limit_by_tier(results: list[SearchResult], max_results: int) -> list[SearchResult]:
  buckets: dict[str, list[SearchResult]] = {}
  for result in results:
    buckets.setdefault(result.tier, []).append(result)

  limited: list[SearchResult] = []
  for tier in ["冲刺岗", "主投岗", "保底岗", "不建议"]:
    limited.extend(buckets.get(tier, [])[:TIER_QUOTAS[tier]])

  if len(limited) < max_results:
    used = {id(item) for item in limited}
    for item in results:
      if id(item) not in used:
        limited.append(item)
      if len(limited) >= max_results:
        break

  limited = limited[:max_results]
  for index, result in enumerate(limited, start=1):
    result.index = index
  return limited


def _balance_by_source(results: list[SearchResult], max_results: int) -> list[SearchResult]:
  buckets: dict[str, list[SearchResult]] = {}
  for result in results:
    buckets.setdefault(result.source, []).append(result)

  source_cap = max(12, max_results // 3)
  capped = {source: items[:source_cap] for source, items in buckets.items()}
  balanced: list[SearchResult] = []

  while len(balanced) < max_results and any(capped.values()):
    for source in list(capped.keys()):
      if capped[source] and len(balanced) < max_results:
        balanced.append(capped[source].pop(0))

  for index, result in enumerate(balanced, start=1):
    result.index = index
  return balanced


def _source_quota(source: str, max_results: int) -> int:
  if source == BOSS_SOURCE:
    return max(1, int(max_results * BOSS_RESULT_RATIO))
  if source in ["腾讯招聘", "字节招聘", "阿里校园", "百度招聘", "小米招聘", "美团校园", "京东校园", "网易校园", "华为招聘", "快手招聘"]:
    return max(3, max_results // 6)
  if source in ["实习僧", "牛客", "应届生求职网", "智联校园", "前程无忧校园"]:
    return max(4, max_results // 7)
  return max(3, max_results // 8)


def _balance_by_platform(results: list[SearchResult], max_results: int) -> list[SearchResult]:
  buckets: dict[str, list[SearchResult]] = {}
  for result in results:
    buckets.setdefault(result.source, []).append(result)

  boss_items = buckets.pop(BOSS_SOURCE, [])
  capped: dict[str, list[SearchResult]] = {
    source: items[:_source_quota(source, max_results)]
    for source, items in buckets.items()
  }

  preferred_order = [
    "腾讯招聘", "字节招聘", "阿里校园", "百度招聘", "小米招聘", "美团校园", "京东校园", "网易校园", "华为招聘", "快手招聘",
    "实习僧", "牛客", "应届生求职网", "智联校园", "前程无忧校园",
    "智联招聘", "前程无忧", "拉勾", "拉勾校招", "猎聘",
  ]
  ordered_sources = [source for source in preferred_order if source in capped]
  ordered_sources.extend(source for source in capped if source not in ordered_sources)

  balanced: list[SearchResult] = []
  while len(balanced) < max_results and any(capped.values()):
    for source in ordered_sources:
      if capped.get(source) and len(balanced) < max_results:
        balanced.append(capped[source].pop(0))

  boss_cap = max(1, int(max_results * BOSS_RESULT_RATIO))
  for item in boss_items[:boss_cap]:
    if len(balanced) >= max_results:
      break
    balanced.append(item)

  if len(balanced) < max_results:
    used = {id(item) for item in balanced}
    for item in results:
      if item.source == BOSS_SOURCE:
        continue
      if id(item) not in used:
        balanced.append(item)
      if len(balanced) >= max_results:
        break

  for item in boss_items[boss_cap:]:
    if len(balanced) >= max_results:
      break
    if sum(1 for result in balanced if result.source == BOSS_SOURCE) >= boss_cap:
      break
    balanced.append(item)

  balanced = balanced[:max_results]
  for index, result in enumerate(balanced, start=1):
    result.index = index
  return balanced


def search_public_jobs(
  query: str,
  tavily_api_key: str | None,
  max_results: int = 30,
  source_keys: list[str] | None = None,
  mode: str = "fast",
) -> list[SearchResult]:
  if not tavily_api_key:
    raise RuntimeError("未配置 TAVILY_API_KEY。可以先粘贴岗位描述，或在 .env 中填写 Tavily API Key。")

  selected_keys = source_keys or DEFAULT_SOURCE_KEYS
  search_queries = build_platform_search_queries(query, selected_keys, mode)
  per_search_limit = 8 if mode == "fast" else 10

  raw_results = []
  max_workers = min(10, len(search_queries))
  with ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_map = {
      executor.submit(_search_once, search_query, tavily_api_key, per_search_limit): (group_name, target_key)
      for search_query, group_name, target_key in search_queries
    }
    for future in as_completed(future_map):
      group_name, target_key = future_map[future]
      try:
        for item in future.result():
          item["_source_group"] = group_name
          item["_source_target"] = target_key
          raw_results.append(item)
      except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code in {401, 403}:
          raise RuntimeError("Tavily API Key 无效或无权限。你仍然可以粘贴 JD 做本地分析，或使用下方平台链接手动搜索岗位。") from exc
      except Exception:
        continue

  prepared = _prepare_results(raw_results)
  return _balance_by_platform(prepared, max_results)
