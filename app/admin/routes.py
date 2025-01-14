# -*- coding: utf-8 -*-
"""
后台管理路由模块
包含所有管理员相关的路由处理函数，如登录、文章管理、网站设置等
"""

import os
from flask import render_template, redirect, url_for, request, flash, jsonify, send_from_directory, current_app, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from . import admin
from ..models import Admin, Post, SiteConfig, get_utc_time
from ..utils.security import sanitize_string, sanitize_mongo_query, validate_object_id
from datetime import datetime, timezone, timedelta
import uuid
from pathlib import Path

def ensure_upload_folder():
    """
    确保上传文件夹存在并返回正确的路径
    
    Returns:
        Path: 上传文件夹的路径对象
        
    Raises:
        Exception: 如果创建文件夹失败或文件夹不可写
    """
    try:
        # 获取项目根目录（app的父目录）
        base_dir = Path(current_app.root_path).parent
        # 创建uploads目录
        upload_folder = base_dir / 'uploads'
        upload_folder.mkdir(parents=True, exist_ok=True)
        
        # 设置上传文件夹路径到应用配置中
        current_app.config['UPLOAD_FOLDER'] = str(upload_folder)
        
        # 确保目录存在且可写
        if not upload_folder.exists():
            raise Exception("Upload folder does not exist after creation attempt")
        if not os.access(str(upload_folder), os.W_OK):
            raise Exception("Upload folder is not writable")
            
        return upload_folder
    except Exception as e:
        current_app.logger.error(f"Error ensuring upload folder: {str(e)}")
        raise

