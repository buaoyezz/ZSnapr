import os
import json
import sys
from pathlib import Path

# Add utils to path for resource management
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_path = os.path.join(current_dir, "utils")
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)

from utils import get_resource_path, get_data_dir, ensure_dir_exists

# Add assets/modules to Python path for I18N imports
assets_modules_path = get_resource_path("assets/modules")
if assets_modules_path not in sys.path:
    sys.path.insert(0, assets_modules_path)

# Import I18N system with robust path handling
I18N_AVAILABLE = False
_i18n_instance = None

def _init_i18n():
    """初始化I18N系统"""
    global I18N_AVAILABLE, _i18n_instance
    
    if _i18n_instance is not None:
        return _i18n_instance
    
    try:
        # 方法1: 尝试直接从assets.modules.I18N导入
        from assets.modules.I18N import get_i18n, set_locale as i18n_set_locale, get_available_locales as i18n_get_available_locales, get_current_locale as i18n_get_current_locale
        _i18n_instance = get_i18n()
        I18N_AVAILABLE = True
        print("[Config] I18N initialized via assets.modules.I18N")
        return _i18n_instance
        
    except ImportError:
        try:
            # 方法2: 尝试从I18N导入（原方式）
            from I18N import get_i18n, set_locale as i18n_set_locale, get_available_locales as i18n_get_available_locales, get_current_locale as i18n_get_current_locale
            _i18n_instance = get_i18n()
            I18N_AVAILABLE = True
            print("[Config] I18N initialized via I18N module")
            return _i18n_instance
            
        except ImportError:
            try:
                # 方法3: 手动添加路径后导入
                i18n_path = get_resource_path("assets/modules/I18N")
                if i18n_path not in sys.path:
                    sys.path.insert(0, i18n_path)
                
                from i18n import I18nManager
                _i18n_instance = I18nManager()
                I18N_AVAILABLE = True
                print("[Config] I18N initialized via manual path")
                return _i18n_instance
                
            except Exception as e:
                print(f"[Config] All I18N import methods failed: {e}")
                I18N_AVAILABLE = False
                return None

def t(key, **kwargs):
    """翻译函数"""
    i18n = _init_i18n()
    if i18n and I18N_AVAILABLE:
        try:
            return i18n.translate(key, **kwargs)
        except Exception as e:
            print(f"[Config] Translation error for key '{key}': {e}")
            return key
    else:
        # 如果I18N不可用，返回键名
        print(f"[Config] I18N not available, returning key: {key}")
        return key

def set_locale(locale_code):
    """设置语言"""
    i18n = _init_i18n()
    if i18n and I18N_AVAILABLE:
        try:
            return i18n.set_locale(locale_code)
        except Exception as e:
            print(f"[Config] Set locale error: {e}")
            return False
    return False

def get_available_locales():
    """获取可用语言"""
    i18n = _init_i18n()
    if i18n and I18N_AVAILABLE:
        try:
            return i18n.get_available_locales()
        except Exception as e:
            print(f"[Config] Get available locales error: {e}")
            return {}
    return {}

def get_current_locale():
    """获取当前语言"""
    i18n = _init_i18n()
    if i18n and I18N_AVAILABLE:
        try:
            return i18n.get_current_locale()
        except Exception as e:
            print(f"[Config] Get current locale error: {e}")
            return "en"
    return "en"

# Application configuration
APP_NAME = "ZSnapr"
APP_VERSION = "1.0.4"
APP_CHANNEL = "Pre-Release"

# Default save directory
DEFAULT_SAVE_DIR = os.path.join(Path.home(), "Pictures", "ZSnapr")

# Supported image formats
SUPPORTED_FORMATS = [
    {"name": "PNG", "extension": ".png"},
    {"name": "JPEG", "extension": ".jpg"},
    {"name": "BMP", "extension": ".bmp"},
    {"name": "TIFF", "extension": ".tiff"}
]

# Default settings
DEFAULT_SETTINGS = {
    "save_directory": DEFAULT_SAVE_DIR,
    "image_format": "PNG",
    "auto_save": True,
    "show_cursor": False,
    "delay_seconds": 0,
    "auto_copy_fullscreen": False,
    "auto_copy_window": False,
    "language": "auto"  # auto, en, zh-cn
}

# Hotkeys
HOTKEYS = {
    "fullscreen": "ctrl+shift+f",
    "region": "ctrl+shift+r",
    "window": "ctrl+shift+w"
}

CONFIG_DIR = get_resource_path("assets/config")
HOTKEYS_FILE = os.path.join(CONFIG_DIR, "hotkeys.json")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

def load_hotkeys():
    # Load hotkeys from file and merge into HOTKEYS
    try:
        if os.path.exists(HOTKEYS_FILE):
            with open(HOTKEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k in ("fullscreen", "region", "window"):
                    v = data.get(k)
                    if isinstance(v, str) and v.strip():
                        HOTKEYS[k] = v.strip()
    except Exception:
        pass
    return HOTKEYS

def save_hotkeys(hotkeys: dict):
    # Persist hotkeys to file and update in-memory defaults
    try:
        ensure_dir_exists(CONFIG_DIR)
        data = {k: str(hotkeys.get(k, HOTKEYS.get(k, ""))).strip() for k in ("fullscreen", "region", "window")}
        with open(HOTKEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        for k, v in data.items():
            if v:
                HOTKEYS[k] = v
    except Exception:
        pass

def load_settings():
    # Load settings from file and apply language setting
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                language = data.get("language", "auto")
                if I18N_AVAILABLE:
                    if language == "auto":
                        # Let I18N auto-detect
                        pass
                    else:
                        set_locale(language)
                return data
    except Exception:
        pass
    return {}

def save_settings(settings: dict):
    # Persist settings to file
    try:
        ensure_dir_exists(CONFIG_DIR)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        # Apply language setting immediately
        if I18N_AVAILABLE and "language" in settings:
            language = settings["language"]
            if language != "auto":
                set_locale(language)
    except Exception:
        pass

def get_current_language():
    # Get current language setting
    if I18N_AVAILABLE:
        return get_current_locale()
    return "en"

def set_language(language: str):
    # Set language and save to settings
    if I18N_AVAILABLE:
        if language == "auto":
            # Reset to auto-detection
            get_i18n()._detect_system_locale()
        else:
            set_locale(language)
        
        # Save to settings file
        settings = load_settings()
        settings["language"] = language
        save_settings(settings)
        return True
    return False

try:
    load_hotkeys()
    load_settings()
except Exception:
    pass