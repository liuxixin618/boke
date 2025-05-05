# -*- coding: utf-8 -*-
"""
应用工厂模块
负责创建和配置Flask应用实例，注册扩展和蓝图，初始化网站配置
"""

from flask import Flask
from flask_mongoengine import MongoEngine
from flask_login import LoginManager
from flask_moment import Moment
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from config import config
from .models import Admin, db, SiteConfig
from .context_processors import site_config
import logging
from logging.handlers import RotatingFileHandler
import os

db = MongoEngine()
login_manager = LoginManager()
login_manager.login_view = 'admin.login'  # 设置登录视图的端点
login_manager.login_message = '请先登录'  # 设置登录提示消息
login_manager.login_message_category = 'warning'  # 设置消息分类

moment = Moment()

# 初始化限流器
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    return Admin.objects(id=user_id).first()

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # 加载基础配置
    app.config.from_object(config[config_name])
    
    # 设置最大上传文件大小为 64MB
    app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
    
    # 确保设置了时区
    if 'TIMEZONE' not in app.config:
        app.config['TIMEZONE'] = 'Asia/Shanghai'
    
    config[config_name].init_app(app)

    # 初始化 Flask-Moment 并设置默认时区
    moment.init_app(app)
    app.jinja_env.globals.update(moment_timezone=app.config['TIMEZONE'])
    
    db.init_app(app)
    login_manager.init_app(app)
    moment.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    # 注册上下文处理器
    app.context_processor(site_config)

    # 注册蓝图
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    def init_site_config():
        """初始化网站配置"""
        if SiteConfig.objects.count() == 0:
            # 定义配置项
            config_items = [
                {
                    'key': 'site_title',
                    'value': '个人网站',
                    'description': '网站标题',
                    'type': 'str'
                },
                {
                    'key': 'content_preview_length',
                    'value': '200',
                    'description': '博客内容预览长度',
                    'type': 'int'
                },
                {
                    'key': 'posts_per_page',
                    'value': '10',
                    'description': '每页显示的博客数量',
                    'type': 'int'
                },
                {
                    'key': 'nav_home_text',
                    'value': '首页',
                    'description': '首页导航文本',
                    'type': 'str'
                },
                {
                    'key': 'nav_home_visible',
                    'value': 'true',
                    'description': '是否显示首页导航',
                    'type': 'bool'
                },
                {
                    'key': 'nav_message_text',
                    'value': '留言板',
                    'description': '留言板导航文本',
                    'type': 'str'
                },
                {
                    'key': 'nav_message_visible',
                    'value': 'true',
                    'description': '是否显示留言板导航',
                    'type': 'bool'
                },
                {
                    'key': 'nav_about_text',
                    'value': '关于',
                    'description': '关于导航文本',
                    'type': 'str'
                },
                {
                    'key': 'nav_about_visible',
                    'value': 'true',
                    'description': '是否显示关于导航',
                    'type': 'bool'
                },
                {
                    'key': 'nav_goods_text',
                    'value': '好物推荐',
                    'description': '好物推荐导航文本',
                    'type': 'str'
                },
                {
                    'key': 'nav_goods_visible',
                    'value': 'true',
                    'description': '是否显示好物推荐导航',
                    'type': 'bool'
                },
                {
                    'key': 'max_message_length',
                    'value': '500',
                    'description': '留言内容最大长度',
                    'type': 'int'
                },
                {
                    'key': 'max_messages_per_ip',
                    'value': '3',
                    'description': '每个IP最多可提交留言数',
                    'type': 'int'
                },
                {
                    'key': 'messages_per_page',
                    'value': '20',
                    'description': '留言管理每页显示数量',
                    'type': 'int'
                },
                {
                    'key': 'icp_text',
                    'value': '',
                    'description': '备案信息文本',
                    'type': 'str'
                },
                {
                    'key': 'icp_link',
                    'value': '',
                    'description': '备案信息链接地址',
                    'type': 'str'
                }
            ]
            
            # 创建配置项
            for item in config_items:
                config = SiteConfig(
                    key=item['key'],
                    value=item['value'],
                    description=item['description'],
                    type=item['type']
                )
                config.save()
                print(f"Created config: {item['key']} = {item['value']}")

    # 将初始化函数存储在应用配置中
    app.config['init_site_config'] = init_site_config

    # 初始化网站配置
    with app.app_context():
        init_site_config()

    # 日志文件配置
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    file_handler = RotatingFileHandler(os.path.join(logs_dir, 'app.log'), maxBytes=10240, backupCount=10, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    return app 