import requests
import json

# 检查/api/stocks接口返回的数据
response = requests.get('http://127.0.0.1:8787/api/stocks')
if response.status_code == 200:
    data = response.json()
    stocks = data.get('stocks', [])
    print(f"总共有{len(stocks)}只股票")
    
    # 检查前5只股票的完整数据
    print("\n前5只股票的完整数据:")
    for i, stock in enumerate(stocks[:5]):
        print(f"\n{i+1}. {stock['name']} ({stock['code']})")
        print(f"   行业: {stock.get('industry', '未知')}")
        print(f"   概念: {stock.get('concepts', [])}")
        print(f"   概念数量: {len(stock.get('concepts', []))}")
else:
    print(f"请求失败: {response.status_code}")
