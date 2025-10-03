#!/usr/bin/env python3
"""
Flet环境配置
设置Flet使用项目目录下的缓存
"""
import os
import sys

def setup_flet_environment():
    """设置Flet环境变量"""
    project_root = r"E:\ZS_Packge"
    flet_dir = os.path.join(project_root, ".flet")
    
    # 设置Flet相关环境变量
    os.environ["FLET_APP_HIDDEN"] = "true"
    os.environ["FLET_WEB_APP_PATH"] = flet_dir
    
    # 如果有其他Flet环境变量，也可以在这里设置
    # os.environ["FLET_SECRET_KEY"] = "your-secret-key"
    
    print(f"[Flet] 使用项目目录: {flet_dir}")
    
    return flet_dir

# 自动执行设置
if __name__ == "__main__":
    setup_flet_environment()
