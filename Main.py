import PageSourceGet, PageSourceParse, PageUrlGet
from fake_useragent import UserAgent
import time, random, xlrd, datetime, signal


init_url = "http://www.gsxt.gov.cn/SearchItemCaptcha"
index_url = "http://www.gsxt.gov.cn/index.html"
base_url = 'http://www.gsxt.gov.cn'
result_parse_rule = {'search_result_url': '//*[@id="advs"]/div/div[2]/a/@href'}
max_click = 10
chm_headers = ['Host="www.gsxt.gov.cn"',
               'Connection="keep-alive"',
               'User-Agent={}'.format(UserAgent().random),
               'Upgrade-Insecure-Requests=1',
               'Accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"',
               'Accept-Encoding="gzip, deflate"',
               'Accept-Language="zh-CN,zh;q=0.9"']
search = PageUrlGet.CorpSearch(init_url, index_url, chm_headers, max_click)
# book = xlrd.open_workbook(r"C:\Users\zengc\Desktop\diyipi.xls")
book = xlrd.open_workbook(r"C:\Users\zengc\Desktop\company_name.xlsx")
sheet = book.sheet_by_index(0)
num = 1
for i in range(sheet.nrows):
    company_name = sheet.cell(i ,0).value
    company_name = company_name.replace("(","（").replace(")","）")
    print(str(datetime.datetime.now()) + f",开始爬取 {company_name} 数据")
    try:
        search.main(company_name)
        driver = search.detail_page()
        source_get = PageSourceGet.SourceGet(driver)
        source_driver, windows_list = source_get.run()
        parse = PageSourceParse.PageDetailParse(source_driver, company_name)
        print("开始解析HTML页面数据并存库")
        parse.page_source_parse(windows_list)
    except Exception as e:
        with open(r"C:\Users\zengc\Desktop\error_company.txt", "a" , encoding='utf-8') as f:
            f.write(company_name)
            f.write("\n")
        print("{}搜索异常".format(company_name))
        print("异常原因：{}".format(e))
        continue
    print(str(datetime.datetime.now()) + f",{company_name}数据爬取完成")
    num = num + 1
    # if num > 3:
    #     print("已爬取{}家企业数据，爬虫结束！".format(num))
    #     break
    time.sleep(random.randint(8, 15) / 10)

print("共爬取{}家企业数据，爬虫结束！".format(num))
