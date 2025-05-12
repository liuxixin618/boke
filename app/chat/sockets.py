# -*- coding: utf-8 -*-
"""
聊天室 SocketIO 事件
"""
from flask import session, request
from flask_socketio import emit, join_room, leave_room, disconnect
from datetime import datetime, timedelta
from app.chat.models import ChatUser, ChatMessage, ChatConfig
from app.chat.utils import contains_sensitive_word, get_device_info, linkify
from app.constants import DEFAULT_RECEIVE_MSG_COUNT, SEND_MSG_INTERVAL_SECONDS, MAX_INPUT_LENGTH, AUTO_KICK_MINUTES
import random
import pytz

# 在线用户缓存（user_id: last_active_time）
online_users = {}

# 生成随机头像
import os
CHAT_AVATAR_DIR = os.path.join('app', 'static', 'chat')
def get_random_avatar():
    files = [f for f in os.listdir(CHAT_AVATAR_DIR) if f.endswith('.png')]
    if not files:
        return '0.png'
    return random.choice(files)

# 登录事件

def handle_login(data):
    nickname = data.get('nickname', '').strip()[:20]
    ip = request.remote_addr
    device = get_device_info()
    avatar = get_random_avatar()
    gender = data.get('gender', '未知')
    if not nickname:
        emit('login_error', {'msg': '昵称不能为空'})
        return
    user = ChatUser.objects(ip=ip, device=device, is_blacklisted=False).first()
    if not user:
        user = ChatUser(nickname=nickname, ip=ip, device=device, avatar=avatar, gender=gender)
        user.save()
    else:
        user.nickname = nickname
        user.avatar = avatar
        user.gender = gender
        user.is_online = True
        user.last_active_time = datetime.now(pytz.UTC)
        user.save()
    session['chat_user_id'] = str(user.id)
    online_users[str(user.id)] = datetime.now(pytz.UTC)
    # 获取最近消息
    msgs = ChatMessage.objects(is_deleted=False).order_by('-timestamp').limit(DEFAULT_RECEIVE_MSG_COUNT)
    msg_list = [serialize_message(m, user) for m in reversed(msgs)]
    emit('login_success', {
        'user': serialize_user(user),
        'messages': msg_list
    })
    emit_online_count()

# 登出事件

def handle_logout():
    user_id = session.get('chat_user_id')
    if user_id and user_id in online_users:
        del online_users[user_id]
    session.pop('chat_user_id', None)
    emit('logout_success')
    emit_online_count()

# 心跳包

def handle_heartbeat():
    user_id = session.get('chat_user_id')
    if user_id:
        online_users[user_id] = datetime.now(pytz.UTC)

# 发送消息

def handle_send_message(data):
    user_id = session.get('chat_user_id')
    if not user_id:
        emit('send_error', {'msg': '未登录'})
        return
    user = ChatUser.objects(id=user_id, is_blacklisted=False).first()
    if not user:
        emit('send_error', {'msg': '用户不存在或被拉黑'})
        return
    # 频率检测
    last_msg = ChatMessage.objects(user_id=user, is_deleted=False).order_by('-timestamp').first()
    now = datetime.now(pytz.UTC)
    if last_msg and (now - last_msg.timestamp).total_seconds() < SEND_MSG_INTERVAL_SECONDS:
        emit('send_error', {'msg': f'发送过快，请{SEND_MSG_INTERVAL_SECONDS}秒后再试'})
        return
    content = data.get('content', '').strip()
    if not content:
        emit('send_error', {'msg': '消息不能为空'})
        return
    if len(content) > MAX_INPUT_LENGTH:
        emit('send_error', {'msg': f'消息不能超过{MAX_INPUT_LENGTH}字'})
        return
    # 敏感词检测
    sensitive, word = contains_sensitive_word(content)
    is_sensitive = False
    if sensitive:
        is_sensitive = True
        emit('send_error', {'msg': f'消息包含敏感词：{word}'})
        return
    # 超链接识别
    content = linkify(content)
    msg = ChatMessage(
        user_id=user,
        nickname=user.nickname,
        avatar=user.avatar,
        gender=user.gender,
        content=content,
        timestamp=now,
        is_sensitive=is_sensitive,
        ip=user.ip,
        device=user.device
    )
    msg.save()
    # 广播消息
    emit('new_message', serialize_message(msg, user), broadcast=True)

# 获取在线人数

def emit_online_count():
    count = len(online_users)
    emit('online_count', {'count': count}, broadcast=True)

# 聊天室状态

def handle_get_status():
    config = ChatConfig.objects.first()
    status = 1
    open_time = ''
    close_time = ''
    custom_text = ''
    expected_open_time = ''
    if config:
        status = config.status
        open_time = config.open_time
        close_time = config.close_time
        custom_text = config.custom_text
        expected_open_time = config.expected_open_time
    emit('chat_status', {
        'status': status,
        'open_time': open_time,
        'close_time': close_time,
        'custom_text': custom_text,
        'expected_open_time': expected_open_time
    })

# 序列化

def serialize_user(user):
    return {
        'id': str(user.id),
        'nickname': user.nickname,
        'avatar': user.avatar,
        'gender': user.gender,
        'is_online': user.is_online
    }

def serialize_message(msg, current_user=None):
    return {
        'id': str(msg.id),
        'user_id': str(msg.user_id.id) if msg.user_id else '',
        'nickname': msg.nickname,
        'avatar': msg.avatar,
        'gender': msg.gender,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_self': current_user and msg.user_id and str(msg.user_id.id) == str(current_user.id)
    }

# 自动踢下线

def kick_inactive_users():
    now = datetime.now(pytz.UTC)
    to_kick = []
    for user_id, last_active in online_users.items():
        if (now - last_active).total_seconds() > AUTO_KICK_MINUTES * 60:
            to_kick.append(user_id)
    for user_id in to_kick:
        del online_users[user_id]
        user = ChatUser.objects(id=user_id).first()
        if user:
            user.is_online = False
            user.save()
    emit_online_count() 