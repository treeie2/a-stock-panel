let stockRows = [];
let quotesData = {};
let currentPage = 1;
const pageSize = 100;

async function loadPage() {
  const [metaRes, stocksRes] = await Promise.all([
    fetch("/api/meta"),
    fetch("/api/stocks"),
  ]);
  if (!metaRes.ok || !stocksRes.ok) {
    throw new Error("数据加载失败");
  }
  const meta = await metaRes.json();
  const stocksPayload = await stocksRes.json();
  stockRows = stocksPayload.stocks || [];
  renderMeta(meta);
  renderIndustry(meta.top_industries || []);
  renderStockIndex(stockRows);
  
  bindSearch();
  bindWechatParser();
  bindJsonImport();
  bindIndexFilter();
  bindAddStock();
  
  // Render immediately with placeholder quotes, then fetch real quotes
  currentPage = 1;
  renderTable(stockRows);
  fetchQuotesForRows(stockRows.slice(0, pageSize));
}

function bindWechatParser() {
  const btn = document.getElementById("parseBtn");
  const input = document.getElementById("wechatLink");
  btn.addEventListener("click", async () => {
    const url = input.value.trim();
    if (!url) return;
    
    // 显示加载状态
    btn.disabled = true;
    btn.textContent = "处理中...";
    
    // 创建处理进度UI
    const progressDiv = document.createElement('div');
    progressDiv.className = 'process-progress';
    progressDiv.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(0, 0, 0, 0.8);
      color: white;
      padding: 20px;
      border-radius: 8px;
      z-index: 1000;
      min-width: 300px;
      text-align: center;
    `;
    progressDiv.innerHTML = `
      <div class="progress-steps">
        <div class="step active">1. 提取链接内容</div>
        <div class="step">2. 分析股票信息</div>
        <div class="step">3. 生成数据</div>
        <div class="step">4. 完成</div>
      </div>
      <div class="progress-bar" style="width: 0%; height: 4px; background: #3b82f6; margin: 15px 0; transition: width 0.5s ease;"></div>
    `;
    document.body.appendChild(progressDiv);
    
    try {
      // 步骤1: 提取链接内容
      updateProgress(progressDiv, 1, 25);
      const res = await fetch("/api/parse_link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "识别失败");
      
      // 步骤2: 分析股票信息
      updateProgress(progressDiv, 2, 50);
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // 步骤3: 生成数据
      updateProgress(progressDiv, 3, 75);
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // 步骤4: 完成
      updateProgress(progressDiv, 4, 100);
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // 显示预览结果
      if (data.data && data.data.stocks && data.data.stocks.length > 0) {
        showPreviewPage(data.data);
      } else {
        alert("识别成功，但未提取到股票信息");
      }
      
      input.value = "";
    } catch (err) {
      alert("错误: " + err.message);
    } finally {
      // 移除进度UI
      if (progressDiv) {
        document.body.removeChild(progressDiv);
      }
      btn.disabled = false;
      btn.textContent = "识别网页";
    }
  });
}

function showPreviewPage(data) {
  // 创建预览页面
  const previewDiv = document.createElement('div');
  previewDiv.className = 'preview-page';
  previewDiv.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    z-index: 1001;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  `;
  
  const previewContent = document.createElement('div');
  previewContent.style.cssText = `
    background: white;
    border-radius: 8px;
    padding: 30px;
    max-width: 800px;
    max-height: 90vh;
    overflow-y: auto;
    width: 100%;
  `;
  
  // 预览内容
  let html = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h2 style="margin: 0; color: #1890ff;">提取结果预览</h2>
      <button id="closePreview" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #999;">&times;</button>
    </div>
    <div style="margin-bottom: 20px; padding: 10px; background: #f5f5f5; border-radius: 4px;">
      <strong>来源链接:</strong> ${escapeHtml(data.url)}
    </div>
    <h3 style="color: #333; margin-top: 20px; margin-bottom: 15px;">提取的股票信息</h3>
  `;
  
  // 股票信息列表
  data.stocks.forEach((stock, index) => {
    html += `
      <div style="border: 1px solid #e8e8e8; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
        <h4 style="margin-top: 0; color: #1890ff;">${escapeHtml(stock.name)} (${escapeHtml(stock.code)})</h4>
        <div style="margin-top: 10px;">
          <p><strong>行业:</strong> ${escapeHtml(stock.industry || '')}</p>
          <p><strong>板块:</strong> ${escapeHtml(stock.board || '')}</p>
          <p><strong>概念:</strong> ${Array.isArray(stock.concepts) ? stock.concepts.map(c => escapeHtml(c)).join(', ') : escapeHtml(stock.concepts || '')}</p>
          <p><strong>产品:</strong> ${Array.isArray(stock.products) ? stock.products.map(p => escapeHtml(p)).join(', ') : escapeHtml(stock.products || '')}</p>
          <p><strong>主营业务:</strong> ${Array.isArray(stock.core_business) ? stock.core_business.map(c => escapeHtml(c)).join(', ') : escapeHtml(stock.core_business || '')}</p>
          <p><strong>行业地位:</strong> ${Array.isArray(stock.industry_position) ? stock.industry_position.map(i => escapeHtml(i)).join(', ') : escapeHtml(stock.industry_position || '')}</p>
          <p><strong>产业链:</strong> ${Array.isArray(stock.chain) ? stock.chain.map(c => escapeHtml(c)).join(', ') : escapeHtml(stock.chain || '')}</p>
          <p><strong>合作方:</strong> ${Array.isArray(stock.partners) ? stock.partners.map(p => escapeHtml(p)).join(', ') : escapeHtml(stock.partners || '')}</p>
          <p><strong>提及次数:</strong> ${stock.mention_count || 0}</p>
        </div>
        <div style="margin-top: 10px;">
          <strong>文章:</strong>
          <ul style="margin-top: 5px; padding-left: 20px;">
            ${(stock.articles || []).map(article => `
              <li>${escapeHtml(article.title || '无标题')}</li>
            `).join('')}
          </ul>
        </div>
      </div>
    `;
  });
  
  // 操作按钮
  html += `
    <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
      <button id="cancelPreview" class="btn" style="padding: 8px 16px; border: 1px solid #d9d9d9; border-radius: 4px; background: white; cursor: pointer;">取消</button>
      <button id="confirmPreview" class="btn primary" style="padding: 8px 16px; border: 1px solid #1890ff; border-radius: 4px; background: #1890ff; color: white; cursor: pointer;">确认保存</button>
    </div>
  `;
  
  previewContent.innerHTML = html;
  previewDiv.appendChild(previewContent);
  document.body.appendChild(previewDiv);
  
  // 关闭按钮事件
  document.getElementById('closePreview').addEventListener('click', () => {
    document.body.removeChild(previewDiv);
  });
  
  // 取消按钮事件
  document.getElementById('cancelPreview').addEventListener('click', () => {
    document.body.removeChild(previewDiv);
  });
  
  // 确认保存按钮事件
  document.getElementById('confirmPreview').addEventListener('click', async () => {
    try {
      const saveRes = await fetch("/api/save_parsed_data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stocks: data.stocks })
      });
      
      const saveData = await saveRes.json();
      if (saveRes.ok) {
        alert(saveData.message);
        document.body.removeChild(previewDiv);
        // 刷新股票列表
        loadPage();
      } else {
        alert("保存失败: " + saveData.error);
      }
    } catch (err) {
      alert("保存失败: " + err.message);
    }
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function updateProgress(progressDiv, stepIndex, percentage) {
  const steps = progressDiv.querySelectorAll('.step');
  steps.forEach((step, index) => {
    if (index < stepIndex) {
      step.classList.add('active');
      step.style.color = '#3b82f6';
    } else if (index === stepIndex - 1) {
      step.classList.add('active');
      step.style.color = '#3b82f6';
    }
  });
  
  const progressBar = progressDiv.querySelector('.progress-bar');
  if (progressBar) {
    progressBar.style.width = percentage + '%';
  }
}

function bindJsonImport() {
  const fileInput = document.getElementById("jsonFileInput");
  const importBtn = document.getElementById("importJsonBtn");
  
  importBtn.addEventListener("click", () => {
    fileInput.click();
  });
  
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const jsonContent = JSON.parse(event.target.result);
        if (!jsonContent.stocks || !Array.isArray(jsonContent.stocks)) {
          throw new Error("无效的 JSON 格式，缺少 stocks 数组");
        }
        
        importBtn.disabled = true;
        importBtn.textContent = "导入中...";
        
        const res = await fetch("/api/import_json", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(jsonContent)
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "导入失败");
        
        alert(`导入成功！新增/更新了数据。`);
        // Reload page to show new data
        window.location.reload();
      } catch (err) {
        alert("导入错误: " + err.message);
      } finally {
        importBtn.disabled = false;
        importBtn.textContent = "导入 JSON";
        fileInput.value = ""; // Reset input
      }
    };
    reader.readAsText(file);
  });
}

async function fetchQuotesForRows(rows) {
  // We only fetch quotes for top 100 to avoid too long URL
  const codes = rows.slice(0, 100).map(r => {
    const b = (r.board || "").toLowerCase();
    const c = r.code || "";
    // default to sh or sz if missing, simple heuristic
    if (b) return `${b}${c}`;
    if (c.startsWith("6")) return `sh${c}`;
    if (c.startsWith("0") || c.startsWith("3")) return `sz${c}`;
    if (c.startsWith("4") || c.startsWith("8")) return `bj${c}`;
    return c;
  }).filter(Boolean);
  
  if (!codes.length) return;
  
  try {
    const res = await fetch(`/api/quotes?codes=${codes.join(",")}`);
    if (res.ok) {
      const data = await res.json();
      Object.assign(quotesData, data);
      // Re-render table with new quotes
      renderTable(rows);
    }
  } catch (err) {
    console.error("Failed to fetch quotes:", err);
  }
}

function renderMeta(meta) {
  document.getElementById("metaLine").textContent = `版本 ${meta.version || "-"} ｜ 更新时间 ${meta.update_time || "-"}`;
  document.getElementById("totalStocks").textContent = formatNumber(meta.total_stocks || 0);
  document.getElementById("totalMentions").textContent = formatNumber(meta.total_mentions || 0);
  document.getElementById("totalArticles").textContent = formatNumber(meta.total_articles || 0);
}

function renderIndustry(topIndustries) {
  const wrapper = document.getElementById("industryList");
  if (!topIndustries.length) {
    wrapper.innerHTML = "<div>暂无数据</div>";
    return;
  }
  const max = topIndustries[0][1] || 1;
  wrapper.innerHTML = topIndustries
    .map(([name, count]) => {
      const width = Math.max(4, (count / max) * 100);
      return `
        <div class="industry-row">
          <div class="industry-title"><span>${escapeHtml(name)}</span><strong>${count}</strong></div>
          <div class="industry-bar"><span style="width:${width}%"></span></div>
        </div>
      `;
    })
    .join("");
}

function renderTable(rows, append = false) {
  const body = document.getElementById("stocksTableBody");
  const start = (currentPage - 1) * pageSize;
  const end = currentPage * pageSize;
  const toRender = rows.slice(start, end);
  
  const html = toRender
    .map((item) => {
      const url = `/${encodeURIComponent(item.code)}`;
      const c = item.code || "";
      const b = (item.board || "").toLowerCase();
      let quoteKey = c;
      if (b) quoteKey = `${b}${c}`;
      else if (c.startsWith("6")) quoteKey = `sh${c}`;
      else if (c.startsWith("0") || c.startsWith("3")) quoteKey = `sz${c}`;
      else if (c.startsWith("4") || c.startsWith("8")) quoteKey = `bj${c}`;
      
      const q = quotesData[quoteKey] || { price: "-", change_pct: "-", market_cap: "-" };
      
      let changeClass = "";
      if (q.change_pct !== "-") {
        const pct = parseFloat(q.change_pct);
        if (pct > 0) changeClass = 'style="color: #f5222d; font-weight: bold;"';
        else if (pct < 0) changeClass = 'style="color: #52c41a; font-weight: bold;"';
      }
      
      // Concepts to string with click events
      let conceptStr = "";
      if (item.concepts && Array.isArray(item.concepts)) {
        conceptStr = item.concepts.slice(0, 3).map(concept => {
          return `<span class="concept-tag" onclick="filterByConcept('${escapeHtml(concept)}')" style="cursor: pointer; color: #1890ff; text-decoration: underline;">${escapeHtml(concept)}</span>`;
        }).join("、");
        if (item.concepts.length > 3) conceptStr += "...";
      }

      return `
        <tr>
          <td><a href="${url}" style="text-decoration: none; color: #1890ff; font-weight: bold;">${escapeHtml(item.name || "")} (${escapeHtml(item.code || "")})</a></td>
          <td title="${escapeHtml(item.industry || "")}">${truncate(item.industry || "", 15)}</td>
          <td title="${escapeHtml((item.concepts || []).join("、"))}">${conceptStr}</td>
          <td>${q.price}</td>
          <td ${changeClass}>${q.change_pct !== "-" ? q.change_pct + "%" : "-"}</td>
          <td>${q.market_cap !== "-" ? q.market_cap + "亿" : "-"}</td>
        </tr>
      `;
    })
    .join("");
  
  if (append) {
    body.innerHTML += html;
  } else {
    body.innerHTML = html;
  }
  
  // Update load more button
  updateLoadMoreButton(rows);
}

function updateLoadMoreButton(rows) {
  const tableWrap = document.querySelector(".table-wrap");
  let loadMoreBtn = document.getElementById("loadMoreBtn");
  
  if (!loadMoreBtn) {
    loadMoreBtn = document.createElement("div");
    loadMoreBtn.id = "loadMoreBtn";
    loadMoreBtn.className = "load-more-container";
    loadMoreBtn.innerHTML = `
      <button class="btn primary load-more-btn">
        <i class="fa-solid fa-sync-alt"></i> 加载更多
      </button>
    `;
    tableWrap.appendChild(loadMoreBtn);
  }
  
  const totalPages = Math.ceil(rows.length / pageSize);
  if (currentPage >= totalPages) {
    loadMoreBtn.style.display = "none";
  } else {
    loadMoreBtn.style.display = "flex";
  }
  
  // Add click event listener
  loadMoreBtn.querySelector(".load-more-btn").onclick = function() {
    currentPage++;
    renderTable(rows, true);
    fetchQuotesForRows(rows.slice((currentPage - 1) * pageSize, currentPage * pageSize));
  };
}

function renderStockIndex(rows) {
  const indexContainer = document.getElementById("stockIndex");
  if (!rows || !rows.length) {
    indexContainer.innerHTML = "<div>暂无数据</div>";
    return;
  }
  
  const indexData = {};
  rows.forEach(item => {
    const firstChar = (item.name || "").charAt(0).toUpperCase();
    let key = "#";
    
    if (/^[A-Z]$/.test(firstChar)) {
      key = firstChar;
    } else if (/^[\u4e00-\u9fa5]$/.test(firstChar)) {
      key = "#";
    } else if (/^[0-9]$/.test(firstChar)) {
      key = "0-9";
    }
    
    if (!indexData[key]) {
      indexData[key] = [];
    }
    indexData[key].push(item);
  });
  
  const sortedKeys = Object.keys(indexData).sort((a, b) => {
    if (a === "#") return 1;
    if (b === "#") return -1;
    if (a === "0-9") return -1;
    if (b === "0-9") return 1;
    return a.localeCompare(b);
  });
  
  indexContainer.innerHTML = sortedKeys.map(key => {
    const items = indexData[key];
    const displayKey = key === "#" ? "其他" : key;
    return `
      <div class="index-group" data-key="${key}">
        <div class="index-header">${displayKey} <span class="index-count">${items.length}</span></div>
        <div class="index-items">
          ${items.slice(0, 20).map(item => `
            <a href="/${encodeURIComponent(item.code)}" class="index-item" title="${escapeHtml(item.name)} (${escapeHtml(item.code)})">
              ${escapeHtml(item.name)}
            </a>
          `).join("")}
          ${items.length > 20 ? `<div class="index-more">+${items.length - 20} 更多</div>` : ""}
        </div>
      </div>
    `;
  }).join("");
}

function bindIndexFilter() {
  const filterBtns = document.querySelectorAll(".index-btn");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      
      const type = btn.dataset.type;
      const groups = document.querySelectorAll(".index-group");
      
      groups.forEach(group => {
        const key = group.dataset.key;
        if (type === "all") {
          group.style.display = "block";
        } else if (type === "letter") {
          group.style.display = /^[A-Z]$/.test(key) ? "block" : "none";
        } else if (type === "num") {
          group.style.display = (key === "0-9" || key === "#") ? "block" : "none";
        }
      });
    });
  });
}

function bindAddStock() {
  const btn = document.getElementById("addStockBtn");
  if (btn) {
    btn.addEventListener("click", () => {
      // 跳转到股票编辑页面，代码为空表示新增
      window.location.href = "/stock.html?mode=add";
    });
  }
}

function filterByConcept(concept) {
  // 过滤出包含该概念的股票
  const filtered = stockRows.filter(stock => {
    return stock.concepts && Array.isArray(stock.concepts) && stock.concepts.includes(concept);
  });
  
  // 显示过滤结果
  currentPage = 1;
  renderTable(filtered);
  fetchQuotesForRows(filtered.slice(0, pageSize));
  
  // 显示过滤提示
  const filterInfo = document.getElementById("filterInfo");
  if (!filterInfo) {
    const tableWrap = document.querySelector(".table-wrap");
    const infoDiv = document.createElement("div");
    infoDiv.id = "filterInfo";
    infoDiv.className = "filter-info";
    infoDiv.style.cssText = `
      background-color: #e6f7ff;
      border: 1px solid #91d5ff;
      border-radius: 4px;
      padding: 10px;
      margin-bottom: 10px;
      text-align: center;
      font-size: 14px;
    `;
    tableWrap.insertBefore(infoDiv, tableWrap.firstChild);
  }
  
  document.getElementById("filterInfo").innerHTML = `
    正在查看概念 "${concept}" 的股票 (共 ${filtered.length} 只)
    <button onclick="resetFilter()" style="margin-left: 10px; padding: 2px 8px; font-size: 12px; background-color: #1890ff; color: white; border: none; border-radius: 4px; cursor: pointer;">
      重置
    </button>
  `;
}

function resetFilter() {
  // 重置过滤，显示所有股票
  currentPage = 1;
  renderTable(stockRows);
  fetchQuotesForRows(stockRows.slice(0, pageSize));
  
  // 移除过滤提示
  const filterInfo = document.getElementById("filterInfo");
  if (filterInfo) {
    filterInfo.remove();
  }
}

function bindSearch() {
  const input = document.getElementById("searchInput");
  let timer = null;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const keyword = input.value.trim().toLowerCase();
      if (!keyword) {
        currentPage = 1;
        renderTable(stockRows);
        fetchQuotesForRows(stockRows.slice(0, pageSize));
        return;
      }
      const filtered = stockRows.filter((item) => {
        const cStr = (item.concepts || []).join(" ").toLowerCase();
        const key = `${item.name || ""} ${item.code || ""} ${item.industry || ""} ${cStr}`;
        return key.includes(keyword);
      });
      currentPage = 1;
      renderTable(filtered);
      fetchQuotesForRows(filtered.slice(0, pageSize));
    }, 300);
  });
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function truncate(text, maxLength) {
  if (text.length <= maxLength) {
    return escapeHtml(text);
  }
  return `${escapeHtml(text.slice(0, maxLength))}...`;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

loadPage().catch((error) => {
  document.getElementById("metaLine").textContent = error.message;
});
