import os
from datetime import timedelta

class Config:
    SECRET_KEY = 'dev'
    MONGODB_SETTINGS = {
        'db': 'personal_website',
        'host': 'localhost',
        'port': 27017,
        'connect': False  # 避免连接超时
    }
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 限制上传文件大小为16MB
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # 设置session过期时间为7天

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # 生产环境可以设置更安全的配置
    # 比如从环境变量读取数据库连接信息等

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 