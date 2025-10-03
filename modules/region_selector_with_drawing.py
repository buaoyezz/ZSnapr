#!/usr/bin/env python3
# Enhanced Region Selector with Integrated Drawing Tools - Fixed Version

from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QHBoxLayout, 
                               QGraphicsDropShadowEffect, QVBoxLayout, QButtonGroup, QToolButton,
                               QColorDialog, QSlider, QFrame, QMenu, QDialog, QGridLayout, QLineEdit)
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QTimer, QSize, QPointF
from PySide6.QtGui import (QPainter, QPen, QBrush, QColor, QPixmap, QFont, QCursor, 
                          QLinearGradient, QFontDatabase, QPainterPath, QPolygonF, QIcon, QAction)
import sys
import os
import pyautogui
from PIL import Image, ImageQt
import time
from core.log_sys import get_logger
from modules.qt_manager import get_qt_app
import math

# Add utils to path for resource management
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
utils_path = os.path.join(project_root, "utils")
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)

try:
    from utils import ResourcePaths, resource_exists, get_resource_path
except ImportError:
    # Fallback if utils not available
    def get_resource_path(path):
        return path
    def resource_exists(path):
        return os.path.exists(path)
    class ResourcePaths:
        @staticmethod
        def images(filename):
            return os.path.join("assets", "images", filename)

