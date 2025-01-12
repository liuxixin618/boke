from flask import render_template, redirect, url_for, flash, request, send_file, current_app
from . import main
from ..models import Post, SiteConfig
import os

@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = int(SiteConfig.get_config('posts_per_page', 10))
    
    # 获取可见的文章，按置顶、更新时间和创建时间排序
    posts = Post.objects(is_visible=True).order_by('-is_pinned', '-updated_at', '-created_at').paginate(page=page, per_page=per_page)
    
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
        # 查找包含此附件的文章
        post = Post.objects(attachments__stored_filename=filename, is_visible=True).first()
        if not post:
            flash('文件不存在或已被删除', 'error')
            return redirect(url_for('main.index'))
            
        # 获取原始文件名
        attachment = next((a for a in post.attachments if a['stored_filename'] == filename), None)
        if not attachment:
            flash('文件不存在或已被删除', 'error')
            return redirect(url_for('main.index'))
            
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, 
                           download_name=attachment['filename'],
                           as_attachment=True)
        else:
            flash('文件不存在或已被删除', 'error')
            return redirect(url_for('main.index'))
    except Exception as e:
        current_app.logger.error(f'下载文件时发生错误: {str(e)}')
        flash('下载文件时发生错误', 'error')
        return redirect(url_for('main.index')) 