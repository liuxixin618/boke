import os
import uuid
from pathlib import Path
from flask import current_app
from werkzeug.utils import secure_filename

def ensure_upload_folder():
    """
    确保上传文件夹存在并返回正确的路径
    Returns:
        Path: 上传文件夹的路径对象
    Raises:
        Exception: 如果创建文件夹失败或文件夹不可写
    """
    try:
        base_dir = Path(current_app.root_path).parent
        upload_folder = base_dir / 'uploads'
        upload_folder.mkdir(parents=True, exist_ok=True)
        current_app.config['UPLOAD_FOLDER'] = str(upload_folder)
        if not upload_folder.exists():
            raise Exception("Upload folder does not exist after creation attempt")
        if not os.access(str(upload_folder), os.W_OK):
            raise Exception("Upload folder is not writable")
        return upload_folder
    except Exception as e:
        current_app.logger.error(f"Error ensuring upload folder: {str(e)}")
        raise

def sanitize_filename(filename):
    """
    清理文件名，保留中文字符
    Args:
        filename (str): 原始文件名
    Returns:
        str: 清理后的文件名
    """
    unsafe_chars = '<>:"/\\|?*\0'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    filename = filename.strip()
    return filename or 'unnamed'

def save_file(file):
    """
    保存上传的文件并返回存储信息
    Args:
        file: FileStorage对象，上传的文件
    Returns:
        dict: 包含文件信息的字典，如果保存失败返回None
    """
    if not file or not file.filename:
        current_app.logger.warning("No file or filename provided")
        return None
    try:
        # 保存原始文件名
        original_filename = file.filename
        # 分离文件名和扩展名
        if '.' in file.filename:
            name_base, ext = file.filename.rsplit('.', 1)
            ext = '.' + ext.lower()
        else:
            name_base = file.filename
            ext = ''
        safe_name_base = sanitize_filename(name_base)
        original_filename = safe_name_base + ext
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        upload_folder = ensure_upload_folder()
        file_path = upload_folder / stored_filename
        file.save(str(file_path))
        if not file_path.exists():
            current_app.logger.error("File was not saved successfully")
            raise Exception("File was not saved successfully")
        file_size = os.path.getsize(str(file_path))
        file_info = {
            'filename': original_filename,
            'stored_filename': stored_filename,
            'file_type': ext[1:] if ext else '',
            'file_size': file_size,
        }
        return file_info
    except Exception as e:
        current_app.logger.error(f"File save error: {str(e)}")
        return None 