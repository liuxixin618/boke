import re
from typing import Any, Dict
from bson import ObjectId
from flask import abort


def sanitize_string(value: str) -> str:
    """清理字符串输入"""
    if not isinstance(value, str):
        return ""
    # 移除特殊字符
    return re.sub(r'[<>${}]', '', value.strip())


def sanitize_mongo_query(query: Dict[str, Any]) -> Dict[str, Any]:
    """清理 MongoDB 查询参数"""
    sanitized = {}
    for key, value in query.items():
        # 检查键名是否安全
        if not re.match(r'^[a-zA-Z0-9_]+$', key):
            continue

        # 处理不同类型的值
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, (int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, dict):
            # 处理嵌套的查询操作符
            if all(k.startswith('$') for k in value.keys()):
                sanitized[key] = sanitize_mongo_operator(value)
        elif isinstance(value, ObjectId):
            sanitized[key] = value

    return sanitized


def sanitize_mongo_operator(operator_dict: Dict[str, Any]) -> Dict[str, Any]:
    """清理 MongoDB 操作符"""
    safe_operators = {
        '$eq',
        '$gt',
        '$gte',
        '$lt',
        '$lte',
        '$ne',
        '$in',
        '$nin',
        '$exists',
        '$type',
        '$regex',
        '$and',
        '$or',
        '$not',
        '$nor',
        '$all',
        '$elemMatch',
        '$size',
        '$text',
        '$search',
    }

    sanitized = {}
    for op, value in operator_dict.items():
        if op not in safe_operators:
            continue

        if isinstance(value, str):
            sanitized[op] = sanitize_string(value)
        elif isinstance(value, (int, float, bool, ObjectId)):
            sanitized[op] = value
        elif isinstance(value, (list, tuple)):
            sanitized[op] = [sanitize_string(v) if isinstance(v, str) else v for v in value]

    return sanitized


def validate_object_id(id_str: str) -> ObjectId:
    """验证并转换 ObjectId"""
    try:
        return ObjectId(id_str)
    except:
        abort(404)


def escape_regex_pattern(pattern: str) -> str:
    """转义正则表达式特殊字符"""
    return re.escape(pattern)
