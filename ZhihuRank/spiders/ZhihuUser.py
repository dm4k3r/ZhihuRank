from scrapy_redis.spiders import RedisSpider
import scrapy
import json
from datetime import datetime
from ZhihuRank.items import ZhihuUserItem, ZhihuUserItemLoader


class MySpider(RedisSpider):
    """Spider that reads urls from redis queue (myspider:start_urls)."""
    name = 'user'
    redis_key = 'user:start_urls'
    allowed_domains = 'zhihu.com'
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 16,
        'RETRY_ENABLED': False,
        'DOWNLOADER_MIDDLEWARES': {
            # 'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,
            # 'ZhihuRank.middlewares.HttpProxyMiddleware': 460,
            'ZhihuRank.middlewares.IngoreRequestMiddleware': 480,
            'ZhihuRank.middlewares.RandomUserAgentMiddleware': 500,
        },
        'ITEM_PIPELINES': {
            'ZhihuRank.pipelines.DropItemPipeline': 310,
            'ZhihuRank.pipelines.InserRedis': 300,
            'ZhihuRank.pipelines.MongoPipeline': 320,
        }
    }

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

    def parse(self, response):
        url_token = response.url.split('/')[-2]
        yield scrapy.Request(url=self.following_url.format(url_token=url_token, include=self.following_query),
                             callback=self.parse_following, dont_filter=True)
        yield scrapy.Request(url=self.followers_url.format(url_token=url_token, include=self.followers_query),
                             callback=self.parse_followers, dont_filter=True)

    def parse_following(self, response):
        following_content = json.loads(response.text)
        if 'data' in following_content.keys():
            for user in following_content.get('data'):
                url_token = user.get('url_token')
                yield scrapy.Request(url=self.user_url.format(url_token=url_token, include=self.user_query),
                                     callback=self.parse_user, dont_filter=True, meta={'url_token': url_token})
        if 'paging' in following_content.keys() and following_content.get('paging').get('is_end') == False:
            next_page = following_content.get('paging').get('next')
            yield scrapy.Request(url=next_page, callback=self.parse_following, dont_filter=True)


    def parse_followers(self, response):
        followers_content = json.loads(response.text)
        if 'data' in followers_content.keys():
            for user in followers_content.get('data'):
                url_token = user.get('url_token')
                yield scrapy.Request(url=self.user_url.format(url_token=url_token, include=self.user_query),
                                     callback=self.parse_user, dont_filter=True, meta={'url_token': url_token})
        if 'paging' in followers_content.keys() and followers_content.get('paging').get('is_end') == False:
            next_page = followers_content.get('paging').get('next')
            yield scrapy.Request(url=next_page, callback=self.parse_followers, dont_filter=True)

    def parse_user(self, response):
        url_token = response.meta.get('url_token')
        user_content = json.loads(response.text)
        user_item = ZhihuUserItemLoader(item=ZhihuUserItem(), response=response)
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
        yield scrapy.Request(url='https://www.zhihu.com/people/{}/activities'.format(url_token),
                             callback=self.parse,
                             dont_filter=True)

        yield user_item.load_item()







