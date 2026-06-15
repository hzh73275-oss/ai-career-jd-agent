import { createApp, reactive, computed, onMounted } from "https://unpkg.com/vue@3/dist/vue.esm-browser.js";

const API_BASE = "http://127.0.0.1:8765";

const pages = [
  { key: "dashboard", name: "工作台", icon: "⌂" },
  { key: "resume", name: "简历管理", icon: "▣" },
  { key: "search", name: "岗位搜索", icon: "⌕" },
  { key: "detail", name: "岗位详情", icon: "◉" },
  { key: "match", name: "匹配分析", icon: "◎" },
  { key: "skills", name: "技能库", icon: "◆" },
  { key: "polish", name: "简历润色", icon: "✎" },
  { key: "report", name: "详细报告", icon: "□" },
];

const tierNames = ["冲刺岗", "主投岗", "保底岗", "不建议"];

const fallbackJobs = [
  {
    index: 1,
    title: "小米-大模型智能体研究实习生",
    url: "https://example.com",
    summary: "探索大模型智能体研究的前沿技术，构建具备持续学习能力的通用 Agent。",
    source: "示例数据",
    tier: "冲刺岗",
    tier_reason: "示例岗位。启动本地 API 后可以搜索真实公开岗位。",
  },
  {
    index: 2,
    title: "AI Agent 开发实习生",
    url: "https://example.com",
    summary: "参与 Agent 工具调用、RAG 检索和 Python 服务开发。",
    source: "示例数据",
    tier: "主投岗",
    tier_reason: "示例岗位。启动本地 API 后可以搜索真实公开岗位。",
  },
];

const manualSearchPlatforms = [
  { name: "Boss 直聘", url: "https://www.zhipin.com/web/geek/job?query=" },
  { name: "实习僧", url: "https://www.shixiseng.com/interns?keyword=" },
  { name: "牛客", url: "https://www.nowcoder.com/jobs/recommend?query=" },
  { name: "智联招聘", url: "https://sou.zhaopin.com/?kw=" },
  { name: "前程无忧", url: "https://we.51job.com/pc/search?keyword=" },
  { name: "拉勾", url: "https://www.lagou.com/wn/jobs?kd=" },
  { name: "公司官网/百度", url: "https://www.baidu.com/s?wd=" },
];

const emptyReport = {
  level: "-",
  score: "-",
  matched_keywords: [],
  missing_keywords: [],
  recommendation: "读取简历并选择岗位后生成。",
};

const emptySkillInsights = {
  matched_skills: [],
  weak_evidence_skills: [],
  missing_skills: [],
  project_suggestions: [],
  interview_questions: [],
  notice: "生成匹配分析后显示岗位技能知识库结果。",
};

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",")[1] : result);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

async function apiPost(path, payload = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!data.ok) {
    throw new Error(data.message || "请求失败");
  }
  return data;
}

