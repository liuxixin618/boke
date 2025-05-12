from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required
from app.chat.models import ChatSensitiveWord, ChatBlacklist, ChatUser, ChatMessage, ChatConfig
from mongoengine.queryset.visitor import Q

admin_chat = Blueprint('admin_chat', __name__)

# 敏感词管理
@admin_chat.route('/api/chat/sensitive', methods=['GET'])
@login_required
def get_sensitive_words():
    words = ChatSensitiveWord.objects.order_by('-created_at')
    return jsonify([{'id': str(w.id), 'word': w.word} for w in words])

@admin_chat.route('/api/chat/sensitive', methods=['POST'])
@login_required
def add_sensitive_word():
    word = request.json.get('word', '').strip()
    if not word:
        return jsonify({'error': '敏感词不能为空'}), 400
    if ChatSensitiveWord.objects(word=word).first():
        return jsonify({'error': '敏感词已存在'}), 400
    ChatSensitiveWord(word=word).save()
    return jsonify({'success': True})

@admin_chat.route('/api/chat/sensitive/<id>', methods=['DELETE'])
@login_required
def delete_sensitive_word(id):
    ChatSensitiveWord.objects(id=id).delete()
    return jsonify({'success': True})

# 黑名单管理
@admin_chat.route('/api/chat/blacklist', methods=['GET'])
@login_required
def get_blacklist():
    bl = ChatBlacklist.objects.order_by('-created_at')
    result = []
    for b in bl:
        user = b.user_id
        result.append({
            'id': str(b.id),
            'user_id': str(user.id) if user else '',
            'nickname': user.nickname if user else '',
            'ip': user.ip if user else '',
            'reason': b.reason,
            'created_at': b.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return jsonify(result)

@admin_chat.route('/api/chat/blacklist', methods=['POST'])
@login_required
def add_blacklist():
    user_id = request.json.get('user_id')
    reason = request.json.get('reason', '')
    user = ChatUser.objects(id=user_id).first()
    if not user:
        return jsonify({'error': '用户不存在'}), 400
    user.is_blacklisted = True
    user.save()
    ChatBlacklist(user_id=user, reason=reason).save()
    return jsonify({'success': True})

@admin_chat.route('/api/chat/blacklist/<id>', methods=['DELETE'])
@login_required
def remove_blacklist(id):
    bl = ChatBlacklist.objects(id=id).first()
    if bl and bl.user_id:
        bl.user_id.is_blacklisted = False
        bl.user_id.save()
    ChatBlacklist.objects(id=id).delete()
    return jsonify({'success': True})

# 聊天室状态管理
@admin_chat.route('/api/chat/config', methods=['GET'])
@login_required
def get_chat_config():
    config = ChatConfig.objects.first()
    if not config:
        return jsonify({})
    return jsonify({
        'status': config.status,
        'open_time': config.open_time,
        'close_time': config.close_time,
        'custom_text': config.custom_text,
        'expected_open_time': config.expected_open_time
    })

@admin_chat.route('/api/chat/config', methods=['POST'])
@login_required
def set_chat_config():
    data = request.json
    config = ChatConfig.objects.first()
    if not config:
        config = ChatConfig()
    config.status = int(data.get('status', 1))
    config.open_time = data.get('open_time', '')
    config.close_time = data.get('close_time', '')
    config.custom_text = data.get('custom_text', '')
    config.expected_open_time = data.get('expected_open_time', '')
    config.save()
    return jsonify({'success': True})

# 消息管理
@admin_chat.route('/api/chat/messages', methods=['GET'])
@login_required
def get_messages():
    msgs = ChatMessage.objects(is_deleted=False).order_by('-timestamp').limit(1000)
    result = []
    for m in msgs:
        result.append({
            'id': str(m.id),
            'nickname': m.nickname,
            'avatar': m.avatar,
            'content': m.content,
            'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'ip': m.ip,
            'device': m.device
        })
    return jsonify(result)

@admin_chat.route('/api/chat/messages/<id>', methods=['DELETE'])
@login_required
def delete_message(id):
    ChatMessage.objects(id=id).update(is_deleted=True)
    return jsonify({'success': True})

# 用户管理
@admin_chat.route('/api/chat/users', methods=['GET'])
@login_required
def get_users():
    users = ChatUser.objects.order_by('-last_active_time').limit(1000)
    result = []
    for u in users:
        last_msg = ChatMessage.objects(user_id=u).order_by('-timestamp').first()
        result.append({
            'id': str(u.id),
            'nickname': u.nickname,
            'ip': u.ip,
            'device': u.device,
            'avatar': u.avatar,
            'gender': u.gender,
            'is_online': u.is_online,
            'is_blacklisted': u.is_blacklisted,
            'last_active_time': u.last_active_time.strftime('%Y-%m-%d %H:%M:%S'),
            'last_msg': last_msg.content if last_msg else ''
        })
    return jsonify(result)

@admin_chat.route('/chat_admin')
@login_required
def chat_admin():
    return render_template('admin/chat_admin.html') 