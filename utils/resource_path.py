"""
资源路径管理模块
专门处理打包后的资源文件访问问题
"""
import os
import sys
from pathlib import Path
import tempfile


def get_resource_path(relative_path: str) -> str:
    """
    获取资源文件的绝对路径，兼容开发和打包环境
    
    Args:
        relative_path: 相对于项目根目录的路径，如 "assets/images/logo.png"
    
    Returns:
        资源文件的绝对路径
    """
    try:
        # 检查是否在Nuitka打包环境中
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller环境
            base_path = sys._MEIPASS
        elif hasattr(sys, 'frozen') and hasattr(sys, 'executable'):
            # Nuitka环境 - 可执行文件所在目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境 - 脚本所在的项目根目录
            # 当前文件在 utils/ 目录下，需要获取父目录
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(current_file))
            base_path = project_root
        
        # 构建完整路径
        full_path = os.path.join(base_path, relative_path)
        
        # 如果文件不存在，尝试其他可能的位置
        if not os.path.exists(full_path):
            # 尝试当前工作目录
            alt_path = os.path.join(os.getcwd(), relative_path)
            if os.path.exists(alt_path):
                return os.path.abspath(alt_path)
            
            # 尝试脚本目录的父目录
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            alt_path = os.path.join(script_dir, relative_path)
            if os.path.exists(alt_path):
                return os.path.abspath(alt_path)
        
        return os.path.abspath(full_path)
        
    except Exception:
        # 回退到原始的相对路径
        return os.path.abspath(relative_path)


def get_executable_dir() -> str:
    """
    获取可执行文件所在目录
    
    Returns:
        可执行文件目录的绝对路径
    """
    try:
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller环境
            return sys._MEIPASS
        elif hasattr(sys, 'frozen') and hasattr(sys, 'executable'):
            # Nuitka环境
            return os.path.dirname(sys.executable)
        else:
            # 开发环境
            current_file = os.path.abspath(__file__)
            return os.path.dirname(os.path.dirname(current_file))
    except Exception:
        return os.getcwd()


def get_data_dir() -> str:
    """
    获取数据目录（用于存放配置文件等）
    
    Returns:
        数据目录的绝对路径
    """
    try:
        if hasattr(sys, 'frozen'):
            # 打包环境 - 使用可执行文件目录
            return get_executable_dir()
        else:
            # 开发环境 - 使用项目根目录
            return get_executable_dir()
    except Exception:
        return os.getcwd()


def get_temp_dir() -> str:
    """
    获取临时目录
    
    Returns:
        临时目录的绝对路径
    """
    return tempfile.gettempdir()


def ensure_dir_exists(dir_path: str) -> str:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        dir_path: 目录路径
    
    Returns:
        目录的绝对路径
    """
    try:
        abs_path = os.path.abspath(dir_path)
        os.makedirs(abs_path, exist_ok=True)
        return abs_path
    except Exception:
        return dir_path


def get_python_executable() -> str:
    """
    获取Python可执行文件路径，兼容打包和开发环境
    
    Returns:
        Python可执行文件路径
    """
    try:
        if hasattr(sys, 'frozen'):
            # 打包环境 - 返回当前可执行文件
            return sys.executable
        else:
            # 开发环境 - 返回Python解释器
            return sys.executable
    except Exception:
        return sys.executable


def get_module_path(module_name: str) -> str:
    """
    获取模块文件的绝对路径
    
    Args:
        module_name: 模块相对路径，如 "modules/region_worker.py"
    
    Returns:
        模块文件的绝对路径
    """
    return get_resource_path(module_name)


def is_packaged() -> bool:
    """
    检查是否在打包环境中运行
    
    Returns:
        True if packaged, False if development
    """
    return hasattr(sys, 'frozen') or hasattr(sys, '_MEIPASS')


# 预定义常用路径
class ResourcePaths:
    """常用资源路径的快捷访问"""
    
    @staticmethod
    def images(filename: str = "") -> str:
        """获取图片资源路径"""
        if filename:
            return get_resource_path(f"assets/images/{filename}")
        return get_resource_path("assets/images")
    
    @staticmethod
    def config(filename: str = "") -> str:
        """获取配置文件路径"""
        if filename:
            return get_resource_path(f"assets/config/{filename}")
        return get_resource_path("assets/config")
    
    @staticmethod
    def modules(filename: str = "") -> str:
        """获取模块文件路径"""
        if filename:
            return get_resource_path(f"modules/{filename}")
        return get_resource_path("modules")
    
    @staticmethod
    def locales(filename: str = "") -> str:
        """获取本地化文件路径"""
        if filename:
            return get_resource_path(f"assets/modules/I18N/locales/{filename}")
        return get_resource_path("assets/modules/I18N/locales")


# 便捷函数
def resource_exists(relative_path: str) -> bool:
    """检查资源文件是否存在"""
    return os.path.exists(get_resource_path(relative_path))


def get_icon_path() -> str:
    """获取应用图标路径，自动选择最佳图标"""
    icons = [
        "assets/images/logo2png.ico",
        "assets/images/FullBlack.png", 
        "assets/images/logo1.png"
    ]
    
    for icon in icons:
        if resource_exists(icon):
            return get_resource_path(icon)
    
    # 如果都不存在，返回第一个作为默认值
    return get_resource_path(icons[0])