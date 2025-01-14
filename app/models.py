# -*- coding: utf-8 -*-
"""
数据模型模块
定义了应用中使用的所有数据模型，包括管理员、文章、网站配置等
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mongoengine import MongoEngine
from datetime import datetime
import pytz
from flask import current_app
from mongoengine.errors import ValidationError

db = MongoEngine()

def get_utc_time():
    """获取UTC时间"""
    return datetime.utcnow()

def convert_to_local_time(utc_dt):
    """将UTC时间转换为本地时间"""
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
    local_tz = pytz.timezone(current_app.config['TIMEZONE'])
    return utc_dt.astimezone(local_tz)

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
    created_at = db.DateTimeField(default=get_utc_time)
    updated_at = db.DateTimeField(default=get_utc_time)
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

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = get_utc_time()
        self.updated_at = get_utc_time()
        return super(Post, self).save(*args, **kwargs)

    @property
    def local_created_at(self):
        return convert_to_local_time(self.created_at)

    @property
    def local_updated_at(self):
        return convert_to_local_time(self.updated_at)

class Attachment(db.Document):
    """附件模型"""
    filename = db.StringField(required=True)
    original_filename = db.StringField(required=True)
    file_path = db.StringField(required=True)
    file_type = db.StringField()
    file_size = db.IntField()
    upload_time = db.DateTimeField(default=get_utc_time)
    post = db.ReferenceField('Post')

    meta = {
        'collection': 'attachment',
        'indexes': [
            'filename',
            'post',
            'upload_time'
        ]
    }

    @property
    def local_upload_time(self):
        return convert_to_local_time(self.upload_time)

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