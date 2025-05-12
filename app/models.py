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

db = MongoEngine()


def get_utc_time():
    """
    获取当前的UTC时间

    Returns:
        datetime: 当前的UTC时间对象
    """
    current_app.logger.debug("获取UTC时间")
    # 获取当前时间并设置为UTC时区
    now = datetime.now(pytz.UTC)
    current_app.logger.debug(f"当前UTC时间: {now}")
    return now


def convert_to_local_time(utc_dt):
    """
    将UTC时间转换为本地时间（中国时区）

    Args:
        utc_dt (datetime): UTC时间对象

    Returns:
        datetime: 本地时间对象
    """
    if utc_dt is None:
        return None

    # 如果输入时间没有时区信息，假定为UTC时间
    if utc_dt.tzinfo is None:
        utc_dt = pytz.UTC.localize(utc_dt)
        # current_app.logger.debug(f"添加UTC时区信息: {utc_dt}")

    # 转换为本地时间
    local_tz = pytz.timezone(current_app.config['TIMEZONE'])
    local_dt = utc_dt.astimezone(local_tz)
    # current_app.logger.debug(f"转换时间: UTC {utc_dt} -> 本地 {local_dt}")
    return local_dt


class Admin(db.Document, UserMixin):
    """管理员模型，包含用户名和密码哈希。"""

    username = db.StringField(required=True, unique=True)
    password_hash = db.StringField(required=True)

    meta = {'collection': 'user', 'indexes': ['username']}

    def set_password(self, password):
        """设置管理员密码。"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证管理员密码。"""
        return check_password_hash(self.password_hash, password)

    def save(self, *args, **kwargs):
        """保存管理员信息。"""
        return super(Admin, self).save(*args, **kwargs)


class Category(db.Document):
    """分类模型。"""

    name = db.StringField(required=True, unique=True)
    description = db.StringField()
    created_at = db.DateTimeField(default=get_utc_time)

    meta = {'collection': 'category', 'ordering': ['-created_at'], 'indexes': ['name']}

    def __str__(self):
        return self.name


class Post(db.Document):
    """文章模型，支持普通和Markdown文章。"""

    title = db.StringField(required=True)
    content = db.StringField(required=True)
    categories = db.ListField(db.ReferenceField('Category'))
    created_at = db.DateTimeField(default=get_utc_time)
    updated_at = db.DateTimeField(default=get_utc_time)
    is_visible = db.BooleanField(default=True)
    is_pinned = db.BooleanField(default=False)
    attachments = db.ListField(db.DictField())
    is_markdown = db.BooleanField(default=False)
    md_file_path = db.StringField()

    meta = {
        'collection': 'post',
        'ordering': ['-is_pinned', '-updated_at', '-created_at'],
        'indexes': ['title', 'categories', 'created_at', 'updated_at', 'is_visible', 'is_pinned'],
    }

    def save(self, *args, **kwargs):
        """保存文章，自动更新时间。"""
        if not self.created_at:
            self.created_at = get_utc_time()
        self.updated_at = get_utc_time()
        return super(Post, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """删除文章。"""
        return super(Post, self).delete(*args, **kwargs)

    @property
    def local_created_at(self):
        """获取本地时区的创建时间。"""
        return convert_to_local_time(self.created_at)

    @property
    def local_updated_at(self):
        """获取本地时区的更新时间。"""
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

    meta = {'collection': 'attachment', 'indexes': ['filename', 'post', 'upload_time']}

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

    key = db.StringField(required=True, unique=True)  # 配置项键名
    value = db.DynamicField(required=True)  # 配置项值
    description = db.StringField()  # 配置项描述
    type = db.StringField(required=True)  # 配置项类型

    meta = {'collection': 'site_config', 'indexes': ['key']}

    @classmethod
    def get_config(cls, key, default=None):
        """获取配置项值"""
        config = cls.objects(key=key).first()
        if not config:
            return default
        return config.get_typed_value()

    @classmethod
    def get_configs(cls):
        """获取所有配置项"""
        configs = {}
        for config in cls.objects:
            configs[config.key] = config.get_typed_value()
        return configs

    @classmethod
    def get_message_configs(cls):
        """获取留言相关配置"""
        keys = [
            'max_message_length',
            'max_messages_per_ip',
            'messages_per_page',
            'nav_message_text',
            'nav_message_visible',
        ]
        configs = {}
        for key in keys:
            config = cls.objects(key=key).first()
            if config:
                configs[key] = config.get_typed_value()
        return configs

    def get_typed_value(self):
        """获取类型转换后的值"""
        if not self.value:
            return None

        try:
            if self.type == 'int':
                return int(self.value)
            elif self.type == 'float':
                return float(self.value)
            elif self.type == 'bool':
                if isinstance(self.value, bool):
                    return self.value
                return str(self.value).lower() in ('true', '1', 'yes', 'on')
            elif self.type == 'str':
                return str(self.value)
            else:
                return self.value
        except (ValueError, TypeError):
            return None

    def set_value(self, value):
        """设置配置项值"""
        if self.type == 'int':
            self.value = int(value)
        elif self.type == 'float':
            self.value = float(value)
        elif self.type == 'bool':
            if isinstance(value, bool):
                self.value = value
            else:
                self.value = str(value).lower() in ('true', '1', 'yes', 'on')
        elif self.type == 'str':
            self.value = str(value)
        else:
            self.value = value


class Message(db.Document):
    """留言模型"""

    content = db.StringField(required=True)  # 留言内容
    contact = db.StringField()  # 联系方式
    allow_public = db.BooleanField(default=True)  # 是否允许公开
    is_public = db.BooleanField(default=False)  # 是否已公开
    created_at = db.DateTimeField(default=get_utc_time)  # 留言时间
    ip_address = db.StringField()  # IP地址
    attachment = db.DictField()  # 附件信息

    meta = {
        'collection': 'message',
        'ordering': ['-created_at'],
        'indexes': ['ip_address', 'created_at', 'is_public'],
    }

    @property
    def local_created_at(self):
        """获取本地时区的创建时间"""
        return convert_to_local_time(self.created_at)


class IPRecord(db.Document):
    """IP记录模型"""

    ip_address = db.StringField(required=True, unique=True)  # IP地址
    message_count = db.IntField(default=0)  # 留言数量
    is_blocked = db.BooleanField(default=False)  # 是否被禁止留言
    last_message_at = db.DateTimeField()  # 最后留言时间

    meta = {'collection': 'ip_record', 'indexes': ['ip_address', 'is_blocked']}


class Cache(db.Document):
    """缓存集合"""

    key = db.StringField(required=True, unique=True)  # 缓存键
    value = db.StringField(required=True)  # 缓存值（JSON字符串）
    created_at = db.DateTimeField(default=datetime.utcnow)  # 创建时间

    meta = {
        'collection': 'caches',
        'indexes': [
            'key',
            {'fields': ['created_at'], 'expireAfterSeconds': 3600},  # 1小时后自动过期
        ],
    }


class SiteShare(db.Document):
    """好站分享模型"""

    name = db.StringField(required=True)  # 网站名
    url = db.StringField(required=True)  # 跳转链接
    is_visible = db.BooleanField(default=True)  # 是否显示
    is_pinned = db.BooleanField(default=False)  # 是否置顶
    created_at = db.DateTimeField(default=get_utc_time)

    meta = {
        'collection': 'site_share',
        'ordering': ['-is_pinned', '-created_at'],
        'indexes': ['name', 'is_visible', 'is_pinned'],
    }
