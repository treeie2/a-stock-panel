import json
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
STOCKS_FILE = ROOT_DIR / "stocks_master.json"
CONCEPTS_FILE = ROOT_DIR / "所属概念.xls"


def load_stocks():
    """加载股票数据"""
    with STOCKS_FILE.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_stocks(data):
    """保存股票数据"""
    with STOCKS_FILE.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_concepts():
    """加载概念数据"""
    try:
        df = pd.read_excel(CONCEPTS_FILE)
        print(f"成功读取Excel文件，共{len(df)}行数据")
        return df
    except Exception as e:
        print(f"读取Excel文件失败: {e}")
        return None


def update_concepts():
    """更新概念数据"""
    # 加载数据
    stocks_data = load_stocks()
    concepts_df = load_concepts()
    
    if concepts_df is None:
        print("无法加载概念数据，退出")
        return
    
    # 构建股票代码到概念的映射
    concept_map = {}
    
    for _, row in concepts_df.iterrows():
        code_with_suffix = str(row.get('股票代码', '')).strip()
        if not code_with_suffix:
            continue
        
        # 移除后缀，只保留数字部分
        code = code_with_suffix.split('.')[0].strip()
        
        # 提取概念字段并分割
        concepts_str = str(row.get('所属概念', '')).strip()
        if concepts_str and concepts_str != 'nan':
            # 用分号分割概念
            concepts = [c.strip() for c in concepts_str.split(';') if c.strip()]
            concept_map[code] = concepts
    
    print(f"共提取{len(concept_map)}只股票的概念数据")
    
    # 更新股票数据
    updated_count = 0
    for stock in stocks_data.get('stocks', []):
        code = str(stock.get('code', '')).strip()
        if code in concept_map:
            stock['concepts'] = concept_map[code]
            updated_count += 1
    
    # 更新版本信息
    stocks_data['version'] = f"v17-2026-03-26-concepts-updated"
    
    # 保存数据
    save_stocks(stocks_data)
    
    print(f"成功更新{updated_count}只股票的概念数据")
    print(f"更新后股票总数: {len(stocks_data.get('stocks', []))}")


if __name__ == "__main__":
    update_concepts()
