import pandas as pd
from pathlib import Path

STOCKS_FILE = Path(__file__).resolve().parent / "全部个股.xls"


def check_stocks_excel():
    """检查全部个股.xls的结构"""
    try:
        df = pd.read_excel(STOCKS_FILE)
        print("Excel文件列名:")
        print(df.columns.tolist())
        
        print("\n前5行数据:")
        print(df.head())
        
        print("\n数据类型:")
        print(df.dtypes)
        
        print(f"\n总共有{len(df)}条数据")
        
    except Exception as e:
        print(f"读取Excel文件失败: {e}")


if __name__ == "__main__":
    check_stocks_excel()
