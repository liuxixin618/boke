# -*- coding: utf-8 -*-
"""
后台管理路由模块
包含所有管理员相关的路由处理函数，如登录、文章管理、网站设置等
"""

import os
from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
    send_from_directory,
    current_app,
    send_file,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from . import admin
from ..models import (
    Admin,
    Post,
    SiteConfig,
    get_utc_time,
    convert_to_local_time,
    Message,
    IPRecord,
    Category,
    SiteShare,
)
from ..utils.security import sanitize_string, validate_object_id
import uuid
from pathlib import Path
from flask_wtf.csrf import validate_csrf
import glob
from app.utils.file import ensure_upload_folder, sanitize_filename, save_file


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
    posts = (
        Post.objects.order_by('-is_pinned', '-updated_at', '-created_at')
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    # 创建分页对象
    class Pagination:
        def __init__(self, page, per_page, total):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.items = []
            self.pages = (total + per_page - 1) // per_page

            # 转换时间为本地时间
            for post in posts:
                post.created_at = convert_to_local_time(post.created_at)
                post.updated_at = convert_to_local_time(post.updated_at)
                self.items.append(post)

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
                if (
                    num <= left_edge
                    or (num > self.page - left_current - 1 and num < self.page + right_current)
                    or num > self.pages - right_edge
                ):
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    pagination = Pagination(page, per_page, total)
    return render_template('admin/dashboard.html', posts=pagination)


@admin.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    """创建新文章"""
    categories = Category.objects.order_by('-created_at')
    if request.method == 'POST':
        title = sanitize_string(request.form.get('title'))
        content = sanitize_string(request.form.get('content'))
        category_ids = request.form.getlist('categories')
        selected_categories = Category.objects(id__in=category_ids)
        content_type = request.form.get('content_type', 'html')
        is_markdown = content_type == 'markdown'
        md_file_path = None
        # 处理Markdown文件
        if is_markdown:
            md_file = request.files.get('md_file')
            if md_file and md_file.filename:
                # 文件类型校验
                if not md_file.filename.lower().endswith('.md'):
                    flash('只允许上传.md类型的Markdown文件')
                    return render_template('admin/edit_post.html', categories=categories)
                filename = secure_filename(md_file.filename)
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                md_file_path = os.path.join(upload_folder, filename)
                md_file.save(md_file_path)
            else:
                flash('请上传Markdown文件')
                return render_template('admin/edit_post.html', categories=categories)
        if not title or (not content and not is_markdown):
            current_app.logger.warning("[日志] 创建文章失败：标题或内容为空")
            flash('标题和内容不能为空')
            return render_template('admin/edit_post.html', categories=categories)
        post = Post(
            title=title,
            content=content if not is_markdown else '',
            categories=list(selected_categories),
            is_visible=True,
            updated_at=get_utc_time(),
            is_markdown=is_markdown,
            md_file_path=md_file_path,
        )
        files = request.files.getlist('attachments')
        current_app.logger.info(f"[日志] 处理文章附件，共 {len(files)} 个文件")
        attachments = []
        for file in files:
            current_app.logger.info(f"[日志] 处理附件: {file.filename}")
            file_info = save_file(file)
            if file_info:
                attachments.append(file_info)
                current_app.logger.info(f"[日志] 附件保存成功: {file_info}")
        if attachments:
            post.attachments = attachments
        post.save()
        current_app.logger.info(f"[日志] 文章创建成功，ID: {post.id}")
        flash('文章已创建')
        return redirect(url_for('admin.dashboard'))
    current_app.logger.info("[日志] 进入新建文章页面")
    return render_template('admin/edit_post.html', categories=categories)


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
        current_app.logger.info(f"[日志] 开始编辑文章，ID: {post_id}")
        post = Post.objects.get_or_404(id=validate_object_id(post_id))
        categories = Category.objects.order_by('-created_at')
        current_app.logger.info(f"[日志] 找到文章: {post.title}")

        if request.method == 'POST':
            has_changes = False

            # 清理并验证输入
            title = sanitize_string(request.form.get('title'))
            content = sanitize_string(request.form.get('content'))
            category_ids = request.form.getlist('categories')
            selected_categories = Category.objects(id__in=category_ids)
            content_type = request.form.get('content_type', 'html')
            is_markdown = content_type == 'markdown'
            md_file_path = post.md_file_path

            # 处理Markdown文件
            if is_markdown:
                md_file = request.files.get('md_file')
                if md_file and md_file.filename:
                    # 文件类型校验
                    if not md_file.filename.lower().endswith('.md'):
                        flash('只允许上传.md类型的Markdown文件')
                        return render_template(
                            'admin/edit_post.html', post=post, categories=categories
                        )
                    filename = secure_filename(md_file.filename)
                    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)
                    md_file_path_new = os.path.join(upload_folder, filename)
                    # 删除旧md文件
                    if post.md_file_path and os.path.exists(post.md_file_path):
                        try:
                            os.remove(post.md_file_path)
                        except Exception as e:
                            current_app.logger.warning(f"删除旧Markdown文件失败: {e}")
                    md_file.save(md_file_path_new)
                    md_file_path = md_file_path_new
                elif not md_file_path:
                    flash('请上传Markdown文件')
                    return render_template('admin/edit_post.html', post=post, categories=categories)

            if not title or (not content and not is_markdown):
                current_app.logger.warning("[日志] 更新文章失败：标题或内容为空")
                flash('标题和内容不能为空')
                return render_template('admin/edit_post.html', post=post, categories=categories)

            # 记录字段变更
            if post.title != title:
                current_app.logger.info(f"[日志] 文章标题更新: {post.title} -> {title}")
                has_changes = True
                post.title = title

            if set(post.categories) != set(selected_categories):
                current_app.logger.info(
                    f"[日志] 文章分类更新: {post.categories} -> {list(selected_categories)}"
                )
                has_changes = True
                post.categories = list(selected_categories)

            if post.content != content and not is_markdown:
                current_app.logger.info("[日志] 文章内容已更新")
                has_changes = True
                post.content = content

            if post.is_markdown != is_markdown:
                has_changes = True
                post.is_markdown = is_markdown

            if post.md_file_path != md_file_path:
                has_changes = True
                post.md_file_path = md_file_path

            # 处理新上传的附件
            files = request.files.getlist('attachments')
            current_app.logger.info(f"[日志] 处理新上传附件，共 {len(files)} 个文件")

            for file in files:
                if file.filename:
                    current_app.logger.info(f"[日志] 处理新附件: {file.filename}")
                    file_info = save_file(file)
                    if file_info:
                        current_app.logger.info(f"[日志] 新附件保存成功: {file_info}")
                        has_changes = True
                        if not post.attachments:
                            post.attachments = []
                        post.attachments.append(file_info)

            # 更新现有附件的文件大小
            if post.attachments:
                current_app.logger.info("[日志] 检查现有附件的文件大小")
                upload_folder = ensure_upload_folder()
                for attachment in post.attachments:
                    if 'file_size' not in attachment:
                        file_path = upload_folder / attachment['stored_filename']
                        if file_path.exists():
                            old_size = attachment.get('file_size', 'unknown')
                            attachment['file_size'] = os.path.getsize(str(file_path))
                            current_app.logger.info(
                                f"[日志] 更新附件 {attachment['filename']} 的文件大小: {old_size} -> {attachment['file_size']}"
                            )
                            has_changes = True

            if has_changes:
                post.updated_at = get_utc_time()
                post.save()
                current_app.logger.info(f"[日志] 文章更新成功，ID: {post_id}")
                flash('文章已更新')
            else:
                current_app.logger.info("[日志] 文章无变更")
            return redirect(url_for('admin.dashboard'))
        current_app.logger.info("[日志] 进入编辑文章页面")
        return render_template('admin/edit_post.html', post=post, categories=categories)

    except Exception as e:
        current_app.logger.error(f"[日志] 编辑文章出错，ID: {post_id}, 错误: {str(e)}")
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
    # CSRF校验
    token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
    try:
        validate_csrf(token)
    except Exception:
        return jsonify({'status': 'error', 'message': 'CSRF token missing or invalid'}), 400
    try:
        current_app.logger.info(f"开始删除文章，ID: {post_id}")
        current_app.logger.info(f"请求方法: {request.method}")
        current_app.logger.info(f"请求头: {dict(request.headers)}")
        current_app.logger.info(f"表单数据: {dict(request.form)}")

        post = Post.objects(id=validate_object_id(post_id)).first_or_404()
        current_app.logger.info(f"找到要删除的文章: {post.title}")

        # 删除所有附件文件
        if post.attachments:
            upload_folder = ensure_upload_folder()
            current_app.logger.info(f"开始删除附件文件，共 {len(post.attachments)} 个")

            for attachment in post.attachments:
                file_path = upload_folder / attachment['stored_filename']
                try:
                    if file_path.exists():
                        current_app.logger.info(f"删除附件文件: {attachment['filename']}")
                        file_path.unlink()
                except Exception as e:
                    current_app.logger.error(
                        f"删除附件文件失败: {attachment['filename']}, 错误: {str(e)}"
                    )

        # 删除文章记录
        post.delete()
        current_app.logger.info(f"文章删除成功，ID: {post_id}")
        return jsonify({'status': 'success'})

    except Exception as e:
        current_app.logger.error(
            f"删除文章失败，ID: {post_id}, 错误类型: {type(e)}, 错误信息: {str(e)}"
        )
        current_app.logger.error(f"错误详情: ", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """网站设置"""
    if request.method == 'POST':
        try:
            # 获取所有配置项
            configs = SiteConfig.objects

            # 先处理所有布尔类型的配置，将未出现在表单中的设置为 false
            bool_configs = configs(type='bool')
            for config in bool_configs:
                config.value = str(config.key in request.form).lower()
                config.save()

            # 处理其他类型的配置
            for key, value in request.form.items():
                if key == 'csrf_token':
                    continue

                config = configs(key=key).first()
                if config and config.type != 'bool':  # 跳过布尔类型，因为已经处理过了
                    if config.type == 'int':
                        config.value = str(int(value))
                    else:  # str
                        config.value = str(value)
                    config.save()

            current_app.logger.info('网站设置已更新')
            flash('设置已保存', 'success')
        except Exception as e:
            current_app.logger.error(f'保存设置失败: {str(e)}')
            flash('保存失败，请重试', 'danger')

    # 获取所有配置
    site_config = SiteConfig.get_configs()
    return render_template('admin/settings.html', site_config=site_config)


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
        return send_file(str(file_path), download_name=attachment['filename'], as_attachment=True)

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

        # 验证CSRF token
        csrf_token = request.form.get('csrf_token')
        if not csrf_token:
            current_app.logger.error("缺少CSRF token")
            return 'CSRF token missing', 400

        post = Post.objects.get_or_404(id=validate_object_id(post_id))
        current_app.logger.info(f"找到文章: {post.title}")

        # 查找并删除附件
        found = False
        for i, attachment in enumerate(post.attachments):
            if attachment['stored_filename'] == filename:
                try:
                    upload_folder = ensure_upload_folder()
                    file_path = upload_folder / filename
                    if file_path.exists():
                        current_app.logger.info(f"删除文件: {file_path}")
                        file_path.unlink()

                    current_app.logger.info(f"从数据库中移除附件记录: {attachment['filename']}")
                    post.attachments.pop(i)
                    post.updated_at = get_utc_time()
                    post.save()
                    found = True
                    break

                except OSError as e:
                    current_app.logger.error(f"删除文件失败: {str(e)}")
                    return jsonify({'error': '删除文件失败'}), 500

        if not found:
            current_app.logger.warning(f"附件不存在: {filename}")
            return jsonify({'error': '附件不存在'}), 404

        return jsonify({'status': 'success'})

    except Exception as e:
        current_app.logger.error(f"删除附件失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin.route('/posts/<post_id>/pin', methods=['POST'])
@login_required
def toggle_pin(post_id):
    """切换文章置顶状态"""
    # CSRF校验
    token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
    try:
        validate_csrf(token)
    except Exception:
        return jsonify({'success': False, 'message': 'CSRF token missing or invalid'}), 400
    try:
        post = Post.objects(id=post_id).first()
        if not post:
            return jsonify({'success': False, 'message': '文章不存在'})
        # 切换置顶状态
        is_pinned = not post.is_pinned
        Post.objects(id=post_id).update(is_pinned=is_pinned)
        return jsonify({'success': True, 'is_pinned': is_pinned})
    except Exception as e:
        current_app.logger.error(f'切换文章置顶状态失败: {str(e)}')
        return jsonify({'success': False, 'message': '操作失败，请重试'})


@admin.route('/posts/<post_id>/visibility', methods=['POST'])
@login_required
def toggle_visibility(post_id):
    """切换文章可见性"""
    # CSRF校验
    token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
    try:
        validate_csrf(token)
    except Exception:
        return jsonify({'success': False, 'message': 'CSRF token missing or invalid'}), 400
    try:
        post = Post.objects(id=post_id).first()
        if not post:
            return jsonify({'success': False, 'message': '文章不存在'})
        # 切换可见性状态
        is_visible = not post.is_visible
        Post.objects(id=post_id).update(is_visible=is_visible)
        return jsonify({'success': True, 'is_visible': is_visible})
    except Exception as e:
        current_app.logger.error(f'切换文章可见性失败: {str(e)}')
        return jsonify({'success': False, 'message': '操作失败，请重试'})


@admin.route('/admins')
@login_required
def admins():
    """管理员列表页面"""
    admins = Admin.objects.all()
    return render_template('admin/admins.html', admins=admins)


@admin.route('/admins/<admin_id>/username', methods=['POST'])
def change_username(admin_id):
    """修改管理员用户名"""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': '请先登录'}), 401

    # 验证ObjectId
    if not validate_object_id(admin_id):
        return jsonify({'success': False, 'message': '无效的管理员ID'}), 400

    # 获取新用户名
    new_username = request.form.get('username', '').strip()
    if not new_username:
        return jsonify({'success': False, 'message': '用户名不能为空'}), 400

    # 检查用户名是否已存在
    if Admin.objects(username=new_username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400

    # 更新用户名
    try:
        admin = Admin.objects(id=admin_id).first()
        if not admin:
            return jsonify({'success': False, 'message': '管理员不存在'}), 404

        admin.username = new_username
        admin.save()
        return jsonify({'success': True, 'message': '用户名修改成功'})
    except Exception as e:
        current_app.logger.error(f'修改用户名失败: {str(e)}')
        return jsonify({'success': False, 'message': '修改失败，请重试'}), 500


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


@admin.route('/messages')
@login_required
def messages():
    """留言管理页面"""
    page = request.args.get('page', 1, type=int)
    site_config = SiteConfig.get_message_configs()
    per_page = site_config['messages_per_page']

    pagination = Message.objects.order_by('-created_at').paginate(page=page, per_page=per_page)

    return render_template('admin/messages.html', pagination=pagination, show_ip=True)


@admin.route('/messages/<message_id>')
@login_required
def view_message(message_id):
    """查看留言详情"""
    message = Message.objects(id=message_id).first_or_404()
    ip_record = None
    if message.ip_address:
        ip_record = IPRecord.objects(ip_address=message.ip_address).first()

    return render_template(
        'admin/view_message.html', message=message, ip_record=ip_record, show_ip=True
    )


@admin.route('/messages/<message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """删除留言"""
    message = Message.objects(id=message_id).first_or_404()

    # 如果有附件，删除附件文件
    if message.attachment:
        try:
            file_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], message.attachment['stored_filename']
            )
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            current_app.logger.error(f'删除附件文件失败：{str(e)}')

    # 更新IP记录
    if message.ip_address:
        ip_record = IPRecord.objects(ip_address=message.ip_address).first()
        if ip_record:
            ip_record.message_count = max(0, ip_record.message_count - 1)
            if ip_record.message_count == 0 and not ip_record.is_blocked:
                ip_record.delete()
            else:
                ip_record.save()

    message.delete()
    return jsonify({'success': True})


@admin.route('/messages/<message_id>/public', methods=['POST'])
@login_required
def toggle_message_public(message_id):
    """切换留言公开状态"""
    message = Message.objects(id=message_id).first_or_404()

    if not message.allow_public:
        return jsonify({'success': False, 'message': '该留言不允许公开'})

    message.is_public = not message.is_public
    message.save()

    return jsonify({'success': True})


@admin.route('/ip/<ip_address>/block', methods=['POST'])
@login_required
def toggle_ip_block(ip_address):
    """切换IP限制状态"""
    ip_record = IPRecord.objects(ip_address=ip_address).first()

    if not ip_record:
        ip_record = IPRecord(ip_address=ip_address)

    ip_record.is_blocked = not ip_record.is_blocked
    ip_record.save()

    return jsonify({'success': True})


@admin.route('/ip_records')
@login_required
def ip_records():
    """IP管理页面"""
    page = request.args.get('page', 1, type=int)
    per_page = int(SiteConfig.get_config('messages_per_page', 20))  # 使用留言管理的每页显示数量

    # 按最后留言时间倒序排序
    pagination = IPRecord.objects.order_by('-last_message_at').paginate(
        page=page, per_page=per_page
    )

    return render_template('admin/ip_records.html', pagination=pagination)


@admin.route('/categories')
@login_required
def category_list():
    """分类列表"""
    categories = Category.objects.order_by('-created_at')
    return render_template('admin/category_list.html', categories=categories)


@admin.route('/category/new', methods=['GET', 'POST'])
@login_required
def category_new():
    """新增分类"""
    if request.method == 'POST':
        name = sanitize_string(request.form.get('name'))
        description = sanitize_string(request.form.get('description'))
        if not name:
            flash('分类名称不能为空')
            return render_template('admin/edit_category.html')
        if Category.objects(name=name).first():
            flash('分类名称已存在')
            return render_template('admin/edit_category.html')
        category = Category(name=name, description=description)
        category.save()
        flash('分类已创建')
        return redirect(url_for('admin.category_list'))
    return render_template('admin/edit_category.html')


@admin.route('/category/edit/<category_id>', methods=['GET', 'POST'])
@login_required
def category_edit(category_id):
    """编辑分类"""
    category = Category.objects(id=category_id).first_or_404()
    if request.method == 'POST':
        name = sanitize_string(request.form.get('name'))
        description = sanitize_string(request.form.get('description'))
        if not name:
            flash('分类名称不能为空')
            return render_template('admin/edit_category.html', category=category)
        if Category.objects(name=name, id__ne=category.id).first():
            flash('分类名称已存在')
            return render_template('admin/edit_category.html', category=category)
        category.name = name
        category.description = description
        category.save()
        flash('分类已更新')
        return redirect(url_for('admin.category_list'))
    return render_template('admin/edit_category.html', category=category)


@admin.route('/category/delete/<category_id>', methods=['POST'])
@login_required
def category_delete(category_id):
    """删除分类"""
    category = Category.objects(id=category_id).first_or_404()
    # 检查是否有文章引用该分类
    if Post.objects(categories=category).first():
        flash('有文章引用该分类，无法删除')
        return redirect(url_for('admin.category_list'))
    category.delete()
    flash('分类已删除')
    return redirect(url_for('admin.category_list'))


@admin.route('/logs')
@login_required
def view_logs():
    """后台日志查看页面"""
    import os

    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'logs', 'app.log')
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-500:]
            log_content = ''.join(lines)
    except Exception as e:
        log_content = f'无法读取日志文件: {e}'
    return render_template('admin/logs.html', log_content=log_content)


