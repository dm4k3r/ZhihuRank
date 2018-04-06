# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, MapCompose


def dont_do_anything(value):
    if isinstance(value, list):
        return value
    else:
        return [value]


class ZhihuUserItemLoader(ItemLoader):
    default_output_processor = TakeFirst()

class ZhihuUserItem(scrapy.Item):
    # 用户id
    id = scrapy.Field()
    # 昵称
    name = scrapy.Field()
    # 头像
    avatar_url = scrapy.Field()
    # url_token用户标识
    url_token = scrapy.Field()
    # 性别
    gender = scrapy.Field()
    # 用户类型
    user_type = scrapy.Field()
    # 想法数量
    pins_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 收藏数量
    favorite_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 被收藏数量
    favorited_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 关注数量
    following_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 被关注数量
    follower_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 回答数量
    answer_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 提问数量
    question_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 文章数量
    articles_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 被感谢数量
    thanked_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 点赞数量
    voteup_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 关注话题数量
    following_topic_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 关注专栏数量
    following_columns_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 专栏数量
    columns_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 赞助live数量
    participated_live_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 举办live数量
    hosted_live_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 关注收藏夹数量
    following_favlists_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 位置
    locations = scrapy.Field()
    # 关注问题数量
    following_question_count = scrapy.Field(output_processor=MapCompose(dont_do_anything))
    # 简介
    description = scrapy.Field()
    # 说说
    headline = scrapy.Field()
    # 教育背景
    educations = scrapy.Field()
    # 职业背景
    employments = scrapy.Field()
    # 商业背景
    business = scrapy.Field()
    # 爬虫生成时间
    crawl_created_time = scrapy.Field()
    # 爬虫更新时间
    crawl_update_time = scrapy.Field()

class ZhihuUserSnapshotItem(scrapy.Item):
    # 用户id
    id = scrapy.Field()
    # 昵称
    name = scrapy.Field()
    # 头像
    avatar_url = scrapy.Field()
    # url_token用户标识
    url_token = scrapy.Field()
    # 性别
    gender = scrapy.Field()
    # 用户类型
    user_type = scrapy.Field()
    # 想法数量
    pins_count = scrapy.Field()
    # 收藏数量
    favorite_count = scrapy.Field()
    # 被收藏数量
    favorited_count = scrapy.Field()
    # 关注数量
    following_count = scrapy.Field()
    # 被关注数量
    follower_count = scrapy.Field()
    # 回答数量
    answer_count = scrapy.Field()
    # 提问数量
    question_count = scrapy.Field()
    # 文章数量
    articles_count = scrapy.Field()
    # 被感谢数量
    thanked_count = scrapy.Field()
    # 点赞数量
    voteup_count = scrapy.Field()
    # 关注话题数量
    following_topic_count = scrapy.Field()
    # 关注专栏数量
    following_columns_count = scrapy.Field()
    # 专栏数量
    columns_count = scrapy.Field()
    # 赞助live数量
    participated_live_count = scrapy.Field()
    # 举办live数量
    hosted_live_count = scrapy.Field()
    # 关注收藏夹数量
    following_favlists_count = scrapy.Field()
    # 位置
    locations = scrapy.Field()
    # 关注问题数量
    following_question_count = scrapy.Field()
    # 简介
    description = scrapy.Field()
    # 说说
    headline = scrapy.Field()
    # 教育背景
    educations = scrapy.Field()
    # 职业背景
    employments = scrapy.Field()
    # 商业背景
    business = scrapy.Field()
    # 爬虫生成时间
    crawl_created_time = scrapy.Field()
    # 爬虫更新时间
    crawl_update_time = scrapy.Field()