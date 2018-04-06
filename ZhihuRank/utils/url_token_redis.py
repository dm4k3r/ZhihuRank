from ZhihuRank.settings import REDIS_URL, MONGO_URI, MONGO_DATABASE
import redis
import pymongo
import logging

logger = logging.getLogger(__name__)

reds = redis.Redis.from_url(REDIS_URL, db=2, decode_responses=True)
coon = pymongo.MongoClient(MONGO_URI)[MONGO_DATABASE]

def init_url_token(collection='user'):
    # 初始化已抓url_token队列
    if reds.llen('url_token') == 0:
        collection = coon[collection]
        for i in collection.find({}, {'_id': 0, 'url_token': 1}):
            reds.lpush('url_token', i['url_token'])
        logger.info("初始化url_token完毕")


