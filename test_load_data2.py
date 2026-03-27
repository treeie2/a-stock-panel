import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_FILE = ROOT_DIR / "stocks_master.json"

def test_load_data():
    """测试加载数据"""
    try:
        with DATA_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"数据类型: {type(data)}")
        print(f"数据键: {list(data.keys())}")
        
        stocks = data.get('stocks', [])
        print(f"成功加载{len(stocks)}只股票")
        
        # 检查前5只股票
        for i, stock in enumerate(stocks[:5]):
            name = stock.get('name', '未知')
            code = stock.get('code', '未知')
            concepts = stock.get('concepts', [])
            print(f"{i+1}. {name} ({code}): {concepts[:3]}...")
            print(f"   概念数量: {len(concepts)}")
            
    except Exception as e:
        print(f"加载数据失败: {e}")


if __name__ == "__main__":
    test_load_data()
