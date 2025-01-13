from app import create_app
from app.models import Admin, SiteConfig

app = create_app('development')

# 创建初始管理员账号和网站配置
with app.app_context():
    # 创建管理员账号
    if not Admin.objects(username='admin').first():
        admin = Admin(username='admin')
        admin.set_password('admin')
        admin.save()
        print('Created admin user')
    
    # 创建网站配置
    configs = [
        {
            'key': 'site_title',
            'value': '我的个人网站',
            'description': '网站标题',
            'type': 'str'
        },
        {
            'key': 'content_preview_length',
            'value': '50',
            'description': '博客内容预览长度（字符数）',
            'type': 'int'
        },
        {
            'key': 'posts_per_page',
            'value': '10',
            'description': '每页显示的博客数量',
            'type': 'int'
        },
        {
            'key': 'icp_text',
            'value': '© 2024 个人网站 - 备案信息',
            'description': '页脚备案信息文本',
            'type': 'str'
        },
        {
            'key': 'icp_link',
            'value': 'https://beian.miit.gov.cn',
            'description': '备案信息链接地址',
            'type': 'url'
        },
        # 导航栏配置
        {
            'key': 'nav_home_text',
            'value': '首页',
            'description': '导航栏-首页文本',
            'type': 'str'
        },
        {
            'key': 'nav_home_visible',
            'value': 'true',
            'description': '导航栏-首页是否显示',
            'type': 'bool'
        },
        {
            'key': 'nav_goods_text',
            'value': '好物分享',
            'description': '导航栏-好物分享文本',
            'type': 'str'
        },
        {
            'key': 'nav_goods_visible',
            'value': 'true',
            'description': '导航栏-好物分享是否显示',
            'type': 'bool'
        },
        {
            'key': 'nav_about_text',
            'value': '关于作者',
            'description': '导航栏-关于作者文本',
            'type': 'str'
        },
        {
            'key': 'nav_about_visible',
            'value': 'true',
            'description': '导航栏-关于作者是否显示',
            'type': 'bool'
        }
    ]
    
    # 更新或创建配置
    for config in configs:
        existing_config = SiteConfig.objects(key=config['key']).first()
        if not existing_config:
            SiteConfig(**config).save()
            print(f"Created config: {config['key']}")
        else:
            # 更新类型字段
            existing_config.type = config['type']
            existing_config.description = config['description']
            existing_config.save()
            print(f"Updated config: {config['key']}")

print('Database initialization completed') 