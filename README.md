# Flask 个人博客系统

一个使用 Flask 和 MongoDB 构建的个人博客系统。

## 功能特点

- 前台展示博客文章
- 后台管理系统
- 文章的增删改查
- 支持文章预览和分页
- 可配置的网站设置
- 响应式设计

## 系统要求

- Python 3.8+
- MongoDB 4.4+
- Nginx
- Ubuntu 20.04+ (推荐)

## 目录结构

```
/var/www/blog/              # 项目根目录
├── app/                    # 应用主目录
│   ├── __init__.py        # 应用初始化
│   ├── config.py          # 配置文件
│   ├── models.py          # 数据模型
│   ├── admin/             # 管理后台模块
│   │   ├── __init__.py
│   │   └── routes.py      # 后台路由
│   ├── main/              # 前台模块
│   │   ├── __init__.py
│   │   └── routes.py      # 前台路由
│   ├── static/            # 静态文件
│   │   └── icons/         # 图标文件
│   └── templates/         # 模板文件
│       ├── base.html      # 基础模板
│       ├── admin/         # 后台模板
│       └── main/          # 前台模板
├── venv/                  # Python 虚拟环境
├── logs/                  # 日志目录
├── .env                   # 环境变量配置
├── requirements.txt       # Python 依赖
├── run.py                 # 开发服务器启动脚本
└── wsgi.py               # WSGI 应用入口

/etc/nginx/sites-available/ # Nginx 配置目录
└── blog                   # 网站 Nginx 配置文件

/etc/systemd/system/       # Systemd 服务目录
└── blog.service          # 应用服务配置文件
```

## 部署步骤

### 1. 系统准备

```bash
# 更新系统
sudo apt update
sudo apt upgrade -y

# 安装必要的系统包
sudo apt install -y python3 python3-pip python3-venv nginx mongodb git

# 启动并启用 MongoDB
sudo systemctl start mongodb
sudo systemctl enable mongodb

# 安装中文语言包
sudo apt-get install language-pack-zh-hans
sudo locale-gen zh_CN.UTF-8
sudo update-locale LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8
```

### 2. 创建项目目录

```bash
# 创建项目目录
sudo mkdir -p /var/www/blog
sudo mkdir -p /var/www/blog/logs

# 设置目录权限
sudo chown -R www-data:www-data /var/www/blog
```

### 3. 配置 Python 环境

```bash
# 切换到项目目录
cd /var/www/blog

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 配置环境变量

创建 `/var/www/blog/.env` 文件：

```bash
SECRET_KEY=your-very-secret-key-here
MONGODB_DB=personal_website
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USERNAME=your-username
MONGODB_PASSWORD=your-password
FLASK_ENV=production
```

### 5. 配置 Nginx

创建 `/etc/nginx/sites-available/blog` 文件：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名
    charset utf-8;

    access_log /var/www/blog/logs/access.log;
    error_log /var/www/blog/logs/error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/blog/app/static;
        expires 30d;
        charset utf-8;
        add_header Content-Type "text/plain; charset=utf-8";
    }
}
```

启用网站配置：

```bash
sudo ln -s /etc/nginx/sites-available/blog /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. 配置应用服务

创建 `/etc/systemd/system/blog.service` 文件：

```ini
[Unit]
Description=Personal Blog
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/blog
Environment="PATH=/var/www/blog/venv/bin"
Environment="LANG=zh_CN.UTF-8"
Environment="LC_ALL=zh_CN.UTF-8"
Environment="LC_LANG=zh_CN.UTF-8"
EnvironmentFile=/var/www/blog/.env
ExecStart=/var/www/blog/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app --access-logfile /var/www/blog/logs/access.log --error-logfile /var/www/blog/logs/error.log
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start blog
sudo systemctl enable blog
```

### 7. 配置防火墙

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow ssh
```

### 8. 初始化数据库

```bash
# 激活虚拟环境
source /var/www/blog/venv/bin/activate

# 运行 Python 交互式环境
python3

# 在 Python 环境中执行
from app import create_app
from app.models import User

app = create_app()
with app.app_context():
    # 创建管理员用户
    if not User.objects(username='admin').first():
        user = User(username='admin')
        user.set_password('admin')  # 记得修改密码
        user.save()
```

## 维护命令

### 查看服务状态
```bash
sudo systemctl status blog
sudo systemctl status nginx
sudo systemctl status mongodb
```

### 查看日志
```bash
tail -f /var/www/blog/logs/access.log
tail -f /var/www/blog/logs/error.log
```

### 重启服务
```bash
sudo systemctl restart blog
sudo systemctl restart nginx
sudo systemctl restart mongodb
```

### 数据库备份
```bash
mongodump --db personal_website --out /backup/$(date +%Y%m%d)
```

## 安全建议

1. 修改默认管理员密码
2. 使用强密钥（SECRET_KEY）
3. 配置 SSL 证书启用 HTTPS
4. 定期更新系统和依赖包
5. 定期备份数据库
6. 配置日志轮转
7. 监控服务器资源使用情况

## 常见问题

### 1. 中文显示问题
确保所有 Python 文件都添加了 UTF-8 编码声明：
```python
# -*- coding: utf-8 -*-
```

### 2. 权限问题
检查目录权限：
```bash
sudo chown -R www-data:www-data /var/www/blog
sudo chmod -R 755 /var/www/blog
```

### 3. 服务无法启动
检查日志文件：
```bash
sudo journalctl -u blog.service
```

### 4. 静态文件无法访问
检查 Nginx 配置和目录权限：
```bash
sudo nginx -t
ls -la /var/www/blog/app/static
```

## 更新说明

- v1.0.0 (2024-01-01)
  - 初始版本发布
  - 基本的博客功能
  - 后台管理系统

## 许可证

MIT License
