const query = new URLSearchParams(window.location.search);
const code = resolveCode();
const mode = query.get('mode') || 'view';
let currentStock = null;

const fieldKeys = [
  "name",
  "code",
  "board",
  "industry",
  "mention_count",
  "concepts",
  "products",
  "core_business",
  "industry_position",
  "chain",
  "partners",
  "articles",
];

function resolveCode() {
  const fromQuery = (query.get("code") || "").trim();
  if (fromQuery) {
    return fromQuery;
  }
  const fromPath = window.location.pathname.replace(/^\/+|\/+$/g, "");
  if (/^\d{5,6}$/.test(fromPath)) {
    return fromPath;
  }
  return "";
}

function mapStockFields(stock) {
  // 字段映射，解决后端返回字段与前端期望字段不匹配的问题
  return {
    name: stock.name || stock.stock_name || "",
    code: stock.code || stock.stock_code || "",
    board: stock.board || stock.market || "",
    industry: stock.industry || stock.industry_name || "",
    mention_count: stock.mention_count || stock.mention_times || 0,
    concepts: stock.concepts || stock.concept || [],
    products: stock.products || stock.product || [],
    core_business: stock.core_business || stock.main_business || [],
    industry_position: stock.industry_position || stock.industry_status || [],
    chain: stock.chain || stock.industry_chain || [],
    partners: stock.partners || stock.cooperation || [],
    articles: stock.articles || stock.sample_articles || []
  };
}

async function loadStock() {
  if (mode === 'add') {
    // 新增模式，初始化空表单
    currentStock = {
      name: '',
      code: '',
      board: '',
      industry: '',
      mention_count: 0,
      concepts: [],
      products: [],
      core_business: [],
      industry_position: [],
      chain: [],
      partners: [],
      articles: []
    };
    fillForm(currentStock);
    document.getElementById("stockTitle").textContent = "新增股票";
    document.getElementById("stockSubTitle").textContent = "请填写股票信息";
    document.getElementById("code").readOnly = false; // 新增时代码可编辑
    setStatus("准备新增股票");
  } else if (!code) {
    setStatus("缺少股票代码");
    return;
  } else {
    const res = await fetch(`/api/stocks/${encodeURIComponent(code)}`);
    if (!res.ok) {
      throw new Error("加载个股失败");
    }
    const payload = await res.json();
    
    // 字段映射，解决后端返回字段与前端期望字段不匹配的问题
    currentStock = mapStockFields(payload.stock);
    
    fillForm(currentStock);
    document.getElementById("stockTitle").textContent = `${currentStock.name} (${currentStock.code})`;
    document.getElementById("stockSubTitle").textContent = currentStock.industry || "";
    
    loadRelatedStocks();
    bindQueryTabs();
  }
  
  bindEditButton();
}

function fillForm(stock) {
  // 显示基本信息
  document.getElementById("name").textContent = stock.name || "";
  document.getElementById("code").textContent = stock.code || "";
  document.getElementById("board").textContent = stock.board || "";
  document.getElementById("industry").textContent = stock.industry || "";
  document.getElementById("mention_count").textContent = Number(stock.mention_count || 0);
  
  // 显示概念（标签形式）
  renderConcepts(stock.concepts || []);
  
  // 显示其他列表数据
  document.getElementById("products").textContent = joinLines(stock.products);
  document.getElementById("core_business").textContent = joinLines(stock.core_business);
  document.getElementById("industry_position").textContent = joinLines(stock.industry_position);
  document.getElementById("chain").textContent = joinLines(stock.chain);
  document.getElementById("partners").textContent = joinLines(stock.partners);
  
  // 显示文章数据（可视化方式）
  renderArticlesVisualizer(stock.articles || []);
}

function renderConcepts(concepts) {
  const container = document.getElementById("concepts");
  if (!concepts || concepts.length === 0) {
    container.innerHTML = "<p style='color: #999;'>暂无概念数据</p>";
    return;
  }
  
  container.innerHTML = concepts.map(concept => {
    return `<span class="tag" onclick="filterByConcept('${escapeHtml(concept)}')" style="cursor: pointer;">${escapeHtml(concept)}</span>`;
  }).join("");
}

