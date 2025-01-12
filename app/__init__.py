from flask import Flask
from flask_login import LoginManager
from flask_moment import Moment
from config import config
from .models import Admin, db, SiteConfig
from .context_processors import site_config

login_manager = LoginManager()
login_manager.login_view = 'admin.login'
moment = Moment()

def init_site_config():
    """初始化网站配置"""
    configs = [
        {
            'key': 'site_title',
            'value': '我的个人网站',
            'description': '网站标题',
            'type': 'str'
        },
        {
            'key': 'nav_home_text',
            'value': '首页',
            'description': '导航栏-首页文本',
            'type': 'str'
        },
        {
            'key': 'nav_home_visible',
            'value': True,
            'description': '导航栏-首页是否显示',
            'type': 'bool'
        },
        {
            'key': 'nav_goods_text',
            'value': '好物分享',
            'description': '导航栏-好物分享文本',
            'type': 'str'
        },
        {
            'key': 'nav_goods_visible',
            'value': True,
            'description': '导航栏-好物分享是否显示',
            'type': 'bool'
        },
        {
            'key': 'nav_about_text',
            'value': '关于作者',
            'description': '导航栏-关于作者文本',
            'type': 'str'
        },
        {
            'key': 'nav_about_visible',
            'value': True,
            'description': '导航栏-关于作者是否显示',
            'type': 'bool'
        },
        # 添加缺失的配置项
        {
            'key': 'content_preview_length',
            'value': 200,
            'description': '博客内容预览长度（字符数）',
            'type': 'int'
        },
        {
            'key': 'posts_per_page',
            'value': 10,
            'description': '每页显示的博客数量',
            'type': 'int'
        },
        {
            'key': 'icp_text',
            'value': '',
            'description': '页脚备案信息文本',
            'type': 'str'
        },
        {
            'key': 'icp_link',
            'value': '',
            'description': '备案信息链接地址',
            'type': 'url'
        }
    ]

    # 仅在配置项不存在时创建
    for config in configs:
        if not SiteConfig.objects(key=config['key']).first():
            SiteConfig(**config).save()

@login_manager.user_loader
def load_user(user_id):
    return Admin.objects(id=user_id).first()

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)

    # 注册上下文处理器
    app.context_processor(site_config)

    # 注册蓝图
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    # 初始化网站配置
    with app.app_context():
        init_site_config()

    return app 