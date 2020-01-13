from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent
import platform
from selenium.webdriver.support.wait import WebDriverWait
import json, time, random, requests, os, re
from hashlib import md5
from lxml import etree
from PIL import Image
from io import BytesIO
import execjs,xlrd, cv2, random
import numpy as np
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
import easing,random_ip
# import timeout_decorator

# 初始滑块验证码左边界
BORDER_1 = 5
BORDER_2 = 15
BORDER_3 = 28

class SearchResultParse(object):
    '''查询结果页解析
    '''
    def __init__(self, pagesource, base_url, parse_rule):
        self.selector = etree.HTML(pagesource)
        self.url_list = []
        self.base_url = base_url
        self.parse_rule = parse_rule['search_result_url']  # self.parse_rule = '//*[@id="advs"]/div/div[2]/a/@href'
    def search_result_parse(self):
        self.url_list = [self.base_url + i for i in self.selector.xpath(self.parse_rule)]
        return self.url_list

class PageDetailParse(object):
    '''详情页解析
    '''
    def __init__(self, pagesource, parse_rule):
        self.selector = etree.HTML(pagesource)
        self.parse_rule = parse_rule
        self.info_list = {}

    def search_result_parse(self, primary_info=None):
        if primary_info is None:
            primary_info = []
        for i in self.parse_rule['primaryinfo']: # 15个匹配规则
            primary_info.append(
                self.selector.xpath(i).replace("\n", "").replace("\t", "").replace("\r", "").replace(" ", "")) # 提取工商数据单条原始数据做处理 （'\r\t\t\t                         企业名称：\r\t\t\t                         华为投资控股有限公司\r\t\t\t                     '）
        self.info_list['primary_info'] = primary_info
        return self.info_list


# 超级鹰接口
class GtClickShot(object):
    def __init__(self, username, password, soft_id):
        '''初始化超级鹰
        softid已固化到程序
        args:
            username(str):超级鹰普通用户名
            password(str):超级鹰密码
        '''
        self.username = username
        self.password = md5(password.encode("utf-8")).hexdigest()
        self.soft_id = soft_id
        self.base_params = {
            'user': self.username,
            'pass2': self.password,
            'softid': self.soft_id,  # 软件ID，在用户中心->软件ID->自己生成
        }
        self.headers = {
            'Connection': 'Keep-Alive',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0)',
        }

    def PostPic(self, im, codetype):
        """发送图片至打码平台
        args：
            im(Byte): 图片字节
            codetype(str): 题目类型 参考 http://www.chaojiying.com/price.html
        return(json):返回打码信息，包含坐标信息，坐标信息用“|”隔开
        """
        params = {
            'codetype': codetype,
        }
        params.update(self.base_params)
        files = {'userfile': ('ccc.jpg', im)}
        r = requests.post('http://upload.chaojiying.net/Upload/Processing.php', data=params, files=files,
                          headers=self.headers)
        return r.json()

    def ReportError(self, im_id):
        """识别错误返回题分
        args：
            im_id(str):报错题目的图片ID
        return(str):报错反馈
        """
        params = {
            'id': im_id,
        }
        params.update(self.base_params)
        r = requests.post('http://upload.chaojiying.net/Upload/ReportError.php', data=params, headers=self.headers)
        return r.json()

class MaxEnterError(Exception):
    '''输入关键字最大尝试次数
    '''
    def __init__(self, ErrorInfo):
        super().__init__(self)  # 初始化父类
        self.errorinfo = ErrorInfo

    def __str__(self):
        return self.errorinfo