function renderArticlesVisualizer(articles) {
  const container = document.getElementById("articlesList");
  if (!articles || !articles.length) {
    container.innerHTML = "<p>暂无文章数据</p>";
    return;
  }
  
  container.innerHTML = articles.map((article, index) => {
    const renderTags = (items, type) => {
      if (!items || !items.length) return "";
      return `<div class="tag-list">` + items.map(item => `<span class="tag ${type}">${escapeHtml(item)}</span>`).join("") + `</div>`;
    };
    
    return `
      <div class="article-card">
        <h4>${index + 1}. ${escapeHtml(article.title || "无标题")}</h4>
        <div class="article-meta">
          <span>日期: ${escapeHtml(article.date || "-")}</span>
          ${article.source ? `<span><a href="${escapeHtml(article.source)}" target="_blank">来源链接</a></span>` : ""}
        </div>
        
        ${article.accidents && article.accidents.length ? `<div class="article-section-title">事故/风险 (Accidents)</div>${renderTags(article.accidents, 'danger')}` : ''}
        ${article.insights && article.insights.length ? `<div class="article-section-title">核心观点 (Insights)</div>${renderTags(article.insights, 'success')}` : ''}
        ${article.key_metrics && article.key_metrics.length ? `<div class="article-section-title">关键指标 (Key Metrics)</div>${renderTags(article.key_metrics, '')}` : ''}
        ${article.target_valuation && article.target_valuation.length ? `<div class="article-section-title">估值 (Valuation)</div>${renderTags(article.target_valuation, '')}` : ''}
      </div>
    `;
  }).join("");
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function collectForm() {
  const next = {};
  next.name = getValue("name");
  next.code = getValue("code");
  next.board = getValue("board");
  next.industry = getValue("industry");
  next.mention_count = Number(getValue("mention_count") || 0);
  next.concepts = splitLines(getValue("concepts"));
  next.products = splitLines(getValue("products"));
  next.core_business = splitLines(getValue("core_business"));
  next.industry_position = splitLines(getValue("industry_position"));
  next.chain = splitLines(getValue("chain"));
  next.partners = splitLines(getValue("partners"));
  const articlesRaw = getValue("articles").trim();
  next.articles = articlesRaw ? JSON.parse(articlesRaw) : [];
  if (!Array.isArray(next.articles)) {
    throw new Error("文章数据必须是 JSON 数组");
  }
  const safeBase = currentStock || {};
  const merged = {};
  for (const key of Object.keys(safeBase)) {
    merged[key] = safeBase[key];
  }
  for (const key of fieldKeys) {
    merged[key] = next[key];
  }
  merged.article_count = next.articles.length;
  return merged;
}

async function saveStock() {
  try {
    const stock = collectForm();
    let res;
    
    if (mode === 'add') {
      // 新增股票
      res = await fetch("/api/stocks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ stock }),
      });
    } else {
      // 更新股票
      res = await fetch(`/api/stocks/${encodeURIComponent(code)}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ stock }),
      });
    }
    
    const payload = await res.json();
    if (!res.ok) {
      throw new Error(payload.error || "保存失败");
    }
    
    setStatus("保存成功");
    
    if (mode === 'add') {
      // 新增成功后跳转到详情页
      window.location.href = `/${encodeURIComponent(stock.code)}`;
    } else {
      await loadStock();
    }
  } catch (error) {
    setStatus(error.message || "保存失败");
  }
}

function getValue(id) {
  const element = document.getElementById(id);
  return element ? element.value : '';
}

function splitLines(input) {
  return input
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function joinLines(value) {
  if (!Array.isArray(value)) {
    return "";
  }
  return value.join("\n");
}

function setStatus(text) {
  document.getElementById("statusLine").textContent = text;
}

function bindEditButton() {
  const editBtn = document.getElementById("editBtn");
  if (editBtn) {
    editBtn.addEventListener("click", function() {
      // 切换表单为编辑模式
      switchToEditMode(currentStock);
      setStatus("编辑模式已开启");
    });
  }
}

function switchToEditMode(stock) {
  // 检查是否是待完善的股票（没有正确代码）
  const isPendingStock = stock.pending_code === true || (stock.code && stock.code.startsWith('PENDING_'));
  
  // 替换基本信息为输入框
  replaceInfoWithInput("name", stock.name || "");
  // 待完善的股票允许编辑代码，其他股票代码只读
  replaceInfoWithInput("code", stock.code || "", !isPendingStock); 
  replaceInfoWithInput("board", stock.board || "");
  replaceInfoWithInput("industry", stock.industry || "");
  replaceInfoWithInput("mention_count", stock.mention_count || 0, false, "number");
  
  // 替换列表数据为textarea
  replaceSectionWithTextarea("concepts", joinLines(stock.concepts));
  replaceSectionWithTextarea("products", joinLines(stock.products));
  replaceSectionWithTextarea("core_business", joinLines(stock.core_business));
  replaceSectionWithTextarea("industry_position", joinLines(stock.industry_position));
  replaceSectionWithTextarea("chain", joinLines(stock.chain));
  replaceSectionWithTextarea("partners", joinLines(stock.partners));
}

function replaceInfoWithInput(id, value, readOnly = false, type = "text") {
  const element = document.getElementById(id);
  const input = document.createElement("input");
  input.type = type;
  input.id = id;
  input.value = value;
  input.readOnly = readOnly;
  input.style.width = "100%";
  input.style.padding = "8px";
  input.style.border = "1px solid #d9d9d9";
  input.style.borderRadius = "4px";
  input.style.fontSize = "16px";
  element.parentNode.replaceChild(input, element);
}

function replaceSectionWithTextarea(id, value) {
  const element = document.getElementById(id);
  const textarea = document.createElement("textarea");
  textarea.id = id;
  textarea.value = value;
  textarea.rows = 5;
  textarea.style.width = "100%";
  textarea.style.padding = "12px";
  textarea.style.border = "1px solid #d9d9d9";
  textarea.style.borderRadius = "8px";
  textarea.style.resize = "vertical";
  textarea.style.fontSize = "15px";
  textarea.style.lineHeight = "1.6";
  element.parentNode.replaceChild(textarea, element);
}

async function loadRelatedStocks() {
  try {
    const allStocksRes = await fetch("/api/stocks");
    if (!allStocksRes.ok) {
      throw new Error("加载全部股票失败");
    }
    const allStocksData = await allStocksRes.json();
    const allStocks = allStocksData.stocks || [];
    
    const currentIndustry = currentStock.industry || "";
    const currentConcepts = new Set(currentStock.concepts || []);
    const currentChain = new Set(currentStock.chain || []);
    const currentPartners = new Set(currentStock.partners || []);
    
    const industryResults = [];
    const conceptResults = [];
    const chainResults = [];
    const partnerResults = [];
    
    allStocks.forEach(stock => {
      if (stock.code === currentStock.code) return;
      
      if (stock.industry === currentIndustry && currentIndustry) {
        industryResults.push(stock);
      }
      
      const stockConcepts = new Set(stock.concepts || []);
      const commonConcepts = [...currentConcepts].filter(c => stockConcepts.has(c));
      if (commonConcepts.length > 0) {
        conceptResults.push({ stock, commonConcepts });
      }
      
      const stockChain = new Set(stock.chain || []);
      const commonChain = [...currentChain].filter(c => stockChain.has(c));
      if (commonChain.length > 0) {
        chainResults.push({ stock, commonChain });
      }
      
      const stockPartners = new Set(stock.partners || []);
      const commonPartners = [...currentPartners].filter(p => stockPartners.has(p));
      if (commonPartners.length > 0) {
        partnerResults.push({ stock, commonPartners });
      }
    });
    
    renderRelatedStocks("industry", industryResults.slice(0, 20));
    renderRelatedStocks("concept", conceptResults.slice(0, 20));
    renderRelatedStocks("chain", chainResults.slice(0, 20));
    renderRelatedStocks("partner", partnerResults.slice(0, 20));
  } catch (error) {
    console.error("加载关联股票失败:", error);
  }
}

function renderRelatedStocks(type, results) {
  const container = document.getElementById(`${type}Results`);
  if (!results || results.length === 0) {
    container.innerHTML = "<p class=\"no-results\">暂无关联数据</p>";
    return;
  }
  
  container.innerHTML = results.map(item => {
    const stock = item.stock || item;
    const commonTags = item.commonConcepts || item.commonChain || item.commonPartners || [];
    return `
      <div class="related-stock-item">
        <a href="/${encodeURIComponent(stock.code)}" class="related-stock-link">
          <span class="stock-name">${escapeHtml(stock.name)}</span>
          <span class="stock-code">${escapeHtml(stock.code)}</span>
        </a>
        ${commonTags.length > 0 ? `
          <div class="common-tags">
            ${commonTags.slice(0, 5).map(tag => `<span class="common-tag">${escapeHtml(tag)}</span>`).join("")}
          </div>
        ` : ""}
      </div>
    `;
  }).join("");
}

function bindQueryTabs() {
  const tabs = document.querySelectorAll(".query-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      
      const selectedTab = tab.dataset.tab;
      const results = document.querySelectorAll(".query-result");
      results.forEach(r => r.classList.remove("active"));
      
      document.getElementById(`${selectedTab}Results`).classList.add("active");
    });
  });
}

document.getElementById("saveBtn").addEventListener("click", saveStock);
document.getElementById("reloadBtn").addEventListener("click", () => {
  loadStock().catch((error) => setStatus(error.message || "重载失败"));
});

loadStock().catch((error) => {
  setStatus(error.message || "加载失败");
});
