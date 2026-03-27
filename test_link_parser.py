import link_parser

# 测试链接
url = "https://mp.weixin.qq.com/s/L-8gwdwBdHc7oHn7cKpMwA"

# 运行处理流程
result = link_parser.process_link(url)

# 打印结果
print("测试结果:")
print(f"类型: {type(result)}")
if isinstance(result, dict):
    print(f"包含stocks: {'stocks' in result}")
    if 'stocks' in result:
        print(f"股票数量: {len(result['stocks'])}")
        for stock in result['stocks'][:5]:
            print(f"  - {stock.get('name', '未知')} ({stock.get('code', '未知')})")
print(f"完整结果: {result}")
