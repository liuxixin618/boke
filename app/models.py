from datetime import datetime, timezone
from flask_mongoengine import MongoEngine
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = MongoEngine()

class User(UserMixin, db.Document):
    username = db.StringField(max_length=80, unique=True, required=True)
    password_hash = db.StringField(required=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Document):
    title = db.StringField(required=True)
    content = db.StringField(required=True)
    category = db.StringField(required=True)
    created_at = db.DateTimeField(default=datetime.now(timezone.utc))
    updated_at = db.DateTimeField(default=None)
    is_visible = db.BooleanField(default=True)
    is_pinned = db.BooleanField(default=False)
    
    meta = {
        'collection': 'post',
        'ordering': ['-is_pinned', '-updated_at', '-created_at']
    }

    def get_display_time(self):
        """获取显示时间，优先返回更新时间，如果没有则返回创建时间"""
        return self.updated_at if self.updated_at else self.created_at

class SiteConfig(db.Document):
    key = db.StringField(required=True, unique=True)
    value = db.DynamicField(required=True)
    description = db.StringField(required=True)
    type = db.StringField(required=True, choices=['int', 'str', 'url'])

    @classmethod
    def get_config(cls, key, default=None):
        config = cls.objects(key=key).first()
        return config.value if config else default

    meta = {
        'collection': 'site_config'
    } 