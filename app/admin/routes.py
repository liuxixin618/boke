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
    """确保上传文件夹存在，并返回正确的路径"""
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
    """自定义文件名清理函数，保留中文字符"""
    # 替换不安全的字符为下划线
    unsafe_chars = '<>:"/\\|?*\0'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    # 去除首尾空格
    filename = filename.strip()
    # 如果文件名为空，返回 unnamed
    return filename or 'unnamed'

def save_file(file):
    """保存上传的文件并返回存储信息"""
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
    return redirect(url_for('admin.dashboard'))

@admin.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = sanitize_string(request.form.get('username'))
        password = request.form.get('password')
        
        if not username or not password:
            flash('请输入用户名和密码')
            return render_template('admin/login.html')
            
        user = Admin.objects(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('用户名或密码错误')
    return render_template('admin/login.html')

@admin.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录')
    return redirect(url_for('admin.login'))

@admin.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 获取总文档数
    total = Post.objects.count()
    
    # 获取当前页的文档
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
            return self.page > 1
            
        @property
        def has_next(self):
            return self.page < self.pages
            
        @property
        def prev_num(self):
            return self.page - 1
            
        @property
        def next_num(self):
            return self.page + 1
            
        def iter_pages(self):
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
    if request.method == 'POST':
        # 清理并验证输入
        title = sanitize_string(request.form.get('title'))
        content = sanitize_string(request.form.get('content'))
        category = sanitize_string(request.form.get('category'))
        
        if not title or not content:
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
        attachments = []
        for file in files:
            file_info = save_file(file)
            if file_info:
                attachments.append(file_info)
        
        if attachments:
            post.attachments = attachments
        
        post.save()
        flash('文章已创建')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/edit_post.html')

@admin.route('/post/edit/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    try:
        # 验证并转换 ObjectId
        post = Post.objects.get_or_404(id=validate_object_id(post_id))
        
        if request.method == 'POST':
            has_changes = False
            
            # 清理并验证输入
            title = sanitize_string(request.form.get('title'))
            content = sanitize_string(request.form.get('content'))
            category = sanitize_string(request.form.get('category'))
            
            if not title or not content:
                flash('标题和内容不能为空')
                return render_template('admin/edit_post.html', post=post)
            
            # 检查基本字段是否有修改
            if post.title != title:
                has_changes = True
                post.title = title
                
            if post.category != category:
                has_changes = True
                post.category = category
                
            if post.content != content:
                has_changes = True
                post.content = content
                
            is_visible = bool(request.form.get('is_visible'))
            if post.is_visible != is_visible:
                has_changes = True
                post.is_visible = is_visible
            
            # 处理新上传的附件
            files = request.files.getlist('attachments')
            current_app.logger.info(f"Number of files uploaded: {len(files)}")
            
            for file in files:
                if file.filename:
                    current_app.logger.info(f"Processing uploaded file: {file.filename}")
                    file_info = save_file(file)
                    if file_info:
                        current_app.logger.info(f"File info after save: {file_info}")
                        has_changes = True
                        if not post.attachments:
                            post.attachments = []
                        post.attachments.append(file_info)
                        current_app.logger.info(f"Current post attachments: {post.attachments}")
            
            # 更新现有附件的文件大小（如果缺失）
            if post.attachments:
                current_app.logger.info("Checking existing attachments")
                upload_folder = ensure_upload_folder()
                for attachment in post.attachments:
                    current_app.logger.info(f"Checking attachment: {attachment}")
                    if 'file_size' not in attachment:
                        file_path = upload_folder / attachment['stored_filename']
                        if file_path.exists():
                            attachment['file_size'] = os.path.getsize(str(file_path))
                            has_changes = True
                            current_app.logger.info(f"Updated file size for {attachment['filename']}: {attachment['file_size']} bytes")
            
            # 只有在有实际修改时才更新时间戳
            if has_changes:
                post.updated_at = get_utc_time()
                
            post.save()
            current_app.logger.info("Post saved successfully")
            flash('文章已更新')
            return redirect(url_for('admin.dashboard'))
        
        # 在显示编辑页面时更新文件大小信息
        if post.attachments:
            current_app.logger.info("Updating file sizes for display")
            upload_folder = ensure_upload_folder()
            has_changes = False
            for attachment in post.attachments:
                current_app.logger.info(f"Checking attachment for display: {attachment}")
                if 'file_size' not in attachment:
                    file_path = upload_folder / attachment['stored_filename']
                    if file_path.exists():
                        attachment['file_size'] = os.path.getsize(str(file_path))
                        has_changes = True
                        current_app.logger.info(f"Updated display file size for {attachment['filename']}: {attachment['file_size']} bytes")
            if has_changes:
                post.save()
        
        return render_template('admin/edit_post.html', post=post)
        
    except Exception as e:
        current_app.logger.error(f"Edit post error: {str(e)}")
        flash('操作失败，请重试')
        return redirect(url_for('admin.dashboard'))

@admin.route('/post/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    try:
        # 验证并转换 ObjectId
        post = Post.objects(id=validate_object_id(post_id)).first_or_404()
        
        # 删除所有附件文件
        if post.attachments:
            upload_folder = ensure_upload_folder()
            for attachment in post.attachments:
                file_path = upload_folder / attachment['stored_filename']
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception as e:
                    current_app.logger.error(f"Error deleting attachment {attachment['stored_filename']}: {str(e)}")
        
        # 删除文章记录
        post.delete()
        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Delete post error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        try:
            # 更新网站配置
            for config in SiteConfig.objects.all():
                # 直接使用配置的 key 作为表单字段名
                value = request.form.get(config.key)
                
                if config.type == 'bool':
                    # 复选框未选中时不会提交值，所以使用 get() 方法
                    value = request.form.get(config.key, 'false') == 'on'
                elif value is not None:
                    value = value.strip()
                
                # 设置新值
                if value is not None:
                    try:
                        config.value = value
                        config.save()
                    except ValidationError as e:
                        flash(f'配置项 {config.description} 的值无效: {str(e)}')
                        return redirect(url_for('admin.settings'))
            
            flash('配置已更新')
            return redirect(url_for('admin.settings'))
            
        except Exception as e:
            current_app.logger.error(f"Settings update error: {str(e)}")
            flash('更新配置时出错，请重试')
            return redirect(url_for('admin.settings'))
    
    # 获取所有配置项
    configs = {}
    for config in SiteConfig.objects.all():
        configs[config.key] = config.value
    
    return render_template('admin/settings.html', site_config=configs)

@admin.route('/post/<post_id>/attachment/<filename>')
@login_required
def download_attachment(post_id, filename):
    try:
        post = Post.objects.get_or_404(id=post_id)
        attachment = next((a for a in post.attachments if a['stored_filename'] == filename), None)
        
        if not attachment:
            return '附件不存在', 404
        
        upload_folder = ensure_upload_folder()
        file_path = upload_folder / filename
        
        if not file_path.exists():
            return '文件不存在', 404
            
        return send_file(
            str(file_path),
            download_name=attachment['filename'],
            as_attachment=True
        )
        
    except Exception as e:
        current_app.logger.error(f"Download attachment error: {str(e)}")
        return '下载失败', 500

@admin.route('/post/<post_id>/attachment/<filename>/delete', methods=['POST'])
@login_required
def delete_attachment(post_id, filename):
    try:
        post = Post.objects.get_or_404(id=post_id)
        
        # 查找并删除附件
        for i, attachment in enumerate(post.attachments):
            if attachment['stored_filename'] == filename:
                # 删除文件
                try:
                    upload_folder = ensure_upload_folder()  # 获取正确的上传文件夹路径
                    file_path = upload_folder / filename
                    if file_path.exists():
                        file_path.unlink()
                except OSError as e:
                    current_app.logger.error(f"File delete error: {str(e)}")
                
                # 从数据库中移除附件记录
                post.attachments.pop(i)
                post.updated_at = get_utc_time()  # 使用北京时间
                post.save()
                
                return '', 204
        
        return 'Attachment not found', 404
        
    except Exception as e:
        current_app.logger.error(f"Delete attachment error: {str(e)}")
        return 'Internal server error', 500 

@admin.route('/post/<post_id>/pin', methods=['POST'])
@login_required
def toggle_pin(post_id):
    post = Post.objects(id=post_id).first_or_404()
    data = request.get_json()
    is_pinned = data.get('is_pinned', False)
    
    # 如果要设置为置顶，先取消其他文章的置顶状态
    if is_pinned:
        Post.objects(is_pinned=True).update(is_pinned=False)
    
    # 使用 update 方法只更新 is_pinned 字段，不触发 save() 方法
    Post.objects(id=post_id).update(is_pinned=is_pinned)
    
    return '', 204 

@admin.route('/admins')
@login_required
def admins():
    """管理员列表页面"""
    admins = Admin.objects.all()
    return render_template('admin/admins.html', admins=admins)

@admin.route('/admins/<admin_id>/username', methods=['POST'])
@login_required
def update_username(admin_id):
    """更新管理员用户名"""
    try:
        # 验证并获取管理员
        admin = Admin.objects.get_or_404(id=validate_object_id(admin_id))
        
        # 获取并验证新用户名
        new_username = sanitize_string(request.form.get('new_username', '').strip())
        if not new_username:
            return '用户名不能为空', 400
            
        # 检查用户名是否已存在
        if Admin.objects(username=new_username, id__ne=admin.id).first():
            return '用户名已存在', 400
            
        # 更新用户名
        admin.username = new_username
        admin.save()
        
        return '', 204
        
    except Exception as e:
        current_app.logger.error(f"Update username error: {str(e)}")
        return '操作失败，请重试', 500 

@admin.route('/admins/change_password', methods=['POST'])
@login_required
def admin_change_password():
    """修改管理员密码"""
    try:
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(old_password):
            return '当前密码错误', 400
        elif new_password != confirm_password:
            return '两次输入的新密码不一致', 400
        elif len(new_password) < 1:
            return '新密码不能为空', 400
            
        current_user.set_password(new_password)
        current_user.save()
        
        return '', 204
        
    except Exception as e:
        current_app.logger.error(f"Change password error: {str(e)}")
        return '操作失败，请重试', 500 