class CorpSearch(object):
    def __init__(self, init_url, index_url, headers, max_click):

        '''初始化
        args:
            init_url:初始化url,加速乐反爬JS要求访问目标网站前需先访问初始化url获取gt和challenge
            index_url:目标网站首页url
            headers：请求头信息
            max_click：最大循环点击次数为了应对点击不灵敏，设置循环检查点击。
            self.wait:默认条件等待最大时间
            self.click_valitimes:点击验证次数，大于0时需返回题分，等于0时不需要
        '''
        chrome_options = webdriver.ChromeOptions()
        prefs = {
            'profile.default_content_setting_values': {
                'images': 1,  # 加载图片
                "User-Agent": UserAgent().random,  # 更换UA
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("--start-maximized")

        self.init_url = init_url
        self.index_url = index_url
        if platform.system() == "Windows":
            chrome_options.add_argument("--headless")  # 隐藏浏览器
            chrome_options.add_argument('--no-sandbox')  # 解决DevToolsActivePort文件不存在的报错
            self.driver = webdriver.Chrome('chromedriver.exe', options=chrome_options)
        elif platform.system() == "Linux":
            chrome_options.add_argument("--headless") # 隐藏浏览器
            chrome_options.add_argument('--disable-gpu') # 谷歌文档提到需要加上这个属性来规避bug
            chrome_options.add_argument('--no-sandbox')  # 解决DevToolsActivePort文件不存在的报错
            self.driver = webdriver.Chrome(
                executable_path="/usr/bin/chromedriver",
                options=chrome_options)
        self.wait = WebDriverWait(self.driver, 50)
        self.mainWindow = ""
        self.max_entertimes = max_click
        self.click_valitimes = 0
        self.now_num = 3
        self.flesh_num = 1
        self.try_num = 3
        self.num = 1
        self.success = False
        self.action = ActionChains(self.driver)
        self.gt_shot = GtClickShot("*****", "*******", "*******")   # 超级鹰账号密码
        self.options = webdriver.ChromeOptions()
        self.headers = headers
        for option in self.headers:
            self.options.add_argument(option)

    # 初始化页面，绕过过加速乐反爬，获取gt和challenge,并加载进入首页
    # @timeout_decorator.timeout(30)
    def init(self):

        '''
        请求初始化网站，并进入首页
        '''
        self.driver.get(self.init_url)
        # self.mainWindow = self.driver.current_window_handle
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body > pre:nth-child(1)")),message="请求初始化网站出错")
        self.driver.get(self.index_url)

    # 加载首页，输入查询关键词，点击查询按钮
    # 如果点击按钮失效,自动重新回车，并设定最大回车次数，一旦超过设定值，抛出异常，结束程序
    # @timeout_decorator.timeout(40)
    def input_query(self, keyword):
        '''输入关键词进行查询
        args:
            keyword:查询关键词
        return:
            仅用于方法返回
        '''
        # 搜索偶尔出现回车后页面自动刷新，需重新填入数据
        num = 3
        while True:
            try:
                enter_word = self.wait.until(EC.presence_of_element_located((By.ID, "keyword")), message="搜索框未加载完毕") # 判断某个元素是否被加到了dom树里，定位搜索框元素（通过css解析器构建出样式表规则将这些规则分别放到对应的DOM树节点上，得到一颗带有样式属性的DOM树。）
                self.wait.until(EC.presence_of_element_located((By.ID, "btn_query")),message="搜索按钮未加载完毕") # 查询按钮加载完毕
                time.sleep(random.randint(4, 8) / 10)
                enter_word.send_keys(keyword)
                time.sleep(random.randint(4, 8) / 10)
                enter_word.send_keys(Keys.ENTER)
            #    continue
            # 判断按回车搜索后是否出现验证弹框
                if self.max_entertimes == 0:
                    raise MaxEnterError('---Out of max times on the search enter---')
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body > div.geetest_panel.geetest_wind")), message="验证码窗口未弹出")
                gt_panel = self.driver.find_element_by_css_selector("body > div.geetest_panel.geetest_wind") # css_selector定位
                style_value = gt_panel.value_of_css_property("display") # 获取css样式中属性值
            except Exception as e:
                if num - 1 > 0:
                    print("刷新")
                    self.driver.refresh()
                    num = num - 1
                    continue
                else:
                    raise TimeoutError(e)
            if style_value.strip() == "block":
                break
            elif num - 1 > 0:
                print("刷新")
                self.driver.refresh()
                num = num - 1
            else:
                raise EOFError("搜索异常")
        return

    # 判断页面中是否包含某个元素，注意是class_name
    def is_element_exist(self, class_name):

        '''判断某个元素是否存在
        args:
            class_name:元素class属性名称
        return:
            存在(True),不存在(False)
        '''

        try:
            self.driver.find_element_by_class_name(class_name)
            return True
        except:
            return False

    # 屏幕截图，并将截图内容读入内存，加速计算操作
    def get_screenshot(self):

        '''屏幕截图
        return:
            返回截图
        '''

        # screenshot = self.driver.get_screenshot_as_png()
        # screenshot = Image.open(BytesIO(screenshot))
        # return screenshot
        self.driver.save_screenshot('snap.png')
        page_snap_obj = Image.open('snap.png')
        return page_snap_obj

    # 获取验证验证码图片的位置，用于裁图
    def get_position(self, pos_img):

        '''验证图片的坐标尺寸信息
        args:
            pos_img:验证码定位点元素
        return:
            验证码定位点的坐标信息，注意依次为：左底，左高，右高，右底
        '''

        location = pos_img.location
        size = pos_img.size
        top, bottom, left, right = location['y'], location['y'] + size['height'], location['x'], location['x'] + size[
            'width']
        return (left, top, right, bottom)

    # 对于滑块验证码，获取完整的和缺块的验证码图片截图
    def get_slide_images(self):

        '''获取有缺口和没缺口的图片
        '''
        # if os.path.exists("befor_click.png"):
        #     os.remove("befor_click.png")
        # canvas_img = self.wait.until(
            # EC.presence_of_element_located((By.CSS_SELECTOR, ".geetest_canvas_img.geetest_absolute > div")))
            # EC.presence_of_element_located((By.CSS_SELECTOR, "body > div.geetest_panel.geetest_wind > div.geetest_panel_box.geetest_panelshowslide > div.geetest_panel_next > div > div.geetest_wrap > div.geetest_widget > div > a > div.geetest_canvas_img.geetest_absolute > div > canvas.geetest_canvas_slice.geetest_absolute")))
        canvas_img = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'geetest_canvas_img')))
        time.sleep(0.3)
        position = self.get_position(canvas_img)
        befor_screenshot = self.get_screenshot()
        befor_img = befor_screenshot.crop(position)
        befor_img.save("befor_click.png")
        return befor_img

    # 对于点击验证码，获取验证码的校验文字和待点击图片截图,以及验证码弹框元素
    def get_click_images(self):

        '''获取需点击的图片
        return:
            需点击坐标的图片，
            提示图片(用于调试打码时的计算点击次数)，
            验证码图片定位元素(用于定位鼠标位置并计算相对坐标)
        '''

        click_img_element = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "geetest_widget")))
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "geetest_item_img")))
        time.sleep(random.randint(1, 5) / 10)
        click_position = self.get_position(click_img_element)
        all_screenshot = self.get_screenshot()
        click_img = all_screenshot.crop(click_position)
        click_img.save("click_img.png")

        tip_img = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "geetest_tip_img")))
        tip_position = self.get_position(tip_img)
        tip_img = all_screenshot.crop(tip_position)
        tip_img.save("tip_img.png")

        return (click_img, tip_img, click_img_element)

    # 计算要点击的字符数量，灰度化，反向二值化,转置，沿X坐标对Y求和，判断分割点数量，判断字符数量
    def cal_char_num(self, char_img_path):

        '''计算需点击的字符数量
        args:
            char_img_path:提示图片的存储路径
        return:
            点击次数
        '''

        flag = 0
        origin_img = cv2.imread(char_img_path)
        gray_img = cv2.cvtColor(origin_img, cv2.COLOR_BGR2GRAY)
        ret, thresh1 = cv2.threshold(gray_img, 127, 255, cv2.THRESH_BINARY_INV)
        transpos_img = np.array(thresh1).T
        result = list(map(lambda x: sum(x), transpos_img))
        for i in range(len(result) - 3):
            if result[i] == 0 and result[i + 1] == 0 and result[i + 2] > 0:
                flag += 1
        return flag

    # 返回验证码字符的坐标，每个点击点的坐标,并转化为整数坐标
    def char_absolute_coord(self, img, num, coord=None):

        '''调试用，点击验证码图片返回整数值坐标
        args:
            img:验证码图片
            num：点击次数
        kargs:
            coord:验证码字符坐标
        return:
            字符坐标
        '''
        if coord is None:
            coord = []
        img = Image.open(img)
        plt.imshow(img)
        points = plt.ginput(num)
        plt.close()
        for i in points:
            x_co, y_co = i
            coord.append((round(x_co), round(y_co)))
        return coord

    # 返回从起点开始依次到每个点击文字的相对位置，形式为[(xoffset,yoffset),(),(),...]
    def get_offset_coord(self, absolute_coord, click_track=None):

        '''获取相邻点击字符的相对坐标，用于鼠标移动点击
        args:
            absolute_coord：验证码字符的绝对坐标
        kargs:
            click_track:每个需点击字符间的相对坐标或位移
        return:
            相对坐标或位移
        '''

        if click_track is None:
            click_track = []
        for i, j in enumerate(absolute_coord):
            if i == 0:
                click_track.append(j)
            else:
                click_track.append((j[0] - absolute_coord[i - 1][0], j[1] - absolute_coord[i - 1][1]))
        return click_track

    # 验证点击验证码,获取验证码数量，人工点击，按照计算的坐标相对偏移位置，依次点击文字进行验证
    # 通过打码平台，将验证码图片发送后返回坐标信息，通过超级鹰打码平台
    def click_captcha_validate(self, pic_id=None):

        '''根据打码平台返回的坐标进行验证

        return:
            仅仅用于方法返回
        '''
        if self.click_valitimes > 0 and pic_id:
            # 返回错误验证码ID返回积分
            print("返回错误验证码ID:{}".format(pic_id))
            self.gt_shot.ReportError(pic_id)
        self.click_valitimes += 1
        self.action = ActionChains(self.driver)
        click_img, tip_img, click_img_element = self.get_click_images()
        bytes_array = BytesIO()
        click_img.save(bytes_array, format="PNG")
        coord_result = self.gt_shot.PostPic(bytes_array.getvalue(), "9005")
        print(coord_result)
        groups = coord_result.get("pic_str").split('|')
        if groups == "":
            raise RuntimeError("打码超时")
        pic_id_new = coord_result.get("pic_id")
        points = [[int(num) for num in group.split(',')] for group in groups]
        mouse_track = self.get_offset_coord(points)
        self.action.move_to_element_with_offset(click_img_element, 0, 0)
        for position in mouse_track:
            self.action.move_by_offset(position[0], position[1])
            self.action.click()
            self.action.pause(random.randint(3, 7) / 10)
        self.action.perform()
        time.sleep(random.randint(4, 6) / 10)
        # 点击验证码提交按钮
        click_submit_btn = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'geetest_commit_tip')))
        click_submit_btn.click()
        self.action.reset_actions()
        self.valide_process(pic_id=pic_id_new)
        return

    # 验证是否成功破解，设置重启机制
    # 超过最大验证次数需点击“点击此处重试”
    def valide_process(self, pic_id=None, validate_type = None, company_name=None):
        '''验证过程
        args:
            cap_type:验证码类型
            pic_id:点击类验证码图片id
        return:
            要么验证成功，要么退出浏览器
        '''

        try:
            WebDriverWait(self.driver, 5).until_not(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "body > div.geetest_panel")))  # EC方法判断某个元素是否可见. 可见代表元素非隐藏
            WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, "advs")))
            print("验证通过！")
            return
        except:
            try:
                if validate_type == "slide":
                    gt_panel_error = self.driver.find_element_by_css_selector(
                        "body > div.geetest_panel.geetest_wind > div.geetest_panel_box.geetest_panelshowslide > div.geetest_panel_next")
                else:
                    gt_panel_error = self.driver.find_element_by_css_selector(
                        "body > div.geetest_panel.geetest_wind > div.geetest_panel_box.geetest_panelshowclick")
                error_display = gt_panel_error.value_of_css_property("display")
                if error_display.strip() == "block" and validate_type == "slide":
                    if self.driver.find_element_by_css_selector("body > div.geetest_panel.geetest_wind > div.geetest_panel_box.geetest_panelshowslide > div.geetest_panel_next > div > div.geetest_wrap > div.geetest_slider.geetest_ready > div.geetest_slider_track > div"):
                        refresh = self.driver.find_element_by_css_selector("body > div.geetest_panel.geetest_wind > div.geetest_panel_box.geetest_panelshowslide > div.geetest_panel_next > div > div.geetest_panel > div > a.geetest_refresh_1")
                        # 控制滑块验证次数
                        if self.num > 3:
                            raise Exception("验证码异常。")
                        print("验证码第{}次尝试破解".format(self.num))
                        refresh.click()
                        self.num = self.num + 1
                        self.slide_captcha_validate(company_name)
                elif error_display.strip() == "block":
                    self.click_captcha_validate(pic_id=pic_id)
                else:
                    raise Exception("验证出错。")
            except Exception as e:
                print('发生异常，记录企业名称')
                return

    # 判断是执行点击还是滑块
    def slide_orclick_validate(self, pic_id=None,company_name=None):

        '''判断下一步是选择滑动验证还是点击验证还是退出浏览器
        args:
            pic_id:点击类验证码图片id
        return:
            要么滑动验证，要么点击验证，要么None
        '''
        WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "geetest_close")),message="验证框加载过慢")
        if self.is_element_exist("geetest_canvas_img"):
            print('执行滑块验证')
            return self.slide_captcha_validate(company_name)
        else:
            print('执行语义点击验证')
            # if self.click_valitimes > 0:
            #     # 返回错误验证码ID返回积分
            #     print("返回错误验证码ID:{}".format(pic_id))
            #     self.gt_shot.ReportError(pic_id)
            # self.click_valitimes += 1
            return self.click_captcha_validate()

    # 带cookie切换至首页继续检索
    # @timeout_decorator.timeout(30)
    def switch_hmpg(self):

        '''由结果页切换至首页
        return: 用于方法返回
        '''
        self.wait.until(EC.presence_of_element_located((By.ID, "advs")))
        hmpg_btn = self.driver.find_element_by_css_selector(
            "body > div.container > div.header_box > div > div > a:nth-child(1)")
        self.action.move_to_element(hmpg_btn).click().perform()
        self.action.reset_actions()
        self.wait.until(lambda x: x.find_element_by_id('btn_query').is_displayed())
        return

    # 通过index界面或者点击首页继续检索时的爬取步骤
    def main(self, keyword, start_pg=None):

        '''操作主程序
        args:
            keyword:查询关键词
        kargs:
            start_pg:是否需要初始化访问加速乐，默认要

        '''

        if start_pg == "homepage":
            self.switch_hmpg()
        else:
            self.init()
        # time.sleep(random.randint(7,10) / 10)
        # self.action = ActionChains(self.driver)
        self.input_query(keyword)
        self.slide_orclick_validate(company_name=keyword)
        self.num = 1

    # 保存cookie和检索结果，用于requests及详情解析
    def to_dict(self):

        '''保存cookie（用于requests请求及详情解析）和查询结果
        args:
            cookie_name:cookie文件名称
        '''

        htmlpage = self.driver.page_source
        # self.driver.close()
        return {
            'page': htmlpage
        }

    # 进入详情页
    def detail_page(self):
        selector = etree.HTML(self.driver.page_source)
        if selector.xpath('string(//*[@id="advs"]/div/div[1]/span)') not in ["0",""]:
            time.sleep(random.randint(5,10)/10)
            # self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="advs"]/div/div[2]/a[1]/h1')))
            element = self.driver.find_element_by_xpath('//*[@id="advs"]/div/div[2]/a[1]/h1')
            self.driver.execute_script("arguments[0].click();", element)
            time.sleep(0.7)
            return self.driver
        else:
            raise EOFError("未搜索到该公司")

    # 验证滑动验证码，获取滑动距离和滑动轨迹，分别在起始，中间，结束时随机停顿
    def slide_captcha_validate(self,company_name=None):

        '''滑动验证码验证
        return:
            仅仅用于方法返回
        '''
        before = self.get_slide_images()
        image = Image.open("befor_click.png")
        image = image.convert("RGB")
        left_list = []
        left_list = self.get_gap(image)
        x_max = image.size[0]
        left_list = sorted(left_list, key=lambda x: abs(x[1] - int(x_max / 6.45)))
        if not left_list:
            raise EOFError("未获取到滑块位移值")
        distance = left_list[0][0]
        self.slider_try(distance, BORDER_1)
        self.valide_process(validate_type="slide", company_name=company_name)
        return

    def get_gap(self, image):
        """
        获取缺口偏移量
        :param image: 带缺口图片
        :return:
        """
        # left_list保存所有符合条件的x轴坐标
        left_list = []
        # 我们需要获取的是凹槽的x轴坐标，就不需要遍历所有y轴，遍历几个等分点就行
        for i in [10 * i for i in range(1, int(image.size[1] / 11))]:
            # x轴从x为image.size[0]/5.16的像素点开始遍历，因为凹槽不会在x轴为50以内
            for j in range(int(image.size[0] / 5.16), image.size[0] - int(image.size[0] / 8.6)):
                if self.is_pixel_equal(image, j, i, left_list):
                    break
        return left_list

    def is_pixel_equal(self, image, x, y, left_list):
        """
        判断两个像素是否相同
        :param image: 图片
        :param x: 位置x
        :param y: 位置y
        :return: 像素是否相同
        """
        # 取两个图片的像素点
        pixel1 = image.load()[x, y]
        threshold = 150
        # count记录一次向右有多少个像素点R、G、B都是小于150的
        count = 0
        # 如果该点的R、G、B都小于150，就开始向右遍历，记录向右有多少个像素点R、G、B都是小于150的
        if pixel1[0] < threshold and pixel1[1] < threshold and pixel1[2] < threshold:
            for i in range(x + 1, image.size[0]):
                piexl = image.load()[i, y]
                if piexl[0] < threshold and piexl[1] < threshold and piexl[2] < threshold:
                    count += 1
                else:
                    break
        if int(image.size[0] / 8.6) < count < int(image.size[0] / 4.3):
            left_list.append((x, count))
            return True
        else:
            return False

    def slider_try(self, gap, BORDER):
        if self.now_num:
            # 减去缺口位置
            gap = gap - BORDER
            # 计算滑动距离
            track = self.get_track(int(gap))
            # offsets, track = easing.get_tracks(gap, 5, 'ease_out_quart')
            track.extend([2,1,-2,-1])
            print(track)
            # 拖动滑块
            slider = self.get_slider()
            self.move_to_gap(slider, track, gap)

    def move_to_gap(self, slider, track, gap=None):
        """
        拖动滑块到缺口处
        :param slider: 滑块
        :param track: 轨迹
        :return:
        """
        self.action = ActionChains(self.driver)
        self.action.click_and_hold(slider).perform()
        for x in track:
            self.action.move_by_offset(xoffset=x, yoffset=0).perform()
            #
            self.action = ActionChains(self.driver)
        self.action.pause(random.randint(6, 10) / 10).release().perform()

    def get_slider(self):
        """
        获取滑块
        :return: 滑块对象
        """
        try:
            slider = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'geetest_slider_button')))
        except Exception:
            # self.crack()
            return
        return slider

    # 模拟鼠标轨迹，按照开始慢加速（2），中间快加速（5），后面慢加速（2），最后慢减速的方式（1）
    # 返回值是x值与Y值坐标以及sleep时间截点，起始中间最后都要sleep
    def get_track(self, distance, track_list=None):
        '''获取滑动轨迹
        args:
            distance:滑动距离
        kargs:
            Track_list:滑动轨迹，初始化为空
        return:
            滑动轨迹
        '''
        track = []
        current = 0
        mid = distance * 4 / 5
        t = random.randint(2, 3) / 10
        v = 0
        while current < distance:
            if current < mid:
                a = 10
            else:
                a = -5
            v0 = v
            v = v0 + a * t
            move = v0 * t + 1 / 2 * a * t * t
            current += move
            track.append(round(move))
        return track
