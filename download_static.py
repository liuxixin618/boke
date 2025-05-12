import os
import requests
from pathlib import Path


def download_file(url, save_path):
    """下载文件到指定路径"""
    print(f"下载 {url} 到 {save_path}")
    response = requests.get(url)
    if response.status_code == 200:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        print(f"下载成功: {save_path}")
    else:
        print(f"下载失败: {url}")


def main():
    # 静态资源目录
    static_dir = Path("app/static")

    # 要下载的文件列表
    files_to_download = [
        # Bootstrap CSS
        {
            "url": "https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.0/css/bootstrap.min.css",
            "path": static_dir / "css" / "bootstrap.min.css",
        },
        # Bootstrap JS
        {
            "url": "https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.3.0/js/bootstrap.bundle.min.js",
            "path": static_dir / "js" / "bootstrap.bundle.min.js",
        },
        # Bootstrap Icons CSS
        {
            "url": "https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.10.0/font/bootstrap-icons.css",
            "path": static_dir / "css" / "bootstrap-icons.css",
        },
        # Bootstrap Icons Fonts
        {
            "url": "https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.10.0/font/fonts/bootstrap-icons.woff",
            "path": static_dir / "fonts" / "bootstrap-icons.woff",
        },
        {
            "url": "https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.10.0/font/fonts/bootstrap-icons.woff2",
            "path": static_dir / "fonts" / "bootstrap-icons.woff2",
        },
        # markdown-it JS
        {
            "url": "https://cdn.jsdelivr.net/npm/markdown-it@13.0.1/dist/markdown-it.min.js",
            "path": static_dir / "js" / "markdown-it.min.js",
        },
        # github-markdown-css
        {
            "url": "https://cdn.jsdelivr.net/npm/github-markdown-css@5.5.1/github-markdown.min.css",
            "path": static_dir / "css" / "github-markdown.min.css",
        },
    ]

    # 下载文件
    for file in files_to_download:
        download_file(file["url"], file["path"])

    # 修改 bootstrap-icons.css 中的字体路径
    icons_css_path = static_dir / "css" / "bootstrap-icons.css"
    if icons_css_path.exists():
        content = icons_css_path.read_text()
        content = content.replace('url("../fonts/', 'url("../fonts/')
        icons_css_path.write_text(content)
        print("已更新 bootstrap-icons.css 中的字体路径")


if __name__ == "__main__":
    main()
