from scrapy_redis.spiders import RedisSpider
import scrapy
import json
from datetime import datetime
from ZhihuRank.items import ZhihuUserSnapshotItem, ZhihuUserItemLoader
from ZhihuRank import settings
import redis


class MySpider(RedisSpider):
    """Spider that reads urls from redis queue (myspider:start_urls)."""
    name = 'snapshot'
    redis_key = 'snapshot:start_urls'
    allowed_domains = ['zhihu.com']
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'DOWNLOADER_MIDDLEWARES': {
            'ZhihuRank.middlewares.RandomUserAgentMiddleware': 560,
        },
        'ITEM_PIPELINES': {
            'ZhihuRank.pipelines.PushRedis': 300,
            'ZhihuRank.pipelines.MongoSnapshotPipeline': 310,
        }
    }

    def __init__(self):
        self.reds = redis.from_url(settings.REDIS_URL, db=3, decode_responses=True)
        super(MySpider, self).__init__()

    user_url = 'https://www.zhihu.com/api/v4/members/{url_token}?include={include}'
    user_query = 'locations,employments,gender,educations,business,voteup_count,thanked_Count,follower_count,' \
                 'following_count,cover_url,following_topic_count,following_question_count,following_favlists_count,' \
                 'following_columns_count,avatar_hue,answer_count,articles_count,pins_count,question_count,' \
                 'columns_count,commercial_question_count,favorite_count,favorited_count,' \
                 'logs_count,included_answers_count,included_articles_count,included_text,' \
                 'message_thread_token,account_status,is_active,is_bind_phone,is_force_renamed,' \
                 'is_bind_sina,is_privacy_protected,sina_weibo_url,sina_weibo_name,show_sina_weibo,' \
                 'is_blocking,is_blocked,is_following,is_followed,is_org_createpin_white_user,mutual_followees_count,' \
                 'vote_to_count,vote_from_count,thank_to_count,thank_from_count,thanked_count,description,' \
                 'hosted_live_count,participated_live_count,allow_message,industry_category,org_name,org_homepage,' \
                 'badge'

    following_url = 'https://www.zhihu.com/api/v4/members/{url_token}/followees?include={include}&offset=20&limit=20'
    following_query = 'data[*].answer_count,articles_count,gender,follower_count,is_followed,is_following,' \
                      'badge'

    followers_url = 'https://www.zhihu.com/api/v4/members/{url_token}/followees?include={include}&offset=0&limit=20'
    followers_query = 'data[*].answer_count,articles_count,gender,follower_count,is_followed,is_following,' \
                      'badge'

    def start_requests(self):
        url_token = self.reds.lpop('url_token')
        yield scrapy.Request(url='https://www.zhihu.com/people/{}/activities'.format(url_token),dont_filter=True,
                             callback=self.parse)

    def parse(self, response):
        url_token = response.url.split('/')[-2]
        yield scrapy.Request(url=self.user_url.format(url_token=url_token, include=self.user_query),
                             callback=self.parse_user, dont_filter=True)

    def parse_user(self, response):
        user_content = json.loads(response.text)
        user_item = ZhihuUserItemLoader(item=ZhihuUserSnapshotItem(), response=response)
        for field in user_item.item.fields:
            if field in user_content.keys():
                if 'count' in field:
                    user_item.add_value(field, {datetime.now().strftime('%Y-%m-%d'): user_content.get(field)})
                elif 'locations' == field or 'business' == field:
                    content = user_content.get(field)
                    if isinstance(content, list) and len(content) > 0:
                        content = content[0]
                        user_item.add_value(field, content.get('name', ''))
                    if isinstance(content, dict):
                        user_item.add_value(field, content.get('name', ''))
                else:
                    user_item.add_value(field, user_content.get(field))
        user_item.add_value('crawl_created_time', datetime.now().strftime('%Y-%m-%d'))
        user_item.add_value('crawl_update_time', datetime.now().strftime('%Y-%m-%d'))
        url_token = self.reds.lpop('url_token')
        yield scrapy.Request(url='https://www.zhihu.com/people/{}/activities'.format(url_token), dont_filter=True,
                             callback=self.parse)
        yield user_item.load_item()