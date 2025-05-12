# -*- coding: utf-8 -*-
"""
聊天室工具函数
"""
import re
from app.chat.models import ChatSensitiveWord
from flask import request

# 敏感词检测

def load_sensitive_words():
    words = [w.word for w in ChatSensitiveWord.objects]
    return set(words)

SENSITIVE_WORDS = None

def refresh_sensitive_words():
    global SENSITIVE_WORDS
    SENSITIVE_WORDS = load_sensitive_words()

refresh_sensitive_words()

def contains_sensitive_word(text):
    if SENSITIVE_WORDS is None:
        refresh_sensitive_words()
    for word in SENSITIVE_WORDS:
        if word in text:
            return True, word
    return False, None

# 设备识别

def get_device_info():
    ua = request.headers.get('User-Agent', '')
    if 'Windows' in ua:
        return 'Windows'
    elif 'Macintosh' in ua:
        return 'Mac'
    elif 'iPhone' in ua:
        return 'iPhone'
    elif 'Android' in ua:
        return 'Android'
    elif 'Linux' in ua:
        return 'Linux'
    else:
        return 'Other'

# 超链接识别

def linkify(text):
    url_pattern = re.compile(r'(https?://[\w\-./?%&=#:]+)')
    return url_pattern.sub(r'<a href="\1" target="_blank" style="color: #007bff;">\1</a>', text) 