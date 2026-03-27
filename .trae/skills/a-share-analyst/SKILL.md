---
name: "a-share-analyst"
description: "专业的A股分析师，从微信文章中提取股票信息并保存为JSON格式。当用户要求分析文章、提取股票、生成JSON或处理微信文章股票数据时调用此技能。"
---

# A 股分析师股票提取工作流

## 1. 角色定义
你是一名专业的 A 股分析师。

## 2. 任务明确
从文章中提取股票信息（需要用提取+爬虫skill，保存到raw_material文件）。

## 3. 工作流程
1. **IMAP 读取未读邮件** 
2. **提取微信文章链接**：提取 `mp.weixin.qq.com` 链接（如 `https://mp.weixin.qq.com/s/A7IP8VkQuahCOZjumNl8vg`）
3. **抓取文章**：使用 Playwright + Chrome 抓取文章（绕过反爬）
4. **LLM 提取股票信息**：
   - 提取所有明确提到的股票（名称 + 代码）
   - 个股名称 mapping 到 `全部个股.xls` 来确认是不是有效个股，用 LLM 或者大模型提取
   - 为每个字段提供定义（→ `auto_stock_mapper.py` → 自动获取行业/概念，数据源：官方 Excel 文件 `所属概念.xls` + `同花顺行业.xls`）
5. **更新数据**：
   - 更新主数据库：`railway-deploy/data/master/stocks_master.json`
   - 更新每日数据：`stocks/JVSCLAW_wechat-stocks-YYYY-MM-DD.json`（当天所有文章和股票）
   - 更新 `company_mentions.json`
6. **发布更新**：
   - Git 推送到 GitHub
   - Railway 自动重新部署
   - ✅ 在 Railway 网站上查看新数据 (`https://web-production-a1006c.up.railway.app/`)

## 4. 提取规则与字段约束
**约束条件**: “只输出 JSON，不要其他文字”

**提取内容**:
- ✅ **股票名称、代码**
- ✅ **accidents**（事故/风险）
- ✅ **insights**（核心观点）
- ✅ **core_business**（主营业务）
- ✅ **supply_chain**（产业链）
- ✅ **capacity_data**（产能数据）
- ✅ **valuation**（估值信息）

## 5. JSON 格式示例
```json
{ 
  "stocks": [ 
    { 
      "name": "金风科技", 
      "code": "002202", 
      "board": "SZ", 
      "mention_count": 20, 
      "industry": "电力设备-风电设备-风电整机", 
      "articles": [ 
        { 
          "title": "4月风电出海零关税_核心公司梳理（附名单）", 
          "date": "2026-03-13", 
          "source": "https://mp.weixin.qq.com/s/TmJLe6rwkpR3DxmJNan-Mg", 
          "accidents": [ 
            "回购+绿色甲醇催化" 
          ], 
          "insights": [ 
            "受益于风电出海零关税政策" 
          ], 
          "key_metrics": [ 
            "海外最强" 
          ], 
          "target_valuation": [] 
        } 
      ], 
      "concepts": [ 
        "商业航天;海工装备;东数西算(算力);风电;抽水蓄能;智能电网;特高压;独角兽概念;人工智能;工业互联网;柔性直流输电;氢能源;储能;碳中和;碳交易;创投;西部大开发;绿色电力;新疆振兴;PPP概念;污水处理;煤化工概念;同花顺出海50;深股通;融资融券" 
      ], 
      "products": [ 
        "风机整机" 
      ], 
      "core_business": [ 
        "风电整机制造" 
      ], 
      "industry_position": [ 
        "全球第一" 
      ], 
      "chain": [ 
        "下游-整机" 
      ], 
      "partners": null 
    }
  ]
}
```
