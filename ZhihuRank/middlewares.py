# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from fake_useragent import UserAgent
from ZhihuRank.utils.cookie_redis import init_cookie
from twisted.internet.error import TimeoutError, ConnectError
from twisted.web._newclient import ResponseNeverReceived
from scrapy.exceptions import IgnoreRequest
from datetime import datetime, timedelta
import time
import requests
import redis
import random
import json
import logging

logger = logging.getLogger(__name__)

class IngoreRequestMiddleware(object):
    def __init__(self, settings, crawler):
        self.rcoon = redis.from_url(settings['REDIS_URL'], db=1, decode_responses=True)
        self.redis_key = 'url_token'

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings, crawler)

    def process_request(self, request, spider):
        url_token = request.meta.get('url_token')
        if self.rcoon.hexists(self.redis_key, url_token):
            logger.info('已经抓取: {}'.format(url_token))
            raise IgnoreRequest('IgnoreRequest: {}'.format(url_token))

class CookieMiddleware(RetryMiddleware):
    """
    获取redis中的cookie
    """
    def __init__(self, settings, crawler):
        RetryMiddleware.__init__(self, settings)
        self.rcoon = redis.from_url(settings['REDIS_URL'], db=1, decode_responses=True)
        init_cookie(crawler.spider.name)


    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings, crawler)

    def process_request(self, request, spider):
        redisKeys = self.rcoon.keys()
        while len(redisKeys) > 0:
            elem = random.choice(redisKeys)
            if 'user' + ':Cookies' in elem and self.rcoon.get(elem) != None:
                cookie = json.loads(self.rcoon.get(elem))
                logger.info('使用帐号: {}进行抓取'.format(elem))
                request.cookies = cookie
                request.meta['accountText'] = elem.split(':Cookies')[-1]
                break


class HttpProxyMiddleware(object):
    # 遇到这些类型的错误直接当做代理不可用处理掉, 不再传给retrymiddleware
    DONT_RETRY_ERRORS = (TimeoutError, ConnectError)

    def __init__(self, settings):
        # 从配置文件中中获取代理池服务器地址
        self.proxy_pool_url = settings.get('PROXY_REQUEST_API')
        # 最后一次切换代理的时间
        self.last_proxy_time = datetime.now()
        # 代理模式切换时间，默认每3分钟切换一次
        self.proxy_delay_tiem = 1
        # 切换代理状态
        self.proxy_status = False
        # 临时代理ip列表
        self.proxy_ip_list = []
        self.proxy_ip = ''

    @classmethod
    def from_crawler(cls, crawler):
        # 默认从setting.py获取配置，若有自定义配置，从自定义配置中获取
        settings = crawler.settings
        return cls(settings)

    # 从代理池中获取代理ip，格式为ip:port
    def get_proxy(self):
        while True:
            ip_port_json = json.loads(requests.get(self.proxy_pool_url, timeout=5).text)
            errorcode = ip_port_json['ERRORCODE']
            if errorcode == '0':
                result = ip_port_json['RESULT']
                for ip in result:
                    ip_port = ip['ip'] + ':' + ip['port']
                    logger.info('获取到: {}'.format(ip_port))
                    self.proxy_ip_list.append(ip_port)
                break
            else:
                logger.info('获取ip过快, 稍后重试')
                time.sleep(10)


    #  对当前请求设置代理，代理格式为http://ip:port
    def set_proxy(self, request):
        if len(self.proxy_ip_list) <= 1:
            self.get_proxy()
        self.proxy_ip = self.proxy_ip_list.pop()
        request.meta["proxy"] = "http://" + self.proxy_ip
        logger.info("切换代理: {}".format(self.proxy_ip))

    def process_request(self, request, spider):
        """
        处理请求的函数，切换代理模式，并根据模式设置是否使用代理,20分钟切换
        """
        if len(self.proxy_ip_list) <= 1:
            self.get_proxy()
            self.proxy_ip = self.proxy_ip_list.pop()

        if datetime.now() > (self.last_proxy_time + timedelta(minutes=self.proxy_delay_tiem)):
            if self.proxy_status:
                logger.info("<<<<<<<<<<切换代理>>>>>>>>>>")
                self.proxy_status = False
                self.last_proxy_time = datetime.now()
                request.meta["dont_redirect"] = True
                self.set_proxy(request)
            else:
                logger.info("<<<<<<<<<<切换代理>>>>>>>>>>")
                self.proxy_status = True
                self.last_proxy_time = datetime.now()
                request.meta["dont_redirect"] = True
                self.set_proxy(request)

        request.meta["proxy"] = "http://" + self.proxy_ip


    def process_response(self, request, response, spider):
        """
        检查response.status
        """
        if response.status == 200:
            if "proxy" in request.meta.keys():
                logger.info("使用代理[{}]成功爬取:{}".format(request.meta['proxy'], response.url))
            if response.url.startswith('https://www.zhihu.com/account/unhuman'):
                logger.info("触发反爬条件：ip抓取频次过高,更换ip")
                time.sleep(1)
                self.set_proxy(request)
                self.last_proxy_time = datetime.now()
                new_request = request.copy()
                new_request.dont_filter = True
                return new_request

        if response.status != 200 and response.status != 403 and response.status != 401:
            logger.info("response status[{}],url:{}".format(response.status, response.url))
            self.set_proxy(request)
            self.last_proxy_time = datetime.now()
            new_request = request.copy()
            new_request.dont_filter = True
            return new_request
        else:
            return response


    def process_exception(self, request, exception, spider):
        """
        处理由于使用代理导致的连接异常
        """
        if isinstance(exception, self.DONT_RETRY_ERRORS):
            logger.info("处理异常url，并更换代理重试")
            time.sleep(10)
            self.set_proxy(request)
            self.last_proxy_time = datetime.now()
            new_request = request.copy()
            new_request.dont_filter = True
            return new_request


class SetUserAgentMiddleware(object):
    """
    Select different headers according to different requests URL
    根据不同的url构造不同的headers参数
    """

    def __init__(self):
        super(SetUserAgentMiddleware, self).__init__()

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        request_url = request.url
        if request_url.startswith('https://www.zhihu.com/api/v4/members/'):
            cookiesText = request.cookies
            authoriztaion_code = cookiesText.get('z_c0').replace('"', '')
            udid = cookiesText.get('d_c0').split('|')[0].replace('"', '')
            request.headers['Authorization'] = 'Bearer ' + authoriztaion_code
            request.headers['x-udid'] = udid

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)

class RandomUserAgentMiddleware(object):
    """
    随机切换User_Agent,Type在settings中设置，默认为random
    """
    def __init__(self, settings):
        super(RandomUserAgentMiddleware, self).__init__()
        self.ua = UserAgent()
        self.ua_type = settings.get('USERAGENT_TYPE', 'random')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        def get_ua():
            return getattr(self.ua, self.ua_type)
        request.headers.setdefault(b'User-Agent', get_ua())


