import os
import json
import locale
import sys
from typing import Dict, Any, Optional
from utils.resource_path import ResourcePaths

# 添加日志模块导入
try:
    from core.log_sys import get_logger
    logger = get_logger()
    LOG_AVAILABLE = True
except ImportError:
    # 如果无法导入日志模块，则使用print进行输出
    import logging
    logger = logging.getLogger(__name__)
    LOG_AVAILABLE = False

class I18nManager:
    def __init__(self, default_locale: str = "en"):
        self.default_locale = default_locale
        self.current_locale = default_locale
        self.translations: Dict[str, Dict[str, Any]] = {}
        
        # 使用资源路径管理来获取正确的locales目录
        self.locales_dir = self._get_locales_dir()
        
        # Load all available translations
        self._load_translations()
        
        # Auto-detect system locale
        self._detect_system_locale()
    
    def _get_locales_dir(self) -> str:
        """获取locales目录的正确路径，兼容开发和打包环境"""
        try:
            # 尝试导入资源路径管理工具
            current_dir = os.path.dirname(os.path.abspath(__file__))
            utils_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), "utils")
            if utils_path not in sys.path:
                sys.path.insert(0, utils_path)
            
            from utils.resource_path import ResourcePaths
            return ResourcePaths.locales()
            
        except ImportError:
            # 回退到原始方法
            return self._get_locales_dir_fallback()
    
    def _get_locales_dir_fallback(self) -> str:
        """回退方法：直接计算locales目录路径"""
        try:
            # 检查是否在打包环境中
            if hasattr(sys, '_MEIPASS'):  # type: ignore[attr-defined]
                # PyInstaller环境
                base_path = sys._MEIPASS  # type: ignore[attr-defined]
            elif hasattr(sys, 'frozen') and hasattr(sys, 'executable'):
                # Nuitka环境 - 可执行文件所在目录
                base_path = os.path.dirname(sys.executable)
            else:
                # 开发环境 - 当前文件的相对路径
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            locales_path = os.path.join(base_path, "assets", "modules", "I18N", "locales")
            
            # 记录路径查找过程
            if LOG_AVAILABLE:
                logger.debug(f"[I18N] Checking locales path: {locales_path}")
            else:
                print(f"[I18N] Checking locales path: {locales_path}")
            
            # 如果路径不存在，尝试其他可能的位置
            if not os.path.exists(locales_path):
                if LOG_AVAILABLE:
                    logger.warning(f"[I18N] Locales directory not found at primary path: {locales_path}")
                else:
                    print(f"[I18N] Locales directory not found at primary path: {locales_path}")
                
                # 尝试当前工作目录
                alt_path = os.path.join(os.getcwd(), "assets", "modules", "I18N", "locales")
                if os.path.exists(alt_path):
                    if LOG_AVAILABLE:
                        logger.info(f"[I18N] Found locales directory at current working dir path: {alt_path}")
                    else:
                        print(f"[I18N] Found locales directory at current working dir path: {alt_path}")
                    return alt_path
                
                # 尝试脚本目录
                script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                alt_path = os.path.join(script_dir, "assets", "modules", "I18N", "locales")
                if os.path.exists(alt_path):
                    if LOG_AVAILABLE:
                        logger.info(f"[I18N] Found locales directory at script dir path: {alt_path}")
                    else:
                        print(f"[I18N] Found locales directory at script dir path: {alt_path}")
                    return alt_path
                
                # 最后尝试相对于当前文件的路径
                fallback_path = os.path.join(os.path.dirname(__file__), "locales")
                if LOG_AVAILABLE:
                    logger.info(f"[I18N] Using fallback path: {fallback_path}")
                else:
                    print(f"[I18N] Using fallback path: {fallback_path}")
                return fallback_path
            
            if LOG_AVAILABLE:
                logger.info(f"[I18N] Found locales directory at: {locales_path}")
            else:
                print(f"[I18N] Found locales directory at: {locales_path}")
            return locales_path
            
        except Exception as e:
            # 最终回退
            fallback_path = os.path.join(os.path.dirname(__file__), "locales")
            if LOG_AVAILABLE:
                logger.error(f"[I18N] Error getting locales directory, using fallback path {fallback_path}: {e}")
            else:
                print(f"[I18N] Error getting locales directory, using fallback path {fallback_path}: {e}")
            return fallback_path
    
    def _load_translations(self):
        """加载所有翻译文件，兼容开发和打包环境"""
        # 在开发环境下显示详细信息，打包环境下保持静默
        is_packaged = hasattr(sys, 'frozen') or hasattr(sys, '_MEIPASS')  # type: ignore[attr-defined]
        debug_mode = not is_packaged
        
        if debug_mode:
            print(f"[I18N] Loading translations from: {self.locales_dir}")
        
        if LOG_AVAILABLE:
            logger.info(f"[I18N] Attempting to load translations from: {self.locales_dir}")
        else:
            print(f"[I18N] Attempting to load translations from: {self.locales_dir}")
        
        if not os.path.exists(self.locales_dir):
            if debug_mode:
                print(f"[I18N] Locales directory not found: {self.locales_dir}")
            
            if LOG_AVAILABLE:
                logger.error(f"[I18N] Locales directory not found: {self.locales_dir}")
            else:
                print(f"[I18N] Locales directory not found: {self.locales_dir}")
            
            # 尝试创建目录（仅在开发环境）
            try:
                if not is_packaged:
                    os.makedirs(self.locales_dir, exist_ok=True)
                    if debug_mode:
                        print(f"[I18N] Created locales directory: {self.locales_dir}")
                    if LOG_AVAILABLE:
                        logger.info(f"[I18N] Created locales directory: {self.locales_dir}")
                    else:
                        print(f"[I18N] Created locales directory: {self.locales_dir}")
            except Exception as e:
                if debug_mode:
                    print(f"[I18N] Failed to create locales directory: {e}")
                if LOG_AVAILABLE:
                    logger.error(f"[I18N] Failed to create locales directory: {e}")
                else:
                    print(f"[I18N] Failed to create locales directory: {e}")
            
            # 如果目录仍然不存在，加载回退翻译
            if not os.path.exists(self.locales_dir):
                if debug_mode:
                    print("[I18N] Using fallback translations")
                if LOG_AVAILABLE:
                    logger.warning("[I18N] Using fallback translations - locales directory not found")
                else:
                    print("[I18N] Using fallback translations")
                self._load_fallback_translations()
                return
        
        # 检查目录是否可读
        if not os.access(self.locales_dir, os.R_OK):
            if LOG_AVAILABLE:
                logger.error(f"[I18N] Cannot read locales directory: {self.locales_dir}")
            else:
                print(f"[I18N] Cannot read locales directory: {self.locales_dir}")
            self._load_fallback_translations()
            return
        
        # 加载翻译文件
        loaded_count = 0
        failed_files = []
        try:
            files = os.listdir(self.locales_dir)
            if LOG_AVAILABLE:
                logger.info(f"[I18N] Found {len(files)} files in locales directory")
            else:
                print(f"[I18N] Found {len(files)} files in locales directory")
            
            for filename in files:
                if filename.endswith('.json'):
                    locale_code = filename[:-5]  # Remove .json extension
                    file_path = os.path.join(self.locales_dir, filename)
                    
                    if LOG_AVAILABLE:
                        logger.debug(f"[I18N] Attempting to load translation file: {file_path}")
                    else:
                        print(f"[I18N] Attempting to load translation file: {file_path}")
                    
                    # 检查文件是否存在且可读
                    if not os.path.exists(file_path):
                        error_msg = f"[I18N] Translation file does not exist: {file_path}"
                        if LOG_AVAILABLE:
                            logger.error(error_msg)
                        else:
                            print(error_msg)
                        failed_files.append((filename, "File does not exist"))
                        continue
                        
                    if not os.access(file_path, os.R_OK):
                        error_msg = f"[I18N] Cannot read translation file: {file_path}"
                        if LOG_AVAILABLE:
                            logger.error(error_msg)
                        else:
                            print(error_msg)
                        failed_files.append((filename, "Permission denied"))
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            self.translations[locale_code] = data
                            loaded_count += 1
                            if debug_mode:
                                print(f"[I18N] Loaded translation: {locale_code} from {filename}")
                            if LOG_AVAILABLE:
                                logger.info(f"[I18N] Successfully loaded translation: {locale_code} from {filename}")
                            else:
                                print(f"[I18N] Successfully loaded translation: {locale_code} from {filename}")
                    except json.JSONDecodeError as e:
                        error_msg = f"[I18N] Error parsing JSON in translation file {filename}: {e}"
                        if LOG_AVAILABLE:
                            logger.error(error_msg)
                        else:
                            print(error_msg)
                        failed_files.append((filename, f"JSON decode error: {e}"))
                    except Exception as e:
                        error_msg = f"[I18N] Error loading translation file {filename}: {e}"
                        if LOG_AVAILABLE:
                            logger.error(error_msg)
                        else:
                            print(error_msg)
                        failed_files.append((filename, str(e)))
                else:
                    if LOG_AVAILABLE:
                        logger.debug(f"[I18N] Skipping non-JSON file: {filename}")
                    else:
                        print(f"[I18N] Skipping non-JSON file: {filename}")
        except PermissionError as e:
            error_msg = f"[I18N] Permission denied accessing locales directory: {e}"
            if LOG_AVAILABLE:
                logger.error(error_msg)
            else:
                print(error_msg)
            failed_files.append(("directory", "Permission denied"))
        except Exception as e:
            error_msg = f"[I18N] Error accessing locales directory: {e}"
            if LOG_AVAILABLE:
                logger.error(error_msg)
            else:
                print(error_msg)
            failed_files.append(("directory", str(e)))
        
        if LOG_AVAILABLE:
            logger.info(f"[I18N] Translation loading complete. Loaded: {loaded_count}, Failed: {len(failed_files)}")
        else:
            print(f"[I18N] Translation loading complete. Loaded: {loaded_count}, Failed: {len(failed_files)}")
        
        if debug_mode:
            print(f"[I18N] Total translations loaded: {loaded_count}")
        
        if failed_files:
            if LOG_AVAILABLE:
                logger.warning(f"[I18N] Failed to load {len(failed_files)} files: {failed_files}")
            else:
                print(f"[I18N] Failed to load {len(failed_files)} files: {failed_files}")
        
        if loaded_count == 0:
            if debug_mode:
                print(f"[I18N] WARNING: No translation files found in {self.locales_dir}")
            if LOG_AVAILABLE:
                logger.warning(f"[I18N] WARNING: No translation files found in {self.locales_dir}")
            else:
                print(f"[I18N] WARNING: No translation files found in {self.locales_dir}")
            # 提供基本的翻译作为回退
            self._load_fallback_translations()
    
    def _detect_system_locale(self):
        """智能检测系统语言，支持多种检测方式"""
        detected_locale = self._get_system_locale()
        
        # 在开发环境下显示检测信息
        is_packaged = hasattr(sys, 'frozen') or hasattr(sys, '_MEIPASS')  # type: ignore[attr-defined]
        debug_mode = not is_packaged
        
        if debug_mode:
            print(f"[I18N] Detected system locale: {detected_locale}")
        
        if LOG_AVAILABLE:
            logger.info(f"[I18N] Detected system locale: {detected_locale}")
        else:
            print(f"[I18N] Detected system locale: {detected_locale}")
        
        if detected_locale and detected_locale in self.translations:
            self.current_locale = detected_locale
            if debug_mode:
                print(f"[I18N] Set current locale to: {detected_locale}")
            if LOG_AVAILABLE:
                logger.info(f"[I18N] Set current locale to: {detected_locale}")
            else:
                print(f"[I18N] Set current locale to: {detected_locale}")
        else:
            if debug_mode:
                print(f"[I18N] Using default locale: {self.default_locale}")
            if LOG_AVAILABLE:
                logger.info(f"[I18N] Using default locale: {self.default_locale} (detected: {detected_locale})")
            else:
                print(f"[I18N] Using default locale: {self.default_locale} (detected: {detected_locale})")
    
    def _get_system_locale(self) -> Optional[str]:
        """获取系统语言，使用多种检测方法"""
        detected_locales = []
        
        # 方法1: 使用locale.getdefaultlocale()
        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                detected_locales.append(system_locale)
                if LOG_AVAILABLE:
                    logger.debug(f"[I18N] Locale detection method 1 (getdefaultlocale): {system_locale}")
                else:
                    print(f"[I18N] Locale detection method 1 (getdefaultlocale): {system_locale}")
        except Exception as e:
            if LOG_AVAILABLE:
                logger.warning(f"[I18N] Error in locale detection method 1: {e}")
            else:
                print(f"[I18N] Error in locale detection method 1: {e}")
            pass
        
        # 方法2: 使用locale.getlocale()
        try:
            current_locale = locale.getlocale()[0]
            if current_locale:
                detected_locales.append(current_locale)
                if LOG_AVAILABLE:
                    logger.debug(f"[I18N] Locale detection method 2 (getlocale): {current_locale}")
                else:
                    print(f"[I18N] Locale detection method 2 (getlocale): {current_locale}")
        except Exception as e:
            if LOG_AVAILABLE:
                logger.warning(f"[I18N] Error in locale detection method 2: {e}")
            else:
                print(f"[I18N] Error in locale detection method 2: {e}")
            pass
        
        # 方法3: 使用环境变量
        env_vars = ['LANG', 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES']
        for var in env_vars:
            env_locale = os.environ.get(var)
            if env_locale:
                detected_locales.append(env_locale)
                if LOG_AVAILABLE:
                    logger.debug(f"[I18N] Locale detection method 3 (environment variable {var}): {env_locale}")
                else:
                    print(f"[I18N] Locale detection method 3 (environment variable {var}): {env_locale}")
        
        # 方法4: Windows特定检测
        if sys.platform == 'win32':
            try:
                import ctypes
                # 获取Windows系统语言ID
                windll = ctypes.windll.kernel32
                lang_id = windll.GetUserDefaultUILanguage()
                
                # 常见的语言ID映射
                lang_map = {
                    0x0804: 'zh-CN',  # 简体中文
                    0x0404: 'zh-TW',  # 繁体中文
                    0x0409: 'en-US',  # 英语(美国)
                    0x0809: 'en-GB',  # 英语(英国)
                    0x0411: 'ja-JP',  # 日语
                    0x0412: 'ko-KR',  # 韩语
                }
                
                if lang_id in lang_map:
                    detected_locales.append(lang_map[lang_id])
                    if LOG_AVAILABLE:
                        logger.debug(f"[I18N] Locale detection method 4 (Windows UI language): {lang_map[lang_id]} (ID: 0x{lang_id:04x})")
                    else:
                        print(f"[I18N] Locale detection method 4 (Windows UI language): {lang_map[lang_id]} (ID: 0x{lang_id:04x})")
            except Exception as e:
                if LOG_AVAILABLE:
                    logger.warning(f"[I18N] Error in locale detection method 4 (Windows): {e}")
                else:
                    print(f"[I18N] Error in locale detection method 4 (Windows): {e}")
                pass
        
        # 方法5: 尝试从系统命令获取
        try:
            if sys.platform == 'win32':
                import subprocess
                result = subprocess.run(['powershell', '-Command', 
                                       'Get-Culture | Select-Object -ExpandProperty Name'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    detected_locales.append(result.stdout.strip())
                    if LOG_AVAILABLE:
                        logger.debug(f"[I18N] Locale detection method 5 (PowerShell Get-Culture): {result.stdout.strip()}")
                    else:
                        print(f"[I18N] Locale detection method 5 (PowerShell Get-Culture): {result.stdout.strip()}")
        except Exception as e:
            if LOG_AVAILABLE:
                logger.warning(f"[I18N] Error in locale detection method 5 (subprocess): {e}")
            else:
                print(f"[I18N] Error in locale detection method 5 (subprocess): {e}")
            pass
        
        # 分析检测到的语言并返回最佳匹配
        result = self._analyze_detected_locales(detected_locales)
        if LOG_AVAILABLE:
            logger.info(f"[I18N] Analyzed detected locales {detected_locales}, best match: {result}")
        else:
            print(f"[I18N] Analyzed detected locales {detected_locales}, best match: {result}")
        return result
    
    def _analyze_detected_locales(self, detected_locales: list) -> Optional[str]:
        """分析检测到的语言列表，返回最佳匹配"""
        if not detected_locales:
            return None
        
        # 语言映射规则
        locale_mapping = {
            # 中文变体
            'zh': 'zh-cn',
            'zh_CN': 'zh-cn', 
            'zh-CN': 'zh-cn',
            'zh_cn': 'zh-cn',
            'chinese': 'zh-cn',
            'chs': 'zh-cn',
            'zh_TW': 'zh-cn',  # 暂时映射到简体中文
            'zh-TW': 'zh-cn',
            'zh_HK': 'zh-cn',
            'zh-HK': 'zh-cn',
            
            # 英文变体
            'en': 'en',
            'en_US': 'en',
            'en-US': 'en',
            'en_GB': 'en',
            'en-GB': 'en',
            'en_AU': 'en',
            'en-AU': 'en',
            'en_CA': 'en',
            'en-CA': 'en',
            'english': 'en',
            
            # 其他语言（暂时映射到英文）
            'ja': 'en',
            'ja_JP': 'en',
            'ja-JP': 'en',
            'ko': 'en',
            'ko_KR': 'en',
            'ko-KR': 'en',
            'fr': 'en',
            'de': 'en',
            'es': 'en',
            'it': 'en',
            'pt': 'en',
            'ru': 'en',
        }
        
        # 统计各种语言的出现频率
        locale_scores = {}
        
        for detected in detected_locales:
            if not detected:
                continue
                
            # 清理和标准化
            cleaned = detected.lower().strip()
            
            # 移除编码信息 (如 .UTF-8)
            if '.' in cleaned:
                cleaned = cleaned.split('.')[0]
            
            # 直接匹配
            if cleaned in locale_mapping:
                target = locale_mapping[cleaned]
                locale_scores[target] = locale_scores.get(target, 0) + 2
                continue
            
            # 前缀匹配
            for pattern, target in locale_mapping.items():
                if cleaned.startswith(pattern.lower()):
                    locale_scores[target] = locale_scores.get(target, 0) + 1
                    break
            
            # 包含匹配
            if 'zh' in cleaned or 'chinese' in cleaned or 'chn' in cleaned:
                locale_scores['zh-cn'] = locale_scores.get('zh-cn', 0) + 1
            elif 'en' in cleaned or 'english' in cleaned:
                locale_scores['en'] = locale_scores.get('en', 0) + 1
        
        # 返回得分最高的语言
        if locale_scores:
            best_locale = max(locale_scores.items(), key=lambda x: x[1])[0]
            return best_locale
        
        return None
    
    def set_locale(self, locale_code: str) -> bool:
        # Set current locale if available
        if locale_code in self.translations:
            self.current_locale = locale_code
            if LOG_AVAILABLE:
                logger.info(f"[I18N] Locale set to: {locale_code}")
            else:
                print(f"[I18N] Locale set to: {locale_code}")
            return True
        if LOG_AVAILABLE:
            logger.warning(f"[I18N] Failed to set locale to: {locale_code} (not available)")
        else:
            print(f"[I18N] Failed to set locale to: {locale_code} (not available)")
        return False
    
    def get_available_locales(self) -> Dict[str, str]:
        # Return available locales with their display names
        locales = {}
        for locale_code in self.translations:
            translation = self.translations[locale_code]
            display_name = translation.get('_meta', {}).get('display_name', locale_code)
            locales[locale_code] = display_name
        return locales
    
    def t(self, key: str, **kwargs) -> str:
        # Translate a key with optional parameters
        return self.translate(key, **kwargs)
    
    def translate(self, key: str, **kwargs) -> str:
        # Get translation for a key, with fallback to default locale
        translation = self._get_nested_value(self.translations.get(self.current_locale, {}), key)
        
        if translation is None and self.current_locale != self.default_locale:
            # Fallback to default locale
            translation = self._get_nested_value(self.translations.get(self.default_locale, {}), key)
        
        if translation is None:
            # 如果没有找到翻译，尝试从回退翻译中获取
            if not self.translations:
                self._load_fallback_translations()
                translation = self._get_nested_value(self.translations.get(self.current_locale, {}), key)
                if translation is None:
                    translation = self._get_nested_value(self.translations.get(self.default_locale, {}), key)
        
        if translation is None:
            # Return key if no translation found
            if LOG_AVAILABLE:
                logger.warning(f"[I18N] Translation not found for key: '{key}' in locale '{self.current_locale}' or default locale '{self.default_locale}'")
            else:
                print(f"[I18N] Translation not found for key: '{key}' in locale '{self.current_locale}' or default locale '{self.default_locale}'")
            return key
        
        # Replace parameters if provided
        if kwargs:
            try:
                return translation.format(**kwargs)
            except (KeyError, ValueError) as e:
                if LOG_AVAILABLE:
                    logger.warning(f"[I18N] Error formatting translation for key '{key}': {e}")
                else:
                    print(f"[I18N] Error formatting translation for key '{key}': {e}")
                return translation
        
        return translation
    
    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[str]:
        # Get nested value using dot notation (e.g., "app.title")
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def get_current_locale(self) -> str:
        # Get current locale code
        return self.current_locale
    
    def get_system_locale_info(self) -> Dict[str, Any]:
        """获取详细的系统语言信息，用于调试"""
        info = {
            'detected_locale': self._get_system_locale(),
            'current_locale': self.current_locale,
            'available_locales': list(self.translations.keys()),
            'system_info': {}
        }
        
        # 收集系统语言信息
        try:
            info['system_info']['locale.getdefaultlocale()'] = locale.getdefaultlocale()
        except Exception as e:
            info['system_info']['locale.getdefaultlocale()'] = f"Error: {e}"
        
        try:
            info['system_info']['locale.getlocale()'] = locale.getlocale()
        except Exception as e:
            info['system_info']['locale.getlocale()'] = f"Error: {e}"
        
        # 环境变量
        env_vars = ['LANG', 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES']
        for var in env_vars:
            info['system_info'][f'env.{var}'] = os.environ.get(var, 'Not set')
        
        # Windows特定信息
        if sys.platform == 'win32':
            try:
                import ctypes
                lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                info['system_info']['windows_lang_id'] = f"0x{lang_id:04x}"
            except Exception as e:
                info['system_info']['windows_lang_id'] = f"Error: {e}"
        
        return info
    
    def auto_detect_and_set_locale(self) -> Optional[str]:
        """重新检测并设置系统语言"""
        old_locale = self.current_locale
        self._detect_system_locale()
        new_locale = self.current_locale
        
        return new_locale if new_locale != old_locale else None
    
    def _load_fallback_translations(self):
        """加载基本的回退翻译，防止完全找不到翻译文件"""
        fallback_en = {
            "_meta": {"display_name": "English"},
            "app": {
                "ready": "Ready",
                "title": "ZSnapr"
            },
            "tabs": {
                "home": "Home",
                "capture": "Capture", 
                "settings": "Settings",
                "about": "About"
            }
        }
        
        fallback_zh_cn = {
            "_meta": {"display_name": "简体中文"},
            "app": {
                "ready": "就绪",
                "title": "ZSnapr"
            },
            "tabs": {
                "home": "主页",
                "capture": "截图",
                "settings": "设置", 
                "about": "关于"
            }
        }
        
        self.translations["en"] = fallback_en
        self.translations["zh-cn"] = fallback_zh_cn
        
        # 只在开发环境显示调试信息
        if not (hasattr(sys, 'frozen') or hasattr(sys, '_MEIPASS')):  # type: ignore[attr-defined]
            print("[I18N] Loaded fallback translations")
        if LOG_AVAILABLE:
            logger.info("[I18N] Loaded fallback translations")
        else:
            print("[I18N] Loaded fallback translations")
    
    def reload_translations(self):
        # Reload all translation files
        self.translations.clear()
        self.locales_dir = self._get_locales_dir()  # 重新获取路径
        self._load_translations()

# Global instance
_i18n_manager = None

def get_i18n() -> I18nManager:
    # Get global I18n manager instance
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager

def t(key: str, **kwargs) -> str:
    # Shorthand function for translation
    return get_i18n().translate(key, **kwargs)

def set_locale(locale_code: str) -> bool:
    # Set current locale
    return get_i18n().set_locale(locale_code)

def get_available_locales() -> Dict[str, str]:
    # Get available locales
    return get_i18n().get_available_locales()

def get_current_locale() -> str:
    # Get current locale
    return get_i18n().get_current_locale()

def get_system_locale_info() -> Dict[str, Any]:
    # Get detailed system locale information
    return get_i18n().get_system_locale_info()

def auto_detect_locale() -> Optional[str]:
    # Auto-detect and set system locale, return new locale if changed
    return get_i18n().auto_detect_and_set_locale()