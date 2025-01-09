# Flask 博客系统 Ubuntu 部署指南

## 1. 系统依赖安装

```bash
# 更新包管理器
sudo apt update

# 安装 Python3 和相关工具
sudo apt install python3 python3-pip python3-venv

# 安装 MongoDB
sudo apt install mongodb

# 启动 MongoDB 服务并设置开机自启
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

## 2. 项目配置修改

### 修改 config.py，添加生产环境配置：

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    # MongoDB 配置
    MONGODB_SETTINGS = {
        'db': os.environ.get('MONGODB_DB', 'personal_website'),
        'host': os.environ.get('MONGODB_HOST', 'localhost'),
        'port': int(os.environ.get('MONGODB_PORT', 27017)),
        'username': os.environ.get('MONGODB_USERNAME'),
        'password': os.environ.get('MONGODB_PASSWORD')
    }

class ProductionConfig(Config):
    DEBUG = False
    # 使用更安全的密钥
    SECRET_KEY = os.environ.get('SECRET_KEY')
    # 如果使用 Nginx 作为反向代理
    PREFERRED_URL_SCHEME = 'https'
```

## 3. 环境配置

### 创建生产环境配置文件 .env：

```bash
SECRET_KEY=your-very-secret-key-here
MONGODB_DB=personal_website
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USERNAME=your-username
MONGODB_PASSWORD=your-password
FLASK_ENV=production
```

## 4. WSGI 服务器配置

### 更新 requirements.txt：

```
Flask==3.0.0
flask-login==0.6.3
flask-mongoengine==1.0.0
mongoengine==0.27.0
python-dotenv==1.0.0
Werkzeug==3.0.1
gunicorn==21.2.0
```

### 创建 wsgi.py：

```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
```

## 5. 系统服务配置

### 创建 Systemd 服务文件 /etc/systemd/system/blog.service：

```ini
[Unit]
Description=Personal Blog
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/blog
Environment="PATH=/var/www/blog/venv/bin"
EnvironmentFile=/var/www/blog/.env
ExecStart=/var/www/blog/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## 6. Nginx 配置

### 创建 Nginx 配置文件 /etc/nginx/sites-available/blog：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /var/www/blog/app/static;
    }
}
```

## 7. 部署步骤

```bash
# 创建项目目录
sudo mkdir -p /var/www/blog
sudo chown www-data:www-data /var/www/blog

# 复制项目文件
sudo cp -r * /var/www/blog/

# 创建虚拟环境
cd /var/www/blog
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 设置权限
sudo chown -R www-data:www-data /var/www/blog

# 启用 Nginx 配置
sudo ln -s /etc/nginx/sites-available/blog /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 启动应用服务
sudo systemctl start blog
sudo systemctl enable blog
```

## 8. 安全配置

### 防火墙配置：

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow ssh
```

### 数据库备份：

```bash
mongodump --db personal_website --out /backup/$(date +%Y%m%d)
```

## 9. 常用维护命令

### 查看服务状态：
```bash
sudo systemctl status blog
sudo systemctl status nginx
sudo systemctl status mongodb
```

### 查看日志：
```bash
tail -f /var/log/blog/app.log
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 重启服务：
```bash
sudo systemctl restart blog
sudo systemctl restart nginx
sudo systemctl restart mongodb
```

## 注意事项

1. 确保所有密码和密钥都是安全的，不要使用默认值
2. 定期备份数据库
3. 定期更新系统和依赖包
4. 监控服务器资源使用情况
5. 配置 SSL 证书以启用 HTTPS
6. 设置日志轮转以防止日志文件过大 