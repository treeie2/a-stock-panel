import os
from pathlib import Path

print(f"当前工作目录: {os.getcwd()}")
print(f"脚本所在目录: {Path(__file__).resolve().parent}")

# 检查stocks_master.json文件是否存在
ROOT_DIR = Path(__file__).resolve().parent
DATA_FILE = ROOT_DIR / "stocks_master.json"
print(f"stocks_master.json文件存在: {DATA_FILE.exists()}")
print(f"stocks_master.json文件大小: {DATA_FILE.stat().st_size if DATA_FILE.exists() else '不存在'}")
