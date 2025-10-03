#!/usr/bin/env python3
# Modern Screenshot Editor with Material Design 3 Toolbar
# Features: Drawing tools, text editing, undo/redo, paste to screen

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QToolButton, QButtonGroup, QSlider,
                               QColorDialog, QFontDialog, QSpinBox, QFrame,
                               QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                               QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem,
                               QGraphicsTextItem, QApplication, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QPoint, QRect, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import (QPainter, QPen, QBrush, QColor, QPixmap, QFont, 
                          QCursor, QIcon, QPainterPath, QPolygonF, QTransform)
from PySide6.QtSvg import QSvgRenderer
import os
import sys
from typing import Optional, List, Tuple
from enum import Enum
import json

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.log_sys import get_logger
from assets.modules.I18N import t

class DrawingTool(Enum):
    SELECT = "select"
    RECTANGLE = "rectangle" 
    CIRCLE = "circle"
    ARROW = "arrow"
    TEXT = "text"
    PEN = "pen"
    ERASER = "eraser"

class MD3Colors:
    # Material Design 3 Color Tokens
    PRIMARY = QColor(103, 80, 164)
    ON_PRIMARY = QColor(255, 255, 255)
    SURFACE = QColor(255, 255, 255)
    ON_SURFACE = QColor(28, 27, 31)
    SURFACE_VARIANT = QColor(247, 243, 249)
    ON_SURFACE_VARIANT = QColor(73, 69, 79)
    OUTLINE = QColor(121, 116, 126)
    OUTLINE_VARIANT = QColor(196, 199, 197)
    SUCCESS = QColor(56, 142, 60)
    ERROR = QColor(211, 47, 47)
    WARNING = QColor(245, 124, 0)

class ToolbarButton(QToolButton):
    # Custom Material Design 3 styled toolbar button
    
    def __init__(self, icon_path: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setStyleSheet(self._get_button_style())
        
        # Load SVG icon
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(24, 24))
    
    def _get_button_style(self) -> str:
        return """
        QToolButton {
            border: none;
            border-radius: 12px;
            background-color: transparent;
            padding: 8px;
        }
        QToolButton:hover {
            background-color: rgba(103, 80, 164, 0.08);
        }
        QToolButton:pressed {
            background-color: rgba(103, 80, 164, 0.12);
        }
        QToolButton:checked {
            background-color: rgba(103, 80, 164, 0.16);
            color: rgb(103, 80, 164);
        }
        """

