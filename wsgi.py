# -*- coding: utf-8 -*-
import sys
import locale

# 设置默认编码为 UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