@admin.route('/nginx_logs')
@login_required
def view_nginx_logs():
    """Nginx 日志查看页面"""
    access_log_path = '/var/www/blog/logs/access.log'
    error_log_path = '/var/www/blog/logs/error.log'
    try:
        with open(access_log_path, 'r', encoding='utf-8', errors='ignore') as f:
            access_lines = f.readlines()[-500:]
            access_content = ''.join(access_lines)
    except Exception as e:
        access_content = f'无法读取 access.log: {e}'
    try:
        with open(error_log_path, 'r', encoding='utf-8', errors='ignore') as f:
            error_lines = f.readlines()[-500:]
            error_content = ''.join(error_lines)
    except Exception as e:
        error_content = f'无法读取 error.log: {e}'
    return render_template(
        'admin/nginx_logs.html', access_content=access_content, error_content=error_content
    )


@admin.route('/siteshare')
@login_required
def siteshare_list():
    sites = SiteShare.objects.order_by('-is_pinned', '-created_at')
    return render_template('admin/siteshare_list.html', sites=sites)


@admin.route('/siteshare/new', methods=['GET', 'POST'])
@login_required
def siteshare_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        url = request.form.get('url', '').strip()
        is_visible = bool(request.form.get('is_visible'))
        is_pinned = bool(request.form.get('is_pinned'))
        if not name or not url:
            flash('名称和链接不能为空', 'danger')
            return render_template('admin/edit_siteshare.html', site=None)
        site = SiteShare(name=name, url=url, is_visible=is_visible, is_pinned=is_pinned)
        site.save()
        flash('好站已添加', 'success')
        return redirect(url_for('admin.siteshare_list'))
    return render_template('admin/edit_siteshare.html', site=None)


