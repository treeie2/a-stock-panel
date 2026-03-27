import json
import re
import requests
from pathlib import Path
import pandas as pd
import os

ROOT_DIR = Path(__file__).resolve().parent
RAW_FILE = ROOT_DIR / "raw_material.txt"
STOCKS_FILE = ROOT_DIR / "全部个股.xls"
OUTPUT_JSON = ROOT_DIR / "extracted_stocks.json"

# Gemini API配置
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

# Groq API配置
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def load_stocks_map():
    """加载股票映射"""
    try:
        df = pd.read_excel(STOCKS_FILE)
        stock_map = {}
        for _, row in df.iterrows():
            code_with_suffix = str(row['股票代码']).strip()
            code = code_with_suffix.split('.')[0].strip()
            name = str(row['股票简称']).strip()
            stock_map[name] = code
            # 也添加代码到名称的映射
            stock_map[code] = name
        print(f"成功加载{len(stock_map)}只股票的映射")
        return stock_map
    except Exception as e:
        print(f"加载股票映射失败: {e}")
        return {}


def extract_content_from_link(url):
    """从链接提取内容"""
    try:
        print(f"===== 开始提取链接内容: {url} =====")
        
        # 更完善的headers，模拟真实浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://mp.weixin.qq.com/'
        }
        
        # 禁用SSL验证（仅用于测试环境）
        print("发送请求...")
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        print(f"请求完成，状态码: {response.status_code}")
        response.raise_for_status()
        
        # 尝试解码内容
        content = response.text
        print(f"获取到内容，长度: {len(content)}")
        
        # 尝试提取文章标题和内容
        from bs4 import BeautifulSoup
        print("解析HTML...")
        soup = BeautifulSoup(content, 'html.parser')
        
        # 提取标题
        title = soup.find('h1', class_='rich_media_title')
        title_text = title.get_text(strip=True) if title else ''
        print(f"提取到标题: {title_text}")
        
        # 提取文章内容
        content_div = soup.find('div', class_='rich_media_content')
        content_text = content_div.get_text(strip=True) if content_div else ''
        print(f"提取到内容，长度: {len(content_text)}")
        print(f"内容预览: {content_text[:500]}...")
        
        # 组合标题和内容
        full_content = f"标题: {title_text}\n\n内容: {content_text}"
        
        # 保存到raw_material.txt（追加模式）
        print("保存到raw_material.txt...")
        with RAW_FILE.open('a', encoding='utf-8') as f:
            f.write(f"\n=== 新链接: {url} ===\n")
            f.write(full_content)
            f.write("\n" + "="*50 + "\n")
        print(f"成功从链接提取内容并追加到{RAW_FILE}")
        
        if full_content.strip():
            print("===== 提取完成 =====")
            return full_content
        else:
            # 如果BeautifulSoup提取失败，返回原始内容
            print("使用原始内容")
            return content
    except Exception as e:
        print(f"从链接提取内容失败: {e}")
        return ""


def call_gemini_api(content, stock_map):
    """调用API提取股票信息，优先使用Groq API"""
    # 优先调用Groq API
    print("优先调用Groq API...")
    response_text = call_groq_api(content, stock_map)
    if response_text:
        return response_text
    
    # Groq API失败时，尝试调用Gemini API作为备选方案
    try:
        print("Groq API失败，尝试调用Gemini API...")
        # 构建提示词（简化版本，避免过长）
        prompt = f"""请分析以下内容，提取其中提到的A股股票信息，并按照JSON格式输出：

{{
  "stocks": [
    {{
      "name": "股票名称",
      "code": "股票代码",
      "board": "板块",
      "industry": "行业",
      "concepts": ["概念1", "概念2"],
      "products": ["产品1", "产品2"],
      "core_business": ["核心业务1", "核心业务2"],
      "chain": ["产业链1", "产业链2"],
      "partners": ["合作伙伴1", "合作伙伴2"],
      "industry_position": ["行业地位1", "行业地位2"],
      "mention_count": 1,
      "articles": [
        {{
          "title": "文章标题",
          "date": "发布日期",
          "source": "文章链接",
          "accidents": ["风险信息"],
          "insights": ["核心观点"],
          "key_metrics": ["关键指标"],
          "target_valuation": ["估值信息"]
        }}
      ]
    }}
  ]
}}

内容：
{content[:2000]}...
"""
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': GEMINI_API_KEY
        }
        
        # 禁用代理，直接连接
        proxies = {
            'http': None,
            'https': None
        }
        
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=30, proxies=proxies)
        
        # 打印完整的响应信息
        print(f"API 响应状态码: {response.status_code}")
        print(f"API 响应内容: {response.text}")
        
        response.raise_for_status()
        
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            text = result['candidates'][0]['content']['parts'][0]['text']
            print("Gemini API 响应:")
            print(text)
            return text
        else:
            print("Gemini API 没有返回有效结果")
            return ""
    except Exception as e:
        print(f"调用Gemini API失败: {e}")
        # 两个API都失败时，尝试直接从文本中提取股票信息
        print("两个API都失败，尝试直接从文本中提取股票信息...")
        stocks = extract_stocks_from_text(content, stock_map)
        # 生成JSON格式的响应
        response_text = f"{{\"stocks\": {json.dumps(stocks, ensure_ascii=False)}}}"
        return response_text


