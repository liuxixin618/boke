from app import create_app, db
from app.models import User, SiteConfig

app = create_app()

# 创建初始管理员账号和网站配置
with app.app_context():
    # 创建管理员账号
    if not User.objects(username='1').first():
        user = User(username='1')
        user.set_password('1')
        user.save()
    
    # 创建网站配置
    configs = [
        {
            'key': 'content_preview_length',
            'value': 50,
            'description': '博客内容预览长度（字符数）',
            'type': 'int'
        },
        {
            'key': 'posts_per_page',
            'value': 10,
            'description': '每页显示的博客数量',
            'type': 'int'
        },
        {
            'key': 'icp_text',
            'value': '© 2023 个人网站 - 浙ICP备2023003303号',
            'description': '页脚备案信息文本',
            'type': 'str'
        },
        {
            'key': 'icp_link',
            'value': 'https://beian.miit.gov.cn',
            'description': '备案信息链接地址',
            'type': 'url'
        }
    ]
    
    # 更新或创建配置
    for config in configs:
        existing_config = SiteConfig.objects(key=config['key']).first()
        if not existing_config:
            SiteConfig(**config).save()
        else:
            # 更新类型字段
            existing_config.type = config['type']
            existing_config.description = config['description']
            existing_config.save()

if __name__ == '__main__':
    app.run(debug=True) 