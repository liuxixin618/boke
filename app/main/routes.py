# -*- coding: utf-8 -*-
"""
主路由模块
包含所有前台页面的路由处理函数，如首页、文章详情页等
"""

from flask import render_template, redirect, url_for, flash, request, send_file, current_app, send_from_directory, abort
from . import main
from ..models import Post, SiteConfig, Message, IPRecord
from ..utils.security import sanitize_string, sanitize_mongo_query, validate_object_id, escape_regex_pattern
from ..utils.cache import cache_for
import os
from pathlib import Path
import json
from flask_login import current_user
import uuid
from werkzeug.utils import secure_filename

def ensure_upload_folder():
    """确保上传文件夹存在并返回正确的路径"""
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

def save_file(file):
    """
    保存上传的文件
    
    Args:
        file: 文件对象
        
    Returns:
        dict: 包含保存结果的字典
    """
    try:
        if not file:
            return {'success': False, 'message': '没有文件'}
            
        # 获取原始文件名和扩展名
        original_filename = file.filename
        filename = secure_filename(original_filename)
        if not filename:
            return {'success': False, 'message': '无效的文件名'}
            
        # 生成唯一的文件名
        ext = os.path.splitext(filename)[1]
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        
        # 确保上传目录存在
        upload_folder = ensure_upload_folder()
        
        # 保存文件
        file_path = upload_folder / stored_filename
        file.save(str(file_path))
        
        # 获取文件大小（KB）
        file_size = round(os.path.getsize(str(file_path)) / 1024)
        
        return {
            'success': True,
            'file_info': {
                'filename': original_filename,  # 使用原始文件名
                'stored_filename': stored_filename,
                'file_type': file.content_type,
                'file_size': file_size
            }
        }
    except Exception as e:
        current_app.logger.error(f"保存文件失败: {str(e)}")
        return {'success': False, 'message': str(e)}

@main.route('/')
@cache_for(duration=300)  # 5分钟缓存
def index():
    """首页路由"""
    current_app.logger.info("访问首页")
    page = request.args.get('page', 1, type=int)
    per_page = int(SiteConfig.get_config('posts_per_page', 10))
    search_query = sanitize_string(request.args.get('search', '').strip())
    
    # 构建查询条件
    query = {'is_visible': True}
    if search_query:
        current_app.logger.info(f"搜索文章，关键词: {search_query}")
        pattern = escape_regex_pattern(search_query)
        query['title'] = {'$regex': pattern, '$options': 'i'}
    
    # 使用清理后的查询条件
    safe_query = sanitize_mongo_query(query)
    current_app.logger.info(f"查询文章列表，页码: {page}, 每页数量: {per_page}")
    posts = Post.objects(**safe_query).order_by('-is_pinned', '-updated_at', '-created_at').paginate(page=page, per_page=per_page)
    
    # 获取所有网站配置
    current_app.logger.info("获取网站配置")
    site_configs = {}
    for config in SiteConfig.objects:
        site_configs[config.key] = config.value
    
    return render_template('main/index.html', 
                         posts=posts,
                         site_config=site_configs)

@main.route('/goods')
@cache_for(duration=600)  # 10分钟缓存
def goods():
    """好物分享页面"""
    current_app.logger.info("访问好物分享页面")
    return render_template('main/goods.html')

@main.route('/about')
@cache_for(duration=600)  # 10分钟缓存
def about():
    """关于作者页面"""
    current_app.logger.info("访问关于作者页面")
    return render_template('main/about.html')

