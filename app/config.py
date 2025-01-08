import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    # MongoDB 配置
    MONGODB_SETTINGS = {
        'db': 'personal_website',
        'host': 'localhost',
        'port': 27017
    } 