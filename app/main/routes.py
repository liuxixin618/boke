from flask import render_template, redirect, url_for, flash, request, send_file, current_app
from . import main
from ..models import Post, SiteConfig
from ..utils.security import sanitize_string, sanitize_mongo_query, validate_object_id, escape_regex_pattern
import os
from pathlib import Path

@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = int(SiteConfig.get_config('posts_per_page', 10))
    search_query = sanitize_string(request.args.get('search', '').strip())
    
    # 构建查询条件
    query = {'is_visible': True}
    if search_query:
        # 使用转义后的正则模式进行模糊匹配
        pattern = escape_regex_pattern(search_query)
        query['title'] = {'$regex': pattern, '$options': 'i'}
    
    # 使用清理后的查询条件
    safe_query = sanitize_mongo_query(query)
    posts = Post.objects(**safe_query).order_by('-is_pinned', '-updated_at', '-created_at').paginate(page=page, per_page=per_page)
    
    # 获取所有网站配置
    site_configs = {}
    for config in SiteConfig.objects:
        site_configs[config.key] = config.value
    
    return render_template('main/index.html', 
                         posts=posts,
                         site_config=site_configs)

@main.route('/goods')
def goods():
    return render_template('main/goods.html')

@main.route('/about')
def about():
    return render_template('main/about.html')

@main.route('/download/<filename>')
def download_attachment(filename):
    try:
        # 清理文件名
        safe_filename = sanitize_string(filename)
        if not safe_filename:
            flash('无效的文件名', 'error')
            return redirect(url_for('main.index'))
            
        # 查找包含此附件的文章
        query = {
            'attachments__stored_filename': safe_filename,
            'is_visible': True
        }
        safe_query = sanitize_mongo_query(query)
        post = Post.objects(**safe_query).first()
        
        if not post:
            flash('文件不存在或已被删除', 'error')
            return redirect(url_for('main.index'))
            
        # 获取原始文件名
        attachment = next((a for a in post.attachments if a['stored_filename'] == safe_filename), None)
        if not attachment:
            flash('文件不存在或已被删除', 'error')
            return redirect(url_for('main.index'))
            
        # 使用项目根目录下的 uploads 文件夹
        base_dir = Path(current_app.root_path).parent
        upload_folder = base_dir / 'uploads'
        file_path = upload_folder / safe_filename
        
        if file_path.exists():
            return send_file(
                str(file_path),
                download_name=attachment['filename'],
                as_attachment=True
            )
        else:
            flash('文件不存在或已被删除', 'error')
            return redirect(url_for('main.index'))
    except Exception as e:
        current_app.logger.error(f'下载文件时发生错误: {str(e)}')
        flash('下载文件时发生错误', 'error')
        return redirect(url_for('main.index')) 