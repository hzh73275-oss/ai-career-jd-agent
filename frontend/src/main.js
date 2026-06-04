import { createApp, reactive, computed, onMounted } from "https://unpkg.com/vue@3/dist/vue.esm-browser.js";

const API_BASE = "http://127.0.0.1:8765";

const pages = [
  { key: "dashboard", name: "工作台", icon: "⌂" },
  { key: "resume", name: "简历管理", icon: "▣" },
  { key: "search", name: "岗位搜索", icon: "⌕" },
  { key: "detail", name: "岗位详情", icon: "◉" },
  { key: "match", name: "匹配分析", icon: "◎" },
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
      report: emptyReport,
      reportText: "",
      adviceText: "",
      comparisonRows: [],
      comparisonText: "",
      translationText: "",
      fullReport: "",

      polishTab: "rule",
      polishLoading: false,
      llmPolishText: "",
      reportExpanded: {
        match: false,
        comparison: false,
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

    const setPage = (page) => {
      state.page = page;
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
        setNotice("岗位信息已提取。");
      } catch (error) {
        setError(`岗位信息提取失败：${error.message}`);
      } finally {
        state.jobLoading = false;
      }
    };

    const generateMatch = async () => {
      state.matchLoading = true;
      try {
        const data = await apiPost("/api/match", {});
        state.reportReady = true;
        state.report = data.report;
        state.reportText = data.report_text;
        state.adviceText = data.advice_text;
        state.comparisonRows = data.comparison_rows || [];
        state.comparisonText = data.comparison_text;
        state.translationText = data.translation_text;
        state.fullReport = data.full_report;
        setNotice("匹配分析已生成。");
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
      tierCounts,
      currentJobs,
      showNoKeyGuide,
      manualSearchLinks,
      currentTierPage,
      totalJobPages,
      pagedJobs,
      visiblePageNumbers,
      selectedJobView,
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
              <div class="helper-title">使用说明</div>
              <div class="helper-text">先启动本地 API，再上传简历、搜索岗位、生成匹配报告。</div>
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
                <div class="section-title">搜索条件</div>
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
                  <div class="key-guide-title">无 Key 也可以继续使用</div>
                  <div class="key-guide-note">
                    {{ state.searchFallbackReason || "没有 Tavily Key？没关系。你可以先去招聘平台手动搜索岗位，再把 JD 粘贴到这里做本地分析。" }}
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
                  <div class="field manual-jd-field">
                    <label>粘贴 JD 做本地分析</label>
                    <textarea
                      class="textarea"
                      v-model="state.manualJdText"
                      placeholder="把招聘网站复制来的岗位描述粘贴到这里，不配置 Tavily Key 也能提取 JD、匹配简历。"
                    ></textarea>
                  </div>
                  <button class="btn primary full" @click="analyzeManualJd" :disabled="state.jobLoading">
                    {{ state.jobLoading ? "提取中..." : "提取手动 JD" }}
                  </button>
                  <a class="key-guide-link" href="https://app.tavily.com" target="_blank">想开启自动搜索？去 Tavily 获取自己的 Key</a>
                </div>
                <button class="btn primary full" @click="searchJobs" :disabled="state.searchLoading">
                  {{ state.searchLoading ? "跨平台搜索中..." : "搜索岗位" }}
                </button>
                <div class="metric-note" style="margin-top:10px;">联网搜索使用你自己的 Tavily Key；深度搜索会消耗更多免费额度。</div>
              </div>

              <div>
                <div class="page-head" style="margin-bottom:12px;">
                  <div>
                    <h1 class="page-title">岗位列表</h1>
                <div class="page-subtitle">{{ state.jobs.length ? '共 ' + state.jobs.length + ' 个候选岗位' : '还没有岗位结果。请先搜索岗位，或粘贴 JD 做本地分析。' }}</div>
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
              <button class="btn primary" @click="generateMatch" :disabled="state.matchLoading">{{ state.matchLoading ? "生成中..." : "生成匹配分析" }}</button>
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
