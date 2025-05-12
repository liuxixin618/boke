"""
缓存装饰器模块
用于提供数据库查询结果的缓存功能
"""

from functools import wraps
from flask import current_app, request
import time
import json
from ..models import Cache


def cache_for(duration=300):
    """
    数据库静态缓存装饰器

    Args:
        duration (int): 缓存时间，单位秒，默认5分钟

    Returns:
        function: 装饰器函数
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键，包含query参数
            query_string = "&".join(f"{k}={v}" for k, v in sorted(request.args.items()))
            cache_key = f"{f.__name__}:{str(args)}:{str(kwargs)}:{query_string}"

            try:
                # 查找缓存
                cache = Cache.objects(key=cache_key).first()

                # 如果找到缓存且未过期
                if cache and time.time() - cache.created_at.timestamp() < duration:
                    current_app.logger.info(f"从缓存获取数据: {cache_key}")
                    return json.loads(cache.value)

                # 执行原函数
                result = f(*args, **kwargs)

                # 更新或创建缓存
                cache_data = {'key': cache_key, 'value': json.dumps(result)}

                if cache:
                    Cache.objects(key=cache_key).update_one(**cache_data, upsert=True)
                else:
                    Cache(**cache_data).save()

                current_app.logger.info(f"更新缓存: {cache_key}")
                return result

            except Exception as e:
                current_app.logger.error(f"缓存操作失败: {str(e)}")
                # 如果缓存操作失败，直接返回原函数结果
                return f(*args, **kwargs)

        return decorated_function

    return decorator
