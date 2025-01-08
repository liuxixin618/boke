from flask import Flask
from flask_login import LoginManager
from .config import Config
from .models import db, User, SiteConfig

login_manager = LoginManager()
login_manager.login_view = 'admin.login'

@login_manager.user_loader
def load_user(user_id):
    return User.objects(id=user_id).first()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # 注册蓝图
    from .main import main as main_blueprint
    from .admin import admin as admin_blueprint

    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    # 添加配置到模板上下文
    @app.context_processor
    def inject_config():
        def get_site_config(key, default=None):
            return SiteConfig.get_config(key, default)
        return {'site_config': get_site_config}

    return app 