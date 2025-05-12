# -*- coding: utf-8 -*-
"""
聊天室相关数据模型
"""
from flask_mongoengine import MongoEngine
from datetime import datetime
import pytz
from flask import current_app
from app.constants import AUTO_KICK_MINUTES

db = MongoEngine()

def get_utc_time():
    now = datetime.now(pytz.UTC)
    return now

class ChatUser(db.Document):
    nickname = db.StringField(required=True)
    ip = db.StringField(required=True)
    device = db.StringField()
    avatar = db.StringField(required=True)  # 头像文件名
    gender = db.StringField(default="未知")
    last_active_time = db.DateTimeField(default=get_utc_time)
    is_online = db.BooleanField(default=True)
    is_blacklisted = db.BooleanField(default=False)
    created_at = db.DateTimeField(default=get_utc_time)
    updated_at = db.DateTimeField(default=get_utc_time)

    meta = {
        'collection': 'chat_user',
        'indexes': ['ip', 'nickname', 'is_blacklisted']
    }

class ChatMessage(db.Document):
    user_id = db.ReferenceField(ChatUser)
    nickname = db.StringField(required=True)
    avatar = db.StringField(required=True)
    gender = db.StringField(default="未知")
    content = db.StringField(required=True)
    timestamp = db.DateTimeField(default=get_utc_time)
    is_deleted = db.BooleanField(default=False)
    is_sensitive = db.BooleanField(default=False)
    ip = db.StringField()
    device = db.StringField()

    meta = {
        'collection': 'chat_message',
        'indexes': ['timestamp', 'user_id', 'is_deleted']
    }

class ChatBlacklist(db.Document):
    user_id = db.ReferenceField(ChatUser)
    reason = db.StringField()
    created_at = db.DateTimeField(default=get_utc_time)

    meta = {
        'collection': 'chat_blacklist',
        'indexes': ['user_id']
    }

class ChatConfig(db.Document):
    # status: 0=关闭, 1=开启, 2=时间段
    status = db.IntField(default=1)
    open_time = db.StringField()  # 格式 08:00
    close_time = db.StringField() # 格式 20:00
    custom_text = db.StringField()  # 关闭时自定义文本
    expected_open_time = db.StringField()  # 预计开放时间
    updated_at = db.DateTimeField(default=get_utc_time)

    meta = {
        'collection': 'chat_config',
    }

class ChatSensitiveWord(db.Document):
    word = db.StringField(required=True, unique=True)
    created_at = db.DateTimeField(default=get_utc_time)

    meta = {
        'collection': 'chat_sensitive_word',
        'indexes': ['word']
    } 