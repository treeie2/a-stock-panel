const API_CONFIG = {
  // 本地开发环境
  local: {
    baseUrl: 'http://localhost:8787'
  },
  // 生产环境（需要替换为实际的云服务器地址）
  production: {
    baseUrl: 'https://your-server-domain.com'  // 替换为您的云服务器域名
  }
};

// 根据当前环境自动选择API地址
function getApiBaseUrl() {
  // 检查是否在GitHub Pages环境
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return API_CONFIG.local.baseUrl;
  } else {
    return API_CONFIG.production.baseUrl;
  }
}

// 导出API配置
window.API_BASE_URL = getApiBaseUrl();
