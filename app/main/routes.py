from flask import render_template, jsonify, request
from . import main
from ..models import Post, SiteConfig

@main.route('/')
def index():
    page = int(request.args.get('page', 1))
    per_page = SiteConfig.get_config('posts_per_page', 10)
    preview_length = SiteConfig.get_config('content_preview_length', 50)
    
    posts = Post.objects(is_visible=True).paginate(page=page, per_page=per_page)
    return render_template('main/index.html', posts=posts, preview_length=preview_length)

@main.route('/post/<post_id>')
def get_post(post_id):
    post = Post.objects(id=post_id, is_visible=True).first_or_404()
    return jsonify({
        'title': post.title,
        'content': post.content,
        'created_at': post.created_at.strftime('%Y-%m-%d %H:%M')
    }) 