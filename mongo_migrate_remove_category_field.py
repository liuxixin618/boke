import os
from mongoengine import connect
from pymongo import MongoClient

# 数据库配置
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/personal_website')
DB_NAME = 'personal_website'
COLLECTION_NAME = 'post'

# 用pymongo连接数据库
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
result = db[COLLECTION_NAME].update_many({}, {'$unset': {'category': ""}})
print(f"已移除 {result.modified_count} 篇文章的 category 字段。")
