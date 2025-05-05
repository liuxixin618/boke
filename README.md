# Flask 博客系统

一个基于 **Flask + MongoDB** 的现代化博客系统，支持文章管理、分类、多附件上传、富文本编辑、留言、好站分享、系统日志可视化、动态公告、移动端自适应等功能。前端采用 Bootstrap 5，支持 Markdown 格式内容展示。

---

## 主要功能

### 文章与分类
- 文章的创建、编辑、删除、置顶、可见性控制
- 支持多分类（文章可属于多个分类）
- 分类的增删改查
- 富文本编辑（CKEditor 5，支持图片/视频上传）
- 附件上传与管理

### 留言系统
- 访客留言、弹幕展示
- 留言管理、删除、公开/私密切换
- IP 记录与限制，防刷机制

### 好站分享
- "好站分享"模块，支持增删改查、置顶、显示/隐藏
- 前台页面美观展示，置顶项有星标
- 后台管理入口

### 公告与关于作者
- 公告弹窗，内容支持 Markdown，静态文件管理
- "关于作者"页面，内容通过 Markdown 文件自定义，支持格式化展示

### 网站设置与导航
- 后台可配置导航栏各项显示与名称
- 所有导航项支持自定义顺序、显示与文本

### 日志与监控
- 后台可视化系统日志、Nginx 日志
- 支持日志滚动查看

### 其它
- 支持移动端自适应
- 全站缓存优化，缓存 key 合理
- 兼容 Windows 开发与 Linux 部署

---

## 技术栈

- **后端**：Flask 2.2.5、Flask-MongoEngine、Flask-Login、Flask-WTF、Flask-Limiter
- **数据库**：MongoDB 4.0+（推荐 4.2+）
- **前端**：Bootstrap 5.3.0、Bootstrap Icons、markdown-it、CKEditor 5
- **依赖管理**：requirements.txt
- **日志**：RotatingFileHandler，支持日志文件分割

---

## 目录结构

```
boke/
├── app/
│   ├── admin/           # 后台管理蓝图
│   ├── main/            # 前台主站蓝图
│   ├── models.py        # 数据模型
│   ├── constants.py     # 全局常量（如版本号）
│   ├── static/          # 静态资源（css/js/file/等）
│   │   └── file/
│   │       ├── Version_Announcement.md   # 公告内容
│   │       └── About_author.md           # 关于作者内容
│   ├── templates/       # Jinja2 模板
│   └── utils/           # 工具函数
├── uploads/             # 上传文件存储
├── logs/                # 日志文件
├── requirements.txt     # 依赖包
├── run.py / wsgi.py     # 启动入口
├── download_static.py   # 静态资源下载脚本
├── init_siteshare_nav_config.py # 初始化好站分享配置
└── README.md
```

---

## 快速开始

1. **克隆项目并进入目录**
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. **创建并激活虚拟环境**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **下载静态资源**
   ```bash
   python download_static.py
   ```

5. **初始化好站分享导航配置（如首次部署）**
   ```bash
   python init_siteshare_nav_config.py
   ```

6. **配置环境变量（可用 .env 文件）**
   ```
   MONGODB_URI=mongodb://localhost:27017/blog
   SECRET_KEY=your-secret-key
   FLASK_ENV=development
   ```

7. **运行项目**
   ```bash
   flask run
   # 或
   python run.py
   ```

---

## 生产部署

- 推荐使用 Gunicorn + Nginx，详见 `deployment_guide.md`
- 支持 Systemd 服务管理、Nginx 静态资源代理
- 日志、数据库备份、权限等安全建议详见部署文档

---

## 配置与自定义

- **全局常量**：`app/constants.py` 统一管理（如版本号）
- **公告内容**：`app/static/file/Version_Announcement.md`，支持 Markdown
- **关于作者**：`app/static/file/About_author.md`，支持 Markdown
- **导航栏**：后台"网站设置"可自定义显示与文本
- **好站分享**：后台管理，前台 `/siteshare` 展示

---

## 数据库管理

- MongoDB 数据结构详见 `mongo.txt`
- 常用命令、备份恢复、数据维护等均有说明

---

## 依赖包

详见 `requirements.txt`，主要依赖包括：
- Flask、Flask-Login、Flask-MongoEngine、Flask-WTF、Flask-Limiter
- mongoengine、pymongo、python-dotenv、gunicorn 等

---

## 安全建议

- 修改默认 SECRET_KEY
- 数据库账号密码安全
- 上传目录权限控制
- 定期备份数据库
- 及时更新依赖

---

## 许可证

MIT License

---

如需更多帮助或功能扩展，欢迎提 issue 或联系作者！