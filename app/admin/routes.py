from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import admin
from ..models import User, Post, SiteConfig
from datetime import datetime, timezone

@admin.route('/')
@login_required
def index():
    return redirect(url_for('admin.dashboard'))

@admin.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.objects(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('Invalid username or password')
    return render_template('admin/login.html')

@admin.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@admin.route('/dashboard')
@login_required
def dashboard():
    # 使用模型中定义的默认排序
    posts = Post.objects.all()
    return render_template('admin/dashboard.html', posts=posts)

@admin.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        post = Post(
            title=request.form.get('title'),
            content=request.form.get('content'),
            category=request.form.get('category'),
            is_visible=bool(request.form.get('is_visible'))
        )
        post.save()
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/edit_post.html')

@admin.route('/post/edit/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.objects(id=post_id).first_or_404()
    if request.method == 'POST':
        new_title = request.form.get('title')
        new_content = request.form.get('content')
        new_category = request.form.get('category')
        new_is_visible = bool(request.form.get('is_visible'))
        
        # 检查是否有实际修改
        if (post.title != new_title or 
            post.content != new_content or 
            post.category != new_category or 
            post.is_visible != new_is_visible):
            
            post.title = new_title
            post.content = new_content
            post.category = new_category
            post.is_visible = new_is_visible
            post.updated_at = datetime.now(timezone.utc)
            post.save()
            flash('文章已更新')
        else:
            flash('文章内容未发生变化')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/edit_post.html', post=post)

@admin.route('/post/delete/<post_id>')
@login_required
def delete_post(post_id):
    post = Post.objects(id=post_id).first_or_404()
    post.delete()
    return redirect(url_for('admin.dashboard'))

@admin.route('/post/toggle_pin/<post_id>')
@login_required
def toggle_pin(post_id):
    post = Post.objects(id=post_id).first_or_404()
    
    if post.is_pinned:
        # 取消置顶
        post.is_pinned = False
        post.save()
        flash('文章已取消置顶')
    else:
        # 先取消其他文章的置顶状态
        Post.objects(is_pinned=True).update(is_pinned=False)
        # 设置当前文章为置顶
        post.is_pinned = True
        post.save()
        flash('文章已置顶')
    
    return redirect(url_for('admin.dashboard'))

@admin.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # 更新网站配置
        for key in request.form:
            if key.startswith('config_'):
                config_key = key[7:]  # 移除 'config_' 前缀
                config = SiteConfig.objects(key=config_key).first()
                if config:
                    value = request.form[key].strip()
                    if config.type == 'int':
                        try:
                            config.value = int(value)
                        except ValueError:
                            flash(f'配置项 {config.description} 必须是数字')
                            return redirect(url_for('admin.settings'))
                    else:  # str 或 url 类型
                        config.value = value
                    config.save()
        flash('配置已更新')
        return redirect(url_for('admin.settings'))
    
    configs = SiteConfig.objects.all()
    return render_template('admin/settings.html', configs=configs)

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