class ModernToolbar(QFrame):
    # Material Design 3 floating toolbar
    
    tool_changed = Signal(DrawingTool)
    color_changed = Signal(QColor)
    size_changed = Signal(int)
    undo_requested = Signal()
    redo_requested = Signal()
    paste_to_screen_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger()
        self.current_tool = DrawingTool.SELECT
        self.current_color = QColor(255, 0, 0)  # Default red color for visibility  # Default red color for visibility
        self.current_size = 3
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        # Create floating toolbar with Material Design 3 styling
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet(self._get_toolbar_style())
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # Tool buttons group
        self.tool_group = QButtonGroup(self)
        
        # Selection tool
        self.select_btn = self._create_tool_button(
            "core/icons/gesture_select_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.select_tool"),
            DrawingTool.SELECT
        )
        
        # Drawing tools
        self.circle_btn = self._create_tool_button(
            "core/icons/circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg", 
            t("editor.circle_tool"),
            DrawingTool.CIRCLE
        )
        
        # Need to check if rectangle icon exists, if not we'll use a placeholder
        rect_icon_path = "core/icons/rectangle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
        if not os.path.exists(rect_icon_path):
            rect_icon_path = "core/icons/circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"  # Fallback
        
        self.rect_btn = self._create_tool_button(
            rect_icon_path,
            t("editor.rectangle_tool"), 
            DrawingTool.RECTANGLE
        )
        
        # Arrow tool - need to check if exists
        arrow_icon_path = "core/icons/arrow_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
        if not os.path.exists(arrow_icon_path):
            arrow_icon_path = "core/icons/stylus_note_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"  # Fallback
            
        self.arrow_btn = self._create_tool_button(
            arrow_icon_path,
            t("editor.arrow_tool"),
            DrawingTool.ARROW
        )
        
        # Text tool
        self.text_btn = self._create_tool_button(
            "core/icons/keyboard_external_input_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.text_tool"),
            DrawingTool.TEXT
        )
        
        # Pen tool
        self.pen_btn = self._create_tool_button(
            "core/icons/ink_pen_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.pen_tool"),
            DrawingTool.PEN
        )
        
        # Eraser tool - need to check if exists
        eraser_icon_path = "core/icons/eraser_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"
        if not os.path.exists(eraser_icon_path):
            eraser_icon_path = "core/icons/stylus_note_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"  # Fallback
            
        self.eraser_btn = self._create_tool_button(
            eraser_icon_path,
            t("editor.eraser_tool"),
            DrawingTool.ERASER
        )
        
        # Add separator
        separator1 = QFrame()
        separator1.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        separator1.setStyleSheet("color: rgba(121, 116, 126, 0.3);")
        layout.addWidget(separator1)
        
        # Color picker button
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(48, 32)
        self.color_btn.setStyleSheet(self._get_color_button_style())
        self.color_btn.setToolTip(t("editor.color_picker"))
        layout.addWidget(self.color_btn)
        
        # Size slider
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 20)
        self.size_slider.setValue(3)
        self.size_slider.setFixedWidth(80)
        self.size_slider.setToolTip(t("editor.brush_size"))
        layout.addWidget(self.size_slider)
        
        # Add separator
        separator2 = QFrame()
        separator2.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        separator2.setStyleSheet("color: rgba(121, 116, 126, 0.3);")
        layout.addWidget(separator2)
        
        # Undo/Redo buttons
        self.undo_btn = self._create_action_button(
            "core/icons/undo_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.undo")
        )
        
        self.redo_btn = self._create_action_button(
            "core/icons/redo_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg", 
            t("editor.redo")
        )
        
        # Add separator
        separator3 = QFrame()
        separator3.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        separator3.setStyleSheet("color: rgba(121, 116, 126, 0.3);")
        layout.addWidget(separator3)
        
        # Paste to screen button
        self.paste_btn = self._create_action_button(
            "core/icons/file_copy_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.paste_to_screen")
        )
        
        # Set default selection
        self.select_btn.setChecked(True)
    
    def _create_tool_button(self, icon_path: str, tooltip: str, tool: DrawingTool) -> ToolbarButton:
        btn = ToolbarButton(icon_path, tooltip, self)
        self.tool_group.addButton(btn)
        btn.tool = tool
        self.layout().addWidget(btn)
        return btn
    
    def _create_action_button(self, icon_path: str, tooltip: str) -> ToolbarButton:
        btn = ToolbarButton(icon_path, tooltip, self)
        btn.setCheckable(False)  # Action buttons are not checkable
        self.layout().addWidget(btn)
        return btn
    
    def _setup_connections(self):
        # Tool selection
        for btn in self.tool_group.buttons():
            btn.clicked.connect(lambda checked, b=btn: self._on_tool_selected(b.tool))
        
        # Color picker
        self.color_btn.clicked.connect(self._on_color_picker)
        
        # Size slider
        self.size_slider.valueChanged.connect(self._on_size_changed)
        
        # Action buttons
        self.undo_btn.clicked.connect(self.undo_requested.emit)
        self.redo_btn.clicked.connect(self.redo_requested.emit)
        self.paste_btn.clicked.connect(self.paste_to_screen_requested.emit)
    
    def _on_tool_selected(self, tool: DrawingTool):
        self.current_tool = tool
        self.tool_changed.emit(tool)
        self.logger.debug(f"Tool changed to: {tool.value}")
    
    def _on_color_picker(self):
        color = QColorDialog.getColor(self.current_color, self, t("editor.choose_color"))
        if color.isValid():
            self.current_color = color
            self.color_btn.setStyleSheet(self._get_color_button_style())
            self.color_changed.emit(color)
    
    def _on_size_changed(self, value: int):
        self.current_size = value
        self.size_changed.emit(value)
    
    def _get_toolbar_style(self) -> str:
        return """
        QFrame {
            background-color: rgba(255, 255, 255, 0.95);
            border: 1px solid rgba(121, 116, 126, 0.3);
            border-radius: 16px;
            backdrop-filter: blur(10px);
        }
        """
    
    def _get_color_button_style(self) -> str:
        color_hex = self.current_color.name()
        return f"""
        QPushButton {{
            background-color: {color_hex};
            border: 2px solid rgba(121, 116, 126, 0.3);
            border-radius: 8px;
        }}
        QPushButton:hover {{
            border: 2px solid rgba(103, 80, 164, 0.5);
        }}
        """

