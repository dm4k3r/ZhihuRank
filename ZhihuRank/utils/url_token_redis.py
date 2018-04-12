from ZhihuRank.settings import REDIS_URL, MONGO_URI, MONGO_DATABASE
import redis
import pymongo
import logging

logger = logging.getLogger(__name__)

reds = redis.Redis.from_url('redis://root@35.229.240.163:6379', db=1, decode_responses=True)
coon = pymongo.MongoClient(MONGO_URI)[MONGO_DATABASE]
collection = coon['user']
for i in collection.find({}, {'_id': 0, 'url_token': 1}):
    print(('wrire to redis: ' + i['url_token']))
    reds.hset('url_token', i['url_token'], 0)