@admin.route('/siteshare/edit/<site_id>', methods=['GET', 'POST'])
@login_required
def siteshare_edit(site_id):
    site = SiteShare.objects(id=site_id).first_or_404()
    if request.method == 'POST':
        site.name = request.form.get('name', '').strip()
        site.url = request.form.get('url', '').strip()
        site.is_visible = bool(request.form.get('is_visible'))
        site.is_pinned = bool(request.form.get('is_pinned'))
        if not site.name or not site.url:
            flash('名称和链接不能为空', 'danger')
            return render_template('admin/edit_siteshare.html', site=site)
        site.save()
        flash('好站已更新', 'success')
        return redirect(url_for('admin.siteshare_list'))
    return render_template('admin/edit_siteshare.html', site=site)


@admin.route('/siteshare/delete/<site_id>', methods=['POST'])
@login_required
def siteshare_delete(site_id):
    site = SiteShare.objects(id=site_id).first_or_404()
    site.delete()
    flash('好站已删除', 'success')
    return redirect(url_for('admin.siteshare_list'))


@admin.route('/siteshare/toggle_pin/<site_id>', methods=['POST'])
@login_required
def siteshare_toggle_pin(site_id):
    site = SiteShare.objects(id=site_id).first_or_404()
    site.is_pinned = not site.is_pinned
    site.save()
    return redirect(url_for('admin.siteshare_list'))


@admin.route('/siteshare/toggle_visible/<site_id>', methods=['POST'])
@login_required
def siteshare_toggle_visible(site_id):
    site = SiteShare.objects(id=site_id).first_or_404()
    site.is_visible = not site.is_visible
    site.save()
    return redirect(url_for('admin.siteshare_list'))


@admin.route('/logs/clear', methods=['POST'])
@login_required
def clear_logs():
    log_dir = current_app.config.get('LOG_DIR') or os.path.join(
        os.path.dirname(__file__), '../../logs'
    )
    log_files = glob.glob(os.path.join(log_dir, '*.log*'))
    deleted = 0
    for f in log_files:
        try:
            os.remove(f)
            deleted += 1
        except Exception as e:
            current_app.logger.warning(f'清理日志文件失败: {f}, 错误: {e}')
    flash(f'已清理{deleted}个日志文件', 'success')
    return redirect(url_for('admin.view_logs'))