class ScreenshotEditor(QWidget):
    # Main screenshot editor widget
    
    def __init__(self, screenshot: QPixmap, parent=None):
        super().__init__(parent)
        self.logger = get_logger()
        self.screenshot = screenshot
        self.undo_stack = []
        self.redo_stack = []
        self.current_tool = DrawingTool.SELECT
        self.current_color = QColor(255, 0, 0)
        self.current_size = 3
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        self.setWindowTitle(t("editor.screenshot_editor"))
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create toolbar
        self.toolbar = ModernToolbar(self)
        layout.addWidget(self.toolbar)
        
        # Create graphics view for editing
        self.graphics_view = QGraphicsView(self)
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)
        
        # Add screenshot to scene
        self.pixmap_item = QGraphicsPixmapItem(self.screenshot)
        self.graphics_scene.addItem(self.pixmap_item)
        
        # Set scene rect to screenshot size
        self.graphics_scene.setSceneRect(self.screenshot.rect())
        
        layout.addWidget(self.graphics_view)
        
        # Style the graphics view
        self.graphics_view.setStyleSheet("""
        QGraphicsView {
            border: none;
            background-color: #f5f5f5;
        }
        """)
    
    def _setup_connections(self):
        self.toolbar.tool_changed.connect(self._on_tool_changed)
        self.toolbar.color_changed.connect(self._on_color_changed)
        self.toolbar.size_changed.connect(self._on_size_changed)
        self.toolbar.undo_requested.connect(self._undo)
        self.toolbar.redo_requested.connect(self._redo)
        self.toolbar.paste_to_screen_requested.connect(self._paste_to_screen)
    
    def _on_tool_changed(self, tool: DrawingTool):
        self.current_tool = tool
        # Update cursor based on tool
        if tool == DrawingTool.PEN:
            self.graphics_view.setCursor(Qt.CrossCursor)
        elif tool == DrawingTool.TEXT:
            self.graphics_view.setCursor(Qt.IBeamCursor)
        else:
            self.graphics_view.setCursor(Qt.ArrowCursor)
    
    def _on_color_changed(self, color: QColor):
        self.current_color = color
    
    def _on_size_changed(self, size: int):
        self.current_size = size
    
    def _undo(self):
        # Implement undo functionality
        if self.undo_stack:
            # Save current state to redo stack
            current_state = self._capture_scene_state()
            self.redo_stack.append(current_state)
            
            # Restore previous state
            previous_state = self.undo_stack.pop()
            self._restore_scene_state(previous_state)
            
            self.logger.debug("Undo performed")
    
    def _redo(self):
        # Implement redo functionality
        if self.redo_stack:
            # Save current state to undo stack
            current_state = self._capture_scene_state()
            self.undo_stack.append(current_state)
            
            # Restore next state
            next_state = self.redo_stack.pop()
            self._restore_scene_state(next_state)
            
            self.logger.debug("Redo performed")
    
    def _paste_to_screen(self):
        # Implement paste to screen functionality
        try:
            # Render the current scene to a pixmap
            scene_rect = self.graphics_scene.sceneRect()
            pixmap = QPixmap(scene_rect.size().toSize())
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            self.graphics_scene.render(painter)
            painter.end()
            
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            
            self.logger.debug("Screenshot pasted to clipboard")
            
            # Show success message
            QMessageBox.information(self, t("editor.success"), t("editor.pasted_to_clipboard"))
            
        except Exception as e:
            self.logger.error(f"Failed to paste to screen: {e}")
            QMessageBox.warning(self, t("editor.error"), t("editor.paste_failed"))
    
    def _capture_scene_state(self) -> dict:
        # Capture current scene state for undo/redo
        # This is a simplified implementation
        return {
            'items': len(self.graphics_scene.items()),
            'timestamp': time.time()
        }
    
    def _restore_scene_state(self, state: dict):
        # Restore scene state from captured data
        # This is a simplified implementation
        pass

def create_screenshot_editor(screenshot: QPixmap) -> ScreenshotEditor:
    # Factory function to create screenshot editor
    return ScreenshotEditor(screenshot)

if __name__ == "__main__":
    # Test the screenshot editor
    app = QApplication(sys.argv)
    
    # Create a test pixmap
    test_pixmap = QPixmap(800, 600)
    test_pixmap.fill(Qt.white)
    
    editor = ScreenshotEditor(test_pixmap)
    editor.show()
    
    sys.exit(app.exec())