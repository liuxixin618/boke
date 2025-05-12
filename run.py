import os
from app import create_app, db
from app.models import Admin, Post, SiteConfig
import logging
from logging.handlers import TimedRotatingFileHandler

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Admin=Admin, Post=Post, SiteConfig=SiteConfig)

if __name__ == '__main__':
    # 日志分级与轮转配置
    log_file = app.config.get('LOG_FILE', 'logs/app.log')
    file_handler = TimedRotatingFileHandler(
        log_file, when='midnight', backupCount=7, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    file_handler.setFormatter(formatter)
    if not app.logger.handlers:
        app.logger.addHandler(file_handler)
    else:
        for h in app.logger.handlers:
            app.logger.removeHandler(h)
        app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.run() 