@main.route('/download/<filename>')
def download_attachment(filename):
    """下载附件"""
    try:
        current_app.logger.info(f"开始下载附件: {filename}")
        
        # 清理文件名
        safe_filename = sanitize_string(filename)
        if not safe_filename:
            current_app.logger.warning(f"无效的文件名: {filename}")
            flash('无效的文件名', 'error')
            return redirect(url_for('main.index'))
            
        # 查找包含此附件的文章
        query = {
            'attachments__stored_filename': safe_filename,
            'is_visible': True
        }
        safe_query = sanitize_mongo_query(query)
        current_app.logger.info(f"查找包含附件的文章: {safe_filename}")
        post = Post.objects(**safe_query).first()
        
        if not post:
            current_app.logger.warning(f"未找到包含附件的文章: {safe_filename}")
            flash('文件不存在或已被删除', 'error')
            return redirect(url_for('main.index'))
            
        # 获取原始文件名
        attachment = next((a for a in post.attachments if a['stored_filename'] == safe_filename), None)
        if not attachment:
            current_app.logger.warning(f"文章中未找到附件记录: {safe_filename}")
            flash('文件不存在或已被删除', 'error')
            return redirect(url_for('main.index'))
            
        # 使用项目根目录下的 uploads 文件夹
        base_dir = Path(current_app.root_path).parent
        upload_folder = base_dir / 'uploads'
        file_path = upload_folder / safe_filename
        
        if file_path.exists():
            current_app.logger.info(f"开始发送文件: {attachment['filename']}")
            return send_file(
                str(file_path),
                download_name=attachment['filename'],
                as_attachment=True
            )
        else:
            current_app.logger.warning(f"文件不存在: {file_path}")
            flash('文件不存在或已被删除', 'error')
            return redirect(url_for('main.index'))
    except Exception as e:
        current_app.logger.error(f"下载文件时发生错误: {str(e)}")
        flash('下载文件时发生错误', 'error')
        return redirect(url_for('main.index')) 

@main.route('/message')
def message():
    """留言页面"""
    # 获取所有网站配置
    site_config = SiteConfig.get_configs()
    # 添加留言相关的配置
    message_config = SiteConfig.get_message_configs()
    site_config.update(message_config)
    return render_template('main/message.html', site_config=site_config)

@main.route('/message/preview', methods=['POST'])
def preview_message():
    """预览留言"""
    content = request.form.get('content', '').strip()
    contact = request.form.get('contact', '').strip()
    allow_public = request.form.get('allow_public', 'false') == 'true'
    
    # 检查内容长度
    site_config = SiteConfig.get_message_configs()
    if len(content) > site_config['max_message_length']:
        flash('留言内容超过最大长度限制', 'danger')
        return redirect(url_for('main.message'))
    
    # 处理附件
    attachment = None
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            result = save_file(file)
            if result['success']:
                attachment = result['file_info']
            else:
                flash(f'附件上传失败：{result["message"]}', 'danger')
                return redirect(url_for('main.message'))
    
    message = {
        'content': content,
        'contact': contact,
        'allow_public': allow_public,
        'attachment': attachment
    }
    
    return render_template('main/preview_message.html', message=message)

