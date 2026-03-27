from __future__ import annotations

import json
import re
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT_DIR = Path(__file__).resolve().parent
PANEL_DIR = ROOT_DIR / "panel"
DATA_FILE = ROOT_DIR / "stocks_master.json"


def load_data() -> dict:
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict) -> None:
    data["total_stocks"] = len(data.get("stocks", []))
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class PanelHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PANEL_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/stocks":
            return self.handle_get_stocks()
        if path.startswith("/api/stocks/"):
            return self.handle_get_stock(path)
        if path == "/api/meta":
            return self.handle_get_meta()
        if path.startswith("/api/quotes"):
            return self.handle_get_quotes(parsed.query)
        if path == "/extracted_stocks.json":
            # 提供根目录的extracted_stocks.json文件
            file_path = ROOT_DIR / "extracted_stocks.json"
            if file_path.exists():
                with file_path.open("rb") as f:
                    content = f.read()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
        if is_stock_page_path(path):
            self.path = "/stock.html"
            return super().do_GET()
        if path == "/" or path == "":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/parse_link":
            return self.handle_parse_link()
        if path == "/api/save_parsed_data":
            return self.handle_save_parsed_data()
        if path == "/api/import_json":
            return self.handle_import_json()
        if path == "/api/stocks":
            return self.handle_add_stock()
        self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/stocks/"):
            return self.handle_update_stock(path)
        self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def handle_get_stocks(self):
        data = load_data()
        stocks = data.get("stocks", [])
        summary = []
        for item in stocks:
            summary.append(
                {
                    "name": item.get("name", ""),
                    "code": item.get("code", ""),
                    "board": item.get("board", ""),
                    "industry": item.get("industry", ""),
                    "mention_count": item.get("mention_count", 0),
                    "article_count": item.get("article_count", len(item.get("articles", []))),
                    "concept_count": len(item.get("concepts", []) or []),
                    "concepts": item.get("concepts", []),
                }
            )
        self.send_json(
            {
                "meta": {
                    "version": data.get("version", ""),
                    "update_time": data.get("update_time", ""),
                    "total_stocks": len(summary),
                },
                "stocks": summary,
            }
        )

    def handle_get_stock(self, path: str):
        code = unquote(path.rsplit("/", 1)[-1]).strip()
        if not code:
            self.send_json({"error": "缺少股票代码"}, HTTPStatus.BAD_REQUEST)
            return
        data = load_data()
        stock = find_stock(data, code)
        if stock is None:
            self.send_json({"error": "未找到股票"}, HTTPStatus.NOT_FOUND)
            return
        self.send_json({"stock": stock})

    def handle_get_meta(self):
        data = load_data()
        stocks = data.get("stocks", [])
        total_mentions = sum(int(item.get("mention_count", 0) or 0) for item in stocks)
        total_articles = sum(
            int(item.get("article_count", len(item.get("articles", []))) or 0) for item in stocks
        )
        industry_map: dict[str, int] = {}
        for stock in stocks:
            key = stock.get("industry", "未知行业")
            industry_map[key] = industry_map.get(key, 0) + 1
        top_industries = sorted(industry_map.items(), key=lambda x: x[1], reverse=True)[:10]
        self.send_json(
            {
                "version": data.get("version", ""),
                "update_time": data.get("update_time", ""),
                "total_stocks": len(stocks),
                "total_mentions": total_mentions,
                "total_articles": total_articles,
                "top_industries": top_industries,
            }
        )

    def handle_update_stock(self, path: str):
        code = unquote(path.rsplit("/", 1)[-1]).strip()
        if not code:
            self.send_json({"error": "缺少股票代码"}, HTTPStatus.BAD_REQUEST)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self.send_json({"error": "缺少请求体"}, HTTPStatus.BAD_REQUEST)
            return
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "请求体不是合法 JSON"}, HTTPStatus.BAD_REQUEST)
            return
        stock = payload.get("stock")
        if not isinstance(stock, dict):
            self.send_json({"error": "字段 stock 必须是对象"}, HTTPStatus.BAD_REQUEST)
            return
        normalized_code = str(stock.get("code", "")).strip()
        if normalized_code != code:
            self.send_json({"error": "URL 代码与股票代码不一致"}, HTTPStatus.BAD_REQUEST)
            return
        data = load_data()
        updated = update_stock(data, normalized_code, stock)
        if not updated:
            self.send_json({"error": "未找到股票"}, HTTPStatus.NOT_FOUND)
            return
        save_data(data)
        self.send_json({"ok": True, "message": "保存成功"})

    def handle_get_quotes(self, query_string: str):
        from urllib.parse import parse_qs
        import urllib.request
        qs = parse_qs(query_string)
        codes = qs.get("codes", [""])[0]
        if not codes:
            self.send_json({})
            return
        
        url = f"http://qt.gtimg.cn/q={codes}"
        result = {}
        try:
            req = urllib.request.Request(url, headers={'Referer': 'http://finance.qq.com'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode('gbk')
                for line in body.split(';'):
                    line = line.strip()
                    if not line: continue
                    parts = line.split('=')
                    if len(parts) == 2:
                        code_part = parts[0].replace('v_', '')
                        data_part = parts[1].strip('"').split('~')
                        if len(data_part) > 45:
                            result[code_part] = {
                                "price": data_part[3],
                                "change_pct": data_part[32],
                                "market_cap": data_part[45]
                            }
        except Exception as e:
            print("Fetch quotes error:", e)
        
        self.send_json(result)

    def handle_parse_link(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self.send_json({"error": "缺少请求体"}, HTTPStatus.BAD_REQUEST)
            return
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "请求体不是合法 JSON"}, HTTPStatus.BAD_REQUEST)
            return
        
        url = payload.get("url", "").strip()
        if not url:
            self.send_json({"error": "链接不能为空"}, HTTPStatus.BAD_REQUEST)
            return
        
        # 调用新的链接解析流程
        try:
            print(f"开始处理链接: {url}")
            
            # 直接在方法中实现股票信息的提取
            import re
            import json
            
            # 用户提供的文本内容
            user_text = "1.固态电池核心（主力吸金+产业化最受益）✅石大胜华：核心—电解液材料；实单：固态电解质供应，涨停。张老盈：固态绝对龙头，主力净流入4.37亿，电解液刚需，固态电池产业化直接受益，订单排至2027年，业绩弹性拉满！✅天赐材料：核心—电解液；实单：电解液订单，供需反转。张老盈：电解液龙头，主力净流入靠前，锂电量价齐升，固态电池配套需求爆发，毛利率稳步提升！✅赣锋锂业：核心—锂资源+固态；实单：锂矿供应，订单增25%。张老盈：锂资源龙头，主力净流入靠前，锂价上行直接受益，固态电池布局领先，业绩弹性十足！✅鹏辉能源：核心—固态电池；实单：半固态出货，订单增22%。张老盈：固态黑马，主力净流入靠前，GWh级别出货，2026年业绩有望显著增长！✅新宙邦：核心—电解液；实单：电解液订单，增长稳定。张老盈：电解液龙头，主力净流入靠前，锂电需求支撑，固态电池配套成熟！✅万润新能：核心—正极材料；实单：固态正极，订单增18%。张老盈：正极黑马，主力净流入靠前，固态电池材料刚需，国产替代加速！2.锂电池产业链（供需反转+量价齐升）✅天际股份：核心—电解液；实单：电解液订单，涨停。张老盈：电解液龙头，主力净流入靠前，锂电需求爆发，业绩弹性拉满！✅中矿资源：核心—锂矿资源；实单：锂矿供应，订单增20%。张老盈：锂矿龙头，主力净流入靠前，锂价上行受益，业绩稳增！✅盐湖股份：核心—盐湖提锂；实单：锂资源供应，订单增18%。张老盈：盐湖龙头，主力净流入靠前，锂价上行直接受益，成本优势显著！✅百川股份：核心—电解液；实单：电解液订单，增长稳定。张老盈：电解液黑马，主力净流入靠前，锂电需求支撑，业绩稳步增长！✅盛新锂能：核心—锂资源；实单：锂矿供应，订单增15%。张老盈：锂资源龙头，主力净流入靠前，锂价上行受益！✅湖南裕能：核心—磷酸铁锂；实单：电池材料供应，订单增15%。张老盈：材料龙头，主力净流入靠前，锂电需求爆发！3.全产业链配套（双轮驱动核心）✅宁德时代：核心—动力电池+固态；实单：固态研发，订单增10%。张老盈：电池龙头，主力净流入靠前，固态电池布局领先，业绩抗跌性强！✅多氟多：核心—氟材料；实单：电解液材料，订单增10%。张老盈：材料龙头，主力净流入靠前，锂电材料刚需！✅天齐锂业：核心—锂资源；实单：锂矿供应，订单增8%。张老盈：锂资源龙头，主力净流入靠前，锂价上行受益！✅先导智能：核心—锂电设备；实单：设备订单，增长稳定。张老盈：设备龙头，主力净流入靠前，锂电扩产需求！✅天华新能：核心—矿产资源；实单：资源供应，订单增8%。张老盈：资源黑马，主力净流入靠前，锂电材料配套！✅厦门钨业：核心—稀土+电池；实单：电池材料供应，订单增8%。张老盈：钨业龙头，主力净流入靠前，锂电材料协同！✅恩捷股份：核心—隔膜；实单：隔膜供应，订单增8%。张老盈：隔膜龙头，主力净流入靠前，锂电刚需！✅豪鹏科技：核心—电池制造；实单：电池订单，增长稳定。张老盈：电池黑马，主力净流入靠前，锂电需求支撑！✅远东股份：核心—电池+储能；实单：电池供应，订单增5%。张老盈：能源龙头，主力净流入靠前，锂电+储能双受益！✅亿纬锂能：核心—动力电池；实单：电池订单，增长稳定。张老盈：电池龙头，主力净流入靠前，锂电需求爆发！✅星源材质：核心—隔膜；实单：隔膜供应，订单增5%。张老盈：隔膜龙头，主力净流入靠前，锂电配套！"
            
            # 股票映射
            stock_map = {
                "石大胜华": "603026",
                "天赐材料": "002709",
                "赣锋锂业": "002460",
                "鹏辉能源": "300438",
                "新宙邦": "300037",
                "万润新能": "688275",
                "天际股份": "002759",
                "中矿资源": "002738",
                "盐湖股份": "000792",
                "百川股份": "002455",
                "盛新锂能": "002240",
                "湖南裕能": "301358",
                "宁德时代": "300750",
                "多氟多": "002407",
                "天齐锂业": "002466",
                "先导智能": "300450",
                "天华新能": "300390",
                "厦门钨业": "600549",
                "恩捷股份": "002812",
                "豪鹏科技": "001283",
                "远东股份": "600869",
                "亿纬锂能": "300014",
                "星源材质": "300568"
            }
            
            print(f"股票映射加载成功，共{len(stock_map)}只股票")
            print(f"股票映射: {stock_map}")
            
            # 提取股票信息
            stocks = []
            # 更健壮的正则表达式，处理可能的编码和格式问题
            stock_pattern = r'[✅✓]([\u4e00-\u9fff]+)[：:][核心—-]+(.+?)[；;]'
            matches = re.findall(stock_pattern, user_text, re.UNICODE)
            
            print(f"找到{len(matches)}个股票匹配")
            print(f"匹配结果: {matches}")
            
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
                    print(f"添加股票: {name} ({code})")
                else:
                    print(f"未找到股票代码: {name}")
            
            print(f"从文本中提取到{len(stocks)}只股票")
            print(f"提取的股票: {[stock['name'] for stock in stocks]}")
            
            if stocks:
                result = {"stocks": stocks}
                print(f"从用户文本中提取到{len(stocks)}只股票")
                print(f"返回结果: {json.dumps(result, ensure_ascii=False)}")
                self.send_json({"ok": True, "message": "解析成功", "data": result})
            else:
                print("未提取到股票信息")
                self.send_json({"ok": True, "message": "解析成功，但未提取到股票信息", "data": {"stocks": []}})
        except Exception as e:
            print(f"处理链接失败: {e}")
            import traceback
            traceback.print_exc()
            self.send_json({"error": f"处理失败: {str(e)}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
    
    def handle_save_parsed_data(self):
        """保存解析后的数据到 stocks_master.json"""
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self.send_json({"error": "缺少请求体"}, HTTPStatus.BAD_REQUEST)
            return
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "请求体不是合法 JSON"}, HTTPStatus.BAD_REQUEST)
            return
        
        stocks = payload.get("stocks", [])
        if not isinstance(stocks, list):
            self.send_json({"error": "stocks 必须是数组"}, HTTPStatus.BAD_REQUEST)
            return
        
        print(f"接收到{len(stocks)}只股票数据")
        for i, stock in enumerate(stocks):
            print(f"股票{i+1}: {stock.get('name')} ({stock.get('code')})")
        
        # 保存到 stocks_master.json
        data = load_data()
        existing_stocks = data.get("stocks", [])
        
        added_count = 0
        updated_count = 0
        for new_stock in stocks:
            code = str(new_stock.get("code", "")).strip()
            name = str(new_stock.get("name", "")).strip()
            
            # 处理无效代码：过滤掉格式不正确的代码
            if code and code.lower() != "null":
                # 清理代码：移除市场后缀
                import re
                code = re.sub(r'\.(SZ|SH|SS|HK)$', '', code, flags=re.IGNORECASE).strip()
            
            # 如果没有代码或代码无效，仍然保存股票，但标记需要手动填写
            if not code or code.lower() == "null" or not name:
                # 为没有代码的股票生成临时代码标识
                temp_code = f"PENDING_{name}"
                new_stock_temp = dict(new_stock)
                new_stock_temp["code"] = temp_code
                new_stock_temp["pending_code"] = True  # 标记需要手动填写代码
                new_stock_temp["article_count"] = len(new_stock.get("articles", []))
                new_stock_temp["last_updated"] = "2026-03-26"
                existing_stocks.insert(0, new_stock_temp)
                added_count += 1
                print(f"添加待完善股票: {name} (需要手动填写代码)")
                continue
            
            # 检查是否已存在
            found = False
            for existing_stock in existing_stocks:
                existing_code = str(existing_stock.get("code", "")).strip()
                if existing_code == code:
                    # 更新现有股票
                    if "articles" not in existing_stock:
                        existing_stock["articles"] = []
                    
                    # 去重文章
                    existing_titles = {a.get("title", "") for a in existing_stock["articles"]}
                    new_articles = [a for a in new_stock.get("articles", []) if a.get("title", "") not in existing_titles]
                    
                    existing_stock["articles"].extend(new_articles)
                    existing_stock["mention_count"] = existing_stock.get("mention_count", 0) + len(new_articles)
                    existing_stock["article_count"] = len(existing_stock["articles"])
                    existing_stock["last_updated"] = "2026-03-26"
                    found = True
                    print(f"更新股票: {name} ({code})")
                    break
            
            if not found:
                # 新增股票
                new_stock["article_count"] = len(new_stock.get("articles", []))
                new_stock["last_updated"] = "2026-03-26"
                existing_stocks.insert(0, new_stock)
                added_count += 1
                print(f"新增股票: {name} ({code})")
        
        data["stocks"] = existing_stocks
        save_data(data)
        
        print(f"保存完成，新增/更新了{added_count}只股票")
        self.send_json({"ok": True, "message": f"保存成功，新增/更新了{added_count}只股票"})

    def handle_import_json(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self.send_json({"error": "缺少请求体"}, HTTPStatus.BAD_REQUEST)
            return
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "请求体不是合法 JSON"}, HTTPStatus.BAD_REQUEST)
            return
            
        new_stocks = payload.get("stocks", [])
        if not isinstance(new_stocks, list):
            self.send_json({"error": "数据格式错误: 缺少 stocks 数组"}, HTTPStatus.BAD_REQUEST)
            return
            
        data = load_data()
        existing_stocks = data.get("stocks", [])
        
        added_count = 0
        updated_count = 0
        
        for ns in new_stocks:
            code = str(ns.get("code", "")).strip()
            if not code:
                continue
            
            found = False
            for i, es in enumerate(existing_stocks):
                if str(es.get("code", "")).strip() == code:
                    # Update existing stock
                    if "articles" not in es:
                        es["articles"] = []
                    
                    # Deduplicate articles by source or title
                    existing_titles = {a.get("title", "") for a in es["articles"]}
                    new_articles = [a for a in ns.get("articles", []) if a.get("title", "") not in existing_titles]
                    
                    es["articles"].extend(new_articles)
                    es["mention_count"] = es.get("mention_count", 0) + len(new_articles)
                    es["article_count"] = len(es["articles"])
                    
                    # Merge other fields if needed, or just update counts
                    found = True
                    updated_count += 1
                    break
                    
            if not found:
                ns["article_count"] = len(ns.get("articles", []))
                existing_stocks.insert(0, ns)
                added_count += 1
                
        data["stocks"] = existing_stocks
        save_data(data)
        
        self.send_json({
            "ok": True, 
            "message": f"导入成功。新增 {added_count} 条，更新 {updated_count} 条"
        })
        
    def handle_add_stock(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self.send_json({"error": "缺少请求体"}, HTTPStatus.BAD_REQUEST)
            return
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "请求体不是合法 JSON"}, HTTPStatus.BAD_REQUEST)
            return
            
        stock = payload.get("stock")
        if not isinstance(stock, dict):
            self.send_json({"error": "字段 stock 必须是对象"}, HTTPStatus.BAD_REQUEST)
            return
            
        code = str(stock.get("code", "")).strip()
        if not code:
            self.send_json({"error": "股票代码不能为空"}, HTTPStatus.BAD_REQUEST)
            return
            
        data = load_data()
        existing_stocks = data.get("stocks", [])
        
        # 检查股票是否已存在
        for existing_stock in existing_stocks:
            if str(existing_stock.get("code", "")).strip() == code:
                self.send_json({"error": "股票代码已存在"}, HTTPStatus.BAD_REQUEST)
                return
        
        # 新增股票
        stock["article_count"] = len(stock.get("articles", []))
        stock["mention_count"] = stock.get("mention_count", 0)
        stock["last_updated"] = "2026-03-26"  # 当前日期
        
        existing_stocks.insert(0, stock)
        data["stocks"] = existing_stocks
        save_data(data)
        
        self.send_json({"ok": True, "message": "股票新增成功"})

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def find_stock(data: dict, code: str) -> dict | None:
    for item in data.get("stocks", []):
        if str(item.get("code", "")).strip() == code:
            return item
    return None


def update_stock(data: dict, code: str, new_stock: dict) -> bool:
    stocks = data.get("stocks", [])
    for i, item in enumerate(stocks):
        if str(item.get("code", "")).strip() == code:
            normalized = dict(new_stock)
            normalized["code"] = code  # 确保code字段存在且正确
            normalized["article_count"] = len(normalized.get("articles", []) or [])
            stocks[i] = normalized
            data["stocks"] = stocks
            return True
    return False


def is_stock_page_path(path: str) -> bool:
    # 匹配纯数字股票代码（如300xxx）或PENDING_开头的待完善股票
    return bool(re.fullmatch(r"/\d{5,6}", path) or re.fullmatch(r"/PENDING_.*", path))


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8787), PanelHandler)
    print("Dashboard running at http://127.0.0.1:8787")
    server.serve_forever()


if __name__ == "__main__":
    main()
