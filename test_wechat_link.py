import link_parser

# 测试微信链接
url = "https://mp.weixin.qq.com/s/9rtNxVZldkfk7dS9zJXxxQ"

print(f"测试链接: {url}")
result = link_parser.process_link(url)

if result:
    print("解析成功！")
    print(f"提取到{len(result['stocks'])}只股票")
    for stock in result['stocks']:
        print(f"- {stock['name']} ({stock['code']}) - {stock['industry']}")
else:
    print("解析失败")
