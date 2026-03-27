import requests
import json

# 检查/api/stocks接口返回的concepts字段
response = requests.get('http://127.0.0.1:8787/api/stocks')
if response.status_code == 200:
    data = response.json()
    stocks = data.get('stocks', [])
    print(f"总共有{len(stocks)}只股票")
    
    # 检查前10只股票的concepts字段
    print("\n前10只股票的concepts字段:")
    for i, stock in enumerate(stocks[:10]):
        name = stock.get('name', '未知')
        code = stock.get('code', '未知')
        concepts = stock.get('concepts', [])
        print(f"{i+1}. {name} ({code}): {concepts}")
        
    # 检查是否有股票包含concepts
    stocks_with_concepts = [stock for stock in stocks if stock.get('concepts')]
    print(f"\n有{len(stocks_with_concepts)}只股票包含concepts字段")
else:
    print(f"请求失败: {response.status_code}")
