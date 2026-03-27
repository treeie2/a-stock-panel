import pandas as pd
from pathlib import Path

CONCEPTS_FILE = Path(__file__).resolve().parent / "所属概念.xls"


def check_excel_structure():
    """检查Excel文件结构"""
    try:
        df = pd.read_excel(CONCEPTS_FILE)
        print("Excel文件列名:")
        print(df.columns.tolist())
        
        print("\n前5行数据:")
        print(df.head())
        
        print("\n数据类型:")
        print(df.dtypes)
        
        # 检查代码列的格式
        code_column = None
        for col in df.columns:
            if '代码' in col or 'Code' in col:
                code_column = col
                break
        
        if code_column:
            print(f"\n代码列: {code_column}")
            print("前10个代码:")
            print(df[code_column].head(10).tolist())
    except Exception as e:
        print(f"读取Excel文件失败: {e}")


if __name__ == "__main__":
    check_excel_structure()
