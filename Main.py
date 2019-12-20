import PageSourceGet, PageSourceParse, PageUrlGet
from fake_useragent import UserAgent
import time, random, xlrd, datetime


init_url = "http://www.gsxt.gov.cn/SearchItemCaptcha"
index_url = "http://www.gsxt.gov.cn/index.html"
base_url = 'http://www.gsxt.gov.cn'
max_click = 10
chm_headers = ['Host="www.gsxt.gov.cn"',
               'Connection="keep-alive"',
               'User-Agent={}'.format(UserAgent().random),
               'Upgrade-Insecure-Requests=1',
               'Accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"',
               'Accept-Encoding="gzip, deflate"',
               'Accept-Language="zh-CN,zh;q=0.9"']
search = PageUrlGet.CorpSearch(init_url, index_url, chm_headers, max_click)

book = xlrd.open_workbook(r"C:\Users\zengc\Desktop\company_list.xlsx")
sheet = book.sheet_by_index(0)
num = 1
for i in range(sheet.nrows):
    company_name = sheet.cell(i+3,0).value
    company_name = company_name.replace("(","（").replace(")","）")
    print(str(datetime.datetime.now()) + f",{company_name}开始爬取数据")
    search.main(company_name)
    cookie_html = search.to_dict()
    search_result = PageUrlGet.SearchResultParse(cookie_html['page'], base_url)
    target_url = search_result.search_result_parse()  # 获取搜索结果的url地址
    if not target_url:
        print("未搜索到该企业")
        exit(0)
    target_url = target_url[0]
    print("目标公司URL已拿到")
    PSG = PageSourceGet.SourceGet(target_url)
    page_source = PSG.run()
    parse = PageSourceParse.PageDetailParse(page_source, company_name)
    print("开始解析HTML页面数据并存库")
    parse.page_source_parse()
    print(str(datetime.datetime.now()) + f",{i}数据爬取完成")
    time.sleep(random.randint(150, 300)/10)
    num = num + 1
    if num > 20:
        print("爬虫结束")
        break
