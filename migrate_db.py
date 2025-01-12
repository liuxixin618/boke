from app import create_app
from app.models import Post, db
from datetime import datetime, timezone
import json
import os
from flask_mongoengine import MongoEngine

def backup_collection():
    """备份当前文章数据"""
    try:
        # 创建备份目录
        backup_dir = 'backup'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # 生成备份文件名，包含时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'posts_backup_{timestamp}.json')
        
        # 获取所有文章数据
        posts = Post.objects.all()
        
        # 将数据转换为可序列化的格式
        backup_data = []
        for post in posts:
            post_data = {
                'id': str(post.id),
                'title': post.title,
                'content': post.content,
                'category': post.category,
                'created_at': post.created_at.isoformat(),
                'updated_at': post.updated_at.isoformat() if post.updated_at else None,
                'is_visible': post.is_visible
            }
            backup_data.append(post_data)
        
        # 保存备份文件
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f'成功备份 {len(backup_data)} 篇文章到文件: {backup_file}')
        return True
    except Exception as e:
        print(f'备份失败: {str(e)}')
        return False

def migrate_data():
    """迁移数据：添加 is_pinned 字段"""
    try:
        # 更新所有文章
        result = Post.objects().update(
            set__is_pinned=False,  # 默认都不置顶
            upsert=False,  # 不创建新文档
            multi=True    # 更新多个文档
        )
        print(f'成功更新 {result} 篇文章')
        return True
    except Exception as e:
        print(f'迁移失败: {str(e)}')
        return False

def verify_migration():
    """验证迁移结果"""
    try:
        posts = Post.objects.all()
        print(f'\n数据库中共有 {len(posts)} 篇文章：')
        
        # 检查是否所有文章都有 is_pinned 字段
        missing_field = False
        for post in posts:
            if not hasattr(post, 'is_pinned'):
                print(f'警告: 文章 "{post.title}" (ID: {post.id}) 缺少 is_pinned 字段')
                missing_field = True
            
            # 打印文章信息
            status = []
            if getattr(post, 'is_pinned', False):
                status.append('置顶')
            if post.is_visible:
                status.append('可见')
            status_str = '(' + ', '.join(status) + ')' if status else ''
            
            print(f'- {post.title} {status_str}')
            print(f'  ID: {post.id}')
            print(f'  创建于: {post.created_at}')
            if post.updated_at:
                print(f'  更新于: {post.updated_at}')
            print()
        
        return not missing_field
    except Exception as e:
        print(f'验证失败: {str(e)}')
        return False

def migrate_posts_updated_at():
    """更新所有没有 updated_at 的文章记录"""
    print("开始迁移文章的 updated_at 字段...")
    
    # 获取所有 updated_at 为空的文章
    posts = Post.objects(updated_at=None)
    count = 0
    
    for post in posts:
        post.updated_at = post.created_at
        post.save()
        count += 1
    
    print(f"迁移完成，共更新了 {count} 篇文章")

def main():
    """主函数"""
    app = create_app()
    
    with app.app_context():
        print('开始数据迁移...')
        
        # 第一步：备份数据
        print('\n1. 备份当前数据...')
        if not backup_collection():
            print('备份失败，终止迁移')
            return
        
        # 第二步：迁移数据
        print('\n2. 执行数据迁移...')
        if not migrate_data():
            print('迁移失败，请检查备份文件并手动恢复')
            return
        
        # 第三步：验证迁移
        print('\n3. 验证迁移结果...')
        if not verify_migration():
            print('验证失败，请检查备份文件并手动恢复')
            return
        
        print('\n数据迁移完成！')

if __name__ == '__main__':
    main() 