@main.route('/message/submit', methods=['POST'])
def submit_message():
    """提交留言"""
    content = request.form.get('content', '').strip()
    contact = request.form.get('contact', '').strip()
    allow_public = request.form.get('allow_public', 'false') == 'true'
    is_public = False
    attachment_json = request.form.get('attachment')
    
    # 检查内容长度
    site_config = SiteConfig.get_message_configs()
    if len(content) > site_config['max_message_length']:
        flash('留言内容超过最大长度限制', 'danger')
        return redirect(url_for('main.message'))
    
    # 获取IP地址
    def get_real_ip():
        """获取真实IP地址，优先返回IPv4地址"""
        def is_valid_ipv4(ip):
            """检查是否为有效的IPv4地址"""
            if not ip:
                return False
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            try:
                return all(0 <= int(part) <= 255 for part in parts)
            except (ValueError, TypeError):
                return False

        def get_first_ipv4(ips):
            """从IP地址列表中获取第一个IPv4地址"""
            if not ips:
                return None
            ips = [ip.strip() for ip in ips.split(',')]
            for ip in ips:
                if is_valid_ipv4(ip):
                    return ip
            return ips[0]  # 如果没有IPv4地址，返回第一个地址

        # 优先从 X-Forwarded-For 获取
        if 'X-Forwarded-For' in request.headers:
            ip = get_first_ipv4(request.headers['X-Forwarded-For'])
            if ip:
                return ip

        # 其次从 X-Real-IP 获取
        if 'X-Real-IP' in request.headers:
            ip = request.headers['X-Real-IP'].strip()
            if is_valid_ipv4(ip):
                return ip

        # 最后使用远程地址
        remote_addr = request.remote_addr
        if remote_addr and is_valid_ipv4(remote_addr):
            return remote_addr
        
        # 如果都不是有效的IPv4地址，返回原始remote_addr
        return request.remote_addr

    # 获取IP地址
    ip_address = get_real_ip()
    
    # 检查IP是否被限制
    ip_record = IPRecord.objects(ip_address=ip_address).first()
    if ip_record and ip_record.is_blocked:
        flash('网站作者不允许你说话，找他问问为什么吧', 'danger')
        return redirect(url_for('main.message'))
    
    # 检查留言数量限制
    if ip_record:
        if ip_record.message_count >= site_config['max_messages_per_ip']:
            flash(f'每个人最多只能发送{site_config["max_messages_per_ip"]}条留言', 'danger')
            return redirect(url_for('main.message'))
    else:
        ip_record = IPRecord(ip_address=ip_address)
    
    # 创建留言
    message = Message(
        content=content,
        contact=contact,
        allow_public=allow_public,
        ip_address=ip_address,
        is_public=is_public
    )
    
    # 处理附件
    if attachment_json:
        try:
            # 记录接收到的附件信息用于调试
            current_app.logger.debug(f"接收到的附件信息: {attachment_json}")
            
            # 如果附件信息是字符串，尝试解析为 JSON
            if isinstance(attachment_json, str):
                attachment = json.loads(attachment_json)
            else:
                attachment = attachment_json
                
            # 验证附件信息的完整性
            required_fields = ['filename', 'stored_filename', 'file_type', 'file_size']
            if all(field in attachment for field in required_fields):
                message.attachment = attachment
            else:
                raise ValueError("附件信息不完整")
                
        except (json.JSONDecodeError, ValueError) as e:
            current_app.logger.error(f"处理附件信息时出错: {str(e)}")
            flash('附件信息无效', 'danger')
            return redirect(url_for('main.message'))
    
    message.save()
    
    # 更新IP记录
    ip_record.message_count += 1
    ip_record.last_message_at = message.created_at
    ip_record.save()
    
    flash('留言提交成功', 'success')
    return redirect(url_for('main.message'))

@main.route('/message/<message_id>/attachment')
def download_message_attachment(message_id):
    """下载留言附件"""
    message = Message.objects(id=message_id).first_or_404()
    
    if not message.attachment:
        abort(404)
    
    # 检查是否有权限下载
    # 如果留言未公开，只有管理员可以下载
    if not message.is_public and not current_user.is_authenticated:
        abort(403)
    
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        message.attachment['stored_filename'],
        as_attachment=True,
        download_name=message.attachment['filename']
    ) 

@main.route('/post/<post_id>')
@cache_for(duration=300)  # 5分钟缓存
def post(post_id):
    """文章详情页"""
    # 验证并清理 post_id
    post_id = validate_object_id(post_id)
    if not post_id:
        flash('无效的文章ID', 'danger')
        return redirect(url_for('main.index'))
    
    # 查询文章
    post = Post.objects(id=post_id, is_visible=True).first_or_404()
    
    return render_template('main/post.html', post=post) 

@main.route('/messages')
def messages_show():
    """留言墙页面"""
    # 获取最多20条公开的留言，使用 MongoDB 的聚合管理实现随机排序
    pipeline = [
        {'$match': {'is_public': True}},  # 筛选公开留言
        {'$sample': {'size': 20}}  # 随机选择20条
    ]
    messages = list(Message.objects.aggregate(pipeline))
    
    # 转换为字典列表，以便JSON序列化
    messages_list = [{
        'content': msg['content'],
        'contact': msg.get('contact', '匿名')
    } for msg in messages]
    
    return render_template('main/messages_show.html', messages=messages_list) 