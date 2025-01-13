import os
from flask import render_template, redirect, url_for, request, flash, jsonify, send_from_directory, current_app, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from . import admin
from ..models import Admin, Post, SiteConfig, get_beijing_time
from datetime import datetime, timezone, timedelta
import uuid
from pathlib import Path

def ensure_upload_folder():
    """确保上传文件夹存在，并返回正确的路径"""
    # 使用项目根目录下的 uploads 文件夹
    base_dir = Path(current_app.root_path).parent
    upload_folder = base_dir / 'uploads'
    upload_folder.mkdir(parents=True, exist_ok=True)
    current_app.config['UPLOAD_FOLDER'] = str(upload_folder)
    return upload_folder

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    # 文档类
    'pdf', 'doc', 'docx', 'txt',
    # 压缩文件
    'zip', 'rar', '7z',
    # 图片文件
    'jpg', 'jpeg', 'png', 'gif', 'webp',
    # 应用程序
    'apk',
    # Excel文件
    'xls', 'xlsx'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file):
    """保存上传的文件并返回存储信息"""
    if not file or not file.filename:
        return None
        
    if allowed_file(file.filename):
        try:
            # 保存原始文件名
            original_filename = file.filename
            # 生成安全的存储文件名
            stored_filename = f"{uuid.uuid4().hex}.{original_filename.rsplit('.', 1)[1].lower()}"
            
            # 获取上传目录并保存文件
            upload_folder = ensure_upload_folder()
            file_path = upload_folder / stored_filename
            file.save(str(file_path))
            
            return {
                'filename': original_filename,  # 使用原始文件名
                'stored_filename': stored_filename
            }
        except Exception as e:
            current_app.logger.error(f"File save error: {str(e)}")
            return None
    return None

@admin.route('/')
@login_required
def index():
    return redirect(url_for('admin.dashboard'))

@admin.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Admin.objects(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('Invalid username or password')
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
    per_page = 10  # 每页显示的文章数量
    
    # 计算要跳过的文档数量
    skip = (page - 1) * per_page
    
    # 获取总文档数
    total = Post.objects.count()
    
    # 获取当前页的文档，先按置顶状态排序，再按更新时间排序，最后按创建时间排序
    posts = Post.objects.order_by('-is_pinned', '-updated_at', '-created_at').skip(skip).limit(per_page)
    
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
        current_time = get_beijing_time()
        
        # 处理文章内容
        post = Post(
            title=request.form.get('title'),
            content=request.form.get('content'),
            category=request.form.get('category'),
            is_visible=bool(request.form.get('is_visible')),
            updated_at=current_time
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
        post = Post.objects.get_or_404(id=post_id)
        
        if request.method == 'POST':
            has_changes = False
            
            # 检查基本字段是否有修改
            if post.title != request.form.get('title'):
                has_changes = True
                post.title = request.form.get('title')
                
            if post.category != request.form.get('category'):
                has_changes = True
                post.category = request.form.get('category')
                
            if post.content != request.form.get('content'):
                has_changes = True
                post.content = request.form.get('content')
                
            is_visible = bool(request.form.get('is_visible'))
            if post.is_visible != is_visible:
                has_changes = True
                post.is_visible = is_visible
            
            # 处理新上传的附件
            files = request.files.getlist('attachments')
            for file in files:
                if file.filename:
                    file_info = save_file(file)
                    if file_info:
                        has_changes = True
                        if not post.attachments:
                            post.attachments = []
                        post.attachments.append(file_info)
            
            # 只有在有实际修改时才更新时间戳
            if has_changes:
                post.updated_at = get_beijing_time()  # 使用北京时间
                
            post.save()
            flash('文章已更新')
            return redirect(url_for('admin.dashboard'))
        
        return render_template('admin/edit_post.html', post=post)
        
    except Exception as e:
        current_app.logger.error(f"Edit post error: {str(e)}")
        flash('操作失败，请重试')
        return redirect(url_for('admin.dashboard'))

@admin.route('/post/<post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    try:
        post = Post.objects(id=post_id).first_or_404()
        
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
        return jsonify({'message': '文章及其附件已删除'})
    except Exception as e:
        current_app.logger.error(f"Delete post error: {str(e)}")
        return jsonify({'error': '删除失败，请重试'}), 500

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

@admin.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(old_password):
            flash('当前密码错误')
        elif new_password != confirm_password:
            flash('两次输入的新密码不一致')
        elif len(new_password) < 1:
            flash('新密码不能为空')
        else:
            current_user.set_password(new_password)
            current_user.save()
            flash('密码已更新')
            return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/change_password.html')

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
                    file_path = upload_folder / filename
                    if file_path.exists():
                        file_path.unlink()
                except OSError as e:
                    current_app.logger.error(f"File delete error: {str(e)}")
                
                # 从数据库中移除附件记录
                post.attachments.pop(i)
                post.updated_at = get_beijing_time()  # 使用北京时间
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
    
    post.is_pinned = is_pinned
    post.save()
    
    return '', 204 