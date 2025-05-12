# -*- coding: utf-8 -*-
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    # MongoDB 配置
    MONGODB_SETTINGS = {
        'db': os.environ.get('MONGODB_DB', 'personal_website'),
        'host': os.environ.get('MONGODB_HOST', '127.0.0.1'),
        'port': int(os.environ.get('MONGODB_PORT', 27017)),
        'username': os.environ.get('MONGODB_USERNAME'),
        'password': os.environ.get('MONGODB_PASSWORD')
    }
    # 添加编码配置
    JSON_AS_ASCII = False  # 确保 JSON 响应可以包含非 ASCII 字符
    BABEL_DEFAULT_LOCALE = 'zh_CN'  # 设置默认语言为中文
    TIMEZONE = 'Asia/Shanghai'  # 设置时区为中国时区

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 