# -*- coding: utf-8 -*-
"""
主路由模块
包含所有前台页面的路由处理函数，如首页、文章详情页等
"""

from flask import render_template, redirect, url_for, flash, request, send_file, current_app
from . import main
from ..models import Post, SiteConfig
from ..utils.security import sanitize_string, sanitize_mongo_query, validate_object_id, escape_regex_pattern
import os
from pathlib import Path

@main.route('/')
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
def goods():
    """好物分享页面"""
    current_app.logger.info("访问好物分享页面")
    return render_template('main/goods.html')

@main.route('/about')
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