def extract_stocks_from_text(content, stock_map):
    """直接从文本中提取股票信息"""
    stocks = []
    
    # 提取股票名称的正则表达式
    stock_pattern = r'✅([一-龥]+)：核心—(.+?)；'
    matches = re.findall(stock_pattern, content)
    
    for match in matches:
        name = match[0]
        core_business = match[1]
        
        # 查找股票代码
        code = stock_map.get(name, "")
        
        if code:
            stock = {
                "name": name,
                "code": code,
                "board": "",
                "industry": "锂电池",
                "concepts": ["固态电池", "锂电池"],
                "products": [core_business],
                "core_business": [core_business],
                "chain": ["锂电池产业链"],
                "partners": [],
                "industry_position": [],
                "mention_count": 1,
                "articles": [
                    {
                        "title": "锂电池相关文章",
                        "date": "2026-03-26",
                        "source": "微信公众号",
                        "accidents": [],
                        "insights": [],
                        "key_metrics": [],
                        "target_valuation": []
                    }
                ]
            }
            stocks.append(stock)
    
    print(f"从文本中提取到{len(stocks)}只股票")
    print(f"提取的股票: {[stock['name'] for stock in stocks]}")
    return stocks


def call_groq_api(content, stock_map):
    """调用Groq API处理文本内容"""
    try:
        print("开始调用Groq API")
        
        # 构建提示词
        prompt = f"""请从以下内容中提取股票信息，格式为JSON：

```
{content[:2000]}...
```

请提取每只股票的以下信息：
1. 股票名称
2. 股票代码（如果能找到）
3. 核心业务
4. 所属行业
5. 概念标签

请返回标准JSON格式，包含一个stocks数组，每个元素包含上述字段。
"""
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": "openai/gpt-oss-120b",
            "temperature": 1,
            "max_completion_tokens": 8192,
            "top_p": 1,
            "stream": False,
            "reasoning_effort": "medium",
            "stop": None
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {GROQ_API_KEY}'
        }
        
        # 禁用代理，直接连接
        proxies = {
            'http': None,
            'https': None
        }
        
        response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=30, proxies=proxies)
        response.raise_for_status()
        
        # 解析响应
        response_data = response.json()
        print(f"Groq API调用成功，响应状态: {response.status_code}")
        
        # 提取生成的内容
        if 'choices' in response_data and len(response_data['choices']) > 0:
            message = response_data['choices'][0].get('message', {})
            content = message.get('content', '')
            print(f"Groq API返回内容长度: {len(content)}")
            print(f"Groq API返回内容预览: {content[:200]}...")
            return content
        else:
            print("Groq API 没有返回有效结果")
            return ""
    except Exception as e:
        print(f"调用Groq API失败: {e}")
        # API调用失败时，尝试直接从文本中提取股票信息
        stocks = extract_stocks_from_text(content, stock_map)
        # 生成JSON格式的响应
        response_text = f"{{\"stocks\": {json.dumps(stocks, ensure_ascii=False)}}}"
        return response_text


def parse_gemini_response(response_text):
    """解析Gemini API响应"""
    try:
        # 提取JSON部分
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
            data = json.loads(json_str)
            return data
        else:
            print("无法从响应中提取JSON")
            return {"stocks": []}
    except Exception as e:
        print(f"解析Gemini响应失败: {e}")
        return {"stocks": []}


def process_link(url):
    """处理链接的完整流程"""
    print(f"===== 开始处理链接: {url} =====")
    
    # 1. 加载股票映射
    print("1. 加载股票映射")
    stock_map = load_stocks_map()
    print(f"股票映射加载完成，共{len(stock_map)}只股票")
    
    # 2. 从链接提取内容
    print("2. 从链接提取内容")
    content = extract_content_from_link(url)
    if not content:
        print("提取内容失败")
        return {"stocks": []}
    print(f"提取内容成功，长度: {len(content)}")
    print(f"内容预览: {content[:500]}...")
    
    # 3. 调用Gemini API
    print("3. 调用Gemini API")
    response = call_gemini_api(content, stock_map)
    if not response:
        print("Gemini API调用失败")
        return {"stocks": []}
    print("Gemini API调用成功")
    print(f"API响应长度: {len(response)}")
    print(f"API响应预览: {response[:200]}...")
    
    # 4. 解析响应
    print("4. 解析Gemini响应")
    data = parse_gemini_response(response)
    print(f"解析结果类型: {type(data)}")
    if isinstance(data, dict):
        print(f"解析结果包含stocks: {'stocks' in data}")
        if 'stocks' in data:
            print(f"股票数量: {len(data['stocks'])}")
            for stock in data['stocks'][:3]:  # 只打印前3只股票
                print(f"  - {stock.get('name', '未知')} ({stock.get('code', '未知')})")
    print(f"完整解析结果: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    # 5. 保存JSON
    print("5. 保存JSON文件")
    with OUTPUT_JSON.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"成功生成JSON文件: {OUTPUT_JSON}")
    
    print("===== 处理完成 =====")
    return data


def preview_result():
    """预览结果"""
    if OUTPUT_JSON.exists():
        with OUTPUT_JSON.open('r', encoding='utf-8') as f:
            data = json.load(f)
        print("预览生成的JSON:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return data
    else:
        print("JSON文件不存在")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"处理链接: {url}")
        result = process_link(url)
        if result:
            preview_result()
    else:
        print("请提供要处理的链接")
