from flask import current_app
from .models import SiteConfig


def site_config():
    """
    提供网站配置给模板
    """
    configs = {}
    for config in SiteConfig.objects.all():
        configs[config.key] = config.value
    return {'site_config': configs}
