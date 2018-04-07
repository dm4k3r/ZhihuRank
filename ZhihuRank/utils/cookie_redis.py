import requests
import redis
from requests_toolbelt.multipart.encoder import MultipartEncoder
import hmac
import re
import time
import random
import string
import json
import base64
from ZhihuRank.settings import REDIS_URL
from ZhihuRank.utils.dama import YDMHttp
import logging

logger = logging.getLogger(__name__)
yundama = YDMHttp()
reds = redis.Redis.from_url(REDIS_URL, db=1, decode_responses=True)


class login_generation(object):
    """
    生成知乎登录所需要的请求头参数
    """
    def __init__(self, username, password, captcha=None):
        self.username = username
        self.password = password
        self.timestamp = str(int(time.time()))
        self.captcha = captcha

    def boundary_generator(self, size=16, chars=string.ascii_letters + string.digits):
        return '----WebKitFormBoundary' + ''.join(random.choice(chars) for x in range(size))

    def hmac_generator(self):
        # Key值由JS生成,仅有timestamp为动态生成
        my_hmac = hmac.new('d1b964811afb40118a12068ff74a12f4'.encode('utf-8'), b'password', digestmod='sha1')
        my_hmac.update('c3cef7c66a1843f8b3a9e6a1e3160e20'.encode('utf-8'))
        my_hmac.update('com.zhihu.web'.encode('utf-8'))
        my_hmac.update(self.timestamp.encode('utf-8'))
        signature = my_hmac.hexdigest()
        return signature

    def headers_generator(self):
        boundary = self.boundary_generator()
        signature = self.hmac_generator()
        multipart_data = MultipartEncoder(
            fields={
                'client_id': 'c3cef7c66a1843f8b3a9e6a1e3160e20',
                'grant_type': 'password',
                'timestamp': self.timestamp,
                'source': 'com.zhihu.web',
                'signature': signature,
                'username': self.username,
                'password': self.password,
                'captcha': self.captcha,
                'lang': 'en',
                'ref_source': 'other_',
                'utm_source': ''
            },
            boundary=boundary
        )
        multipar_boundary = multipart_data.boundary[2:]
        multipart_data_body = multipart_data.to_string()
        return multipar_boundary, multipart_data_body


class ZhihuUserCookies(object):
    """
    模拟登录知乎并返回cookie
    """

    def __init__(self, username, password):
        self.seesion = requests.session()
        self.username = username
        self.password = password
        self.uid = None
        self.successful_login = False

    def start_request(self, retry=5):
        # 初始请求,获取udid
        count = 1
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
                               Chrome/62.0.3202.75 Safari/537.36',
            'authorization': 'oauth c3cef7c66a1843f8b3a9e6a1e3160e20'}
        while count <= retry:
            signin_page = self.seesion.get('https://www.zhihu.com/signin?lang=en', headers=headers).text
            filter_text = signin_page.replace('&quot;', '')
            try:
                uid = re.search('token:{xUDID:(.*=)}.*', filter_text).group(1)
            except AttributeError as e:
                print('没有获取到udid,重试中...{}次'.format(count))
                count = count+1
            else:
                self.uid = uid
                break

    def get_captcha(self):
        # 请求是否需要验证码
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
                           Chrome/62.0.3202.75 Safari/537.36',
            'authorization': 'oauth c3cef7c66a1843f8b3a9e6a1e3160e20',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Host': 'www.zhihu.com',
            'Referer': 'https://www.zhihu.com/signin?lang=en',
            'X-UDID': self.uid
        }
        captcha = self.seesion.get('https://www.zhihu.com/api/v3/oauth/captcha?lang=en', headers=headers).text
        is_captcha = json.loads(captcha)
        logger.debug("是否需要验证码: {}".format(is_captcha['show_captcha']))
        return is_captcha['show_captcha']

    def download_captcha(self):
        # 下载验证码,并通过打码平台返回识别结果
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
                           Chrome/62.0.3202.75 Safari/537.36',
            'authorization': 'oauth c3cef7c66a1843f8b3a9e6a1e3160e20',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Host': 'www.zhihu.com',
            'Referer': 'https://www.zhihu.com/signin?lang=en',
            'X-UDID': self.uid
        }
        captcha = self.seesion.put('https://www.zhihu.com/api/v3/oauth/captcha?lang=en', headers=headers).text
        captcha_content = json.loads(captcha)['img_base64']
        imgdata = base64.b64decode(captcha_content)
        with open('captcha.jpg', 'wb') as f:
            f.write(imgdata)
        captcha = yundama.decode('captcha.jpg', 1004, 60)[1]
        logger.debug('获取验证码:{}'.format(captcha))
        return captcha

    def login(self, captcha=None):
        # 登录知乎
        login_parmas = login_generation(username=self.username, password=self.password, captcha=captcha)
        multipar_boundary, multipart_data_body = login_parmas.headers_generator()
        login_headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,'
                          ' like Gecko) Chrome/62.0.3202.75 Safari/537.36',
            'authorization': 'oauth c3cef7c66a1843f8b3a9e6a1e3160e20',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Content-Type': 'multipart/form-data; charset=utf-8; boundary=' + multipar_boundary,
            'Host': 'www.zhihu.com',
            'Origin': 'https://www.zhihu.com',
            'Referer': 'https://www.zhihu.com/signin',
            'X-UDID': self.uid
        }
        data = {'input_text': captcha}
        captcha_headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
                           Chrome/62.0.3202.75 Safari/537.36',
            'authorization': 'oauth c3cef7c66a1843f8b3a9e6a1e3160e20',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Host': 'www.zhihu.com',
            'Referer': 'https://www.zhihu.com/signin?lang=en',
            'X-UDID': self.uid
        }

        submit_captcha = self.seesion.post('https://www.zhihu.com/api/v3/oauth/captcha?lang=en', data=data, headers=captcha_headers)
        time.sleep(1)
        submit_login = self.seesion.post('https://www.zhihu.com/api/v3/oauth/sign_in', headers=login_headers, data=multipart_data_body)


    def check_login(self):
        # 检测是否登录成功,成功即返回cookie
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
                               Chrome/62.0.3202.75 Safari/537.36',
            'authorization': 'oauth c3cef7c66a1843f8b3a9e6a1e3160e20'}
        wb_data = self.seesion.get('https://www.zhihu.com/question', headers=headers)
        if wb_data.status_code == 200:
            logger.debug('获取cookie成功！(帐号为{})'.format(self.username))
            cookies = self.seesion.cookies.get_dict()
            self.successful_login = True
            return json.dumps(cookies)

    def main(self):
        self.start_request()
        is_captcha = self.get_captcha()
        if is_captcha:
            captcha = self.download_captcha()
            self.login(captcha=captcha)
        else:
            self.login()
        return self.check_login()

def init_cookie(spidername):
    # 初始化cookie池
    redkeys = reds.keys()
    for user in redkeys:
        if 'user' not in user:
            password = reds.get(user)
            if reds.exists("{}:Cookies:{}--{}".format(spidername, user, password)) == False:
                cookie = ZhihuUserCookies(user, password).main()
                reds.set("{}:Cookies:{}--{}".format(spidername, user, password), cookie)

if __name__ == '__main__':
    init_cookie('user')
    # print(ZhihuUserCookies('+8618580256557', 'z153426').main())
