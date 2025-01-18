# Flask Blog System

一个基于 Flask 和 MongoDB 的博客系统，支持文章管理、留言管理和文件上传等功能。

## 主要功能

### 文章管理
- 创建、编辑、删除文章
- 文章分类管理
- 文章置顶功能
- 文章可见性控制
- 附件上传和管理
  - 支持多文件上传
  - 文件安全存储
  - 文件下载和删除

### 留言系统
- 访客留言功能
- 留言管理（查看、删除）
- 留言公开/私密设置
- IP 地址记录和管理
- 防垃圾留言措施

### 管理员功能
- 管理员登录系统
- 密码修改
- 网站设置管理
- 仪表盘数据统计

## 技术栈

- **后端框架**: Flask
- **数据库**: MongoDB (使用 MongoEngine ORM)
- **前端框架**: Bootstrap 5
- **图标**: Bootstrap Icons
- **安全性**:
  - Flask-Login 用户认证
  - CSRF 保护
  - 文件上传安全处理
  - XSS 防护

## 项目结构

```
app/
├── admin/             # 管理后台模块
├── main/             # 前台页面模块
├── models/           # 数据模型
├── static/           # 静态文件
├── templates/        # 模板文件
└── utils/            # 工具函数
```

## 环境要求

- Python 3.8+
- MongoDB 4.0+
- pip (Python 包管理器)

## 安装和运行

1. 克隆项目并进入项目目录
```bash
git clone <repository-url>
cd <project-directory>
```

2. 创建并激活虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 设置环境变量
```bash
# Linux/Mac
export FLASK_APP=app
export FLASK_ENV=development

# Windows
set FLASK_APP=app
set FLASK_ENV=development
```

5. 运行应用
```bash
flask run
```

## 配置说明

主要配置项在 `.env` 文件中：

```env
MONGODB_URI=mongodb://localhost:27017/blog
SECRET_KEY=your-secret-key
UPLOAD_FOLDER=uploads
```

## 安全注意事项

1. 确保修改默认的 SECRET_KEY
2. 定期备份数据库
3. 及时更新依赖包
4. 确保上传目录具有适当的权限设置

## 开发说明

1. 代码风格遵循 PEP 8 规范
2. 使用 Git Flow 工作流
3. 提交前进行代码审查
4. 保持日志记录的完整性

## 许可证

MIT License