class DrawingItem:
    # Base class for drawing items
    def __init__(self, tool_type, color, width):
        self.tool_type = tool_type
        self.color = color
        self.width = width
        self.points = []
        self.text_content = ""  # Initialize text content attribute
        
        # 新增：文字大小模式标记
        self.text_size_mode = "auto"  # "auto" 表示自动跟随框子大小，"custom" 表示自定义PX
        self.custom_font_size = 14  # 自定义字体大小（PX）
        self.was_manually_resized = False  # 标记是否被手动拖动调整过大小
        self.initial_font_size = width if width > 0 else 14  # 记录初始字体大小
    
    def add_point(self, point):
        self.points.append(point)
    
    def draw(self, painter):
        # Set pen for outline
        painter.setPen(QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        # Set transparent brush for shapes
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        
        if self.tool_type == "pen" and len(self.points) > 1:
            # Draw smooth line
            for i in range(1, len(self.points)):
                painter.drawLine(self.points[i-1], self.points[i])
        elif self.tool_type == "rectangle" and len(self.points) >= 2:
            # Draw transparent rectangle (outline only)
            rect = QRect(self.points[0], self.points[-1]).normalized()
            painter.drawRect(rect)
        elif self.tool_type == "circle" and len(self.points) >= 2:
            # Draw transparent circle (outline only)
            rect = QRect(self.points[0], self.points[-1]).normalized()
            painter.drawEllipse(rect)
        elif self.tool_type == "arrow" and len(self.points) >= 2:
            # Draw arrow
            start = self.points[0]
            end = self.points[-1]
            painter.drawLine(start, end)
            
            # Draw arrowhead
            angle = math.atan2((end.y() - start.y()), (end.x() - start.x()))
            arrowhead_length = 15
            arrowhead_angle = math.pi / 6
            
            arrowhead1 = QPoint(
                int(end.x() - arrowhead_length * math.cos(angle - arrowhead_angle)),
                int(end.y() - arrowhead_length * math.sin(angle - arrowhead_angle))
            )
            arrowhead2 = QPoint(
                int(end.x() - arrowhead_length * math.cos(angle + arrowhead_angle)),
                int(end.y() - arrowhead_length * math.sin(angle + arrowhead_angle))
            )
            
            painter.drawLine(end, arrowhead1)
            painter.drawLine(end, arrowhead2)
        elif self.tool_type == "text" and len(self.points) >= 1:
            # 恢复文本框调整功能：绘制边框和角落手柄
            rect = None
            if len(self.points) >= 2:
                rect = QRect(self.points[0], self.points[-1]).normalized()
                
                # 绘制边框（始终显示，便于识别文本框边界）
                pen = QPen(self.color, 1)
                pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect)
                
                # 绘制四角调整手柄（符合项目规范：只在四个角落）
                hs = 6  # 手柄大小
                handle_color = QColor(103, 80, 164)  # 紫色
                painter.setBrush(Qt.BrushStyle.NoBrush)  # 完全透明，无填充
                painter.setPen(QPen(handle_color, 1))
                
                # 四角手柄 - 只绘制边框，无填充
                painter.drawEllipse(QRect(rect.left()-hs//2, rect.top()-hs//2, hs, hs))  # 左上
                painter.drawEllipse(QRect(rect.right()-hs//2, rect.top()-hs//2, hs, hs))  # 右上
                painter.drawEllipse(QRect(rect.left()-hs//2, rect.bottom()-hs//2, hs, hs))  # 左下
                painter.drawEllipse(QRect(rect.right()-hs//2, rect.bottom()-hs//2, hs, hs))  # 右下
            if hasattr(self, 'text_content') and (self.text_content or hasattr(painter.device(), 'inline_editing')):
                if rect is None:
                    rect = QRect(self.points[0], self.points[0]).adjusted(0, 0, max(40, self.width * 8), max(24, self.width * 6))
                h = max(20, rect.height())
                # 修复：防止框子被点击时自动改变文字大小
                if getattr(self, 'text_size_mode', 'auto') == 'custom':
                    # 自定义模式：始终使用自定义字体大小
                    size = getattr(self, 'custom_font_size', 14)
                elif getattr(self, 'was_manually_resized', False):
                    # 被手动调整过：字体大小跟随框子大小
                    size = max(8, int(h * 0.5))
                else:
                    # 默认模式：让文字大小适应框子大小
                    size = max(10, min(36, int(h * 0.4)))  # 根据框子高度计算合适的字体大小
                
                # Save current painter state
                painter.save()
                
                # Set font with proper rendering
                font = QFont("Microsoft YaHei", size)
                font.setBold(True)  # Make text bold for better visibility
                painter.setFont(font)
                
                # Use high contrast color for text - ensure it's visible
                text_color = self.color
                if text_color.lightness() > 240:  # If too light, use dark color
                    text_color = QColor(0, 0, 0)  # Black
                elif text_color.lightness() < 40:  # If too dark, ensure it's not too dark
                    text_color = QColor(255, 255, 255)  # White
                
                # 不绘制任何背景，保持全透明
                # 直接绘制文字，不需要轮廓效果
                text_rect = rect.adjusted(6, 6, -6, -6)
                
                # 绘制文字主体（使用原始颜色）
                painter.setPen(QPen(text_color, 1))
                
                # 显示正在编辑的文本（如果在内联编辑模式）
                display_text = self.text_content
                if hasattr(painter.device(), 'inline_editing') and painter.device().inline_editing and hasattr(painter.device(), 'editing_text_item') and painter.device().editing_text_item == self:
                    display_text = painter.device().text_input_buffer
                    
                    # 检查文本是否超出框子，如果超出则自动扩展
                    if hasattr(painter.device(), '_auto_expand_text_box'):
                        painter.device()._auto_expand_text_box(self, font, display_text)
                        # 重新计算rect和text_rect
                        rect = QRect(self.points[0], self.points[-1]).normalized()
                        text_rect = rect.adjusted(6, 6, -6, -6)
                    
                    # 绘制文字选择高亮效果
                    if (hasattr(painter.device(), 'text_selection_start') and 
                        hasattr(painter.device(), 'text_selection_end') and 
                        painter.device().text_selection_start != painter.device().text_selection_end):
                        
                        # 计算选择区域的字符位置
                        start_sel = min(painter.device().text_selection_start, painter.device().text_selection_end)
                        end_sel = max(painter.device().text_selection_start, painter.device().text_selection_end)
                        
                        # 绘制选择背景高亮
                        font_metrics = painter.fontMetrics()
                        char_width = font_metrics.averageCharWidth()
                        char_height = font_metrics.height()
                        
                        # 计算选择区域的像素位置（简化版本）
                        sel_start_x = text_rect.left() + start_sel * char_width
                        sel_width = (end_sel - start_sel) * char_width
                        
                        # 绘制蓝色选择背景
                        selection_rect = QRect(int(sel_start_x), text_rect.top(), 
                                             int(sel_width), char_height)
                        painter.fillRect(selection_rect, QColor(0, 120, 215, 100))  # 半透明蓝色
                    
                    # 添加光标显示
                    cursor_pos = painter.device().cursor_position
                    if cursor_pos <= len(display_text):
                        display_text = display_text[:cursor_pos] + '|' + display_text[cursor_pos:]
                    
                    # 修复4: 添加输入法预编辑文本显示（拼音候选）
                    if (hasattr(painter.device(), 'preedit_text') and 
                        painter.device().preedit_text):
                        preedit_text = painter.device().preedit_text
                        preedit_cursor = getattr(painter.device(), 'preedit_cursor_pos', 0)
                        
                        # 将预编辑文本插入到光标位置，并用特殊颜色显示
                        if cursor_pos <= len(display_text) - 1:  # 减去1是因为上面添加了光标字符
                            # 移除之前添加的光标字符，重新构建显示文本
                            base_text = painter.device().text_input_buffer
                            display_text = (base_text[:painter.device().cursor_position] + 
                                          preedit_text + 
                                          base_text[painter.device().cursor_position:])
                            
                            # 在预编辑文本后添加光标
                            cursor_in_preedit = painter.device().cursor_position + preedit_cursor
                            display_text = (display_text[:cursor_in_preedit] + 
                                          '|' + 
                                          display_text[cursor_in_preedit:])
                
                # 绘制文字主体（使用原始颜色）
                painter.setPen(QPen(text_color, 1))
                painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, display_text)
                
                # Restore painter state
                painter.restore()

class RegionSelectorWithDrawing(QWidget):
    # Enhanced region selector with integrated drawing tools
    
    selection_completed = Signal(tuple)
    selection_cancelled = Signal()
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.logger.debug("RegionSelectorWithDrawing.__init__")
        
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.selecting = False
        self.selection_rect = QRect()
        self.screenshot_pixmap = None
        self.toolbar = None
        self.drawing_toolbar = None
        self.result = None
        self.screen_rect = QRect()
        
        # Enhanced interaction states
        self.dragging = False
        self.resizing = False
        self.resize_handle = None
        self.drag_offset = QPoint()
        self.hover_handle = None
        
        # Handle settings
        self.HANDLE_SIZE = 10
        self.HANDLE_MARGIN = 5
        self.MIN_SELECTION_SIZE = 20
        
        # Material Design colors
        self.MD3_PRIMARY = QColor(103, 80, 164)
        self.MD3_ON_PRIMARY = QColor(255, 255, 255)
        self.MD3_SURFACE = QColor(255, 255, 255)
        self.MD3_SUCCESS = QColor(76, 175, 80)
        self.MD3_ERROR = QColor(244, 67, 54)
        self.MD3_ON_SURFACE = QColor(28, 27, 31)
        self.MD3_OUTLINE = QColor(121, 116, 126)
        
        # Drawing tools state
        self.drawing_mode = False
        self.current_tool = "select"  # select, pen, rectangle, circle, arrow, text
        self.drawing_items = []  # Store drawn items
        self.current_drawing_item = None
        self.drawing_start_point = None
        self.drawing_color = QColor(255, 0, 0)  # Red default
        self.drawing_width = 3
        self.undo_stack = []
        self.redo_stack = []
        self.text_input_mode = False
        self.text_input_pos = None
        # Text item interaction state
        self.active_text_item = None
        self.text_dragging = False
        self.text_resizing = False
        self.text_drag_start = QPoint()
        self.text_resize_handle = None
        
        # 内联文本编辑状态
        self.inline_editing = False
        self.editing_text_item = None
        self.text_input_buffer = ""
        self.cursor_position = 0
        
        # 双击检测
        self.last_click_time = 0
        self.last_click_pos = QPoint()
        self.double_click_threshold = 300  # 毫秒
        
        # 修复3: 输入法支持 - 强化中文输入支持
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_KeyCompression, True)  # 启用按键压缩
        self.setAcceptDrops(False)  # 禁用拖放，避免输入法冲突
        
        # 修复：输入法预编辑支持（显示拼音候选）
        self.preedit_text = ""  # 输入法预编辑文本
        self.preedit_cursor_pos = 0  # 预编辑光标位置
        
        # 修复5: 文字选择和编辑功能
        self.text_selection_mode = False
        self.text_selection_start = 0
        self.text_selection_end = 0
        self.selected_text_item = None
        self.selection_drag_start = QPoint()
        
        # 新增：长按检测状态
        self.text_press_timer = None
        self.text_press_start_pos = QPoint()
        self.text_press_threshold = 100  # 100毫秒长按阈值（在80-130范围内的最佳平衡点）
        self.is_long_pressing = False
        
        # 文本工具点击/拖动检测
        self.text_tool_start_pos = QPoint()
        self.text_tool_is_dragging = False
        self.text_tool_drag_threshold = 5  # 5像素的拖动闾值
        
        # 工具栏组件初始化
        self.tool_buttons = None
        self.color_btn = None
        self.color_menu = None
        self.size_btn = None
        self.size_menu = None
        
    def select_region(self):
        # Show enhanced region selection overlay with integrated drawing tools
        self.logger.debug("Starting region selection with drawing tools")
        try:
            self.logger.debug("Getting QApplication through QtManager")
            app = get_qt_app()
            self.logger.debug("Got QApplication instance")
            
            # Get screen geometry for boundary checks
            try:
                # Safer screen access with fallback
                if hasattr(app, 'primaryScreen') and app.primaryScreen():
                    self.screen_rect = app.primaryScreen().geometry()
                else:
                    # Fallback to default screen size
                    self.screen_rect = QRect(0, 0, 1920, 1080)
            except Exception:
                # Final fallback
                self.screen_rect = QRect(0, 0, 1920, 1080)
            self.logger.debug(f"Screen geometry: {self.screen_rect}")
            
            # Capture screenshot
            self.logger.debug("Taking screenshot with pyautogui")
            screenshot = pyautogui.screenshot()
            self.logger.debug(f"Screenshot size: {screenshot.size}")
            
            qt_image = ImageQt.ImageQt(screenshot)
            self.screenshot_pixmap = QPixmap.fromImage(qt_image)
            self.logger.debug("Screenshot converted to QPixmap")
            
            # Setup fullscreen overlay
            self.logger.debug("Setting up fullscreen overlay")
            self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
            self.setGeometry(self.screen_rect)
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            
            self.logger.debug("Calling showFullScreen()")
            self.showFullScreen()
            
            # Force process events to ensure window is shown
            self.logger.debug("Processing events to ensure window display")
            app.processEvents()
            
            # Verify window is visible
            if self.isVisible():
                self.logger.debug("Overlay shown successfully")
            else:
                self.logger.error("Window failed to show properly")
                return None
            
            # Enable smooth mouse tracking
            self.setMouseTracking(True)
            
            # 确保窗口可以接收键盘事件
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.setFocus()
            self.activateWindow()
            
            # Connect signals
            self.selection_completed.connect(self._on_selection_completed)
            self.selection_cancelled.connect(self._on_selection_cancelled)
            self.logger.debug("Signals connected")
            
            self.result = None
            
            # Event processing loop - no timeout to prevent auto-exit
            self.logger.debug("Starting event processing loop")
            start_time = time.time()
            loop_count = 0
            
            while self.result is None:
                try:
                    app.processEvents()
                    time.sleep(0.01)  # 10ms delay for smooth interaction
                    loop_count += 1
                    
                    # Check if window was closed
                    if not self.isVisible():
                        self.logger.debug("Window no longer visible, breaking loop")
                        break
                    
                    # Only break on explicit user action or window close
                    # Remove automatic timeout to prevent unwanted exits
                        
                except Exception as e:
                    self.logger.error(f"Error in event loop: {e}")
                    break
            
            elapsed_total = time.time() - start_time
            self.logger.debug(f"Event loop finished: {loop_count} iterations, {elapsed_total:.2f}s total")
            self.logger.debug(f"Region selection result: {self.result}")
            
            return self.result
            
        except Exception as e:
            self.logger.error(f"Region selection error: {e}")
            self.logger.exception("Region selection exception:")
            return None
    
    def paintEvent(self, event):
        # Highly optimized painting for smooth performance
        painter = QPainter(self)
        
        # Enable optimized rendering hints
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        
        # Only paint the update region for better performance
        update_rect = event.rect()
        
        # Draw screenshot background (only in update region)
        if self.screenshot_pixmap:
            painter.drawPixmap(update_rect.topLeft(), self.screenshot_pixmap, update_rect)
        
        # Draw overlay
        self._draw_overlay(painter)
        
        if not self.selection_rect.isEmpty():
            # Only draw if selection intersects with update region
            if self.selection_rect.intersects(update_rect):
                # Draw all drawing items
                self._draw_drawing_items(painter)
                
                self._draw_selection_border(painter)
                self._draw_resize_handles(painter)
                self._draw_info_overlay(painter)
                
                # Draw current drawing item if in progress
                if self.current_drawing_item and self.drawing_mode:
                    self.current_drawing_item.draw(painter)
    
    def _draw_drawing_items(self, painter):
        # Draw all completed drawing items
        for item in self.drawing_items:
            item.draw(painter)
    
    def _draw_overlay(self, painter):
        # Draw overlay with selection cutout
        overlay_color = QColor(0, 0, 0, 120)
        
        if self.selection_rect.isEmpty():
            # No selection - draw full overlay
            painter.fillRect(self.rect(), overlay_color)
        else:
            # Draw overlay around selection
            # Top area
            if self.selection_rect.top() > 0:
                top_rect = QRect(0, 0, self.width(), self.selection_rect.top())
                painter.fillRect(top_rect, overlay_color)
            
            # Bottom area
            if self.selection_rect.bottom() < self.height():
                bottom_rect = QRect(0, self.selection_rect.bottom() + 1, 
                                  self.width(), self.height() - self.selection_rect.bottom() - 1)
                painter.fillRect(bottom_rect, overlay_color)
            
            # Left area
            if self.selection_rect.left() > 0:
                left_rect = QRect(0, self.selection_rect.top(), 
                                self.selection_rect.left(), self.selection_rect.height())
                painter.fillRect(left_rect, overlay_color)
            
            # Right area
            if self.selection_rect.right() < self.width():
                right_rect = QRect(self.selection_rect.right() + 1, self.selection_rect.top(),
                                 self.width() - self.selection_rect.right() - 1, self.selection_rect.height())
                painter.fillRect(right_rect, overlay_color)
    
    def _draw_selection_border(self, painter):
        # Simple and clean selection border
        # Main border - thin and clean
        main_pen = QPen(QColor("#6750a4"), 1)  # Thin purple border
        main_pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(main_pen)
        painter.drawRect(self.selection_rect)
    
    def _draw_resize_handles(self, painter):
        # Selective icon-based resize handles - only show icons on specific corners
        handles = self._get_resize_handles()
        
        # Only show icons on right-top and left-bottom corners
        icon_handles = {
            'top_right': 'more_up_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg',
            'bottom_left': 'more_down_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg'
        }
        
        for handle_type, handle_rect in handles.items():
            center = handle_rect.center()
            
            # Check if this handle should have an icon
            has_icon = handle_type in icon_handles
            
            if has_icon:
                # Icon handles - more subtle and integrated
                if self.hover_handle == handle_type:
                    handle_size = 18
                    icon_opacity = 255
                    bg_opacity = 40
                else:
                    handle_size = 14
                    icon_opacity = 180
                    bg_opacity = 20
                
                # Very subtle background circle
                bg_rect = QRect(center.x() - handle_size//2, center.y() - handle_size//2,
                               handle_size, handle_size)
                
                # Soft background with transparency
                painter.setBrush(QBrush(QColor(248, 249, 255, bg_opacity)))
                painter.setPen(QPen(QColor(103, 80, 164, 60), 1))
                painter.drawEllipse(bg_rect)
                
                # Draw icon with transparency
                icon_path = get_resource_path(f"core/icons/dark/{icon_handles[handle_type]}")
                if os.path.exists(icon_path):
                    icon = QIcon(icon_path)
                    icon_size = handle_size - 2
                    icon_rect = QRect(center.x() - icon_size//2, center.y() - icon_size//2,
                                    icon_size, icon_size)
                    
                    # Create semi-transparent icon
                    painter.setOpacity(icon_opacity / 255.0)
                    icon.paint(painter, icon_rect)
                    painter.setOpacity(1.0)  # Reset opacity
            else:
                # Regular handles without icons - minimal design
                if self.hover_handle == handle_type:
                    handle_size = 8
                    handle_color = QColor("#6750a4")
                    border_width = 2
                else:
                    handle_size = 6
                    handle_color = QColor(103, 80, 164, 150)
                    border_width = 1
                
                # Small circular handle
                handle_rect_small = QRect(center.x() - handle_size//2, center.y() - handle_size//2,
                                        handle_size, handle_size)
                
                # Fill and border
                painter.setBrush(QBrush(QColor("#f8f9ff")))
                painter.setPen(QPen(handle_color, border_width))
                painter.drawEllipse(handle_rect_small)
    
    def _draw_info_overlay(self, painter):
        # Draw a single compact info badge with only size
        w = self.selection_rect.width()
        h = self.selection_rect.height()
        if w < 10 or h < 10:
            return
        info_text = f"{w} × {h}"
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        text_rect = painter.fontMetrics().boundingRect(info_text)
        padding = 8
        badge_w = text_rect.width() + padding * 2
        badge_h = text_rect.height() + padding
        x = self.selection_rect.left()
        y = self.selection_rect.top() - badge_h - 8
        if y < 10:
            y = self.selection_rect.top() + 8
        x = max(10, min(x, self.width() - badge_w - 10))
        y = max(10, min(y, self.height() - badge_h - 10))
        badge_rect = QRect(x, y, badge_w, badge_h)
        path = QPainterPath()
        path.addRoundedRect(badge_rect, 4, 4)
        painter.fillPath(path, QColor(248, 249, 255, 240))
        painter.setPen(QPen(QColor("#c0c0c0"), 1))
        painter.drawPath(path)
        painter.setPen(QPen(QColor("#333333")))
        tx = x + (badge_w - text_rect.width()) // 2
        ty = y + text_rect.height() + padding // 2
        painter.drawText(QPoint(tx, ty), info_text)
    
    def _get_resize_handles(self):
        # Get resize handle rectangles
        if self.selection_rect.isEmpty():
            return {}
        
        handles = {}
        margin = self.HANDLE_MARGIN
        size = self.HANDLE_SIZE
        
        rect = self.selection_rect
        
        # Corner handles
        handles['top_left'] = QRect(rect.left() - margin, rect.top() - margin, size, size)
        handles['top_right'] = QRect(rect.right() - size + margin, rect.top() - margin, size, size)
        handles['bottom_left'] = QRect(rect.left() - margin, rect.bottom() - size + margin, size, size)
        handles['bottom_right'] = QRect(rect.right() - size + margin, rect.bottom() - size + margin, size, size)
        
        # Edge handles
        handles['top'] = QRect(rect.center().x() - size//2, rect.top() - margin, size, size)
        handles['bottom'] = QRect(rect.center().x() - size//2, rect.bottom() - size + margin, size, size)
        handles['left'] = QRect(rect.left() - margin, rect.center().y() - size//2, size, size)
        handles['right'] = QRect(rect.right() - size + margin, rect.center().y() - size//2, size, size)
        
        return handles
    
    def _get_cursor_for_handle(self, handle_type):
        # Return appropriate cursor for handle
        cursors = {
            'top_left': Qt.CursorShape.SizeFDiagCursor,
            'top_right': Qt.CursorShape.SizeBDiagCursor,
            'bottom_left': Qt.CursorShape.SizeBDiagCursor,
            'bottom_right': Qt.CursorShape.SizeFDiagCursor,
            'top': Qt.CursorShape.SizeVerCursor,
            'bottom': Qt.CursorShape.SizeVerCursor,
            'left': Qt.CursorShape.SizeHorCursor,
            'right': Qt.CursorShape.SizeHorCursor,
        }
        return cursors.get(handle_type, Qt.CursorShape.ArrowCursor)
    
    def _auto_expand_text_box(self, text_item, font, text):
        """自动扩展文本框以适应文字内容"""
        if not text or len(text_item.points) < 2:
            return
        
        # 计算文字占用的实际尺寸
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        
        # 计算文字的边界矩形
        text_bounds = metrics.boundingRect(text)
        required_width = text_bounds.width() + 20  # 加上一些边距
        required_height = text_bounds.height() + 20
        
        # 获取当前文本框大小
        current_rect = QRect(text_item.points[0], text_item.points[-1]).normalized()
        
        # 检查是否需要扩展
        needs_expansion = False
        new_rect = QRect(current_rect)
        
        # 水平扩展（向右扩展）
        if required_width > current_rect.width():
            new_rect.setWidth(required_width)
            needs_expansion = True
        
        # 垂直扩展（向下扩展）
        if required_height > current_rect.height():
            new_rect.setHeight(required_height)
            needs_expansion = True
        
        # 如果需要扩展，更新文本项的点
        if needs_expansion:
            # 保持左上角不变，只扩展右下角
            text_item.points[1] = new_rect.bottomRight()
            
            # 确保不超出屏幕边界
            constrained_rect = self._constrain_to_screen(new_rect)
            text_item.points[0] = constrained_rect.topLeft()
            text_item.points[1] = constrained_rect.bottomRight()
    
    def _constrain_to_screen(self, rect):
        # Ensure rectangle stays within screen bounds
        constrained = QRect(rect)
        
        # Constrain position
        if constrained.left() < 0:
            constrained.moveLeft(0)
        if constrained.top() < 0:
            constrained.moveTop(0)
        if constrained.right() > self.screen_rect.width():
            constrained.moveRight(self.screen_rect.width())
        if constrained.bottom() > self.screen_rect.height():
            constrained.moveBottom(self.screen_rect.height())
        
        # Ensure minimum size
        if constrained.width() < self.MIN_SELECTION_SIZE:
            constrained.setWidth(self.MIN_SELECTION_SIZE)
        if constrained.height() < self.MIN_SELECTION_SIZE:
            constrained.setHeight(self.MIN_SELECTION_SIZE)
        
        # Final boundary check
        if constrained.right() > self.screen_rect.width():
            constrained.moveLeft(self.screen_rect.width() - constrained.width())
        if constrained.bottom() > self.screen_rect.height():
            constrained.moveTop(self.screen_rect.height() - constrained.height())
        
        return constrained
    
    def mousePressEvent(self, event):
        # Optimized mouse press handling for immediate response
        if event.button() == Qt.MouseButton.LeftButton:
            # 修复1: 如果正在内联编辑，检查是否点击在编辑区域内
            if self.inline_editing and self.editing_text_item:
                if len(self.editing_text_item.points) >= 2:
                    edit_rect = QRect(self.editing_text_item.points[0], self.editing_text_item.points[-1]).normalized()
                    if edit_rect.contains(event.pos()):
                        # 点击在编辑区域内，优先检查是否是长按拖动操作
                        # 按照项目规范：允许左键长按文字任意位置进行拖动
                        self.text_press_start_pos = event.pos()
                        self.is_long_pressing = False
                        
                        # 启动定时器检测长按
                        if self.text_press_timer:
                            self.text_press_timer.stop()
                        self.text_press_timer = QTimer()
                        self.text_press_timer.timeout.connect(lambda: self._on_long_press_detected(self.editing_text_item))
                        self.text_press_timer.setSingleShot(True)
                        self.text_press_timer.start(self.text_press_threshold)
                        return
                    else:
                        # 点击在编辑区域外，保存并结束编辑（而不是直接丢失文字）
                        self._finish_inline_text_editing()
                        # 继续处理点击事件
            
            # 检测双击编辑文本
            import time
            current_time = int(time.time() * 1000)  # 毫秒
            if (current_time - self.last_click_time < self.double_click_threshold and 
                (event.pos() - self.last_click_pos).manhattanLength() < 10):
                # 双击检测成功，查找是否点击在文本上
                for item in self.drawing_items:
                    if (getattr(item, "tool_type", "") == "text" and 
                        len(item.points) >= 2 and item.text_content):
                        rect = QRect(item.points[0], item.points[-1]).normalized()
                        if rect.contains(event.pos()):
                            # 双击文本，进入编辑模式
                            self._start_inline_text_editing(item)
                            return
            
            self.last_click_time = current_time
            self.last_click_pos = event.pos()
            if self.drawing_mode and not self.selection_rect.isEmpty():
                # 检查是否点击在已有文本框上（优先级高于创建新文本）
                clicked_on_text = False
                if self.selection_rect.contains(event.pos()):
                    for item in self.drawing_items:
                        if getattr(item, "tool_type", "") == "text" and len(item.points) >= 2:
                            r = QRect(item.points[0], item.points[-1]).normalized()
                            if r.adjusted(-12, -12, 12, 12).contains(event.pos()):
                                clicked_on_text = True
                                break
                
                # 只有在没有点击文本框时才处理文本工具操作
                if not clicked_on_text and self.current_tool == "text" and self.selection_rect.contains(event.pos()):
                    # 记录文本工具开始位置
                    self.text_tool_start_pos = event.pos()
                    self.text_tool_is_dragging = False
                    
                    # 暂时不创建文本项，等待确定是点击还是拖动
                    return
                
                # Start drawing for other tools (排除文本工具冲突)
                if not clicked_on_text and self.current_tool != "text" and self.selection_rect.contains(event.pos()):
                    self.current_drawing_item = DrawingItem(self.current_tool, self.drawing_color, self.drawing_width)
                    self.current_drawing_item.add_point(event.pos())
                    self.drawing_start_point = event.pos()
                    return
            
            if not self.selection_rect.isEmpty():
                # Check for handle interaction
                handles = self._get_resize_handles()
                for handle_type, handle_rect in handles.items():
                    if handle_rect.contains(event.pos()):
                        self.resizing = True
                        self.resize_handle = handle_type
                        self._hide_toolbar()
                        return
                
                # 恢复文本框交互功能：支持拖动和调整大小（移除工具限制）
                if self.selection_rect.contains(event.pos()):
                    for item in reversed(self.drawing_items):
                        if getattr(item, "tool_type", "") == "text" and len(item.points) >= 2:
                            r = QRect(item.points[0], item.points[-1]).normalized()
                            hs = 12  # 扩大手柄触发范围从6增加到12
                            
                            # 检查四角手柄（扩大触发范围）
                            tl = QRect(r.left()-hs, r.top()-hs, hs*2, hs*2)  # 左上
                            tr = QRect(r.right()-hs, r.top()-hs, hs*2, hs*2)  # 右上
                            bl = QRect(r.left()-hs, r.bottom()-hs, hs*2, hs*2)  # 左下
                            br = QRect(r.right()-hs, r.bottom()-hs, hs*2, hs*2)  # 右下
                            
                            # 扩大文本内容区域的触发范围
                            expanded_text_area = r.adjusted(-8, -8, 8, 8)  # 向外扩展8像素
                            bl = QRect(r.left()-hs, r.bottom()-hs, hs*2, hs*2)  # 左下
                            br = QRect(r.right()-hs, r.bottom()-hs, hs*2, hs*2)  # 右下
                            
                            # 检测手柄点击
                            if tl.contains(event.pos()):
                                self.active_text_item = item
                                self.text_resizing = True
                                self.text_resize_handle = "tl"
                                self.text_drag_start = event.pos()
                                item.was_manually_resized = True  # 标记为手动调整
                                self._hide_toolbar()
                                return
                            elif tr.contains(event.pos()):
                                self.active_text_item = item
                                self.text_resizing = True
                                self.text_resize_handle = "tr"
                                self.text_drag_start = event.pos()
                                item.was_manually_resized = True
                                self._hide_toolbar()
                                return
                            elif bl.contains(event.pos()):
                                self.active_text_item = item
                                self.text_resizing = True
                                self.text_resize_handle = "bl"
                                self.text_drag_start = event.pos()
                                item.was_manually_resized = True
                                self._hide_toolbar()
                                return
                            elif br.contains(event.pos()):
                                self.active_text_item = item
                                self.text_resizing = True
                                self.text_resize_handle = "br"
                                self.text_drag_start = event.pos()
                                item.was_manually_resized = True
                                self._hide_toolbar()
                                return
                            elif expanded_text_area.contains(event.pos()):
                                # 点击在扩大的文本区域内，开始长按检测拖动
                                self.text_press_start_pos = event.pos()
                                self.is_long_pressing = False
                                
                                # 启动定时器检测长按
                                if self.text_press_timer:
                                    self.text_press_timer.stop()
                                self.text_press_timer = QTimer()
                                self.text_press_timer.timeout.connect(lambda: self._on_long_press_detected(item))
                                self.text_press_timer.setSingleShot(True)
                                self.text_press_timer.start(self.text_press_threshold)
                                return
                # Fallback: selection drag
                if self.selection_rect.contains(event.pos()):
                    self.dragging = True
                    self.drag_offset = event.pos() - self.selection_rect.topLeft()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                    self._hide_toolbar()
                    return
            
            # Start new selection with immediate visual feedback
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.selecting = True
            self.setCursor(Qt.CursorShape.CrossCursor)
            self._hide_toolbar()
            
            # Create initial selection rect immediately
            self.selection_rect = QRect(self.start_point, self.end_point).normalized()
            # Force immediate update
            self.update()
    
    def _on_long_press_detected(self, text_item):
        """长按检测成功，开始拖动模式"""
        self.is_long_pressing = True
        self.active_text_item = text_item
        self.text_dragging = True
        self.text_drag_start = self.text_press_start_pos
        # 修复：拖动文本框时不隐藏工具条，保持工具条可见
        # self._hide_toolbar()  # 注释掉，保持工具条显示
        # 更改光标为拖动样式
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
    
    def mouseMoveEvent(self, event):
        # Ultra-responsive mouse move handling
        
        # 长按拖动检测：如果移动距离太大，取消长按
        if (self.text_press_timer and self.text_press_timer.isActive() and 
            not self.text_press_start_pos.isNull()):
            distance = (event.pos() - self.text_press_start_pos).manhattanLength()
            if distance > 10:  # 10像素的移动阈值
                self.text_press_timer.stop()
                self.text_press_timer = None
        
        # 文本工具拖动检测（只在绘制模式下且不与现有文本框冲突时触发）
        if (self.drawing_mode and self.current_tool == "text" and 
            hasattr(self, 'text_tool_start_pos') and 
            not self.text_tool_start_pos.isNull() and 
            not self.text_tool_is_dragging):
            # 检查是否超出拖动闾值
            distance = (event.pos() - self.text_tool_start_pos).manhattanLength()
            if distance > self.text_tool_drag_threshold:
                self.text_tool_is_dragging = True
                # 开始拖动，创建文本项
                self.current_drawing_item = DrawingItem(self.current_tool, self.drawing_color, self.drawing_width)
                self.current_drawing_item.add_point(self.text_tool_start_pos)
                self.drawing_start_point = self.text_tool_start_pos
        
        if self.drawing_mode and self.current_drawing_item:
            # Continue drawing
            self.current_drawing_item.add_point(event.pos())
            self.update()
            return
        
        # 禁用文字鼠标拖拽选择处理（避免与拖动整体位置冲突）
        # if self.text_mouse_selecting and self.inline_editing and self.editing_text_item:
        #     ... 原有拖拽选择逻辑已被禁用
        
        # Text item drag/resize updates
        if self.text_dragging and self.active_text_item and len(self.active_text_item.points) >= 2:
            start = self.active_text_item.points[0]
            end = self.active_text_item.points[-1]
            r = QRect(start, end).normalized()
            
            # 修复2: 使用精确的增量位移计算，完全避免累积误差
            delta = event.pos() - self.text_drag_start
            
            # 直接基于当前位置计算新位置，避免累积漂移
            new_rect = QRect(r.topLeft() + delta, r.size())
            new_rect = self._constrain_to_screen(new_rect)
            
            # 更新位置
            self.active_text_item.points[0] = new_rect.topLeft()
            self.active_text_item.points[-1] = new_rect.bottomRight()
            
            # 关键修复：立即更新拖拽起始点，防止位移累积
            self.text_drag_start = event.pos()
            
            self.update()
            return
        if self.text_resizing and self.active_text_item and len(self.active_text_item.points) >= 2:
            start = self.active_text_item.points[0]
            end = self.active_text_item.points[-1]
            r = QRect(start, end).normalized()
            
            # 使用相对位置精确调整尺寸
            current_pos = event.pos()
            
            # 计算新的矩形边界
            new_rect = QRect(r)
            
            # 根据不同的手柄调整对应的边界
            if self.text_resize_handle == "tl":  # 左上
                new_rect.setTopLeft(current_pos)
            elif self.text_resize_handle == "tr":  # 右上
                new_rect.setTopRight(current_pos)
            elif self.text_resize_handle == "bl":  # 左下
                new_rect.setBottomLeft(current_pos)
            elif self.text_resize_handle == "br":  # 右下
                new_rect.setBottomRight(current_pos)
            elif self.text_resize_handle == "tm":  # 上中
                new_rect.setTop(current_pos.y())
            elif self.text_resize_handle == "bm":  # 下中
                new_rect.setBottom(current_pos.y())
            elif self.text_resize_handle == "lm":  # 左中
                new_rect.setLeft(current_pos.x())
            elif self.text_resize_handle == "rm":  # 右中
                new_rect.setRight(current_pos.x())
            
            # 保证最小尺寸
            if new_rect.width() < self.MIN_SELECTION_SIZE:
                if self.text_resize_handle in ("tl", "bl", "lm"):
                    new_rect.setLeft(new_rect.right() - self.MIN_SELECTION_SIZE)
                else:
                    new_rect.setRight(new_rect.left() + self.MIN_SELECTION_SIZE)
            
            if new_rect.height() < self.MIN_SELECTION_SIZE:
                if self.text_resize_handle in ("tl", "tr", "tm"):
                    new_rect.setTop(new_rect.bottom() - self.MIN_SELECTION_SIZE)
                else:
                    new_rect.setBottom(new_rect.top() + self.MIN_SELECTION_SIZE)
            
            # 应用屏幕约束
            new_rect = self._constrain_to_screen(new_rect.normalized())
            
            # 更新文本项的位置
            self.active_text_item.points[0] = new_rect.topLeft()
            self.active_text_item.points[-1] = new_rect.bottomRight()
            self.update()
            return

        if self.selecting:
            # Immediate selection updates
            self.end_point = event.pos()
            # Update selection rect directly for immediate response
            old_rect = self.selection_rect
            self._update_selection_rect()
            # Only update if rect actually changed
            if old_rect != self.selection_rect:
                self.update()
        elif self.resizing and self.resize_handle:
            # Immediate resizing feedback
            old_rect = self.selection_rect
            self._resize_selection(event.pos())
            if old_rect != self.selection_rect:
                self.update()
        elif self.dragging:
            # Immediate dragging feedback
            old_rect = self.selection_rect
            new_top_left = event.pos() - self.drag_offset
            new_rect = QRect(new_top_left, self.selection_rect.size())
            self.selection_rect = self._constrain_to_screen(new_rect)
            if old_rect != self.selection_rect:
                self.update()
        else:
            # Minimal hover updates
            old_hover = self.hover_handle
            self._update_hover_state(event.pos())
            if old_hover != self.hover_handle:
                # Use partial update for hover changes
                self.update()
    
    def mouseReleaseEvent(self, event):
        # Clean mouse release handling with drawing support
        if event.button() == Qt.MouseButton.LeftButton:
            # 重置长按状态
            if self.text_press_timer:
                self.text_press_timer.stop()
                self.text_press_timer = None
            
            # 如果是短按并且不是拖动，可能是正常点击
            if (not self.is_long_pressing and 
                not self.text_press_start_pos.isNull() and
                (event.pos() - self.text_press_start_pos).manhattanLength() < 10):
                # 短按点击，检查是否点击在文本上进入编辑模式
                for item in self.drawing_items:
                    if (getattr(item, "tool_type", "") == "text" and 
                        len(item.points) >= 2 and item.text_content):
                        rect = QRect(item.points[0], item.points[-1]).normalized()
                        if rect.contains(event.pos()):
                            self._start_inline_text_editing(item)
                            break
            
            self.is_long_pressing = False
            self.text_press_start_pos = QPoint()
            
            # Finish text interactions first
            if self.text_dragging or self.text_resizing:
                self.text_dragging = False
                self.text_resizing = False
                self.active_text_item = None
                self.text_resize_handle = None
                self.update()
                return
            if self.drawing_mode and self.current_drawing_item:
                # Finish drawing
                self.current_drawing_item.add_point(event.pos())
                # For text tool, start inline editing instead of dialog
                if self.current_tool == "text":
                    try:
                        # 对于文本工具，直接进入内联编辑模式
                        self.current_drawing_item.text_content = ""
                        self._start_inline_text_editing(self.current_drawing_item)
                    except Exception as e:
                        self.logger.error(f"Text input error: {e}")
                self.drawing_items.append(self.current_drawing_item)
                self.undo_stack.append(self.current_drawing_item)
                self.redo_stack.clear()
                self.current_drawing_item = None
                
                # 重置文本工具状态
                self.text_tool_start_pos = QPoint()
                self.text_tool_is_dragging = False
                
                self.update()
                return
            
            # 处理文本工具的点击（非拖动）
            if (self.current_tool == "text" and 
                hasattr(self, 'text_tool_start_pos') and 
                not self.text_tool_start_pos.isNull() and 
                not self.text_tool_is_dragging):
                # 这是一个点击，在鼠标位置创建默认大小的文本框
                self._handle_text_input(self.text_tool_start_pos)
                
                # 重置文本工具状态
                self.text_tool_start_pos = QPoint()
                self.text_tool_is_dragging = False
                
                self.update()
                return
            
            if self.selecting:
                self.selecting = False
                self.end_point = event.pos()
                self._update_selection_rect()
                if not self.selection_rect.isEmpty():
                    # 选择完成后确保窗口保持焦点，可以接收键盘事件
                    self.setFocus()
                    self.activateWindow()
                    self._show_integrated_toolbar()
            elif self.resizing:
                self.resizing = False
                self.resize_handle = None
                if not self.selection_rect.isEmpty():
                    # 调整大小完成后确保窗口保持焦点
                    self.setFocus()
                    self.activateWindow()
                    self._show_integrated_toolbar()
            elif self.dragging:
                self.dragging = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
                if not self.selection_rect.isEmpty():
                    # 拖拽完成后确保窗口保持焦点
                    self.setFocus()
                    self.activateWindow()
                    self._show_integrated_toolbar()
            
            self.update()
    
    def _resize_selection(self, pos):
        # Resize with boundary constraints
        if not self.resize_handle:
            return
        
        rect = QRect(self.selection_rect)
        
        if 'left' in self.resize_handle:
            rect.setLeft(pos.x())
        if 'right' in self.resize_handle:
            rect.setRight(pos.x())
        if 'top' in self.resize_handle:
            rect.setTop(pos.y())
        if 'bottom' in self.resize_handle:
            rect.setBottom(pos.y())
        
        # Apply constraints
        self.selection_rect = self._constrain_to_screen(rect.normalized())
    
    def _update_hover_state(self, pos):
        # 优化的鼠标悬停状态更新 - 移除手工具影响，让光标自动变化
        if self.selection_rect.isEmpty():
            if self.cursor().shape() != Qt.CursorShape.CrossCursor:
                self.setCursor(Qt.CursorShape.CrossCursor)
            return
        
        # 优先检查文本框的悬停状态（不受手工具影响）
        for item in reversed(self.drawing_items):
            if getattr(item, "tool_type", "") == "text" and len(item.points) >= 2:
                r = QRect(item.points[0], item.points[-1]).normalized()
                hs = 12  # 与上面的触发范围保持一致
                
                # 检查四角手柄悬停
                tl = QRect(r.left()-hs, r.top()-hs, hs*2, hs*2)
                tr = QRect(r.right()-hs, r.top()-hs, hs*2, hs*2)
                bl = QRect(r.left()-hs, r.bottom()-hs, hs*2, hs*2)
                br = QRect(r.right()-hs, r.bottom()-hs, hs*2, hs*2)
                
                if tl.contains(pos) or br.contains(pos):
                    # 左上或右下角：斜对角缩放
                    if self.cursor().shape() != Qt.CursorShape.SizeFDiagCursor:
                        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                    return
                elif tr.contains(pos) or bl.contains(pos):
                    # 右上或左下角：新对角缩放
                    if self.cursor().shape() != Qt.CursorShape.SizeBDiagCursor:
                        self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                    return
                elif r.adjusted(-8, -8, 8, 8).contains(pos):
                    # 文本内容区域：显示开放手势（可拖动）
                    if self.cursor().shape() != Qt.CursorShape.OpenHandCursor:
                        self.setCursor(Qt.CursorShape.OpenHandCursor)
                    return
        
        # 检查区域截图框的手柄
        handles = self._get_resize_handles()
        self.hover_handle = None
        
        for handle_type, handle_rect in handles.items():
            if handle_rect.contains(pos):
                self.hover_handle = handle_type
                cursor_shape = self._get_cursor_for_handle(handle_type)
                if self.cursor().shape() != cursor_shape:
                    self.setCursor(QCursor(cursor_shape))
                return
        
        # 检查选择区域
        if self.selection_rect.contains(pos):
            # 选择区域内：显示开放手势（可拖动）
            if self.cursor().shape() != Qt.CursorShape.OpenHandCursor:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            # 选择区域外：显示十字光标（创建新选择）
            if self.cursor().shape() != Qt.CursorShape.CrossCursor:
                self.setCursor(Qt.CursorShape.CrossCursor)
    
    def _update_selection_rect(self):
        # Update selection with constraints
        rect = QRect(self.start_point, self.end_point).normalized()
        self.selection_rect = self._constrain_to_screen(rect)
    
    def _undo_drawing(self):
        # Undo last drawing action
        if self.undo_stack:
            item = self.undo_stack.pop()
            self.redo_stack.append(item)
            if item in self.drawing_items:
                self.drawing_items.remove(item)
            self.update()
    
    def _redo_drawing(self):
        # Redo last undone drawing action
        if self.redo_stack:
            item = self.redo_stack.pop()
            self.undo_stack.append(item)
            self.drawing_items.append(item)
            self.update()
    
    def _show_integrated_toolbar(self):
        # Show integrated drawing toolbar with fixed styling
        if self.toolbar:
            self.toolbar.hide()
            self.toolbar.deleteLater()
        
        # Create main toolbar container
        self.toolbar = QWidget(self)
        self.toolbar.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.toolbar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # 设置工具栏不获取焦点，确保主窗口保持焦点
        self.toolbar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Enhanced shadow effect
        effect = QGraphicsDropShadowEffect(self.toolbar)
        effect.setBlurRadius(15)
        effect.setOffset(0, 4)
        effect.setColor(QColor(0, 0, 0, 100))
        self.toolbar.setGraphicsEffect(effect)
        
        # Main layout
        main_layout = QHBoxLayout(self.toolbar)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left logo section
        logo_section = QWidget()
        logo_section.setFixedWidth(80)
        logo_section.setStyleSheet("""
            QWidget {
                background: #f8f9ff;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                border: none;
            }
        """)
        
        # Logo layout
        logo_layout = QVBoxLayout(logo_section)
        logo_layout.setContentsMargins(8, 8, 8, 8)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Use black bird logo
        logo_label = QLabel()
        logo_loaded = False
        
        try:
            if resource_exists("assets/images/FullBlack.png"):
                pixmap = QPixmap(ResourcePaths.images("FullBlack.png"))
                scaled_pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
                logo_loaded = True
            elif resource_exists("assets/images/logo1.png"):
                pixmap = QPixmap(ResourcePaths.images("logo1.png"))
                scaled_pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
                logo_loaded = True
        except Exception:
            pass
        
        if not logo_loaded:
            logo_label.setText("🐦")
            logo_label.setStyleSheet("""
                QLabel {
                    color: #333333;
                    font-size: 16px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                }
            """)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_layout.addWidget(logo_label)
        
        # Right function section - FIXED STYLING
        function_section = QWidget()
        function_section.setStyleSheet("""
            QWidget {
                background: #f8f9ff;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                border: none;
            }
            QToolButton {
                background: transparent;
                color: #333333;
                border: none;
                padding: 6px;
                border-radius: 4px;
                min-width: 28px;
                min-height: 28px;
                font-size: 10px;
                font-weight: 500;
            }
            QToolButton:hover {
                background: rgba(0, 0, 0, 8);
                border: 1px solid rgba(0, 0, 0, 15);
            }
            QToolButton:pressed {
                background: rgba(0, 0, 0, 15);
            }
            QToolButton:checked {
                background: rgba(0, 0, 0, 12);
                border: 1px solid rgba(0, 0, 0, 20);
            }
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(0, 0, 0, 8), 
                    stop:1 rgba(0, 0, 0, 15));
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4CAF50, 
                    stop:1 #45a049);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: url(assets/images/slider_handle.svg);
                background-repeat: no-repeat;
                background-position: center;
                border: 2px solid rgba(0, 0, 0, 20);
                width: 20px;
                height: 20px;
                border-radius: 10px;
                margin: -8px 0;
                background-color: #f8f9ff;
            }
            QSlider::handle:horizontal:hover {
                background-color: #ffffff;
                border: 2px solid rgba(0, 0, 0, 40);
                transform: scale(1.1);
            }
            QSlider::handle:horizontal:pressed {
                background-color: #e8e9ef;
                border: 2px solid rgba(0, 0, 0, 60);
            }
            QFrame {
                background: rgba(0, 0, 0, 8);
                border: none;
                max-width: 1px;
            }
        """)
        
        # Function section layout
        layout = QHBoxLayout(function_section)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 6, 8, 6)
        
        # Add sections to main layout
        main_layout.addWidget(logo_section)
        main_layout.addWidget(function_section)
        
        # Tool buttons with dark SVG icons for light background
        tools = [
            ("select", "gesture_select_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg", "Select Tool"),
            ("pen", "ink_pen_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg", "Pen Tool"),
            ("rectangle", "crop_square_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg", "Rectangle Tool"),
            ("circle", "circle_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg", "Circle Tool"),
            ("arrow", "stat_minus_1_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg", "Arrow Tool"),
            ("text", "text_fields_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg", "Text Tool"),
        ]
        
        self.tool_buttons = QButtonGroup()
        for tool_id, icon_filename, tooltip in tools:
            btn = QToolButton()
            
            # 设置按钮不获取焦点，确保主窗口保持焦点
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            
            # Load SVG icon if exists, otherwise use fallback
            icon_path = get_resource_path(f"core/icons/dark/{icon_filename}")
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(20, 20))
            else:
                # Fallback to text if icon doesn't exist
                fallback_icons = {
                    "select": "⚪", "pen": "✏️", "rectangle": "⬜", 
                    "circle": "⭕", "arrow": "➡️", "text": "📝"
                }
                btn.setText(fallback_icons.get(tool_id, "🔧"))
            
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setChecked(tool_id == self.current_tool)
            btn.clicked.connect(lambda checked, t=tool_id: self._set_drawing_tool(t))
            self.tool_buttons.addButton(btn)
            layout.addWidget(btn)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: rgba(70, 70, 70, 180);")
        layout.addWidget(separator)
        
        # Color picker button with dropdown menu
        color_btn = QToolButton()
        color_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 不获取焦点
        color_icon_path = get_resource_path("core/icons/dark/brush_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg")
        if os.path.exists(color_icon_path):
            color_btn.setIcon(QIcon(color_icon_path))
            color_btn.setIconSize(QSize(20, 20))
        else:
            color_btn.setText("🎨")
        
        # Create color menu
        color_menu = QMenu()
        color_menu.setStyleSheet("""
            QMenu {
                background: #f8f9ff;
                border: 1px solid rgba(0, 0, 0, 20);
                border-radius: 6px;
                padding: 8px;
                min-width: 200px;
                color: #333333;
            }
            QMenu::item {
                background: transparent;
                color: #333333;
                padding: 4px 8px;
                border-radius: 4px;
                min-height: 24px;
            }
            QMenu::item:selected {
                background: rgba(0, 0, 0, 8);
                color: #333333;
            }
            QMenu::item:pressed {
                background: rgba(0, 0, 0, 15);
                color: #333333;
            }
        """)
        
        # Add color options with visual indicators
        colors = [
            ("Red", QColor(255, 0, 0)),
            ("Green", QColor(0, 255, 0)),
            ("Blue", QColor(0, 0, 255)),
            ("Yellow", QColor(255, 255, 0)),
            ("Orange", QColor(255, 165, 0)),
            ("Purple", QColor(128, 0, 128)),
            ("Pink", QColor(255, 192, 203)),
            ("Cyan", QColor(0, 255, 255)),
            ("Black", QColor(0, 0, 0)),
            ("White", QColor(255, 255, 255)),
            ("Custom...", None)
        ]
        
        for color_name, color_value in colors:
            action = QAction(color_name, color_menu)
            if color_value:
                # Create color icon
                pixmap = QPixmap(16, 16)
                pixmap.fill(color_value)
                action.setIcon(QIcon(pixmap))
                action.triggered.connect(lambda checked, c=color_value: self._set_drawing_color(c))
            else:
                # Custom color option
                action.triggered.connect(self._choose_custom_color)
            color_menu.addAction(action)
        
        color_btn.setMenu(color_menu)
        color_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        color_btn.setStyleSheet("""
            QToolButton::menu-indicator {
                image: none;
                width: 0px;
                height: 0px;
            }
            QToolButton::menu-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
        """)
        color_btn.setToolTip("Choose Color")
        layout.addWidget(color_btn)
        
        # Store reference for updating
        self.color_btn = color_btn
        self.color_menu = color_menu
        
        # Brush size button with dropdown menu
        size_btn = QToolButton()
        size_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 不获取焦点
        size_icon_path = get_resource_path("core/icons/dark/motion_photos_on_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg")
        if os.path.exists(size_icon_path):
            size_btn.setIcon(QIcon(size_icon_path))
            size_btn.setIconSize(QSize(20, 20))
        else:
            size_btn.setText("●")
        
        # Create size menu
        size_menu = QMenu()
        size_menu.setStyleSheet("""
            QMenu {
                background: #f8f9ff;
                border: 1px solid rgba(0, 0, 0, 20);
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                background: transparent;
                color: #333333;
                padding: 6px 12px;
                border-radius: 4px;
                min-width: 60px;
            }
            QMenu::item:selected {
                background: rgba(0, 0, 0, 8);
            }
            QMenu::item:pressed {
                background: rgba(0, 0, 0, 15);
            }
        """)
        
        # Add size options - 扩大字体大小选择范围并支持自定义
        size_options = [
            ("8px", 8), ("10px", 10), ("12px", 12), ("14px", 14), ("16px", 16),
            ("18px", 18), ("20px", 20), ("24px", 24), ("28px", 28), ("32px", 32),
            ("36px", 36), ("40px", 40), ("48px", 48), ("56px", 56), ("64px", 64),
            ("72px", 72), ("80px", 80), ("90px", 90), ("100px", 100), ("Custom...", -1)
        ]
        
        for size_text, size_value in size_options:
            action = QAction(size_text, size_menu)
            action.setCheckable(True)
            action.setChecked(size_value == self.drawing_width)
            if size_value == -1:  # Custom option
                action.triggered.connect(self._choose_custom_font_size)
            else:
                action.triggered.connect(lambda checked, s=size_value: self._set_brush_size(s))
            size_menu.addAction(action)
        
        size_btn.setMenu(size_menu)
        size_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        size_btn.setStyleSheet("""
            QToolButton::menu-indicator {
                image: none;
                width: 0px;
                height: 0px;
            }
            QToolButton::menu-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
        """)
        size_btn.setToolTip(f"Brush Size ({self.drawing_width}px)")
        layout.addWidget(size_btn)
        
        # Store reference for updating
        self.size_btn = size_btn
        self.size_menu = size_menu
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFixedHeight(30)
        layout.addWidget(separator2)
        
        # Undo/Redo buttons with dark icons
        undo_btn = QToolButton()
        undo_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 不获取焦点
        undo_icon_path = get_resource_path("core/icons/dark/undo_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg")
        if os.path.exists(undo_icon_path):
            undo_btn.setIcon(QIcon(undo_icon_path))
            undo_btn.setIconSize(QSize(20, 20))
        else:
            undo_btn.setText("↶")
        undo_btn.setToolTip("Undo (Ctrl+Z)")
        undo_btn.clicked.connect(self._undo_drawing)
        layout.addWidget(undo_btn)
        
        redo_btn = QToolButton()
        redo_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 不获取焦点
        redo_icon_path = get_resource_path("core/icons/dark/redo_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg")
        if os.path.exists(redo_icon_path):
            redo_btn.setIcon(QIcon(redo_icon_path))
            redo_btn.setIconSize(QSize(20, 20))
        else:
            redo_btn.setText("↷")
        redo_btn.setToolTip("Redo (Ctrl+Y)")
        redo_btn.clicked.connect(self._redo_drawing)
        layout.addWidget(redo_btn)
        
        # Separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.VLine)
        separator3.setFixedHeight(30)
        layout.addWidget(separator3)
        
        # Action buttons with dark icons
        copy_btn = QToolButton()
        copy_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 不获取焦点
        copy_icon_path = get_resource_path("core/icons/dark/file_copy_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg")
        if os.path.exists(copy_icon_path):
            copy_btn.setIcon(QIcon(copy_icon_path))
            copy_btn.setIconSize(QSize(20, 20))
        else:
            copy_btn.setText("📋")
        copy_btn.setToolTip("Copy to Clipboard")
        copy_btn.clicked.connect(self._confirm_selection)
        layout.addWidget(copy_btn)
        
        save_btn = QToolButton()
        save_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 不获取焦点
        save_icon_path = get_resource_path("core/icons/dark/save_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg")
        if os.path.exists(save_icon_path):
            save_btn.setIcon(QIcon(save_icon_path))
            save_btn.setIconSize(QSize(20, 20))
        else:
            save_btn.setText("💾")
        save_btn.setToolTip("Save to File")
        save_btn.clicked.connect(self._save_selection)
        layout.addWidget(save_btn)
        
        cancel_btn = QToolButton()
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 不获取焦点
        cancel_icon_path = get_resource_path("core/icons/dark/close_24dp_000000_FILL0_wght400_GRAD0_opsz24.svg")
        if os.path.exists(cancel_icon_path):
            cancel_btn.setIcon(QIcon(cancel_icon_path))
            cancel_btn.setIconSize(QSize(20, 20))
        else:
            cancel_btn.setText("❌")
        cancel_btn.setToolTip("Cancel (Esc)")
        cancel_btn.clicked.connect(self._cancel_selection)
        layout.addWidget(cancel_btn)
        
        # Enhanced foolproof toolbar positioning with screen boundary protection
        base_toolbar_width = 520
        toolbar_height = 48
        margin = 10  # Increased margin for safety
        
        # Get actual screen dimensions with safety checks
        screen_width = max(800, self.width())  # Minimum safe width
        screen_height = max(600, self.height())  # Minimum safe height
        
        # Use screen_rect if available for more accurate bounds
        if hasattr(self, 'screen_rect') and not self.screen_rect.isEmpty():
            screen_width = self.screen_rect.width()
            screen_height = self.screen_rect.height()
        
        # Calculate safe dimensions
        max_toolbar_width = screen_width - (margin * 4)  # Extra margin for safety
        max_toolbar_height = screen_height - (margin * 4)
        
        # Force toolbar to fit within safe bounds
        toolbar_width = min(base_toolbar_width, max_toolbar_width)
        toolbar_height = min(toolbar_height, max_toolbar_height)
        
        # Ensure minimum viable size
        if toolbar_width < 200:
            toolbar_width = min(200, max_toolbar_width)
        if toolbar_height < 30:
            toolbar_height = min(30, max_toolbar_height)
        
        # Calculate center position with bounds checking
        selection_center_x = self.selection_rect.center().x()
        selection_bottom = self.selection_rect.bottom()
        selection_top = self.selection_rect.top()
        
        # Calculate ideal X position (centered on selection)
        ideal_x = selection_center_x - toolbar_width // 2
        
        # Calculate ideal Y position (below selection with gap)
        gap = 15
        ideal_y = selection_bottom + gap
        
        # 修复：增强工具条边界检查，防止出屏幕
        # 修复：进一步优化工具条边界保护，彻底解决超出屏幕问题
        safe_margin = 30  # 进一步增加安全边距到30像素
        
        # 首先确保工具条尺寸不会超出屏幕
        max_allowed_width = screen_width - (safe_margin * 2)
        max_allowed_height = screen_height - (safe_margin * 2)
        
        # 动态调整工具条尺寸
        if toolbar_width > max_allowed_width:
            toolbar_width = max_allowed_width
        if toolbar_height > max_allowed_height:
            toolbar_height = max_allowed_height
        
        # 重新计算理想位置（基于可能调整过的尺寸）
        ideal_x = selection_center_x - toolbar_width // 2
        
        # X轴严格边界控制
        min_x = safe_margin
        max_x = screen_width - toolbar_width - safe_margin
        toolbar_x = max(min_x, min(ideal_x, max_x))
        
        # Y轴智能定位：优先下方，空间不足时上方，都不行时居中
        min_y = safe_margin
        max_y = screen_height - toolbar_height - safe_margin
        
        if ideal_y <= max_y:
            # 下方有空间
            toolbar_y = ideal_y
        else:
            # 尝试上方
            above_y = selection_top - toolbar_height - gap
            if above_y >= min_y:
                toolbar_y = above_y
            else:
                # 上下都没空间，强制居中并确保可见
                toolbar_y = max(min_y, min(max_y, (screen_height - toolbar_height) // 2))
        
        # 最终强制边界检查，确保100%不出屏幕
        toolbar_x = max(safe_margin, min(toolbar_x, screen_width - toolbar_width - safe_margin))
        toolbar_y = max(safe_margin, min(toolbar_y, screen_height - toolbar_height - safe_margin))
        
        # 修复4: 确保工具栏始终保持可见和可访问
        self.toolbar.setGeometry(toolbar_x, toolbar_y, toolbar_width, toolbar_height)
        self.toolbar.show()
        self.toolbar.raise_()
        self.toolbar.activateWindow()  # 强制激活窗口
        
        # 确保主窗口继续保持焦点以接收键盘事件
        self.setFocus()
        self.activateWindow()
        
        # 防止工具栏在某些情况下消失
        QTimer.singleShot(100, lambda: self._ensure_toolbar_visible())
    
    def _ensure_toolbar_visible(self):
        # 修复4: 确保工具栏始终可见的辅助函数
        if self.toolbar and not self.toolbar.isVisible():
            self.toolbar.show()
            self.toolbar.raise_()
            self.toolbar.activateWindow()
    
    def _set_drawing_tool(self, tool):
        # Set current drawing tool
        self.current_tool = tool
        self.drawing_mode = (tool != "select")
        
        # Update cursor
        if self.drawing_mode:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        # Handle text tool special case
        if tool == "text":
            self.text_input_mode = True
        else:
            self.text_input_mode = False
    
    def _handle_text_input(self, pos):
        # Handle inline text input at specified position
        try:
            # Create text drawing item immediately
            text_item = DrawingItem("text", self.drawing_color, self.drawing_width)
            text_item.add_point(pos)
            # 修复6: 创建一个更大的默认文本框大小 (从120x30增大到250x80)
            default_end = QPoint(pos.x() + 250, pos.y() + 80)  # 更大的默认尺寸
            text_item.add_point(default_end)
            text_item.text_content = ""  # 空文本，将通过内联编辑添加
            
            # Add to drawing items immediately
            self.drawing_items.append(text_item)
            self.undo_stack.append(text_item)
            self.redo_stack.clear()
            
            # 进入内联编辑模式
            self._start_inline_text_editing(text_item)
            
            self.update()
        except Exception as e:
            self.logger.error(f"Text input error: {e}")
    
    def _set_drawing_color(self, color):
        # Set drawing color from menu selection
        self.drawing_color = color
        
        # Update button tooltip
        if hasattr(self, 'color_btn'):
            self.color_btn.setToolTip(f"Color: {color.name()}")
    
    def _choose_custom_color(self):
        # Open custom color picker dialog
        print("DEBUG: _choose_custom_color called")
        try:
            import sys
            import os
            # Add current directory to path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from modules.custom_color_dialog import CustomColorDialog
            print("DEBUG: CustomColorDialog imported successfully")
            
            # Create and show custom dialog
            dialog = CustomColorDialog(self.drawing_color, self)
            print("DEBUG: Dialog created")
            
            result = dialog.exec()
            print(f"DEBUG: Dialog result: {result}")
            
            if result == QDialog.DialogCode.Accepted:
                color = dialog.get_color()
                print(f"DEBUG: Selected color: {color}")
                if color and color.isValid():
                    self._set_drawing_color(color)
                    print("DEBUG: Color set successfully")
            else:
                print("DEBUG: Dialog was cancelled")
                
        except Exception as e:
            print(f"DEBUG: Error with custom dialog: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to system dialog
            print("DEBUG: Falling back to system dialog")
            color = QColorDialog.getColor(self.drawing_color, self, "Choose Color")
            if color.isValid():
                self._set_drawing_color(color)
    
    def _choose_custom_font_size(self):
        # 选择自定义字体大小
        from PySide6.QtWidgets import QInputDialog
        
        current_size = self.drawing_width if self.drawing_width <= 100 else 14
        size, ok = QInputDialog.getInt(
            self, 
            "自定义字体大小", 
            "请输入字体大小（PX）：",
            current_size, 8, 100, 1
        )
        
        if ok:
            self._set_brush_size(size, is_custom=True)
    
    def _auto_adjust_text_box_for_font_size(self, text_item, font_size):
        """根据字体大小自动调整文本框大小"""
        if not hasattr(text_item, 'text_content') or not text_item.text_content:
            return
        
        from PySide6.QtGui import QFontMetrics
        font = QFont("Microsoft YaHei", font_size)
        font.setBold(True)
        metrics = QFontMetrics(font)
        
        # 计算文本占用的实际尺寸
        text_bounds = metrics.boundingRect(text_item.text_content)
        required_width = text_bounds.width() + 40  # 增加边距
        required_height = text_bounds.height() + 40
        
        # 获取当前框子位置
        current_rect = QRect(text_item.points[0], text_item.points[-1]).normalized()
        
        # 保持左上角不变，调整右下角以适应新字体大小
        new_width = max(required_width, self.MIN_SELECTION_SIZE)
        new_height = max(required_height, self.MIN_SELECTION_SIZE)
        
        new_rect = QRect(
            current_rect.topLeft(),
            QSize(new_width, new_height)
        )
        
        # 确保不超出屏幕边界
        new_rect = self._constrain_to_screen(new_rect)
        
        # 更新文本框尺寸
        text_item.points[0] = new_rect.topLeft()
        text_item.points[-1] = new_rect.bottomRight()
    
    def _set_brush_size(self, size, is_custom=False):
        # Set brush size and update UI
        old_size = self.drawing_width
        self.drawing_width = size
        
        # 修复：字体大小设置逻辑 - 区分自定义和自动模式
        if self.inline_editing and self.editing_text_item:
            if is_custom:
                # 自定义模式：设置为自定义字体大小
                self.editing_text_item.text_size_mode = 'custom'
                self.editing_text_item.custom_font_size = size
            else:
                # 工具栏设置：使用工具栏字体大小
                self.editing_text_item.width = size
                if not getattr(self.editing_text_item, 'was_manually_resized', False):
                    # 如果没有被手动调整过，让框子跟着文本大小调整
                    self._auto_adjust_text_box_for_font_size(self.editing_text_item, size)
            
            # 重新绘制文本
            self.update()
        
        # Update tooltip
        if hasattr(self, 'size_btn'):
            self.size_btn.setToolTip(f"Brush Size ({size}px)")
        
        # Update menu checkmarks
        if hasattr(self, 'size_menu'):
            for action in self.size_menu.actions():
                action.setChecked(action.text() == f"{size}px")
    
    def _hide_toolbar(self):
        # Hide toolbar
        if self.toolbar:
            self.toolbar.hide()
    
    def _confirm_selection(self):
        # Confirm selection for copy with drawing overlay
        self.logger.debug("Confirming selection for copy")
        if not self.selection_rect.isEmpty():
            # Validate selection dimensions to prevent unpacking errors
            width = self.selection_rect.width()
            height = self.selection_rect.height()
            
            if width <= 0 or height <= 0:
                self.logger.debug("Invalid selection dimensions, cancelling")
                self.result = None
                self._close_app()
                return
            
            rect = (
                self.selection_rect.x(),
                self.selection_rect.y(),
                width,
                height
            )
            self.logger.debug(f"Confirming selection with rect: {rect}")
            png_path = None
            try:
                composite = self._create_composite_image()
                if composite:
                    import tempfile
                    import os
                    with tempfile.NamedTemporaryFile(prefix="zsnapr_sel_", suffix=".png", delete=False) as tf:
                        png_path = tf.name
                    # Convert QPixmap to QImage for proper cropping
                    composite_image = composite.toImage()
                    cropped_image = composite_image.copy(self.selection_rect)
                    # Ensure image has proper format before saving
                    if cropped_image.format() == cropped_image.Format.Format_Invalid:
                        cropped_image = cropped_image.convertToFormat(cropped_image.Format.Format_ARGB32)
                    # Save the cropped image with high quality
                    success = cropped_image.save(png_path)
                    self.logger.debug(f"Saved composite image: success={success}, size={cropped_image.size()}, format={cropped_image.format()}")
            except Exception as e:
                self.logger.error(f"Composite save error: {e}")
            self.result = (rect, "copy", png_path)
            self._close_app()
        else:
            self.logger.debug("Empty selection, cancelling")
            self.result = None
            self._close_app()
    
    def _save_selection(self):
        # Save selection to file with drawing overlay - 使用保存对话框
        self.logger.debug("Saving selection")
        if not self.selection_rect.isEmpty():
            # Validate selection dimensions to prevent unpacking errors
            width = self.selection_rect.width()
            height = self.selection_rect.height()
            
            if width <= 0 or height <= 0:
                self.logger.debug("Invalid selection dimensions, cancelling")
                self.result = None
                self._close_app()
                return
            
            rect = (
                self.selection_rect.x(),
                self.selection_rect.y(),
                width,
                height
            )
            self.logger.debug(f"Saving selection with rect: {rect}")
            
            # 直接返回save操作，让上层处理保存对话框
            self.result = (rect, "save")
            self._close_app()
        else:
            self.result = None
            self._close_app()
    
    def _create_composite_image(self):
        # Create a composite image with original screenshot + drawings
        if not self.screenshot_pixmap:
            return None
        
        # Create a copy of the original screenshot directly to avoid initialization issues
        composite = self.screenshot_pixmap.copy()
        
        painter = QPainter(composite)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        
        # Screenshot is already the background, just draw drawings on top
        
        # Draw all drawing items on top
        for item in self.drawing_items:
            item.draw(painter)
        
        # Draw current drawing item if in progress
        if self.current_drawing_item and self.drawing_mode:
            self.current_drawing_item.draw(painter)
        
        painter.end()
        return composite
    
    def _cancel_selection(self):
        # Cancel selection - 修复：确保能正确取消截图
        self.logger.debug("Cancelling selection")
        self.result = (None, "cancel", None)  # 明确标记为取消操作
        self._close_app()
    
    def _on_selection_completed(self, rect):
        # Handle completion signal
        self.logger.debug(f"Selection completed with rect: {rect}")
        self.result = rect
        self._close_app()
    
    def _on_selection_cancelled(self):
        # Handle cancellation signal
        self.logger.debug("Selection cancelled")
        self.result = None
        self._close_app()
    
    def _close_app(self):
        # Clean shutdown
        self.logger.debug("Closing region selector")
        if self.toolbar:
            self.logger.debug("Closing toolbar")
            self.toolbar.close()
            self.toolbar = None
        
        # Just close the window, don't quit the app
        self.logger.debug("Closing main window")
        self.close()
        self.logger.debug("Region selector closed")
    
    def _start_inline_text_editing(self, text_item):
        # 开始内联文本编辑
        self.inline_editing = True
        self.editing_text_item = text_item
        # 如果是编辑现有文本，加载现有内容
        self.text_input_buffer = text_item.text_content if hasattr(text_item, 'text_content') else ""
        self.cursor_position = len(self.text_input_buffer)
        
        # 设置光标为文本输入模式
        self.setCursor(Qt.CursorShape.IBeamCursor)
        
        # 启用键盘输入
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
    
    def _finish_inline_text_editing(self):
        # 结束内联文本编辑
        if self.inline_editing and self.editing_text_item:
            # 修复1: 只有在有内容时才保存文字，避免空文字导致文字丢失
            if self.text_input_buffer.strip():  # 有非空白内容才保存
                self.editing_text_item.text_content = self.text_input_buffer
            else:
                # 如果没有输入任何内容，移除这个文本项
                if self.editing_text_item in self.drawing_items:
                    self.drawing_items.remove(self.editing_text_item)
                if self.editing_text_item in self.undo_stack:
                    self.undo_stack.remove(self.editing_text_item)
            
        self.inline_editing = False
        self.editing_text_item = None
        self.text_input_buffer = ""
        self.cursor_position = 0
        
        # 恢复光标
        if self.drawing_mode:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        # 编辑完成后显示工具栏
        if not self.selection_rect.isEmpty():
            self._show_integrated_toolbar()
    
    def keyPressEvent(self, event):
        # 键盘事件处理：支持ESC退出区域截图、Enter确认复制、文本编辑等
        key = event.key()
        modifiers = event.modifiers()
        
        # 优先处理全局快捷键
        if key == Qt.Key.Key_Escape:
            # ESC键：退出区域截图（根据项目规范）
            if self.inline_editing:
                # 如果正在编辑文本，先退出编辑模式
                if self.editing_text_item:
                    # 移除这个文本项
                    if self.editing_text_item in self.drawing_items:
                        self.drawing_items.remove(self.editing_text_item)
                self._finish_inline_text_editing()
                self.update()
            else:
                # 取消整个区域选择，退出截图
                self._cancel_selection()
            return
            
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            # Enter键：确认复制选区内容（根据项目规范）
            if self.inline_editing:
                # 如果正在编辑文本，结束编辑
                self._finish_inline_text_editing()
                self.update()
            elif not self.selection_rect.isEmpty():
                # 确认选区并复制到剪贴板
                self._confirm_selection()
            return
        
        # 文本编辑模式下的键盘处理
        if self.inline_editing:
            text = event.text()
            
            # 处理Ctrl+A全选
            if key == Qt.Key.Key_A and modifiers == Qt.KeyboardModifier.ControlModifier:
                self.text_selection_start = 0
                self.text_selection_end = len(self.text_input_buffer)
                self.cursor_position = self.text_selection_end
                self.update()
                return
            
            # 处理Ctrl+C复制
            if key == Qt.Key.Key_C and modifiers == Qt.KeyboardModifier.ControlModifier:
                if self.text_selection_start != self.text_selection_end:
                    selected_text = self.text_input_buffer[self.text_selection_start:self.text_selection_end]
                    QApplication.clipboard().setText(selected_text)
                return
            
            # 处理Ctrl+V粘贴
            if key == Qt.Key.Key_V and modifiers == Qt.KeyboardModifier.ControlModifier:
                clipboard_text = QApplication.clipboard().text()
                if clipboard_text:
                    # 删除选中的文本（如果有）
                    if self.text_selection_start != self.text_selection_end:
                        start = min(self.text_selection_start, self.text_selection_end)
                        end = max(self.text_selection_start, self.text_selection_end)
                        self.text_input_buffer = (self.text_input_buffer[:start] + 
                                                clipboard_text + 
                                                self.text_input_buffer[end:])
                        self.cursor_position = start + len(clipboard_text)
                    else:
                        # 在光标位置插入
                        self.text_input_buffer = (self.text_input_buffer[:self.cursor_position] + 
                                                clipboard_text + 
                                                self.text_input_buffer[self.cursor_position:])
                        self.cursor_position += len(clipboard_text)
                    self.text_selection_start = self.text_selection_end = self.cursor_position
                    self.update()
                return
            
            elif key == Qt.Key.Key_Backspace:
                # 删除字符
                if self.text_selection_start != self.text_selection_end:
                    # 删除选中的文本
                    start = min(self.text_selection_start, self.text_selection_end)
                    end = max(self.text_selection_start, self.text_selection_end)
                    self.text_input_buffer = (self.text_input_buffer[:start] + 
                                            self.text_input_buffer[end:])
                    self.cursor_position = start
                    self.text_selection_start = self.text_selection_end = start
                elif self.cursor_position > 0:
                    self.text_input_buffer = (self.text_input_buffer[:self.cursor_position-1] + 
                                            self.text_input_buffer[self.cursor_position:])
                    self.cursor_position -= 1
                    self.text_selection_start = self.text_selection_end = self.cursor_position
                self.update()
                return
                
            elif key == Qt.Key.Key_Delete:
                # 删除光标后的字符
                if self.text_selection_start != self.text_selection_end:
                    # 删除选中的文本
                    start = min(self.text_selection_start, self.text_selection_end)
                    end = max(self.text_selection_start, self.text_selection_end)
                    self.text_input_buffer = (self.text_input_buffer[:start] + 
                                            self.text_input_buffer[end:])
                    self.cursor_position = start
                    self.text_selection_start = self.text_selection_end = start
                elif self.cursor_position < len(self.text_input_buffer):
                    self.text_input_buffer = (self.text_input_buffer[:self.cursor_position] + 
                                            self.text_input_buffer[self.cursor_position+1:])
                    self.text_selection_start = self.text_selection_end = self.cursor_position
                self.update()
                return
                
            elif key == Qt.Key.Key_Left:
                # 光标左移
                if modifiers == Qt.KeyboardModifier.ShiftModifier:
                    # Shift+左箭头：扩展选区
                    if self.cursor_position > 0:
                        self.cursor_position -= 1
                        self.text_selection_end = self.cursor_position
                else:
                    # 单纯左移
                    if self.text_selection_start != self.text_selection_end:
                        self.cursor_position = min(self.text_selection_start, self.text_selection_end)
                    elif self.cursor_position > 0:
                        self.cursor_position -= 1
                    self.text_selection_start = self.text_selection_end = self.cursor_position
                self.update()
                return
                
            elif key == Qt.Key.Key_Right:
                # 光标右移
                if modifiers == Qt.KeyboardModifier.ShiftModifier:
                    # Shift+右箭头：扩展选区
                    if self.cursor_position < len(self.text_input_buffer):
                        self.cursor_position += 1
                        self.text_selection_end = self.cursor_position
                else:
                    # 单纯右移
                    if self.text_selection_start != self.text_selection_end:
                        self.cursor_position = max(self.text_selection_start, self.text_selection_end)
                    elif self.cursor_position < len(self.text_input_buffer):
                        self.cursor_position += 1
                    self.text_selection_start = self.text_selection_end = self.cursor_position
                self.update()
                return
                
            elif key == Qt.Key.Key_Up:
                # 上箭头：增大字体（符合项目规范：+2px）
                if self.editing_text_item:
                    current_size = getattr(self.editing_text_item, 'custom_font_size', 14)
                    if getattr(self.editing_text_item, 'text_size_mode', 'auto') != 'custom':
                        # 如果不是自定义模式，使用当前字体大小作为起点
                        current_size = getattr(self.editing_text_item, 'initial_font_size', 14)
                    new_size = min(100, current_size + 2)  # 最大100px（符合项目规范）
                    self.editing_text_item.text_size_mode = 'custom'
                    self.editing_text_item.custom_font_size = new_size
                    self.update()
                return
                
            elif key == Qt.Key.Key_Down:
                # 下箭头：减小字体（符合项目规范：-2px）
                if self.editing_text_item:
                    current_size = getattr(self.editing_text_item, 'custom_font_size', 14)
                    if getattr(self.editing_text_item, 'text_size_mode', 'auto') != 'custom':
                        # 如果不是自定义模式，使用当前字体大小作为起点
                        current_size = getattr(self.editing_text_item, 'initial_font_size', 14)
                    new_size = max(8, current_size - 2)  # 最小8px
                    self.editing_text_item.text_size_mode = 'custom'
                    self.editing_text_item.custom_font_size = new_size
                    self.update()
                return
                
            elif text and text.isprintable():
                # 输入可显示字符
                if self.text_selection_start != self.text_selection_end:
                    # 替换选中的文本
                    start = min(self.text_selection_start, self.text_selection_end)
                    end = max(self.text_selection_start, self.text_selection_end)
                    self.text_input_buffer = (self.text_input_buffer[:start] + 
                                            text + 
                                            self.text_input_buffer[end:])
                    self.cursor_position = start + len(text)
                else:
                    # 在光标位置插入
                    self.text_input_buffer = (self.text_input_buffer[:self.cursor_position] + 
                                            text + 
                                            self.text_input_buffer[self.cursor_position:])
                    self.cursor_position += len(text)
                self.text_selection_start = self.text_selection_end = self.cursor_position
                self.update()
                return

        # 其他按键事件传递给父类
        super().keyPressEvent(event)
    
    def inputMethodEvent(self, event):
        # 修复4: 完整的输入法事件处理（支持中文拼音显示）
        if self.inline_editing:
            commit_string = event.commitString()
            if commit_string:
                # 输入法提交的文字（支持中文、日文、韩文等）
                # 如果有选中的文本，先删除选中内容
                if self.text_selection_start != self.text_selection_end:
                    start = min(self.text_selection_start, self.text_selection_end)
                    end = max(self.text_selection_start, self.text_selection_end)
                    self.text_input_buffer = (self.text_input_buffer[:start] + 
                                            commit_string + 
                                            self.text_input_buffer[end:])
                    self.cursor_position = start + len(commit_string)
                    self.text_selection_start = self.text_selection_end = self.cursor_position
                else:
                    # 在光标位置插入
                    self.text_input_buffer = (self.text_input_buffer[:self.cursor_position] + 
                                            commit_string + 
                                            self.text_input_buffer[self.cursor_position:])
                    self.cursor_position += len(commit_string)
                
                # 清除预编辑文本
                self.preedit_text = ""
                self.preedit_cursor_pos = 0
                self.update()
                
            # 处理输入法预编辑文本（显示拼音等候选）
            preedit_string = event.preeditString()
            # 简化版本处理，避免属性访问错误
            self.preedit_text = preedit_string
            self.preedit_cursor_pos = len(preedit_string)  # 光标放在预编辑文本末尾
            
            # 立即更新显示以显示拼音
            self.update()
        super().inputMethodEvent(event)
    
    def inputMethodQuery(self, query):
        # 输入法查询
        if self.inline_editing and self.editing_text_item:
            if query == Qt.InputMethodQuery.ImCursorRectangle:
                # 返回光标位置
                if len(self.editing_text_item.points) >= 2:
                    rect = QRect(self.editing_text_item.points[0], self.editing_text_item.points[-1]).normalized()
                    return rect
        return super().inputMethodQuery(query)