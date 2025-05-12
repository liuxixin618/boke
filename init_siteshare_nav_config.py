# -*- coding: utf-8 -*-
"""
初始化好站分享导航栏配置项脚本
"""
from app import create_app
from app.models import SiteConfig
import os

# 如有需要可修改环境
os.environ['FLASK_ENV'] = 'development'

app = create_app()

with app.app_context():
    configs = [
        {
            'key': 'nav_siteshare_text',
            'value': '好站分享',
            'description': '好站分享导航文本',
            'type': 'str',
        },
        {
            'key': 'nav_siteshare_visible',
            'value': 'true',
            'description': '是否显示好站分享导航',
            'type': 'bool',
        },
    ]

    for item in configs:
        config = SiteConfig.objects(key=item['key']).first()
        if not config:
            config = SiteConfig(
                key=item['key'],
                value=item['value'],
                description=item['description'],
                type=item['type'],
            )
            config.save()
            print(f"已创建配置项: {item['key']} = {item['value']}")
        else:
            print(f"已存在配置项: {item['key']} = {config.value}")

    print("好站分享导航栏配置检查完毕。")
