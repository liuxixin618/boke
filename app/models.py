from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mongoengine import MongoEngine
from datetime import datetime, timezone, timedelta
from mongoengine.errors import ValidationError

db = MongoEngine()

def get_beijing_time():
    """获取北京时间"""
    utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
    beijing_tz = timezone(timedelta(hours=8))
    return utc_now.astimezone(beijing_tz)

def convert_to_beijing(dt):
    """将时间转换为北京时间"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    beijing_tz = timezone(timedelta(hours=8))
    return dt.astimezone(beijing_tz)

class Admin(db.Document, UserMixin):
    """管理员模型"""
    username = db.StringField(required=True, unique=True)
    password_hash = db.StringField(required=True)

    meta = {
        'collection': 'user',
        'indexes': ['username']
    }

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Document):
    """文章模型"""
    title = db.StringField(required=True)
    content = db.StringField(required=True)
    category = db.StringField()
    created_at = db.DateTimeField(default=get_beijing_time)
    updated_at = db.DateTimeField(default=get_beijing_time)
    is_visible = db.BooleanField(default=True)
    is_pinned = db.BooleanField(default=False)
    attachments = db.ListField(db.DictField())

    meta = {
        'collection': 'post',
        'ordering': ['-is_pinned', '-updated_at', '-created_at'],
        'indexes': [
            'title',
            'category',
            'created_at',
            'updated_at',
            'is_visible',
            'is_pinned'
        ]
    }

    @property
    def created_at_beijing(self):
        return convert_to_beijing(self.created_at)

    @property
    def updated_at_beijing(self):
        return convert_to_beijing(self.updated_at)

class SiteConfig(db.Document):
    """网站配置模型"""
    key = db.StringField(required=True, unique=True)
    value = db.DynamicField(required=True)
    description = db.StringField()
    type = db.StringField(choices=['str', 'int', 'bool', 'url'], default='str')

    meta = {
        'collection': 'site_config',
        'indexes': ['key']
    }

    def __init__(self, *args, **values):
        super().__init__(*args, **values)
        if 'value' in values and 'type' in values:
            self.value = self._convert_value(values['value'], values['type'])

    def _convert_value(self, value, value_type):
        """根据类型转换值"""
        if value is None:
            return None
        
        if isinstance(value, str):
            value = value.strip()
        
        try:
            if value_type == 'int':
                return int(value)
            elif value_type == 'bool':
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() == 'true' or value == 'on'
                return bool(value)
            elif value_type in ['str', 'url']:
                return str(value)
        except (ValueError, TypeError):
            raise ValidationError(f'无法将值 "{value}" 转换为类型 {value_type}')
        
        return value

    def clean(self):
        """在保存前验证和转换值"""
        if self.value is not None:
            self.value = self._convert_value(self.value, self.type)

    @classmethod
    def get_config(cls, key, default=None):
        """获取配置值"""
        config = cls.objects(key=key).first()
        if config:
            return config.value
        return default 