import os
import ctypes
import sys
import socket
import tempfile
import threading  # 确保导入threading模块

# Add utils to path for resource management
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_path = os.path.join(current_dir, "utils")
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)

from utils import get_resource_path, get_icon_path, ResourcePaths, get_python_executable, is_packaged

# Set process DPI awareness as early as possible (Per-Monitor V2), with fallbacks
try:
    # PER_MONITOR_AWARE_V2 = -4 on Windows 10+
    if hasattr(ctypes.windll, "user32"):
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Normalize Qt scale environment to avoid mismatched coordinates
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '0'
os.environ['QT_SCALE_FACTOR'] = '1'
os.environ['QT_SCREEN_SCALE_FACTORS'] = '1'
os.environ['QT_DEVICE_PIXEL_RATIO'] = '1'


# 设置Flet使用项目目录
try:
    from setup_flet_env import setup_flet_environment
    setup_flet_environment()
except ImportError:
    pass

import flet as ft
import keyboard
from modules.screenshot_engine import ScreenshotEngine
from config import APP_NAME, APP_VERSION, DEFAULT_SETTINGS, HOTKEYS, SUPPORTED_FORMATS, save_hotkeys, load_settings, save_settings, set_language, get_current_language
from modules.copy_legacy import ClipboardManager
from modules.save_legacy import SaveManager
import pystray
from PIL import Image, ImageDraw
import queue
from ui.pages import capture_page, settings_page, about_page, home_page
from core.hotkeys import register as register_hotkeys, re_register as re_register_hotkeys
from core.tray import TrayManager
from core.log_sys import get_logger, LogOperation, auto_cleanup_logs, CleanupStrategy
from assets.modules.I18N import I18nManager, get_i18n, t, set_locale as i18n_set_locale
from ui.screenshot_editor import create_enhanced_editor
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
from PIL import ImageQt


def _check_single_instance():
    """Check if another instance of ZSnapr is already running"""
    try:
        # Use a socket to check for running instance
        lock_file = os.path.join(tempfile.gettempdir(), "zsnapr.lock")
        
        # Try to create a socket on a specific port
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', 54321))  # Use a specific port for ZSnapr
            sock.listen(1)
            
            # Write lock file
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            # Keep socket open to maintain lock
            setattr(_check_single_instance, '_socket', sock)
            return True
            
        except OSError:
            # Port is already in use, another instance is running
            return False
            
    except Exception:
        # If any error occurs, assume we can run
        return True


def _check_missing_files():
    logger = get_logger()
    logger.info("开始检查缺失的文件...")
    
    # 定义应该存在的关键文件和目录
    critical_paths = [
        # 配置文件
        "assets/config/hotkeys.json",
        "assets/config/settings.json",
        
        # 国际化文件
        "assets/modules/I18N/locales/en.json",
        "assets/modules/I18N/locales/zh-cn.json",
        
        # 核心模块
        "core/log_sys/logger.py",
        "modules/screenshot_engine.py",
        "ui/pages/home_page.py",
        "ui/pages/capture_page.py",
        "ui/pages/settings_page.py",
        "ui/pages/about_page.py",
        
        # 工具模块
        "utils/resource_path.py",
    ]
    
    missing_files = []
    
    for path in critical_paths:
        full_path = get_resource_path(path)
        if not os.path.exists(full_path):
            missing_files.append(path)
            logger.warning(f"缺失关键文件: {path}")
    
    if missing_files:
        logger.warning(f"总共发现 {len(missing_files)} 个缺失的文件")
        # 记录所有缺失的文件
        for file_path in missing_files:
            logger.warning(f"  - {file_path}")
    else:
        logger.info("所有关键文件检查通过，未发现缺失文件")
    
    return missing_files