def sanitize_filename(filename):
    """
    自定义文件名清理函数，保留中文字符
    
    Args:
        filename (str): 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    # 替换不安全的字符为下划线
    unsafe_chars = '<>:"/\\|?*\0'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    # 去除首尾空格
    filename = filename.strip()
    # 如果文件名为空，返回 unnamed
    return filename or 'unnamed'

def save_file(file):
    """
    保存上传的文件并返回存储信息
    
    Args:
        file: FileStorage对象，上传的文件
        
    Returns:
        dict: 包含文件信息的字典，如果保存失败返回None
    """
    if not file or not file.filename:
        current_app.logger.warning("No file or filename provided")
        return None
        
    try:
        # 保存原始文件名
        current_app.logger.info(f"Original filename: {file.filename}")
        
        # 分离文件名和扩展名
        if '.' in file.filename:
            name_base, ext = file.filename.rsplit('.', 1)
            ext = '.' + ext.lower()
        else:
            name_base = file.filename
            ext = ''
            
        current_app.logger.info(f"Name base: {name_base}, Extension: {ext}")
        
        # 使用自定义函数清理文件名，保留中文字符
        safe_name_base = sanitize_filename(name_base)
        original_filename = safe_name_base + ext
        
        current_app.logger.info(f"Safe original filename: {original_filename}")
        
        # 生成唯一的存储文件名
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        current_app.logger.info(f"Generated stored filename: {stored_filename}")
        
        # 获取上传目录并保存文件
        upload_folder = ensure_upload_folder()
        file_path = upload_folder / stored_filename
        current_app.logger.info(f"Saving file to: {file_path}")
        file.save(str(file_path))
        
        # 确保文件成功保存并获取文件大小
        if not file_path.exists():
            current_app.logger.error("File was not saved successfully")
            raise Exception("File was not saved successfully")
        
        file_size = os.path.getsize(str(file_path))
        current_app.logger.info(f"File size: {file_size} bytes")
        
        # 返回文件信息字典
        file_info = {
            'filename': original_filename,  # 保存清理后的原始文件名
            'stored_filename': stored_filename,  # 存储的文件名（带扩展名）
            'file_type': ext[1:] if ext else '',  # 文件类型（不带点）
            'file_size': file_size  # 文件大小（字节）
        }
        current_app.logger.info(f"Returning file info: {file_info}")
        return file_info
        
    except Exception as e:
        current_app.logger.error(f"File save error: {str(e)}")
        return None

@admin.route('/')
@login_required
def index():
    """后台首页路由，重定向到仪表盘"""
    return redirect(url_for('admin.dashboard'))

@admin.route('/login', methods=['GET', 'POST'])
def login():
    """
    管理员登录
    
    处理GET请求：显示登录页面
    处理POST请求：验证用户名密码并登录
    """
    if request.method == 'POST':
        # 获取并清理用户输入
        username = sanitize_string(request.form.get('username'))
        password = request.form.get('password')
        
        if not username or not password:
            flash('请输入用户名和密码')
            return render_template('admin/login.html')
            
        current_app.logger.info(f"尝试登录用户: {username}")
        user = Admin.objects(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            current_app.logger.info(f"用户 {username} 登录成功")
            return redirect(url_for('admin.dashboard'))
            
        current_app.logger.warning(f"用户 {username} 登录失败：密码错误")
        flash('用户名或密码错误')
    return render_template('admin/login.html')

@admin.route('/logout')
@login_required
def logout():
    """管理员登出"""
    logout_user()
    flash('您已成功退出登录')
    return redirect(url_for('admin.login'))

@admin.route('/dashboard')
@login_required
def dashboard():
    """
    后台仪表盘
    显示文章列表，支持分页
    """
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 获取总文档数
    total = Post.objects.count()
    
    # 获取当前页的文档，按置顶和更新时间排序
    posts = Post.objects.order_by('-is_pinned', '-updated_at', '-created_at').skip((page - 1) * per_page).limit(per_page)
    
    # 创建分页对象
    class Pagination:
        def __init__(self, page, per_page, total):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.items = posts
            self.pages = (total + per_page - 1) // per_page
            
        @property
        def has_prev(self):
            """是否有上一页"""
            return self.page > 1
            
        @property
        def has_next(self):
            """是否有下一页"""
            return self.page < self.pages
            
        @property
        def prev_num(self):
            """上一页页码"""
            return self.page - 1
            
        @property
        def next_num(self):
            """下一页页码"""
            return self.page + 1
            
        def iter_pages(self):
            """生成分页导航的页码"""
            left_edge = 2
            left_current = 2
            right_current = 3
            right_edge = 2
            
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and \
                    num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num
    
    pagination = Pagination(page, per_page, total)
    return render_template('admin/dashboard.html', posts=pagination)

@admin.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    """
    创建新文章
    
    GET请求：显示创建文章表单
    POST请求：处理文章创建
    """
    if request.method == 'POST':
        # 清理并验证输入
        title = sanitize_string(request.form.get('title'))
        content = sanitize_string(request.form.get('content'))
        category = sanitize_string(request.form.get('category'))
        
        current_app.logger.info(f"开始创建新文章: {title}")
        
        if not title or not content:
            current_app.logger.warning("创建文章失败：标题或内容为空")
            flash('标题和内容不能为空')
            return render_template('admin/edit_post.html')
        
        # 创建文章
        post = Post(
            title=title,
            content=content,
            category=category,
            is_visible=bool(request.form.get('is_visible')),
            updated_at=get_utc_time()
        )
        
        # 处理附件
        files = request.files.getlist('attachments')
        current_app.logger.info(f"处理文章附件，共 {len(files)} 个文件")
        
        attachments = []
        for file in files:
            current_app.logger.info(f"处理附件: {file.filename}")
            file_info = save_file(file)
            if file_info:
                attachments.append(file_info)
                current_app.logger.info(f"附件保存成功: {file_info}")
        
        if attachments:
            post.attachments = attachments
        
        post.save()
        current_app.logger.info(f"文章创建成功，ID: {post.id}")
        flash('文章已创建')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/edit_post.html')

@admin.route('/post/edit/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """
    编辑文章
    
    Args:
        post_id: 文章ID
        
    GET请求：显示编辑文章表单
    POST请求：处理文章更新
    """
    try:
        current_app.logger.info(f"开始编辑文章，ID: {post_id}")
        post = Post.objects.get_or_404(id=validate_object_id(post_id))
        current_app.logger.info(f"找到文章: {post.title}")
        
        if request.method == 'POST':
            has_changes = False
            
            # 清理并验证输入
            title = sanitize_string(request.form.get('title'))
            content = sanitize_string(request.form.get('content'))
            category = sanitize_string(request.form.get('category'))
            
            if not title or not content:
                current_app.logger.warning("更新文章失败：标题或内容为空")
                flash('标题和内容不能为空')
                return render_template('admin/edit_post.html', post=post)
            
            # 记录字段变更
            if post.title != title:
                current_app.logger.info(f"文章标题更新: {post.title} -> {title}")
                has_changes = True
                post.title = title
                
            if post.category != category:
                current_app.logger.info(f"文章分类更新: {post.category} -> {category}")
                has_changes = True
                post.category = category
                
            if post.content != content:
                current_app.logger.info("文章内容已更新")
                has_changes = True
                post.content = content
                
            is_visible = bool(request.form.get('is_visible'))
            if post.is_visible != is_visible:
                current_app.logger.info(f"文章可见性更新: {post.is_visible} -> {is_visible}")
                has_changes = True
                post.is_visible = is_visible
            
            # 处理新上传的附件
            files = request.files.getlist('attachments')
            current_app.logger.info(f"处理新上传附件，共 {len(files)} 个文件")
            
            for file in files:
                if file.filename:
                    current_app.logger.info(f"处理新附件: {file.filename}")
                    file_info = save_file(file)
                    if file_info:
                        current_app.logger.info(f"新附件保存成功: {file_info}")
                        has_changes = True
                        if not post.attachments:
                            post.attachments = []
                        post.attachments.append(file_info)
            
            # 更新现有附件的文件大小
            if post.attachments:
                current_app.logger.info("检查现有附件的文件大小")
                upload_folder = ensure_upload_folder()
                for attachment in post.attachments:
                    if 'file_size' not in attachment:
                        file_path = upload_folder / attachment['stored_filename']
                        if file_path.exists():
                            old_size = attachment.get('file_size', 'unknown')
                            attachment['file_size'] = os.path.getsize(str(file_path))
                            current_app.logger.info(f"更新附件 {attachment['filename']} 的文件大小: {old_size} -> {attachment['file_size']}")
                            has_changes = True
            
            if has_changes:
                post.updated_at = get_utc_time()
                post.save()
                current_app.logger.info(f"文章更新成功，ID: {post_id}")
                flash('文章已更新')
            else:
                current_app.logger.info("文章无变更")
            return redirect(url_for('admin.dashboard'))
        
        return render_template('admin/edit_post.html', post=post)
        
    except Exception as e:
        current_app.logger.error(f"编辑文章出错，ID: {post_id}, 错误: {str(e)}")
        flash('操作失败，请重试')
        return redirect(url_for('admin.dashboard'))

@admin.route('/post/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    """
    删除文章
    
    Args:
        post_id: 文章ID
        
    删除文章及其所有附件文件
    """
    try:
        current_app.logger.info(f"开始删除文章，ID: {post_id}")
        post = Post.objects(id=validate_object_id(post_id)).first_or_404()
        current_app.logger.info(f"找到要删除的文章: {post.title}")
        
        # 删除所有附件文件
        if post.attachments:
            upload_folder = ensure_upload_folder()
            for attachment in post.attachments:
                file_path = upload_folder / attachment['stored_filename']
                try:
                    if file_path.exists():
                        current_app.logger.info(f"删除附件文件: {attachment['filename']}")
                        file_path.unlink()
                except Exception as e:
                    current_app.logger.error(f"删除附件文件失败: {attachment['filename']}, 错误: {str(e)}")
        
        # 删除文章记录
        post.delete()
        current_app.logger.info(f"文章删除成功，ID: {post_id}")
        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"删除文章失败，ID: {post_id}, 错误: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """
    网站设置
    
    GET请求：显示设置表单
    POST请求：更新网站配置
    """
    if request.method == 'POST':
        try:
            current_app.logger.info("开始更新网站配置")
            for config in SiteConfig.objects.all():
                value = request.form.get(config.key)
                old_value = config.value
                
                if config.type == 'bool':
                    value = request.form.get(config.key, 'false') == 'on'
                elif value is not None:
                    value = value.strip()
                
                if value is not None and value != old_value:
                    try:
                        current_app.logger.info(f"更新配置项: {config.key}, {old_value} -> {value}")
                        config.value = value
                        config.save()
                    except ValidationError as e:
                        current_app.logger.error(f"配置项 {config.key} 更新失败: {str(e)}")
                        flash(f'配置项 {config.description} 的值无效: {str(e)}')
                        return redirect(url_for('admin.settings'))
            
            current_app.logger.info("网站配置更新成功")
            flash('配置已更新')
            return redirect(url_for('admin.settings'))
            
        except Exception as e:
            current_app.logger.error(f"更新网站配置失败: {str(e)}")
            flash('更新配置时出错，请重试')
            return redirect(url_for('admin.settings'))
    
    current_app.logger.info("获取所有网站配置")
    configs = {}
    for config in SiteConfig.objects.all():
        configs[config.key] = config.value
    
    return render_template('admin/settings.html', site_config=configs)

@admin.route('/post/<post_id>/attachment/<filename>')
@login_required
def download_attachment(post_id, filename):
    """
    下载附件
    
    Args:
        post_id: 文章ID
        filename: 文件名
        
    Returns:
        文件下载响应
    """
    try:
        current_app.logger.info(f"开始下载附件，文章ID: {post_id}, 文件名: {filename}")
        post = Post.objects.get_or_404(id=post_id)
        attachment = next((a for a in post.attachments if a['stored_filename'] == filename), None)
        
        if not attachment:
            current_app.logger.warning(f"附件不存在: {filename}")
            return '附件不存在', 404
        
        upload_folder = ensure_upload_folder()
        file_path = upload_folder / filename
        
        if not file_path.exists():
            current_app.logger.warning(f"文件不存在: {file_path}")
            return '文件不存在', 404
            
        current_app.logger.info(f"开始发送文件: {attachment['filename']}")
        return send_file(
            str(file_path),
            download_name=attachment['filename'],
            as_attachment=True
        )
        
    except Exception as e:
        current_app.logger.error(f"下载附件失败: {str(e)}")
        return '下载失败', 500

@admin.route('/post/<post_id>/attachment/<filename>/delete', methods=['POST'])
@login_required
def delete_attachment(post_id, filename):
    """
    删除附件
    
    Args:
        post_id: 文章ID
        filename: 文件名
    """
    try:
        current_app.logger.info(f"开始删除附件，文章ID: {post_id}, 文件名: {filename}")
        post = Post.objects.get_or_404(id=post_id)
        
        for i, attachment in enumerate(post.attachments):
            if attachment['stored_filename'] == filename:
                try:
                    upload_folder = ensure_upload_folder()
                    file_path = upload_folder / filename
                    if file_path.exists():
                        current_app.logger.info(f"删除文件: {file_path}")
                        file_path.unlink()
                except OSError as e:
                    current_app.logger.error(f"删除文件失败: {str(e)}")
                
                current_app.logger.info(f"从数据库中移除附件记录: {attachment['filename']}")
                post.attachments.pop(i)
                post.updated_at = get_utc_time()
                post.save()
                
                return '', 204
        
        current_app.logger.warning(f"附件不存在: {filename}")
        return 'Attachment not found', 404
        
    except Exception as e:
        current_app.logger.error(f"删除附件失败: {str(e)}")
        return 'Internal server error', 500

@admin.route('/post/<post_id>/pin', methods=['POST'])
@login_required
def toggle_pin(post_id):
    """
    切换文章的置顶状态
    
    Args:
        post_id: 文章ID
    """
    try:
        current_app.logger.info(f"开始切换文章置顶状态，ID: {post_id}")
        post = Post.objects(id=post_id).first_or_404()
        data = request.get_json()
        is_pinned = data.get('is_pinned', False)
        
        if is_pinned:
            current_app.logger.info("取消其他文章的置顶状态")
            Post.objects(is_pinned=True).update(is_pinned=False)
        
        current_app.logger.info(f"更新文章置顶状态: {is_pinned}")
        Post.objects(id=post_id).update(is_pinned=is_pinned)
        
        return '', 204
    except Exception as e:
        current_app.logger.error(f"切换文章置顶状态失败: {str(e)}")
        return 'Internal server error', 500

@admin.route('/admins')
@login_required
def admins():
    """管理员列表页面"""
    admins = Admin.objects.all()
    return render_template('admin/admins.html', admins=admins)

@admin.route('/admins/<admin_id>/username', methods=['POST'])
@login_required
def update_username(admin_id):
    """
    更新管理员用户名
    
    Args:
        admin_id: 管理员ID
    """
    try:
        current_app.logger.info(f"开始更新管理员用户名，ID: {admin_id}")
        admin = Admin.objects.get_or_404(id=validate_object_id(admin_id))
        
        new_username = sanitize_string(request.form.get('new_username', '').strip())
        if not new_username:
            current_app.logger.warning("新用户名为空")
            return '用户名不能为空', 400
            
        if Admin.objects(username=new_username, id__ne=admin.id).first():
            current_app.logger.warning(f"用户名已存在: {new_username}")
            return '用户名已存在', 400
            
        old_username = admin.username
        admin.username = new_username
        admin.save()
        current_app.logger.info(f"管理员用户名更新成功: {old_username} -> {new_username}")
        
        return '', 204
        
    except Exception as e:
        current_app.logger.error(f"更新管理员用户名失败: {str(e)}")
        return '操作失败，请重试', 500

@admin.route('/admins/change_password', methods=['POST'])
@login_required
def admin_change_password():
    """修改管理员密码"""
    try:
        current_app.logger.info(f"开始修改管理员密码，用户: {current_user.username}")
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(old_password):
            current_app.logger.warning("当前密码验证失败")
            return '当前密码错误', 400
        elif new_password != confirm_password:
            current_app.logger.warning("新密码两次输入不一致")
            return '两次输入的新密码不一致', 400
        elif len(new_password) < 1:
            current_app.logger.warning("新密码为空")
            return '新密码不能为空', 400
            
        current_user.set_password(new_password)
        current_user.save()
        current_app.logger.info("管理员密码修改成功")
        
        return '', 204
        
    except Exception as e:
        current_app.logger.error(f"修改管理员密码失败: {str(e)}")
        return '操作失败，请重试', 500 