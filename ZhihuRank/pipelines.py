# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import pymongo
from ZhihuRank.items import ZhihuUserItem, ZhihuUserSnapshotItem
from datetime import datetime
from scrapy.exceptions import DropItem
from ZhihuRank.settings import REDIS_URL
import logging
import redis

logger = logging.getLogger(__name__)

class InserRedis(object):
    def __init__(self, mongo_uri, mongo_db):
        self.reds = redis.Redis.from_url(REDIS_URL, db=1, decode_responses=True)
        self.coon = pymongo.MongoClient(mongo_uri)
        self.db = self.coon[mongo_db]
        # 初始化已抓url_token队列
        if self.reds.hlen('url_token') == 0:
            collection = self.db['user']
            for i in collection.find({}, {'_id': 0, 'url_token': 1}):
                logger.info('wrire to redis: ' + i['url_token'])
                self.reds.hset('url_token', i['url_token'], 0)
            logger.info("初始化url_token完毕")
            self.coon.close()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'items'),
        )

    def process_item(self, item, spider):
        self.reds.hset('url_token', item['url_token'], 0)
        return item

class PushRedis(object):
    def __init__(self, mongo_uri, mongo_db):
        self.reds = redis.Redis.from_url(REDIS_URL, db=3, decode_responses=True)
        self.coon = pymongo.MongoClient(mongo_uri)
        self.db = self.coon[mongo_db]
        # 初始化已抓url_token队列
        if self.reds.llen('url_token') == 0:
            collection = self.db['user']
            for i in collection.find({}, {'_id': 0, 'url_token': 1}):
                self.reds.lupsh('url_token', i['url_token'])
            logger.info("初始化url_token完毕")
            self.coon.close()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'items'),
        )

    def process_item(self, item, spider):
        return item


class DropItemPipeline(object):
    """
    丢弃被关注人数过低的Item
    """
    def process_item(self, item, spider):
        follower_count = 0
        for i in item['follower_count'][0].keys():
            follower_count = item['follower_count'][0].get(i)
        if follower_count <= 15:
            raise DropItem("该号被关注人数过低: {0}".format(item['url_token']))
        return item


class MongoPipeline(object):
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'items'),
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if isinstance(item, ZhihuUserItem):
            collection_name = "user"
        try:
            self.db[collection_name].find({'url_token': item['url_token']}, {'$exists': True})[0]
            logger.info("已经存在,忽略写入{}".format(item['url_token']))
            return item
        except IndexError:
            self.db[collection_name].insert_one(dict(item))
            logger.info("正在写入:{}".format(item['url_token']))
            return item


class MongoSnapshotPipeline(object):
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'items'),
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if isinstance(item, ZhihuUserSnapshotItem):
            collection_name = "user"
        today_datetime = datetime.now().strftime('%Y-%m-%d')
        user_updatetime = self.db[collection_name].find_one({'url_token': item.get('url_token')}).get('crawl_update_time')
        if today_datetime != user_updatetime:
            self.db[collection_name].update({'url_token': item['url_token']},
                                            {'$push':
                                                {'pins_count': item['pins_count'],
                                                 'favorite_count': item['favorite_count'],
                                                 'favorited_count': item['favorited_count'],
                                                 'following_count': item['following_count'],
                                                 'follower_count': item['follower_count'],
                                                 'answer_count': item['answer_count'],
                                                 'question_count': item['question_count'],
                                                 'articles_count': item['articles_count'],
                                                 'thanked_count': item['thanked_count'],
                                                 'voteup_count': item['voteup_count'],
                                                 'following_topic_count': item['following_topic_count'],
                                                 'following_columns_count': item['following_columns_count'],
                                                 'columns_count': item['columns_count'],
                                                 'participated_live_count': item['participated_live_count'],
                                                 'hosted_live_count': item['hosted_live_count'],
                                                 'following_favlists_count': item['following_favlists_count'],
                                                 'following_question_count': item['following_question_count'],
                                                 },
                                             '$set':
                                             {'crawl_update_time': item['crawl_update_time'],
                                              'description': item['description'],
                                              'headline': item['headline'],
                                              'educations': item['educations'],
                                              'employments': item['employments'],
                                              'business': item['business']}})
        else:
            logger.info('{}已更新今日记录'.format(item['url_token']))
        return item
