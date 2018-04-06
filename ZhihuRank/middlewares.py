# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from fake_useragent import UserAgent
from ZhihuRank.utils.cookie_redis import init_cookie
import redis
import random
import json
import logging

logger = logging.getLogger(__name__)


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
            if spider.name + ':Cookies' in elem:
                cookie = json.loads(self.rcoon.get(elem))
                logger.info('使用帐号: {}进行抓取'.format(elem))
                request.cookies = cookie
                request.meta['accountText'] = elem.split(':Cookies')[-1]
                break

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