class ZSnaprApp:
    def __init__(self):
        # Initialize logger first
        self.logger = get_logger()
        self.logger.info("Initializing ZSnaprApp")
        
        # Initialize socket before checking
        self._instance_socket = None
        
        # Check for another instance
        if not self._check_single_instance():
            self.logger.warning("Another instance of ZSnapr is already running")
            print("Another instance of ZSnapr is already running")
            sys.exit(1)
        
        # Initialize I18N system - use global instance
        self.i18n = get_i18n()
        settings = load_settings()
        saved_language = settings.get("language", "auto")
        if saved_language and saved_language != "auto":
            self.i18n.set_locale(saved_language)
        self.logger.info(f"I18N initialized with language: {self.i18n.current_locale}")
        
        # Silent automatic log cleanup on startup
        self._silent_log_cleanup()
        
        # 启动文件检查线程
        self._start_file_check_thread()
        
        self.engine = ScreenshotEngine()
        self.clipboard_manager = ClipboardManager()
        self.save_manager = SaveManager(DEFAULT_SETTINGS["save_directory"])
        
        self.page = None
        self.status_text = None
        self.preview_image = None
        self.last_screenshot = None
        self.last_filepath = None
        
        # UI components
        self.save_dir_field = None
        self.format_dropdown = None
        self.delay_field = None
        self.auto_save_checkbox = None
        self.tabs = None
        self.tray_manager = TrayManager(self)
        self.is_compact = False
        
        self.logger.info("ZSnaprApp initialization completed")
    
    def _check_single_instance(self):
        """Check if another instance of ZSnapr is already running"""
        try:
            # Use a socket to check for running instance
            lock_file = os.path.join(tempfile.gettempdir(), "zsnapr.lock")
            self.logger.debug(f"Checking for lock file: {lock_file}")
            
            # Try to create a socket on a specific port
            try:
                self._instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # Don't use SO_REUSEADDR for instance checking
                self._instance_socket.bind(('127.0.0.1', 54321))  # Use a specific port for ZSnapr
                self._instance_socket.listen(1)
                
                self.logger.debug("Successfully bound to port 54321")
                
                # Write lock file
                with open(lock_file, 'w') as f:
                    f.write(str(os.getpid()))
                
                self.logger.debug(f"Lock file created with PID: {os.getpid()}")
                return True
                
            except OSError as e:
                # Port is already in use, another instance is running
                self.logger.debug(f"Port binding failed: {e}")
                return False
                
        except Exception as e:
            # If any error occurs, assume we can run
            self.logger.warning(f"Instance check error: {e}")
            return True
    
    def _start_file_check_thread(self):
        """启动文件检查线程"""
        try:
            file_check_thread = threading.Thread(target=_check_missing_files, daemon=True)
            file_check_thread.start()
            self.logger.info("文件检查线程已启动")
        except Exception as e:
            self.logger.error(f"启动文件检查线程失败: {e}")
    
    def _silent_log_cleanup(self):
        # Automatic log cleanup with informative logging
        try:
            import threading
            import time
            
            def cleanup_worker():
                try:
                    # Wait a moment for app to fully initialize
                    time.sleep(0.5)
                    
                    # First, check current log file count to determine strategy
                    from core.log_sys.auto_clean import get_log_cleaner
                    cleaner = get_log_cleaner()
                    log_files = cleaner.scan_log_files()
                    file_count = len(log_files)
                    
                    # Determine cleanup strategy based on file count
                    if file_count > 50:
                        # Log overflow detected - use ultra aggressive cleanup
                        self.logger.warning(f"Log overflow detected: {file_count} files found, using ultra aggressive cleanup")
                        strategy = CleanupStrategy.ULTRA_AGGRESSIVE
                    elif file_count > 20:
                        # High file count - use aggressive cleanup
                        self.logger.info(f"High log file count detected: {file_count} files, using aggressive cleanup")
                        strategy = CleanupStrategy.AGGRESSIVE
                    else:
                        # Normal count - use balanced cleanup
                        strategy = CleanupStrategy.BALANCED
                    
                    # Perform cleanup with selected strategy
                    from core.log_sys.auto_clean import cleanup_logs_now
                    result = cleanup_logs_now(strategy, dry_run=False)
                    
                    if result.get("status") == "success":
                        deleted_count = len(result.get("deleted_files", []))
                        files_before = result.get("files_before", 0)
                        files_after = result.get("files_after", 0)
                        mb_freed = result.get("mb_freed", 0)
                        
                        if deleted_count > 0:
                            self.logger.info(f"Log cleanup completed: deleted {deleted_count} old log files")
                            self.logger.info(f"Before: {files_before} files, After: {files_after} files")
                            if mb_freed > 0:
                                self.logger.info(f"Space freed: {mb_freed:.2f} MB")
                            
                            # If still too many files after cleanup, suggest manual intervention
                            if files_after > 30:
                                self.logger.warning(f"Still {files_after} log files remaining after cleanup")
                                self.logger.warning("Consider manual log cleanup or check for application restart issues")
                        else:
                            self.logger.info("Log cleanup check completed: no files need deletion")
                    elif result.get("status") == "no_cleanup_needed":
                        self.logger.info(f"Log cleanup check: current {file_count} files is normal, no cleanup needed")
                    elif result.get("status") == "too_soon":
                        hours_since = result.get("hours_since_last", 0)
                        self.logger.debug(f"Log cleanup skipped: last cleanup was {hours_since:.1f} hours ago")
                    else:
                        self.logger.warning(f"Log cleanup status: {result.get('status', 'unknown')}")
                    
                except Exception as e:
                    self.logger.error(f"Log cleanup failed: {e}")
            
            # Run cleanup in background thread to avoid blocking startup
            cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
            cleanup_thread.start()
            
        except Exception as e:
            self.logger.error(f"启动日志清理线程失败: {e}")
        
    def main(self, page: ft.Page):
        self.page = page
        page.title = f"{APP_NAME} v{APP_VERSION}"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 939
        page.window.height = 597
        page.window.min_width = 500
        page.window.min_height = 350
        page.window.center()
        page.window.visible = True
        page.window.resizable = True
        page.scroll = ft.ScrollMode.HIDDEN
        page.window.title_bar_hidden = True
        page.window.title_bar_buttons_hidden = True
        # Set custom window icon using resource path management
        try:
            icon_path = get_icon_path()
            if icon_path and os.path.exists(icon_path):
                page.window.icon = icon_path
                self.logger.info(f"Window icon set to: {icon_path}")
                # Force page update to apply icon
                page.update()
            else:
                self.logger.warning("No icon files found")
        except Exception as e:
            self.logger.warning(f"Failed to set window icon: {e}")
        
        # Use built-in Flet Material icons (no external font needed)
        
        # Set up cleanup on window close
        # page.window.on_window_event = self._on_window_event  # Not available in current Flet version
        
        # Initialize UI
        self._setup_ui()

        # Responsive handler
        # self.page.on_resize = self._on_resize  # Not available in current Flet version
        
        # Setup global hotkeys
        self._setup_hotkeys()
        
        # Start tray action checker
        self._start_tray_checker()
        
        page.update()
    
    def _setup_ui(self):
        """Setup the user interface with tabs"""
        compact = (self.page.width or 0) < 560 if self.page else False
        self.is_compact = compact
        header_icon_size = 18 if compact else 20
        header_text_size = 13 if compact else 14
        header_spacing = 8 if compact else 10
        header_padding_v = 6 if compact else 8
        header_padding_h = 8 if compact else 10
        # Create tabs with controlled scrolling and responsive width
        tabs_height = max(250, (self.page.height or 411) - 150) if self.page else 250
        self.tabs = ft.Container(
            content=ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(
                        text=t("tabs.home"),
                        icon=ft.Icons.HOME,
                        content=ft.ListView(
                            controls=[home_page.build(self)],
                            expand=True,
                            auto_scroll=False
                        )
                    ),
                    ft.Tab(
                        text=t("tabs.capture"),
                        icon=ft.Icons.CAMERA_ALT,
                        content=ft.ListView(
                            controls=[capture_page.build(self)],
                            expand=True,
                            auto_scroll=False
                        )
                    ),
                    ft.Tab(
                        text=t("tabs.settings"),
                        icon=ft.Icons.SETTINGS,
                        content=ft.ListView(
                            controls=[settings_page.build(self)],
                            expand=True,
                            auto_scroll=False
                        )
                    ),
                    ft.Tab(
                        text=t("tabs.about"),
                        icon=ft.Icons.INFO,
                        content=ft.ListView(
                            controls=[about_page.build(self)],
                            expand=True,
                            auto_scroll=False
                        )
                    ),
                ]
            ),
            height=tabs_height,
            expand=False
        )
        
        # Status bar
        self.status_text = ft.Text(t("app.ready"), color=ft.Colors.GREEN_700, size=12, weight=ft.FontWeight.W_500)
        status_bar = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.CIRCLE, size=8, color=ft.Colors.GREEN_500),
                    margin=ft.margin.only(right=8)
                ),
                self.status_text
            ], spacing=0),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            bgcolor=ft.Colors.GREY_50,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_200)
        )
        
        # Enhanced Header with Material Design
        header = ft.Container(
            content=ft.Row([
                ft.WindowDragArea(
                    content=ft.Row([
                        # App icon without background - enlarged
                        ft.Container(
                            content=ft.Image(
                                src=get_icon_path(),
                                width=48,
                                height=48,
                                fit=ft.ImageFit.CONTAIN
                            ),
                            width=48,
                            height=48,
                            margin=ft.margin.only(right=4),
                        ),
                        # App title with enhanced typography - adjusted for larger icon
                        ft.Column([
                            ft.Text(f"{APP_NAME}", size=header_text_size + 2, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                            ft.Text(f"v{APP_VERSION}", size=header_text_size - 1, color=ft.Colors.BLUE_600, weight=ft.FontWeight.W_400),
                        ], spacing=0, tight=True),
                    ], spacing=header_spacing + 4, alignment=ft.MainAxisAlignment.START),
                    expand=True
                ),
                # Enhanced toolbar with Material Design buttons - Fixed alignment and boundary checking
                ft.Row([
                    # Quick capture buttons with Material Design icons - Improved alignment and responsive sizing
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.Icons.FULLSCREEN, size=16, color=ft.Colors.BLUE_600),
                                    ft.Text("Full", size=9, color=ft.Colors.BLUE_600, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)
                                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                                tooltip="Fullscreen Capture (Ctrl+Shift+F)",
                                on_click=self._capture_fullscreen,
                                padding=ft.padding.symmetric(horizontal=6 if compact else 8, vertical=4 if compact else 6),
                                border_radius=8,
                                bgcolor=ft.Colors.TRANSPARENT,
                                ink=True,
                                on_hover=lambda e: self._on_toolbar_hover(e, ft.Colors.BLUE_50)
                            ),
                            ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.Icons.CROP_FREE, size=16, color=ft.Colors.GREEN_600),
                                    ft.Text("Region", size=9, color=ft.Colors.GREEN_600, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)
                                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                                tooltip="Region Capture (Ctrl+Shift+R)",
                                on_click=self._capture_region,
                                padding=ft.padding.symmetric(horizontal=6 if compact else 8, vertical=4 if compact else 6),
                                border_radius=8,
                                bgcolor=ft.Colors.TRANSPARENT,
                                ink=True,
                                on_hover=lambda e: self._on_toolbar_hover(e, ft.Colors.GREEN_50)
                            ),
                            ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.Icons.WINDOW, size=16, color=ft.Colors.PURPLE_600),
                                    ft.Text("Window", size=9, color=ft.Colors.PURPLE_600, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)
                                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                                tooltip="Window Capture (Ctrl+Shift+W)",
                                on_click=self._capture_window,
                                padding=ft.padding.symmetric(horizontal=6 if compact else 8, vertical=4 if compact else 6),
                                border_radius=8,
                                bgcolor=ft.Colors.TRANSPARENT,
                                ink=True,
                                on_hover=lambda e: self._on_toolbar_hover(e, ft.Colors.PURPLE_50)
                            ),
                        ], spacing=2 if compact else 4, alignment=ft.MainAxisAlignment.CENTER),
                        padding=ft.padding.symmetric(horizontal=4 if compact else 6, vertical=3 if compact else 4),
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=10,
                        border=ft.border.all(1, ft.Colors.GREY_200),
                        # Ensure toolbar doesn't exceed screen bounds
                        width=min(200, (self.page.width or 400) - 100) if self.page else 200
                    ),
                    # Separator
                    ft.Container(
                        width=1,
                        height=24,
                        bgcolor=ft.Colors.GREY_300,
                        margin=ft.margin.symmetric(horizontal=8)
                    ),
                    # Window controls
                    ft.IconButton(
                        icon=ft.Icons.AUTO_AWESOME,
                        icon_color=ft.Colors.RED_600,
                        icon_size=18,
                        tooltip="Minimize to Tray",
                        on_click=self._minimize_to_tray,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            bgcolor={
                                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
                                ft.ControlState.HOVERED: ft.Colors.RED_50
                            },
                            overlay_color={
                                ft.ControlState.PRESSED: ft.Colors.RED_100
                            }
                        )
                    ),
                ], spacing=4, alignment=ft.MainAxisAlignment.END)
            ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(vertical=header_padding_v + 2, horizontal=header_padding_h + 2),
            bgcolor=ft.Colors.WHITE,
            border_radius=15,
            border=ft.border.all(1, ft.Colors.GREY_200),
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.12, ft.Colors.BLUE_300),
                offset=ft.Offset(0, 3)
            )
        )
        
        # Main layout with controlled scrolling
        main_content = ft.ListView(
            controls=[
                header,
                ft.Container(height=12),  # spacing
                self.tabs,
                ft.Container(height=12),  # spacing
                status_bar
            ],
            expand=True,
            spacing=0,
            auto_scroll=False
        )
        
        if self.page:
            self.page.add(
                ft.Container(
                    content=main_content,
                    padding=15
                )
            )
    
    def _setup_hotkeys(self):
        # Delegate to core.hotkeys
        register_hotkeys(self)
    
    def _on_resize(self, e):
        try:
            if not self.page:
                return
            new_compact = (self.page.width or 0) < 560
            if new_compact != getattr(self, "is_compact", False):
                sel = 0
                try:
                    if (self.tabs and hasattr(self.tabs, 'content') and 
                        hasattr(self.tabs.content, 'selected_index')):
                        sel = getattr(self.tabs.content, 'selected_index', 0)
                except (AttributeError, TypeError):
                    sel = 0
                
                if hasattr(self.page, 'controls') and self.page.controls:
                    self.page.controls.clear()
                self._setup_ui()
                
                try:
                    if (self.tabs and hasattr(self.tabs, 'content') and 
                        hasattr(self.tabs.content, 'selected_index')):
                        setattr(self.tabs.content, 'selected_index', sel)
                except (AttributeError, TypeError):
                    pass
                
                self.page.update()
        except Exception:
            pass

    def _update_status(self, message, color=ft.Colors.BLACK):
        """Update status message"""
        if self.status_text and self.page:
            self.status_text.value = message
            self.status_text.color = color
            self.page.update()
    
    def _capture_fullscreen(self, e=None):
        """Capture full screen"""
        self._update_status("Capturing full screen...", ft.Colors.BLUE)
        
        def capture():
            try:
                screenshot = self.engine.capture_fullscreen()
                self._process_screenshot(screenshot, "fullscreen")
            except Exception as ex:
                self._update_status(f"Error: {str(ex)}", ft.Colors.RED)
        
        threading.Thread(target=capture, daemon=True).start()
    
    def _capture_region(self, e=None):
        """Capture selected region"""
        with LogOperation("Region Capture"):
            self.logger.log_screenshot_event("REGION_CAPTURE_START")
            self._update_status("Select region on screen...", ft.Colors.BLUE)
            
            def capture():
                self.logger.log_thread_info("Region capture thread started")
                try:
                    self.logger.debug("Calling engine.capture_region()")
                    result = self.engine.capture_region()
                    self.logger.debug(f"Engine returned: {type(result)} - {result is not None}")
                    
                    if result:
                        self.logger.log_screenshot_event("REGION_CAPTURE_SUCCESS", f"Result type: {type(result)}")
                        self._process_screenshot(result, "region")
                    else:
                        self.logger.log_screenshot_event("REGION_CAPTURE_CANCELLED")
                        self._update_status("Region selection cancelled", ft.Colors.ORANGE)
                except Exception as ex:
                    self.logger.log_screenshot_event("REGION_CAPTURE_ERROR", str(ex))
                    self.logger.exception("Region capture exception:")
                    self._update_status(f"Error: {str(ex)}", ft.Colors.RED)
                finally:
                    self.logger.log_thread_info("Region capture thread finished")
            
            self.logger.debug("Starting region capture thread")
            threading.Thread(target=capture, daemon=True).start()
    
    def _capture_window(self, e=None):
        """Capture active window"""
        self._update_status("Capturing active window...", ft.Colors.BLUE)
        
        def capture():
            try:
                screenshot = self.engine.capture_window()
                self._process_screenshot(screenshot, "window")
            except Exception as ex:
                self._update_status(f"Error: {str(ex)}", ft.Colors.RED)
        
        threading.Thread(target=capture, daemon=True).start()
    
    def _process_screenshot(self, screenshot, capture_type):
        """Process captured screenshot"""
        if screenshot is None:
            self._update_status("Screenshot capture failed", ft.Colors.RED)
            return
            
        action = None
        # Enhanced tuple unpacking with better validation
        if isinstance(screenshot, (tuple, list)):
            if len(screenshot) == 2 and isinstance(screenshot[1], str):
                screenshot, action = screenshot
            elif len(screenshot) >= 2:
                # Handle cases where tuple has more than 2 elements
                screenshot, action = screenshot[0], screenshot[1]
            elif len(screenshot) == 1:
                # Handle single-element tuple
                screenshot = screenshot[0]
            # If tuple is empty or invalid, screenshot remains None and will be caught below
        
        # Additional validation after unpacking
        if screenshot is None:
            self._update_status("Screenshot capture failed after processing", ft.Colors.RED)
            return
        
        self.last_screenshot = screenshot
        
        if capture_type == "region" and action == "copy":
            try:
                ok = self.clipboard_manager.copy_image_to_clipboard(screenshot)
                if ok:
                    self._update_status("Region copied to clipboard", ft.Colors.GREEN)
                else:
                    self._update_status("Failed to copy to clipboard", ft.Colors.RED)
            except Exception as e:
                self._update_status(f"Clipboard error: {str(e)}", ft.Colors.RED)
            if self.page:
                self.page.update()
            return
        
        if capture_type == "region" and action == "save":
            try:
                filepath = self.save_manager.save_as_dialog(self.last_screenshot)
                if filepath:
                    self.last_filepath = filepath
                    self._update_status(f"Screenshot saved: {os.path.basename(filepath)}", ft.Colors.GREEN)
                else:
                    self._update_status("Save cancelled", ft.Colors.ORANGE)
            except Exception as e:
                self._update_status(f"Save error: {str(e)}", ft.Colors.RED)
            if self.page:
                self.page.update()
            return
        
        if capture_type == "region" and action == "edit":
            try:
                self._open_screenshot_editor(screenshot)
                self._update_status("Opening screenshot editor...", ft.Colors.BLUE)
            except Exception as e:
                self._update_status(f"Editor error: {str(e)}", ft.Colors.RED)
            if self.page:
                self.page.update()
            return
        
        # Check for auto-copy settings
        should_auto_copy = False
        try:
            if (capture_type == "fullscreen" and hasattr(self, 'auto_copy_fullscreen_checkbox')):
                checkbox = getattr(self, 'auto_copy_fullscreen_checkbox', None)
                if checkbox and getattr(checkbox, 'value', False):
                    should_auto_copy = True
            elif (capture_type == "window" and hasattr(self, 'auto_copy_window_checkbox')):
                checkbox = getattr(self, 'auto_copy_window_checkbox', None)
                if checkbox and getattr(checkbox, 'value', False):
                    should_auto_copy = True
        except (AttributeError, TypeError):
            should_auto_copy = False
        
        # Auto-copy if enabled
        if should_auto_copy:
            try:
                ok = self.clipboard_manager.copy_image_to_clipboard(screenshot)
                if ok:
                    self._update_status(f"{capture_type.title()} screenshot copied to clipboard", ft.Colors.GREEN)
                else:
                    self._update_status("Failed to copy to clipboard", ft.Colors.RED)
            except Exception as e:
                self._update_status(f"Clipboard error: {str(e)}", ft.Colors.RED)
        
        # Auto-save if enabled
        if self.auto_save_checkbox and getattr(self.auto_save_checkbox, 'value', False):
            try:
                save_dir = getattr(self.save_dir_field, 'value', None) if self.save_dir_field else DEFAULT_SETTINGS["save_directory"]
                img_format = getattr(self.format_dropdown, 'value', None) if self.format_dropdown else DEFAULT_SETTINGS["image_format"]
                save_dir = save_dir or DEFAULT_SETTINGS["save_directory"]
                img_format = img_format or DEFAULT_SETTINGS["image_format"]
                # Ensure types are correct - force string conversion
                save_dir = str(save_dir) if save_dir is not None else DEFAULT_SETTINGS["save_directory"]
                img_format = str(img_format) if img_format is not None else DEFAULT_SETTINGS["image_format"]
                filepath = self.save_manager.quick_save(screenshot, save_dir, img_format)
                if filepath:
                    self.last_filepath = filepath
                    status_msg = f"Screenshot saved: {os.path.basename(filepath)}"
                    if should_auto_copy:
                        status_msg += " and copied to clipboard"
                    self._update_status(status_msg, ft.Colors.GREEN)
                else:
                    self._update_status("Failed to save screenshot", ft.Colors.RED)
            except Exception as e:
                self._update_status(f"Save error: {str(e)}", ft.Colors.RED)
        elif not should_auto_copy:
            self._update_status("Screenshot captured (not saved)", ft.Colors.BLUE)
        
        if self.page:
            self.page.update()
    
    def _apply_settings(self, e):
        """Apply current settings"""
        try:
            # Update engine settings
            if self.save_dir_field:
                self.engine.set_save_directory(self.save_dir_field.value)
                self.save_manager.default_directory = self.save_dir_field.value
            if self.format_dropdown:
                self.engine.set_image_format(self.format_dropdown.value)
            if self.delay_field:
                self.engine.set_delay(float(self.delay_field.value or 0))
            if self.auto_save_checkbox:
                self.engine.auto_save = self.auto_save_checkbox.value

            # Apply hotkeys if fields exist
            new_hotkeys = None
            try:
                fullscreen_field = getattr(self, "fullscreen_hotkey_field", None)
                region_field = getattr(self, "region_hotkey_field", None) 
                window_field = getattr(self, "window_hotkey_field", None)
                
                if fullscreen_field and region_field and window_field:
                    f = (getattr(fullscreen_field, 'value', '') or "").strip()
                    r = (getattr(region_field, 'value', '') or "").strip()
                    w = (getattr(window_field, 'value', '') or "").strip()
                    if f and r and w:
                        new_hotkeys = {"fullscreen": f, "region": r, "window": w}
            except (AttributeError, TypeError):
                new_hotkeys = None

            if new_hotkeys:
                save_hotkeys(new_hotkeys)
                re_register_hotkeys(self, new_hotkeys)
                self._refresh_hotkey_labels()

            self._update_status("Settings applied successfully", ft.Colors.GREEN)
            self._show_snackbar("Settings applied successfully", ft.Colors.GREEN_600)
            self._show_dialog("Settings", "Settings applied successfully", modal=False)
            try:
                if self.tabs and hasattr(self.tabs, 'content') and hasattr(self.tabs.content, 'tabs'):
                    tabs_obj = self.tabs.content
                    # Use dynamic attribute access to avoid type checker errors
                    tabs_list = getattr(tabs_obj, 'tabs', None)
                    if tabs_list and len(tabs_list) > 0:
                        tabs_list[0].content = ft.ListView(
                            controls=[home_page.build(self)],
                            expand=True,
                            auto_scroll=False
                        )
            except Exception:
                pass
            if self.page:
                self.page.update()
        except Exception as ex:
            self._update_status(f"Settings error: {str(ex)}", ft.Colors.RED)
            self._show_snackbar(f"Settings error: {str(ex)}", ft.Colors.RED_600)
            if self.page:
                self.page.update()
    
    def _browse_directory(self, e):
        """Browse for save directory"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()
            
            # Get initial directory with proper type checking
            initial_dir = getattr(self.save_dir_field, 'value', None) if self.save_dir_field else None
            if initial_dir and not isinstance(initial_dir, str):
                initial_dir = None
            initial_dir = initial_dir or DEFAULT_SETTINGS["save_directory"]
            
            directory = filedialog.askdirectory(
                initialdir=str(initial_dir),
                title="Select Save Directory"
            )
            
            root.destroy()
            
            if directory:
                if self.save_dir_field:
                    self.save_dir_field.value = directory
                    if self.page:
                        self.page.update()
                    self._update_status("Directory updated", ft.Colors.GREEN)
                
        except Exception as ex:
            self._update_status(f"Directory selection error: {str(ex)}", ft.Colors.RED)
    
    def _save_as(self, e):
        """Save screenshot with custom name"""
        if self.last_screenshot:
            try:
                filepath = self.save_manager.save_as_dialog(self.last_screenshot)
                if filepath:
                    self.last_filepath = filepath
                    self._update_status(f"Screenshot saved as: {os.path.basename(filepath)}", ft.Colors.GREEN)
                else:
                    self._update_status("Save cancelled", ft.Colors.ORANGE)
            except Exception as ex:
                self._update_status(f"Save error: {str(ex)}", ft.Colors.RED)
        else:
            self._update_status("No screenshot to save", ft.Colors.ORANGE)
    
    def _copy_to_clipboard(self, e):
        """Copy screenshot to clipboard"""
        if self.last_screenshot:
            try:
                success = self.clipboard_manager.copy_image_to_clipboard(self.last_screenshot)
                if success:
                    self._update_status("Screenshot copied to clipboard", ft.Colors.GREEN)
                else:
                    self._update_status("Failed to copy to clipboard", ft.Colors.RED)
            except Exception as ex:
                self._update_status(f"Clipboard error: {str(ex)}", ft.Colors.RED)
        else:
            self._update_status("No screenshot to copy", ft.Colors.ORANGE)
    
    def _open_folder(self, e):
        """Open save folder"""
        try:
            folder_path = getattr(self.save_dir_field, 'value', None) if self.save_dir_field else None
            if self.last_filepath:
                folder_path = os.path.dirname(self.last_filepath)
            
            if not folder_path:
                folder_path = DEFAULT_SETTINGS["save_directory"]
            
            # Ensure folder_path is definitely a string
            folder_path = str(folder_path) if folder_path is not None else DEFAULT_SETTINGS["save_directory"]
            
            os.startfile(folder_path)
            self._update_status("Opened save folder", ft.Colors.GREEN)
        except Exception as ex:
            self._update_status(f"Error opening folder: {str(ex)}", ft.Colors.RED)
    
    def _open_screenshot_editor(self, screenshot):
        """Open screenshot editor with drawing tools"""
        try:
            self.logger.debug("Opening screenshot editor in separate process")
            
            # Save screenshot to temporary file
            import tempfile
            import subprocess
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name
                screenshot.save(temp_path, 'PNG')
            
            # Get correct paths for packaged environment
            python_exe = get_python_executable()
            editor_script = get_resource_path("launch_editor.py")
            
            self.logger.debug(f"Using Python executable: {python_exe}")
            self.logger.debug(f"Editor script path: {editor_script}")
            
            # Launch editor in separate process with proper flags
            if is_packaged():
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            else:
                creation_flags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                
            subprocess.Popen(
                [python_exe, editor_script, temp_path], 
                creationflags=creation_flags
            )
            
            self.logger.debug("Screenshot editor launched successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to open screenshot editor: {e}")
            self.logger.exception("Screenshot editor exception:")
            raise
    
    # Hotkey handlers
    def _hotkey_fullscreen(self):
        """Hotkey handler for fullscreen capture"""
        if self.page:
            self._capture_fullscreen()
    
    def _hotkey_region(self):
        """Hotkey handler for region capture"""
        self.logger.log_hotkey_event("ctrl+shift+r", "region_capture")
        if self.page:
            self.logger.debug("Page exists, calling _capture_region")
            self._capture_region()
        else:
            self.logger.warning("Page is None, cannot capture region")
    
    def _hotkey_window(self):
        """Hotkey handler for window capture"""
        if self.page:
            self._capture_window()

    def _refresh_hotkey_labels(self):
        # Rebuild capture page to reflect latest hotkeys
        try:
            if self.tabs and hasattr(self.tabs, 'content') and hasattr(self.tabs.content, 'tabs'):
                tabs_obj = self.tabs.content
                # Use dynamic attribute access to avoid type checker errors
                tabs_list = getattr(tabs_obj, 'tabs', None)
                if tabs_list and len(tabs_list) > 1:
                    tabs_list[1].content = ft.ListView(
                        controls=[capture_page.build(self)],
                        expand=True,
                        auto_scroll=False
                    )
            if self.page:
                self.page.update()
        except Exception:
            pass

    def _record_hotkey(self, target):
        # Capture a hotkey combo and put it into corresponding field
        self._update_status("Press the desired hotkey...", ft.Colors.BLUE)
        def worker():
            try:
                combo = keyboard.read_hotkey(suppress=True)
                field = None
                if target == "fullscreen":
                    field = getattr(self, "fullscreen_hotkey_field", None)
                elif target == "region":
                    field = getattr(self, "region_hotkey_field", None)
                elif target == "window":
                    field = getattr(self, "window_hotkey_field", None)
                
                if field and hasattr(field, 'value'):
                    field.value = combo
                    if self.page:
                        self.page.update()
                    self._update_status("Hotkey captured", ft.Colors.GREEN)
            except Exception as ex:
                self._update_status(f"Hotkey capture failed: {str(ex)}", ft.Colors.RED)
        threading.Thread(target=worker, daemon=True).start()

    def _show_snackbar(self, message, bgcolor=ft.Colors.BLUE_600):
        try:
            if not self.page:
                return
            
            # Simple responsive configuration
            is_compact = getattr(self, 'is_compact', False)
            text_size = 12 if is_compact else 13
            
            snack_bar = ft.SnackBar(
                content=ft.Text(
                    message, 
                    color=ft.Colors.WHITE,
                    size=text_size,
                    weight=ft.FontWeight.W_500
                ),
                bgcolor=bgcolor,
                behavior=ft.SnackBarBehavior.FLOATING
            )
            snack_bar.open = True
            if hasattr(self.page, 'overlay'):
                self.page.overlay.append(snack_bar)
            else:
                # Fallback for older Flet versions  
                try:
                    # Use setattr to avoid static type checking issues
                    setattr(self.page, 'snack_bar', snack_bar)
                except Exception:
                    pass
            self.page.update()
        except Exception:
            pass

    def _show_dialog(self, title, message, modal=False):
        try:
            if not self.page:
                return
            dlg = ft.AlertDialog(
                modal=modal,
                title=ft.Text(title),
                content=ft.Text(message),
                actions=[ft.TextButton("OK", on_click=lambda e: self._close_dialog_safe(dlg))],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.open(dlg)
        except Exception:
            pass

    # Delegate all tray operations to TrayManager
    def _minimize_to_tray(self, e=None):
        self.tray_manager.minimize_to_tray()
    def _start_tray_checker(self):
        self.tray_manager.start_checker()
    def _restore_from_tray(self):
        self.tray_manager.restore_from_tray()
    def _on_tray_click(self):
        self.tray_manager.on_tray_click()
    def _on_tray_restore(self):
        self.tray_manager.on_tray_restore()
    def _on_tray_exit(self):
        self.tray_manager.on_tray_exit()
    
    def _on_toolbar_hover(self, e, hover_color):
        # Handle toolbar button hover effects
        try:
            if hasattr(e, 'control') and e.control:
                if e.data == "true":  # Mouse enter
                    e.control.bgcolor = hover_color
                else:  # Mouse leave
                    e.control.bgcolor = ft.Colors.TRANSPARENT
                if self.page:
                    self.page.update()
        except Exception:
            pass

    def change_language(self, language_code):
        # Change application language
        try:
            # Use global I18N functions to ensure consistency
            i18n_set_locale(language_code)
            set_language(language_code)
            self.logger.info(f"Language changed to: {language_code}")
            
            # Update UI elements that need refresh
            if hasattr(self, 'page') and self.page:
                # Save current tab index
                current_tab_index = 0
                try:
                    if (hasattr(self, 'tabs') and self.tabs and hasattr(self.tabs, 'content') and 
                        hasattr(self.tabs.content, 'selected_index')):
                        current_tab_index = getattr(self.tabs.content, 'selected_index', 0)
                except (AttributeError, TypeError):
                    current_tab_index = 0
                
                # Clear current UI
                if hasattr(self.page, 'controls') and self.page.controls:
                    self.page.controls.clear()
                
                # Rebuild UI with new language
                self._setup_ui()
                
                # Restore tab selection
                try:
                    if (hasattr(self, 'tabs') and self.tabs and hasattr(self.tabs, 'content') and 
                        hasattr(self.tabs.content, 'selected_index')):
                        setattr(self.tabs.content, 'selected_index', current_tab_index)
                except (AttributeError, TypeError):
                    pass
                
                # Update page
                self.page.update()
                
                # Update status message
                self._update_status(t("settings.language_changed"), ft.Colors.GREEN)
                
        except Exception as e:
            self.logger.error(f"Failed to change language: {e}")
            if hasattr(self, 'page') and self.page:
                self._update_status(t("settings.language_change_error"), ft.Colors.RED)

    def _close_dialog_safe(self, dialog):
        """Safely close dialog"""
        try:
            if self.page and hasattr(self.page, 'close'):
                self.page.close(dialog)
        except Exception:
            pass

    def cleanup(self):
        """Clean up resources including instance lock"""
        try:
            if hasattr(self, '_instance_socket') and self._instance_socket:
                self._instance_socket.close()
                
            # Clean up tray resources
            if hasattr(self, 'tray_manager'):
                self.tray_manager.cleanup()
                
            # Remove lock file
            lock_file = os.path.join(tempfile.gettempdir(), "zsnapr.lock")
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

def main():
    app = ZSnaprApp()
    try:
        ft.app(target=app.main)
    finally:
        app.cleanup()

if __name__ == "__main__":
    main()