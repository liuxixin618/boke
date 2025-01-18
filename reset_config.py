#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import create_app
from app.models import SiteConfig

def reset_config():
    """重置网站配置"""
    app = create_app()
    with app.app_context():
        # 删除所有现有配置
        print('正在删除所有配置...')
        SiteConfig.objects.delete()
        print('配置已删除')
        
        # 重新初始化配置
        print('正在初始化配置...')
        # 获取init_site_config函数
        init_site_config = app.config.get('init_site_config', None)
        if init_site_config:
            init_site_config()
        else:
            print('警告：找不到初始化函数，尝试重新创建应用...')
            app = create_app()  # 重新创建应用以触发初始化
        
        # 验证配置是否已创建
        configs = SiteConfig.objects.all()
        print('\n当前配置项：')
        for config in configs:
            print(f"{config.key}: {config.value} ({config.type})")

if __name__ == '__main__':
    reset_config() 