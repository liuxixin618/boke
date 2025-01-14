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
    current_app.logger.debug("获取UTC时间")
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
        """设置密码"""
        current_app.logger.info(f"设置管理员 {self.username} 的密码")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        result = check_password_hash(self.password_hash, password)
        current_app.logger.info(f"验证管理员 {self.username} 的密码: {'成功' if result else '失败'}")
        return result

    def save(self, *args, **kwargs):
        """保存管理员信息"""
        current_app.logger.info(f"保存管理员信息: {self.username}")
        return super(Admin, self).save(*args, **kwargs)

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
        """保存文章"""
        if not self.created_at:
            self.created_at = get_utc_time()
            current_app.logger.info(f"创建新文章: {self.title}")
        else:
            current_app.logger.info(f"更新文章: {self.title}")
        
        self.updated_at = get_utc_time()
        return super(Post, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """删除文章"""
        current_app.logger.info(f"删除文章: {self.title}")
        return super(Post, self).delete(*args, **kwargs)

    @property
    def local_created_at(self):
        """获取本地时区的创建时间"""
        return convert_to_local_time(self.created_at)

    @property
    def local_updated_at(self):
        """获取本地时区的更新时间"""
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

    def save(self, *args, **kwargs):
        """保存附件信息"""
        current_app.logger.info(f"保存附件信息: {self.original_filename}")
        return super(Attachment, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """删除附件"""
        current_app.logger.info(f"删除附件: {self.original_filename}")
        return super(Attachment, self).delete(*args, **kwargs)

    @property
    def local_upload_time(self):
        """获取本地时区的上传时间"""
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
        except (ValueError, TypeError) as e:
            current_app.logger.error(f"配置值转换失败: key={self.key}, value={value}, type={value_type}, error={str(e)}")
            raise ValidationError(f'无法将值 "{value}" 转换为类型 {value_type}')
        
        return value

    def clean(self):
        """在保存前验证和转换值"""
        if self.value is not None:
            self.value = self._convert_value(self.value, self.type)

    def save(self, *args, **kwargs):
        """保存配置"""
        current_app.logger.info(f"保存配置: {self.key}={self.value}")
        return super(SiteConfig, self).save(*args, **kwargs)

    @classmethod
    def get_config(cls, key, default=None):
        """获取配置值"""
        config = cls.objects(key=key).first()
        if config:
            current_app.logger.debug(f"获取配置: {key}={config.value}")
            return config.value
        current_app.logger.debug(f"配置不存在，使用默认值: {key}={default}")
        return default 