async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`);
  const data = await response.json();
  if (!data.ok) {
    throw new Error(data.message || "请求失败");
  }
  return data;
}

const app = {
  setup() {
    const state = reactive({
      page: "dashboard",
      apiOnline: false,
      apiMessage: "正在连接本地 API...",
      apiChecking: false,
      hasTavilyKey: false,
      hasOpenaiKey: false,

      resumeLoaded: false,
      resumeName: "",
      resumeText: "",
      resumeSummary: "",

      query: "大模型 Agent 实习 北京 上海 武汉",
      cities: "北京 × 上海 × 武汉",
      searchMode: "快速搜索",
      maxResults: 30,
      sourceKeys: ["campus", "general", "company"],
      sourceStats: {},
      platformNotices: [],
      searchStrategy: "",
      searchFallbackActive: false,
      searchFallbackReason: "",
      manualJdText: "",
      activeTier: "冲刺岗",
      pageSize: 5,
      tierPages: {
        冲刺岗: 1,
        主投岗: 1,
        保底岗: 1,
        不建议: 1,
      },
      searchLoading: false,

      jobs: [],
      selectedJob: null,
      jobInfo: null,
      jobText: "",
      jobLoading: false,

      reportReady: false,
      matchLoading: false,
      matchMode: "workflow",
      graphTrace: [],
      report: emptyReport,
      reportText: "",
      adviceText: "",
      comparisonRows: [],
      comparisonText: "",
      skillInsights: emptySkillInsights,
      skillText: "",
      skillLibrary: [],
      skillCategories: [],
      skillQuery: "",
      skillCategory: "",
      skillMode: "hybrid",
      skillLoading: false,
      skillIndexing: false,
      skillVectorStatus: {
        ready: false,
        count: 0,
        path: "",
        model: "",
        message: "本地向量索引未检查",
      },
      contextSkillIds: [],
      translationText: "",
      fullReport: "",

      polishTab: "rule",
      polishLoading: false,
      llmPolishText: "",
      reportExpanded: {
        match: false,
        comparison: false,
        skill: true,
        polish: true,
        advice: false,
      },
      notice: "",
      error: "",
    });

    const shownJobs = computed(() => state.jobs);

    const showNoKeyGuide = computed(() => !state.hasTavilyKey || state.searchFallbackActive);

    const manualSearchLinks = computed(() => {
      const keyword = encodeURIComponent(`${state.query || ""} ${state.cities || ""} 招聘 实习`.trim());
      return manualSearchPlatforms.map((platform) => ({
        name: platform.name,
        url: `${platform.url}${keyword}`,
      }));
    });

    const metrics = computed(() => ({
      score: state.reportReady ? state.report.score : "-",
      level: state.reportReady ? state.report.level : "-",
      matched: state.reportReady ? state.report.matched_keywords?.length || 0 : 0,
      missing: state.reportReady ? state.report.missing_keywords?.length || 0 : 0,
    }));

    const canGenerateMatch = computed(() => Boolean(state.resumeLoaded && state.jobInfo));

    const currentJdText = computed(() => {
      if (!state.jobInfo) return "";
      return [
        state.jobInfo.title,
        state.jobInfo.raw_text,
        state.jobInfo.requirements?.join("；"),
        state.jobInfo.responsibilities?.join("；"),
        state.jobInfo.keywords?.join("、"),
      ].filter(Boolean).join("\n");
    });

    const tierCounts = computed(() => {
      const counts = { 冲刺岗: 0, 主投岗: 0, 保底岗: 0, 不建议: 0 };
      for (const job of shownJobs.value) {
        counts[job.tier] = (counts[job.tier] || 0) + 1;
      }
      return counts;
    });

    const currentJobs = computed(() => {
      const results = shownJobs.value.filter((job) => job.tier === state.activeTier);
      return results;
    });

    const currentTierPage = computed(() => state.tierPages[state.activeTier] || 1);

    const totalJobPages = computed(() => {
      return Math.max(1, Math.ceil(currentJobs.value.length / state.pageSize));
    });

    const pagedJobs = computed(() => {
      const page = Math.min(currentTierPage.value, totalJobPages.value);
      const start = (page - 1) * state.pageSize;
      return currentJobs.value.slice(start, start + state.pageSize);
    });

    const visiblePageNumbers = computed(() => {
      const total = totalJobPages.value;
      const current = Math.min(currentTierPage.value, total);
      const start = Math.max(1, Math.min(current - 2, total - 4));
      const end = Math.min(total, start + 4);
      const pages = [];
      for (let page = start; page <= end; page += 1) {
        pages.push(page);
      }
      return pages;
    });

    const selectedJobView = computed(() => state.selectedJob);

    const searchModeHelp = computed(() => {
      if (state.searchMode === "深度搜索") {
        return "深度搜索会为每个平台使用更多 query，并扩大公司官网搜索范围，覆盖更全但更慢，适合找更多智联、前程无忧、实习僧、牛客和官网岗位。";
      }
      return "快速搜索会为每个平台使用少量 query，优先返回主要来源，速度较快，适合先扫一批岗位。";
    });

    const searchWaitingText = computed(() => {
      const countHint = Number(state.maxResults) > 50 ? "当前候选数量较高，会更慢并消耗更多 Tavily 免费额度。" : "";
      if (!state.searchLoading) {
        return `多平台搜索会逐个平台请求公开网页，速度会比单平台搜索慢。平台越多、候选数量越大，等待时间越长。${countHint}`;
      }
      if (state.searchMode === "深度搜索") {
        return "正在分别搜索招聘平台和公司官网，请耐心等待。深度搜索会更慢，因为会对每个平台发起更多公开网页检索。";
      }
      return "正在分别搜索招聘平台和公司官网，请耐心等待。系统会优先保留非 Boss 平台结果。";
    });

    const apiStatusText = computed(() => state.apiOnline ? "本地 API：已连接" : "本地 API：未连接");
    const searchKeyStatusText = computed(() => state.hasTavilyKey ? "联网搜索：已配置" : "联网搜索：未配置");
    const polishKeyStatusText = computed(() => state.hasOpenaiKey ? "大模型润色：已配置" : "大模型润色：未配置");
    const apiCheckButtonText = computed(() => {
      if (state.apiChecking) return "检查中...";
      if (!state.apiOnline) return "检查接口";
      return state.hasTavilyKey ? "接口正常" : "无 Key 模式";
    });

    const skillStatusById = computed(() => {
      const map = {};
      for (const item of state.skillInsights.matched_skills || []) {
        map[item.id] = "已覆盖";
      }
      for (const item of state.skillInsights.weak_evidence_skills || []) {
        map[item.id] = "证据较弱";
      }
      for (const item of state.skillInsights.missing_skills || []) {
        map[item.id] = "缺失";
      }
      return map;
    });

    const setPage = (page) => {
      state.page = page;
      if (page === "skills") {
        loadSkillLibrary();
      }
    };

    const resetTierPages = () => {
      for (const tier of tierNames) {
        state.tierPages[tier] = 1;
      }
    };

    const setActiveTier = (tier) => {
      state.activeTier = tier;
      state.tierPages[tier] = 1;
    };

    const setTierPage = (page) => {
      const nextPage = Math.max(1, Math.min(page, totalJobPages.value));
      state.tierPages[state.activeTier] = nextPage;
    };

    const toggleReportSection = (key) => {
      state.reportExpanded[key] = !state.reportExpanded[key];
    };

    const setNotice = (message) => {
      state.notice = message;
      state.error = "";
    };

    const setError = (message) => {
      state.error = message;
      state.notice = "";
    };

    const buildJobSkillQuery = () => {
      if (!state.jobInfo) return "";
      return [
        state.jobInfo.title,
        state.jobInfo.keywords?.join(" "),
        state.jobInfo.requirements?.join(" "),
        state.jobInfo.responsibilities?.join(" "),
        state.jobInfo.raw_text,
      ].filter(Boolean).join(" ");
    };

    const loadSkillLibrary = async () => {
      state.skillLoading = true;
      try {
        const data = await apiGet("/api/skills");
        state.skillLibrary = data.skills || [];
        state.skillCategories = data.categories || [];
        state.skillVectorStatus = data.vector_status || state.skillVectorStatus;
        if (state.jobInfo) {
          await refreshContextSkillMatches();
        }
      } catch (error) {
        setError(`技能库读取失败：${error.message}`);
      } finally {
        state.skillLoading = false;
      }
    };

    const searchSkillLibrary = async () => {
      state.skillLoading = true;
      try {
        const data = await apiPost("/api/skills/search", {
          query: state.skillQuery,
          category: state.skillCategory,
          limit: 100,
          mode: state.skillMode,
        });
        state.skillLibrary = data.skills || [];
        state.skillVectorStatus = data.vector_status || state.skillVectorStatus;
      } catch (error) {
        setError(`技能库搜索失败：${error.message}`);
      } finally {
        state.skillLoading = false;
      }
    };

    const rebuildSkillIndex = async () => {
      state.skillIndexing = true;
      try {
        const data = await apiPost("/api/skills/reindex");
        state.skillVectorStatus = data.vector_status || state.skillVectorStatus;
        setNotice(state.skillVectorStatus.message || "本地向量索引已重建。");
        await searchSkillLibrary();
      } catch (error) {
        setError(`本地向量索引构建失败：${error.message}`);
      } finally {
        state.skillIndexing = false;
      }
    };

    const resetSkillFilters = async () => {
      state.skillQuery = "";
      state.skillCategory = "";
      await loadSkillLibrary();
    };

    const refreshContextSkillMatches = async () => {
      const query = buildJobSkillQuery();
      if (!query) {
        state.contextSkillIds = [];
        return;
      }
      try {
        const data = await apiPost("/api/skills/search", { query, limit: 30, mode: "hybrid" });
        state.contextSkillIds = (data.skills || []).map((skill) => skill.id);
        state.skillVectorStatus = data.vector_status || state.skillVectorStatus;
      } catch {
        state.contextSkillIds = [];
      }
    };

    const skillCardStatus = (skill) => {
      if (skillStatusById.value[skill.id]) {
        return skillStatusById.value[skill.id];
      }
      if (state.contextSkillIds.includes(skill.id)) {
        return "当前 JD 命中";
      }
      return "";
    };

    const skillCardStatusClass = (skill) => {
      const status = skillCardStatus(skill);
      if (status === "已覆盖") return "green";
      if (status === "证据较弱" || status === "当前 JD 命中") return "orange";
      if (status === "缺失") return "red";
      return "gray";
    };

    const checkApi = async () => {
      state.apiChecking = true;
      try {
        const data = await apiGet("/api/health");
        state.apiOnline = true;
        state.hasTavilyKey = data.has_tavily_key;
        state.hasOpenaiKey = data.has_openai_key;
        state.apiMessage = "本地 API 已连接";
        state.searchFallbackActive = !data.has_tavily_key;
        state.searchFallbackReason = data.has_tavily_key
          ? ""
          : "未配置 Tavily Key。你可以直接粘贴 JD 做本地分析，或点击下方平台入口手动搜索岗位。";
        setNotice(data.has_tavily_key
          ? "接口已连接，联网搜索 Key 已配置。"
          : "接口已连接；当前未配置 Tavily Key，已显示无 Key 使用入口。");
      } catch (error) {
        state.apiOnline = false;
        state.apiMessage = "本地 API 未启动，当前只显示示例数据";
        setError("本地 API 未连接。请先运行 python run_app.py，再点击检查接口。");
      } finally {
        state.apiChecking = false;
      }
    };

    const loadResumeByText = async () => {
      try {
        const data = await apiPost("/api/resume", { text: state.resumeText });
        state.resumeLoaded = true;
        state.resumeName = state.resumeName || "粘贴简历";
        state.resumeText = data.resume_text;
        state.resumeSummary = data.summary;
        setNotice("简历读取完成。");
      } catch (error) {
        setError(`简历读取失败：${error.message}`);
      }
    };

    const handleResumeFile = async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        const contentBase64 = await readFileAsBase64(file);
        const data = await apiPost("/api/resume", {
          filename: file.name,
          content_base64: contentBase64,
        });
        state.resumeLoaded = true;
        state.resumeName = file.name;
        state.resumeText = data.resume_text;
        state.resumeSummary = data.summary;
        setNotice("简历文件已读取。");
      } catch (error) {
        setError(`简历文件读取失败：${error.message}`);
      } finally {
        event.target.value = "";
      }
    };

    const searchJobs = async () => {
      if (!state.hasTavilyKey) {
        state.searchFallbackActive = true;
        state.searchFallbackReason = "未配置 Tavily Key。你可以直接粘贴 JD 做本地分析，或点击下方平台入口手动搜索岗位。";
        setNotice("已切换到无 Key 使用方式：手动搜索岗位或粘贴 JD 分析。");
        return;
      }
      state.searchLoading = true;
      try {
        const data = await apiPost("/api/search", {
          query: state.query,
          max_results: Number(state.maxResults),
          source_keys: state.sourceKeys,
          mode: state.searchMode,
        });
        state.jobs = data.results || [];
        state.sourceStats = data.source_stats || {};
        state.platformNotices = data.platform_notices || [];
        state.searchStrategy = data.strategy || "";
        state.searchFallbackActive = !state.jobs.length;
        state.searchFallbackReason = state.jobs.length
          ? ""
          : "这次没有搜索到真实岗位。招聘平台经常需要登录或不被搜索引擎收录，你可以改关键词、点击平台入口手动搜索，或直接粘贴 JD 分析。";
        state.selectedJob = state.jobs[0] || null;
        state.activeTier = tierNames.find((tier) => state.jobs.some((job) => job.tier === tier)) || "冲刺岗";
        resetTierPages();
        setNotice(state.jobs.length
          ? `搜索到 ${data.count} 个候选岗位，覆盖 ${Object.keys(state.sourceStats).length} 个来源。`
          : "没有搜到真实岗位，已显示无 Key/手动搜索入口。");
      } catch (error) {
        state.jobs = [];
        state.selectedJob = null;
        state.searchFallbackActive = true;
        state.searchFallbackReason = error.message || "联网搜索不可用。你可以使用平台入口手动搜索，或直接粘贴 JD 做本地分析。";
        setNotice("联网搜索暂不可用，已切换到手动搜索和粘贴 JD 分析入口。");
      } finally {
        state.searchLoading = false;
      }
    };

    const analyzeManualJd = async () => {
      const text = state.manualJdText.trim();
      if (!text) {
        setError("请先粘贴岗位 JD，再提取岗位信息。");
        return;
      }
      state.jobLoading = true;
      try {
        const data = await apiPost("/api/job", { input_text: text });
        state.selectedJob = {
          index: 0,
          title: data.job?.title || "手动粘贴 JD",
          url: "",
          summary: text.slice(0, 220),
          source: "手动粘贴",
          tier: "主投岗",
          tier_reason: "用户手动粘贴的岗位描述。",
        };
        state.jobInfo = data.job;
        state.jobText = data.job_text;
        await refreshContextSkillMatches();
        state.page = "detail";
        setNotice("手动 JD 已提取，可以继续生成匹配报告。");
      } catch (error) {
        setError(`手动 JD 提取失败：${error.message}`);
      } finally {
        state.jobLoading = false;
      }
    };

    const selectJob = async (job) => {
      state.selectedJob = job;
      state.page = "detail";
      await extractJob(job);
    };

    const extractJob = async (job = state.selectedJob) => {
      if (!job) {
        setError("请先选择岗位。");
        return;
      }
      state.jobLoading = true;
      try {
        const inputText = state.jobs.length ? String(job.index) : `${job.title}\n${job.summary}`;
        const data = await apiPost("/api/job", { input_text: inputText });
        state.jobInfo = data.job;
        state.jobText = data.job_text;
        await refreshContextSkillMatches();
        setNotice("岗位信息已提取。");
      } catch (error) {
        setError(`岗位信息提取失败：${error.message}`);
      } finally {
        state.jobLoading = false;
      }
    };

    const generateMatch = async () => {
      if (!canGenerateMatch.value) {
        state.page = "match";
        setNotice("生成完整匹配需要先读取简历并提取 JD。你也可以先直接查看技能库和面试题库。");
        return;
      }
      state.matchLoading = true;
      try {
        const data = state.matchMode === "graph"
          ? await apiPost("/api/graph/match", {
              resume_text: state.resumeText,
              jd_text: currentJdText.value,
            })
          : await apiPost("/api/match", {});
        state.reportReady = true;
        state.report = data.report;
        state.reportText = data.report_text;
        state.adviceText = data.advice_text;
        state.comparisonRows = data.comparison_rows || [];
        state.comparisonText = data.comparison_text;
        state.skillInsights = data.skill_insights || emptySkillInsights;
        state.skillText = data.skill_text || "";
        state.translationText = data.translation_text;
        state.fullReport = data.full_report;
        state.graphTrace = data.graph_trace || [];
        setNotice(state.matchMode === "graph" ? "LangGraph 匹配分析已生成。" : "匹配分析已生成。");
      } catch (error) {
        setError(`匹配分析失败：${error.message}`);
      } finally {
        state.matchLoading = false;
      }
    };

    const generatePolish = async (useLlm = false) => {
      if (useLlm && !state.hasOpenaiKey) {
        setError("未配置大模型 Key，只能使用规则版润色；联网岗位搜索不受影响。");
        state.polishTab = "rule";
        return;
      }
      state.polishLoading = true;
      try {
        const data = await apiPost("/api/polish", { use_llm: useLlm });
        if (useLlm) {
          state.llmPolishText = data.translation_text;
        } else {
          state.translationText = data.translation_text;
        }
        setNotice(useLlm ? "大模型润色已生成。" : "规则版润色建议已生成。");
      } catch (error) {
        setError(`润色失败：${error.message}`);
      } finally {
        state.polishLoading = false;
      }
    };

    const copyText = async (text) => {
      await navigator.clipboard.writeText(text || "");
      setNotice("已复制到剪贴板。");
    };

    const scoreFor = (job) => {
      if (!job) return "-";
      if (job.tier === "冲刺岗") return 78;
      if (job.tier === "主投岗") return 74;
      if (job.tier === "保底岗") return 66;
      return 42;
    };

    const chipClass = (status) => {
      if (status === "已匹配") return "green";
      if (status === "写得不清楚") return "orange";
      if (status === "简历缺失") return "red";
      if (status === "已覆盖") return "green";
      if (status === "证据较弱") return "orange";
      if (status === "缺失") return "red";
      return "gray";
    };

    const short = (text, len = 120) => {
      if (!text) return "";
      return text.length > len ? `${text.slice(0, len)}...` : text;
    };

    onMounted(checkApi);

    return {
      pages,
      tierNames,
      state,
      metrics,
      canGenerateMatch,
      currentJdText,
      tierCounts,
      currentJobs,
      showNoKeyGuide,
      manualSearchLinks,
      currentTierPage,
      totalJobPages,
      pagedJobs,
      visiblePageNumbers,
      selectedJobView,
      skillStatusById,
      searchModeHelp,
      searchWaitingText,
      apiStatusText,
      searchKeyStatusText,
      polishKeyStatusText,
      apiCheckButtonText,
      setPage,
      setActiveTier,
      setTierPage,
      toggleReportSection,
      checkApi,
      loadResumeByText,
      handleResumeFile,
      searchJobs,
      analyzeManualJd,
      loadSkillLibrary,
      searchSkillLibrary,
      rebuildSkillIndex,
      resetSkillFilters,
      skillCardStatus,
      skillCardStatusClass,
      selectJob,
      extractJob,
      generateMatch,
      generatePolish,
      copyText,
      scoreFor,
      chipClass,
      short,
    };
  },
  template: `
    <div class="app-shell">
      <div class="app-frame">
        <aside class="sidebar">
          <div class="side-logo">
            <div class="logo-dot">AI</div>
            <span>AI 求职决策</span>
          </div>

          <div class="nav-list">
            <button
              v-for="item in pages"
              :key="item.key"
              class="nav-item"
              :class="{ active: state.page === item.key }"
              @click="setPage(item.key)"
            >
              <span class="nav-icon">{{ item.icon }}</span>
              <span>{{ item.name }}</span>
            </button>
          </div>

          <div class="side-bottom">
            <div class="helper-card">
              <div class="helper-title">业务流程</div>
              <ol class="flow-list">
                <li>简历管理：上传或粘贴简历。</li>
                <li>岗位输入：联网搜索，或直接粘贴 JD。</li>
                <li>匹配分析：选择普通 Workflow 或 LangGraph。</li>
                <li>技能库：无 JD 也能查技能和面试题。</li>
                <li>简历润色：先用规则版，有 Key 再用大模型。</li>
              </ol>
            </div>
            <div class="helper-card">
              <div class="helper-title">两种路径</div>
              <div class="helper-text"><b>无 Key：</b>粘贴 JD + 本地 RAG + 规则建议。</div>
              <div class="helper-text"><b>有 Key：</b>联网搜岗位 + 可选大模型润色。</div>
              <div class="helper-text"><b>独立模块：</b>技能库、面试题和向量索引不依赖匹配链路。</div>
            </div>
            <div class="helper-card">
              <div class="helper-title">当前状态</div>
              <div class="helper-text">接口：{{ state.apiOnline ? "已连接" : "未连接" }}</div>
              <div class="helper-text">简历：{{ state.resumeLoaded ? "已读取" : "未读取" }}</div>
              <div class="helper-text">岗位：{{ state.selectedJob ? "已选择" : "未选择" }}</div>
              <div class="helper-text">报告：{{ state.reportReady ? "已生成" : "未生成" }}</div>
            </div>
          </div>
        </aside>

        <main class="main">
          <header class="topbar">
            <div class="topbar-left">
              <span class="topbar-pill">AI</span>
              <span>AI 求职决策工作台</span>
            </div>
            <div class="topbar-actions">
              <div class="top-status-list">
                <span class="top-status" :class="{ok: state.apiOnline}">{{ apiStatusText }}</span>
                <span class="top-status" :class="{ok: state.hasTavilyKey}">{{ searchKeyStatusText }}</span>
                <span class="top-status" :class="{ok: state.hasOpenaiKey}">{{ polishKeyStatusText }}</span>
              </div>
              <button class="top-link" @click="checkApi" :disabled="state.apiChecking">{{ apiCheckButtonText }}</button>
              <span class="avatar">人</span>
            </div>
          </header>

          <div v-if="state.notice" class="toast success">{{ state.notice }}</div>
          <div v-if="state.error" class="toast error">{{ state.error }}</div>

          <section v-if="state.page === 'dashboard'" class="page">
            <div class="page-head">
              <div>
                <h1 class="page-title">欢迎使用 AI 求职决策工作台</h1>
                <div class="page-subtitle">上传简历、粘贴 JD 或搜索岗位，生成匹配分析和简历优化建议。</div>
              </div>
            </div>

            <div class="grid grid-4">
              <div class="card metric-card">
                <div class="metric-label">匹配分</div>
                <div class="metric-value" style="color: var(--green);">{{ metrics.score }}<span v-if="metrics.score !== '-'" style="font-size:14px;"> 分</span></div>
                <div class="metric-note">分数仅作参考</div>
              </div>
              <div class="card metric-card">
                <div class="metric-label">推荐等级</div>
                <div class="metric-value" style="color: var(--green);">{{ metrics.level }}</div>
                <div class="metric-note">根据简历和 JD 判断</div>
              </div>
              <div class="card metric-card">
                <div class="metric-label">已匹配能力</div>
                <div class="metric-value" style="color: var(--blue);">{{ metrics.matched }}<span style="font-size:14px;"> 项</span></div>
                <div class="metric-note">已满足岗位要求</div>
              </div>
              <div class="card metric-card">
                <div class="metric-label">待补能力</div>
                <div class="metric-value" style="color: var(--orange);">{{ metrics.missing }}<span style="font-size:14px;"> 项</span></div>
                <div class="metric-note">需要补充或强化</div>
              </div>
            </div>

            <div class="section-title" style="margin-top:24px;">当前进度</div>
            <div class="grid grid-3">
              <div class="card progress-card">
                <div class="progress-title"><span class="status green">简历</span> {{ state.resumeLoaded ? "已读取" : "未读取" }}</div>
                <div class="muted">{{ state.resumeName || "请先上传或粘贴简历" }}</div>
                <button class="btn full" style="margin-top:12px;" @click="setPage('resume')">进入简历管理</button>
              </div>
              <div class="card progress-card">
                <div class="progress-title"><span class="status blue">岗位</span> {{ state.selectedJob ? "已选择" : "未选择" }}</div>
                <div class="muted">{{ state.selectedJob?.title || "请先搜索并选择岗位" }}</div>
                <button class="btn full" style="margin-top:12px;" @click="setPage('search')">进入岗位搜索</button>
              </div>
              <div class="card progress-card">
                <div class="progress-title"><span class="status orange">报告</span> {{ state.reportReady ? "已生成" : "未生成" }}</div>
                <div class="muted">{{ state.reportReady ? "匹配报告已完成" : "选择岗位后生成报告" }}</div>
                <button class="btn primary full" style="margin-top:12px;" @click="generateMatch">生成匹配报告</button>
              </div>
            </div>

            <div class="next-card">
              <div>
                <div class="section-title">下一步建议</div>
                <div class="muted">如果接口未连接，先运行后端 API；如果已连接，就按“简历 → 岗位 → 匹配 → 润色”的顺序走。</div>
              </div>
              <div class="star">✦</div>
            </div>
          </section>

          <section v-if="state.page === 'resume'" class="page">
            <div class="page-head">
              <div>
                <h1 class="page-title">上传简历</h1>
                <div class="page-subtitle">支持 Word / PDF / TXT，也可以直接粘贴简历正文。</div>
              </div>
            </div>

            <div class="layout-detail">
              <div class="card card-pad">
                <div class="section-title">上传简历</div>
                <label class="upload-box">
                  <input type="file" accept=".txt,.docx,.pdf" style="display:none;" @change="handleResumeFile" />
                  <div>
                    <div class="upload-icon">☁</div>
                    <strong>点击这里选择简历文件</strong>
                    <div class="metric-note">支持 PDF / Word / TXT</div>
                  </div>
                </label>
                <div v-if="state.resumeName" class="file-line">
                  <span>{{ state.resumeName }}</span>
                  <span class="status green">已读取</span>
                </div>
                <div class="field" style="margin-top:14px;">
                  <label>或粘贴简历内容</label>
                  <textarea class="textarea" v-model="state.resumeText" placeholder="把简历正文粘贴到这里"></textarea>
                </div>
                <button class="btn primary full" @click="loadResumeByText">读取粘贴内容</button>
              </div>

              <div class="card card-pad">
                <div class="section-title">简历摘要</div>
                <div v-if="state.resumeLoaded" class="detail-block">
                  <p>{{ state.resumeSummary || short(state.resumeText, 800) }}</p>
                </div>
                <div v-else class="empty">还没有读取简历。请上传文件或粘贴文本。</div>
              </div>
            </div>
          </section>

          <section v-if="state.page === 'search'" class="page">
            <div class="layout-search">
              <div class="card card-pad">
                <div class="section-title">联网搜索岗位</div>
                <div class="field">
                  <label>岗位关键词</label>
                  <input class="input" v-model="state.query" />
                </div>
                <div class="field">
                  <label>地区</label>
                  <input class="input" v-model="state.cities" />
                </div>
                <div class="field">
                  <label>搜索模式</label>
                  <select class="select" v-model="state.searchMode">
                    <option>快速搜索</option>
                    <option>深度搜索</option>
                  </select>
                  <div class="mode-help">{{ searchModeHelp }}</div>
                </div>
                <div class="field">
                  <label>候选数量</label>
                  <input class="input" type="number" min="5" max="100" v-model="state.maxResults" />
                </div>
                <div class="field">
                  <label>搜索范围</label>
                  <label class="check-line"><input type="checkbox" value="campus" v-model="state.sourceKeys" /> 实习校招平台</label>
                  <label class="check-line"><input type="checkbox" value="general" v-model="state.sourceKeys" /> 通用招聘平台</label>
                  <label class="check-line"><input type="checkbox" value="company" v-model="state.sourceKeys" /> 公司官网</label>
                </div>
                <div class="search-wait-note" :class="{active: state.searchLoading}">
                  {{ searchWaitingText }}
                </div>
                <div v-if="showNoKeyGuide" class="key-guide-card">
                  <div class="key-guide-title">联网搜索提示</div>
                  <div class="key-guide-note">
                    {{ state.searchFallbackReason || "联网搜索需要 Tavily Key；没有 Key 时可以使用下方手动 JD 入口。" }}
                  </div>
                  <div class="platform-link-grid">
                    <a
                      v-for="platform in manualSearchLinks"
                      :key="platform.name"
                      class="platform-link"
                      :href="platform.url"
                      target="_blank"
                    >
                      {{ platform.name }}
                    </a>
                  </div>
                  <a class="key-guide-link" href="https://app.tavily.com" target="_blank">想开启自动搜索？去 Tavily 获取自己的 Key</a>
                </div>
                <button class="btn primary full" @click="searchJobs" :disabled="state.searchLoading">
                  {{ state.searchLoading ? "跨平台搜索中..." : "搜索岗位" }}
                </button>
                <div class="metric-note" style="margin-top:10px;">联网搜索需要 Tavily Key；没有 Key 时请直接使用下方手动 JD。深度搜索会消耗更多免费额度。</div>

                <div class="section-title" style="margin-top:22px;">手动粘贴 JD</div>
                <div class="helper-text" style="margin-bottom:10px;">
                  不需要 Tavily Key。粘贴招聘网站复制来的 JD 后，可直接提取岗位信息、匹配简历、进入普通 Workflow 或 LangGraph 分析。
                </div>
                <div class="field manual-jd-field">
                  <label>岗位 JD</label>
                  <textarea
                    class="textarea"
                    v-model="state.manualJdText"
                    placeholder="把岗位描述粘贴到这里，例如职责、要求、技术栈、实习地点和投递条件。"
                  ></textarea>
                </div>
                <button class="btn primary full" @click="analyzeManualJd" :disabled="state.jobLoading">
                  {{ state.jobLoading ? "提取中..." : "提取手动 JD" }}
                </button>
              </div>

              <div>
                <div class="page-head" style="margin-bottom:12px;">
                  <div>
                    <h1 class="page-title">岗位列表</h1>
                <div class="page-subtitle">{{ state.jobs.length ? '共 ' + state.jobs.length + ' 个候选岗位' : '你可以联网搜索岗位，也可以直接粘贴 JD 做本地分析。' }}</div>
                  </div>
                </div>
                <div v-if="state.jobs.length" class="source-panel">
                  <div class="source-panel-head">
                    <span>来源分布</span>
                    <span>{{ state.searchStrategy || "平台分桶搜索" }}</span>
                  </div>
                  <div class="source-stat-list">
                    <span v-for="(count, source) in state.sourceStats" :key="source" class="source-stat">
                      {{ source }} {{ count }}
                    </span>
                  </div>
                  <div v-if="state.platformNotices.length" class="source-notices">
                    <div v-for="notice in state.platformNotices" :key="notice">{{ notice }}</div>
                  </div>
                </div>
                <div class="card job-list-panel">
                  <div class="tabs compact-tabs">
                    <button
                      v-for="name in tierNames"
                      :key="name"
                      class="tab"
                      :class="{active: state.activeTier === name}"
                      @click="setActiveTier(name)"
                    >
                      {{ name }} {{ tierCounts[name] || 0 }}
                    </button>
                  </div>

                  <div class="job-list-meta">
                    <span>第 {{ currentTierPage }} / {{ totalJobPages }} 页，共 {{ currentJobs.length }} 个岗位</span>
                    <span>每页 {{ state.pageSize }} 个</span>
                  </div>

                  <div class="job-list-scroll">
                    <div v-if="!pagedJobs.length" class="empty">还没有岗位结果。请先点击“搜索岗位”；如果没有 Key 或搜不到结果，可以使用左侧平台入口手动搜索，并粘贴 JD 做本地分析。</div>
                    <div
                      v-for="job in pagedJobs"
                      :key="job.index + job.title"
                      class="card job-card"
                      :class="{active: state.selectedJob?.index === job.index && state.selectedJob?.title === job.title}"
                    >
                      <div class="job-card-head">
                        <div>
                          <div class="job-title">{{ job.title }}</div>
                          <div class="job-company">{{ job.source }} ｜ {{ job.tier }}</div>
                        </div>
                        <div class="score-badge">参考<br>{{ scoreFor(job) }}</div>
                      </div>
                      <div class="job-summary">{{ short(job.summary, 180) }}</div>
                      <div class="job-tags">
                        <span class="chip">{{ job.tier }}</span>
                        <span class="chip">{{ job.source }}</span>
                        <span class="chip">{{ short(job.tier_reason, 22) }}</span>
                      </div>
                      <button class="btn primary" @click="selectJob(job)">查看详情</button>
                      <a v-if="job.url" class="btn" style="margin-left:8px; text-decoration:none; display:inline-flex; align-items:center;" :href="job.url" target="_blank">打开链接</a>
                    </div>
                  </div>

                  <div class="pagination-bar">
                    <button class="page-btn" :disabled="currentTierPage <= 1" @click="setTierPage(currentTierPage - 1)">上一页</button>
                    <button
                      v-for="page in visiblePageNumbers"
                      :key="page"
                      class="page-btn number"
                      :class="{active: page === currentTierPage}"
                      @click="setTierPage(page)"
                    >
                      {{ page }}
                    </button>
                    <button class="page-btn" :disabled="currentTierPage >= totalJobPages" @click="setTierPage(currentTierPage + 1)">下一页</button>
                  </div>
                </div>
              </div>

              <div class="card card-pad">
                <div class="section-title">当前选中岗位</div>
                <template v-if="selectedJobView">
                  <div class="status green">已选中</div>
                  <h3>{{ selectedJobView.title }}</h3>
                  <div class="detail-list">
                    <div class="detail-block"><h4>来源</h4><p>{{ selectedJobView.source }}</p></div>
                    <div class="detail-block"><h4>层级</h4><p>{{ selectedJobView.tier }}</p></div>
                    <div class="detail-block"><h4>摘要</h4><p>{{ short(selectedJobView.summary, 180) }}</p></div>
                  </div>
                  <button class="btn primary full" style="margin-top:14px;" @click="extractJob(selectedJobView)" :disabled="state.jobLoading">
                    {{ state.jobLoading ? "提取中..." : "提取岗位信息" }}
                  </button>
                  <button class="btn full" style="margin-top:10px;" @click="generateMatch">生成匹配报告</button>
                </template>
                <div v-else class="empty">还没有选择岗位。</div>
              </div>
            </div>
          </section>

          <section v-if="state.page === 'detail'" class="page">
            <div class="page-head">
              <div>
                <h1 class="page-title">{{ selectedJobView?.title || "岗位详情" }}</h1>
                <div class="page-subtitle">选择岗位后先提取结构化 JD，再用于匹配分析。</div>
              </div>
              <span class="status green" v-if="state.selectedJob">已选中</span>
            </div>

            <div class="layout-detail">
              <div class="card card-pad">
                <div class="section-title">岗位摘要</div>
                <template v-if="selectedJobView">
                  <div class="detail-list">
                    <div class="detail-block"><h4>来源</h4><p>{{ selectedJobView.source }}</p></div>
                    <div class="detail-block"><h4>层级</h4><p>{{ selectedJobView.tier }}</p></div>
                    <div class="detail-block"><h4>链接</h4><p>{{ selectedJobView.url || "无" }}</p></div>
                  </div>
                  <button class="btn primary full" style="margin-top:14px;" @click="extractJob(selectedJobView)">提取岗位信息</button>
                  <button class="btn full" style="margin-top:10px;" @click="generateMatch">生成匹配报告</button>
                </template>
                <div v-else class="empty">请先去岗位搜索页选择岗位。</div>
              </div>

              <div class="card card-pad">
                <div class="section-title">结构化岗位信息</div>
                <template v-if="state.jobInfo">
                  <div class="detail-block"><h4>岗位标题</h4><p>{{ state.jobInfo.title }}</p></div>
                  <div class="detail-block"><h4>地点线索</h4><p>{{ state.jobInfo.locations?.join('、') || "未识别" }}</p></div>
                  <div class="detail-block"><h4>薪资线索</h4><p>{{ state.jobInfo.salary_hints?.join('、') || "未识别" }}</p></div>
                  <div class="detail-block"><h4>关键词</h4><p>{{ state.jobInfo.keywords?.join('、') || "未识别" }}</p></div>
                  <div class="detail-block"><h4>岗位职责</h4><p>{{ state.jobInfo.responsibilities?.join('；') || short(state.jobInfo.raw_text, 500) }}</p></div>
                  <div class="detail-block"><h4>岗位要求</h4><p>{{ state.jobInfo.requirements?.join('；') || "暂未提取到明确要求" }}</p></div>
                </template>
                <div v-else class="empty">还没有结构化 JD。点击“提取岗位信息”后显示。</div>
              </div>
            </div>
          </section>

          <section v-if="state.page === 'match'" class="page">
            <div class="page-head">
              <div>
                <h1 class="page-title">匹配分析结果</h1>
                <div class="page-subtitle">用点对点对比看清楚：JD 要什么，你的简历有没有写出来。</div>
              </div>
              <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                <select class="select" v-model="state.matchMode" style="width:180px;">
                  <option value="workflow">普通 Workflow</option>
                  <option value="graph">LangGraph</option>
                </select>
                <button class="btn primary" @click="generateMatch" :disabled="state.matchLoading">{{ state.matchLoading ? "生成中..." : "生成匹配分析" }}</button>
              </div>
            </div>

            <div v-if="state.matchMode === 'graph'" class="card card-pad" style="margin-bottom:14px;">
              <div class="section-title">
                <span>LangGraph 核心链路</span>
                <span class="status blue">Graph 模式</span>
              </div>
              <div class="helper-text">
                Graph 模式只编排“简历 + JD → 匹配报告”这条核心分析链路；技能库浏览、面试题查看和向量索引构建仍然是独立普通 API。
              </div>
            </div>

            <div v-if="!canGenerateMatch" class="card card-pad" style="margin-bottom:14px;">
              <div class="section-title">
                <span>还不能生成完整匹配</span>
                <span class="status orange">需要简历 + JD</span>
              </div>
              <div class="helper-text">匹配分析需要读取简历并提取 JD；但技能库和面试题库是本地模块，不受 Tavily 额度影响，可以直接查看。</div>
              <div class="quick-action-grid">
                <button class="btn" @click="setPage('resume')">{{ state.resumeLoaded ? "查看简历" : "上传/粘贴简历" }}</button>
                <button class="btn" @click="setPage('search')">搜索岗位或粘贴 JD</button>
                <button class="btn primary" @click="setPage('skills')">查看技能库和面试题</button>
              </div>
            </div>

            <div class="grid grid-4">
              <div class="card metric-card"><div class="metric-label">匹配分</div><div class="metric-value" style="color:var(--green);">{{ metrics.score }}<span v-if="metrics.score !== '-'" style="font-size:14px;"> /100</span></div><div class="metric-note">分数仅作参考</div></div>
              <div class="card metric-card"><div class="metric-label">推荐等级</div><div class="metric-value" style="color:var(--green);">{{ metrics.level }}</div><div class="metric-note">建议优先投递</div></div>
              <div class="card metric-card"><div class="metric-label">已匹配能力</div><div class="metric-value" style="color:var(--blue);">{{ metrics.matched }}<span style="font-size:14px;"> 项</span></div><div class="metric-note">已满足岗位要求</div></div>
              <div class="card metric-card"><div class="metric-label">待补能力</div><div class="metric-value" style="color:var(--orange);">{{ metrics.missing }}<span style="font-size:14px;"> 项</span></div><div class="metric-note">需要补充或强化</div></div>
            </div>

            <div class="layout-detail" style="grid-template-columns:minmax(0,1fr) 240px; margin-top:14px;">
              <div class="card card-pad">
                <div class="section-title">JD-简历点对点对比</div>
                <table v-if="state.comparisonRows.length" class="table">
                  <thead><tr><th>JD 要求</th><th>简历证据</th><th>状态</th><th>修改建议</th><th>优先级</th></tr></thead>
                  <tbody>
                    <tr v-for="row in state.comparisonRows" :key="row['JD 要求'] + row['状态']">
                      <td>{{ row['JD 要求'] }}</td>
                      <td>{{ row['简历证据'] }}</td>
                      <td><span class="status" :class="chipClass(row['状态'])">{{ row['状态'] }}</span></td>
                      <td>{{ row['修改建议'] }}</td>
                      <td><span class="status orange">{{ row['优先级'] }}</span></td>
                    </tr>
                  </tbody>
                </table>
                <div v-else class="empty">还没有点对点对比。请先读取简历、选择岗位，再生成匹配分析。</div>
              </div>
              <div class="card card-pad">
                <div class="section-title">分析总结</div>
                <div class="detail-block"><h4>投递建议</h4><p>{{ state.report.recommendation || "生成后显示" }}</p></div>
                <div class="detail-block"><h4>待补关键词</h4><p>{{ state.report.missing_keywords?.slice(0, 8).join('、') || "生成后显示" }}</p></div>
                <button class="btn primary full" @click="setPage('report')">查看完整报告</button>
              </div>
            </div>

            <div v-if="state.graphTrace.length" class="card card-pad" style="margin-top:14px;">
              <div class="section-title">
                <span>LangGraph 执行链路</span>
                <span class="status green">{{ state.graphTrace.length }} 个节点</span>
              </div>
              <div class="detail-list">
                <div v-for="item in state.graphTrace" :key="item.node" class="detail-block">
                  <h4>{{ item.node }} <span class="status" :class="item.status === 'success' ? 'green' : 'red'">{{ item.status }}</span></h4>
                  <p>{{ item.summary }}</p>
                  <div class="helper-text">{{ item.elapsed_ms }} ms</div>
                </div>
              </div>
            </div>

            <div class="card card-pad" style="margin-top:14px;">
              <div class="section-title">
                <span>岗位技能知识库分析</span>
                <span class="status blue">本地 RAG</span>
              </div>
              <div class="helper-text" style="margin-bottom:12px;">{{ state.skillInsights.notice || "基于本地岗位技能知识库做技能识别、简历证据匹配和面试题推荐。" }}</div>
              <div v-if="state.skillInsights.matched_skills?.length || state.skillInsights.weak_evidence_skills?.length || state.skillInsights.missing_skills?.length" class="skill-grid">
                <div class="skill-column">
                  <h4><span class="status green">已覆盖</span></h4>
                  <div v-if="state.skillInsights.matched_skills?.length" class="skill-list">
                    <div v-for="skill in state.skillInsights.matched_skills" :key="skill.id" class="skill-card">
                      <div class="skill-card-head"><strong>{{ skill.name }}</strong><span class="status green">{{ skill.score }}</span></div>
                      <p>{{ skill.definition }}</p>
                      <p v-if="skill.evidence?.length"><b>证据：</b>{{ skill.evidence.slice(0, 2).join("；") }}</p>
                      <p><b>建议：</b>{{ skill.suggestion }}</p>
                    </div>
                  </div>
                  <div v-else class="empty small-empty">暂无明确覆盖技能。</div>
                </div>
                <div class="skill-column">
                  <h4><span class="status orange">证据较弱</span></h4>
                  <div v-if="state.skillInsights.weak_evidence_skills?.length" class="skill-list">
                    <div v-for="skill in state.skillInsights.weak_evidence_skills" :key="skill.id" class="skill-card">
                      <div class="skill-card-head"><strong>{{ skill.name }}</strong><span class="status orange">{{ skill.score }}</span></div>
                      <p>{{ skill.definition }}</p>
                      <p v-if="skill.evidence?.length"><b>已有线索：</b>{{ skill.evidence.slice(0, 2).join("；") }}</p>
                      <p><b>补强：</b>{{ skill.suggestion }}</p>
                    </div>
                  </div>
                  <div v-else class="empty small-empty">暂无证据较弱技能。</div>
                </div>
                <div class="skill-column">
                  <h4><span class="status red">缺失</span></h4>
                  <div v-if="state.skillInsights.missing_skills?.length" class="skill-list">
                    <div v-for="skill in state.skillInsights.missing_skills" :key="skill.id" class="skill-card">
                      <div class="skill-card-head"><strong>{{ skill.name }}</strong><span class="status red">{{ skill.score }}</span></div>
                      <p>{{ skill.definition }}</p>
                      <p><b>补强：</b>{{ skill.suggestion }}</p>
                    </div>
                  </div>
                  <div v-else class="empty small-empty">暂无明显缺失技能。</div>
                </div>
              </div>
              <div v-else class="empty">生成匹配分析后，会显示 JD 命中的标准技能、简历证据、缺口和面试准备题。</div>

              <div class="skill-bottom-grid">
                <div class="detail-block">
                  <h4>推荐补强项目</h4>
                  <ul v-if="state.skillInsights.project_suggestions?.length">
                    <li v-for="item in state.skillInsights.project_suggestions" :key="item">{{ item }}</li>
                  </ul>
                  <p v-else>暂无补强项目建议。</p>
                </div>
                <div class="detail-block">
                  <h4>面试准备题</h4>
                  <ul v-if="state.skillInsights.interview_questions?.length">
                    <li v-for="item in state.skillInsights.interview_questions.slice(0, 8)" :key="item.question">
                      <b>{{ item.skill_name }} / {{ item.level }}：</b>{{ item.question }}
                      <div class="helper-text">答题要点：{{ item.answer_points?.join("；") }}</div>
                    </li>
                  </ul>
                  <p v-else>暂无面试题推荐。</p>
                </div>
              </div>
            </div>
          </section>

          <section v-if="state.page === 'skills'" class="page">
            <div class="page-head">
              <div>
                <h1 class="page-title">岗位技能库 / 面试题库</h1>
                <div class="page-subtitle">本地知识库，不需要 Tavily、DeepSeek 或 OpenAI。没有 JD 和简历也可以直接查看技能、补强项目和面试题。</div>
              </div>
              <button class="btn" @click="loadSkillLibrary" :disabled="state.skillLoading">{{ state.skillLoading ? "读取中..." : "刷新技能库" }}</button>
            </div>

            <div class="card card-pad">
              <div class="section-title">
                <span>本地检索</span>
                <span class="status blue">{{ state.skillLibrary.length }} 项</span>
              </div>
              <div class="skill-toolbar">
                <input class="input" v-model="state.skillQuery" placeholder="搜索技能、JD 关键词或面试题，例如 RAG / Agent / FastAPI" @keyup.enter="searchSkillLibrary" />
                <select class="select" v-model="state.skillMode" @change="searchSkillLibrary">
                  <option value="hybrid">混合检索</option>
                  <option value="keyword">关键词</option>
                  <option value="vector">语义</option>
                </select>
                <select class="select" v-model="state.skillCategory" @change="searchSkillLibrary">
                  <option value="">全部分类</option>
                  <option v-for="item in state.skillCategories" :key="item.name" :value="item.name">{{ item.name }}（{{ item.count }}）</option>
                </select>
                <button class="btn primary" @click="searchSkillLibrary" :disabled="state.skillLoading">搜索</button>
                <button class="btn" @click="resetSkillFilters" :disabled="state.skillLoading">重置</button>
                <button class="btn" @click="rebuildSkillIndex" :disabled="state.skillIndexing || state.skillLoading">
                  {{ state.skillIndexing ? "构建中..." : "构建/重建语义索引" }}
                </button>
              </div>
              <div class="helper-text" style="margin-top:10px;">
                技能库支持独立浏览；如果已经提取 JD，会标记“当前 JD 命中”；如果已经生成匹配分析，会标记“已覆盖 / 证据较弱 / 缺失”。
              </div>
              <div class="helper-text" style="margin-top:8px;">
                语义索引：{{ state.skillVectorStatus.ready ? "已就绪" : "未就绪" }}，
                {{ state.skillVectorStatus.count || 0 }} 条；
                模型：{{ state.skillVectorStatus.model || "BAAI/bge-small-zh-v1.5" }}；
                路径：{{ state.skillVectorStatus.path || "D:\\learn_pytorch\\JD-agent\\agent-implementation\\data\\vector_store" }}
              </div>
            </div>

            <div v-if="state.skillLoading" class="empty" style="margin-top:14px;">正在读取本地技能库...</div>
            <div v-else-if="!state.skillLibrary.length" class="empty" style="margin-top:14px;">暂无技能卡片。请检查本地 API 是否启动，或 data/skill_library.json 是否存在。</div>
            <div v-else class="skill-browser-grid" style="margin-top:14px;">
              <div v-for="skill in state.skillLibrary" :key="skill.id" class="card skill-browser-card">
                <div class="skill-card-head">
                  <div>
                    <div class="skill-title">{{ skill.name }}</div>
                    <div class="helper-text">{{ skill.category }}</div>
                  </div>
                  <span v-if="skillCardStatus(skill)" class="status" :class="skillCardStatusClass(skill)">{{ skillCardStatus(skill) }}</span>
                </div>

                <p class="skill-desc">{{ skill.definition }}</p>

                <div v-if="skill.retrieval_reason" class="helper-text">
                  {{ skill.retrieval_reason }}
                  <span v-if="skill.keyword_score">｜关键词 {{ skill.keyword_score }}</span>
                  <span v-if="skill.vector_score">｜语义 {{ Number(skill.vector_score).toFixed(2) }}</span>
                </div>

                <div class="skill-chip-row">
                  <span v-for="alias in (skill.aliases || []).slice(0, 8)" :key="alias" class="mini-chip">{{ alias }}</span>
                </div>

                <div class="skill-section">
                  <h4>JD 常见说法</h4>
                  <ul>
                    <li v-for="item in (skill.jd_phrases || []).slice(0, 4)" :key="item">{{ item }}</li>
                  </ul>
                </div>

                <div class="skill-section">
                  <h4>项目补强建议</h4>
                  <ul>
                    <li v-for="item in (skill.project_suggestions || []).slice(0, 3)" :key="item">{{ item }}</li>
                  </ul>
                </div>

                <div class="skill-section">
                  <h4>面试题</h4>
                  <ul>
                    <li v-for="item in (skill.interview_questions || []).slice(0, 4)" :key="item.question">
                      <b>{{ item.level }}：</b>{{ item.question }}
                      <div class="helper-text">要点：{{ item.answer_points?.join("；") }}</div>
                    </li>
                  </ul>
                </div>

                <div class="skill-section" v-if="skill.source_refs?.length">
                  <h4>来源</h4>
                  <a v-for="ref in skill.source_refs" :key="ref.url" class="source-link" :href="ref.url" target="_blank" rel="noreferrer">{{ ref.title }}</a>
                </div>
              </div>
            </div>
          </section>

          <section v-if="state.page === 'polish'" class="page">
            <div class="page-head">
              <div>
                <h1 class="page-title">简历润色</h1>
                <div class="page-subtitle">规则版不需要 API；大模型润色会调用你自己配置的 API Key。</div>
              </div>
            </div>

            <div class="tabs">
              <button class="tab" :class="{active: state.polishTab === 'rule'}" @click="state.polishTab = 'rule'">规则版建议（本地）</button>
              <button class="tab" :class="{active: state.polishTab === 'llm'}" @click="state.polishTab = 'llm'">大模型润色（增强版）</button>
            </div>
            <div class="note-box">
              当前使用者需要自己配置大模型 API Key；项目不会内置、保存或上传任何 Key。
              <span v-if="!state.hasOpenaiKey">未配置大模型 Key，只能使用规则版润色；联网岗位搜索不受影响。</span>
              <span v-else>已配置大模型 Key，可以使用增强版润色。</span>
            </div>

            <div class="layout-polish" style="margin-top:14px;">
              <div class="card card-pad">
                <div class="section-title">规则版建议</div>
                <button class="btn primary" @click="generatePolish(false)" :disabled="state.polishLoading">{{ state.polishLoading ? "生成中..." : "生成规则版建议" }}</button>
                <button class="btn" style="margin-left:10px;" @click="copyText(state.translationText)">复制</button>
                <div class="detail-block" style="margin-top:12px; white-space:pre-wrap;">{{ state.translationText || "还没有生成规则版建议。" }}</div>
              </div>
              <div class="card card-pad">
                <div class="section-title">大模型润色版</div>
                <button class="btn primary" @click="generatePolish(true)" :disabled="state.polishLoading || !state.hasOpenaiKey">{{ state.polishLoading ? "生成中..." : "用大模型润色表达" }}</button>
                <button class="btn" style="margin-left:10px;" @click="copyText(state.llmPolishText)">复制</button>
                <div class="detail-block" style="margin-top:12px; white-space:pre-wrap;">{{ state.hasOpenaiKey ? (state.llmPolishText || "还没有生成大模型润色结果。") : "未配置大模型 Key。你仍然可以使用左侧规则版润色建议。" }}</div>
              </div>
            </div>
          </section>

          <section v-if="state.page === 'report'" class="page">
            <div class="page-head">
              <div>
                <h1 class="page-title">完整报告</h1>
                <div class="page-subtitle">阅读模式，集中展示完整匹配分析、润色建议和项目补强计划。</div>
              </div>
              <button class="btn" @click="copyText(state.fullReport)">复制全部</button>
            </div>

            <div class="card card-pad">
              <div class="report-section">
                <button class="report-section-head" @click="toggleReportSection('match')">
                  <span>完整匹配分析</span>
                  <span class="status green">报告</span>
                </button>
                <div v-if="state.reportExpanded.match" class="report-section-body">{{ state.reportText || "暂无" }}</div>
              </div>

              <div class="report-section">
                <button class="report-section-head" @click="toggleReportSection('comparison')">
                  <span>完整点对点对比</span>
                  <span class="status green">对比</span>
                </button>
                <div v-if="state.reportExpanded.comparison" class="report-section-body">{{ state.comparisonText || "暂无" }}</div>
              </div>

              <div class="report-section">
                <button class="report-section-head" @click="toggleReportSection('skill')">
                  <span>岗位技能知识库分析</span>
                  <span class="status blue">RAG</span>
                </button>
                <div v-if="state.reportExpanded.skill" class="report-section-body">{{ state.skillText || "暂无" }}</div>
              </div>

              <div class="report-section">
                <button class="report-section-head" @click="toggleReportSection('polish')">
                  <span>完整简历润色</span>
                  <span class="status green">润色</span>
                </button>
                <div v-if="state.reportExpanded.polish" class="report-section-body">{{ state.translationText || state.llmPolishText || "暂无" }}</div>
              </div>

              <div class="report-section">
                <button class="report-section-head" @click="toggleReportSection('advice')">
                  <span>完整项目补强计划</span>
                  <span class="status orange">补强</span>
                </button>
                <div v-if="state.reportExpanded.advice" class="report-section-body">{{ state.adviceText || "暂无" }}</div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  `,
};

createApp(app).mount("#app");
