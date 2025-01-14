# 个人博客系统

这是一个基于 Flask 和 MongoDB 开发的个人博客系统，支持文章管理、文件上传、搜索等功能。

## 功能特点

- 文章管理
  - 支持文章的创建、编辑、删除
  - 支持文章置顶功能
  - 支持文章可见性控制
  - 支持文章搜索功能（标题模糊匹配）
  
- 文件管理
  - 支持多文件上传
  - 支持文件类型验证
  - 支持批量下载附件
  
- 系统配置
  - 支持网站标题配置
  - 支持导航栏自定义
  - 支持分页设置
  - 支持内容预览长度设置

## 技术栈

- 后端：Flask + MongoDB
- 前端：Bootstrap 5 + jQuery
- 数据库：MongoDB
- Web服务器：uWSGI + Nginx

## 系统要求

- Python 3.8+
- MongoDB 4.0+
- Linux 系统（生产环境）

## 本地开发环境搭建

1. 克隆项目：
```bash
git clone [项目地址]
cd [项目目录]
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux
venv\Scripts\activate     # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 创建配置文件：
```bash
cp .env.example .env
```

5. 修改 .env 文件：
```
SECRET_KEY=your-secret-key
MONGODB_URI=mongodb://localhost:27017/blog
```

6. 初始化数据库：
```bash
python init_db.py
```

7. 运行开发服务器：
```bash
python run.py
```

## Linux 生产环境部署

1. 安装系统依赖：
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-pip python3-dev nginx
sudo apt-get install build-essential python3-venv

# CentOS/RHEL
sudo yum install python3-pip python3-devel nginx
sudo yum groupinstall 'Development Tools'
```

2. 创建项目目录：
```bash
sudo mkdir /var/www/blog
sudo chown $USER:$USER /var/www/blog
```

3. 克隆项目并设置环境：
```bash
cd /var/www/blog
git clone [项目地址] .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. 配置 uWSGI：
使用项目中的 `bk_uwsgi.ini` 文件，内容如下：
```ini
[uwsgi]
# 项目根目录
chdir = /var/www/blog

# Python 虚拟环境
home = /var/www/blog/venv

# 项目的 wsgi 文件
module = wsgi:app

# 进程相关的设置
# 主进程
master = true
# 最大数量的工作进程
processes = 4

# 监听的端口
socket = /var/www/blog/blog.sock
# socket 权限设置
chmod-socket = 666
# 退出的时候是否清理环境
vacuum = true

# 日志相关
daemonize = /var/www/blog/logs/uwsgi.log
log-reopen = true
log-maxsize = 50000000

# 其他优化
harakiri = 30
buffer-size = 32768
post-buffering = 4096
```

5. 配置 Nginx：
```bash
sudo nano /etc/nginx/sites-available/blog
```

添加以下内容：
```nginx
server {
    listen 80;
    server_name your_domain.com;  # 替换为你的域名

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/var/www/blog/blog.sock;
    }

    location /static {
        alias /var/www/blog/app/static;
    }

    location /uploads {
        alias /var/www/blog/uploads;
        add_header Content-Disposition "attachment";
    }
}
```

6. 启用网站配置：
```bash
sudo ln -s /etc/nginx/sites-available/blog /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

7. 创建 systemd 服务：
```bash
sudo nano /etc/systemd/system/blog.service
```

添加以下内容：
```ini
[Unit]
Description=uWSGI instance to serve blog
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/blog
Environment="PATH=/var/www/blog/venv/bin"
ExecStart=/var/www/blog/venv/bin/uwsgi --ini bk_uwsgi.ini

[Install]
WantedBy=multi-user.target
```

8. 启动服务：
```bash
sudo systemctl start blog
sudo systemctl enable blog
```

## 目录结构

```
.
├── app/                    # 应用主目录
│   ├── admin/             # 管理后台模块
│   ├── main/              # 前台模块
│   ├── static/            # 静态文件
│   ├── templates/         # 模板文件
│   ├── __init__.py        # 应用初始化
│   ├── models.py          # 数据模型
│   └── context_processors.py  # 上下文处理器
├── uploads/               # 上传文件目录
├── logs/                  # 日志目录
├── config.py             # 配置文件
├── requirements.txt      # Python 依赖
├── bk_uwsgi.ini         # uWSGI 配置
└── wsgi.py              # WSGI 入口文件
```

## 安全注意事项

1. 确保修改 `.env` 文件中的 `SECRET_KEY`
2. 配置 MongoDB 访问权限
3. 设置适当的文件权限
4. 配置 SSL 证书（推荐使用 Let's Encrypt）
5. 定期备份数据

## 维护建议

1. 定期检查日志文件
2. 配置日志轮转
3. 定期更新依赖包
4. 配置监控系统
5. 设置自动备份

## 许可证

[选择合适的许可证]

## 作者

[作者信息]
老司机左塞