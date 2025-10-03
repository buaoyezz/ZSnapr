#!/usr/bin/env python3
# Enhanced Screenshot Editor with Interactive Drawing Tools

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, 
                               QGraphicsScene, QGraphicsPixmapItem, QApplication,
                               QMessageBox, QInputDialog, QColorDialog, QFrame,
                               QToolButton, QButtonGroup, QSlider, QPushButton,
                               QLabel, QSizePolicy)
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, Signal, QTimer, QSize
from PySide6.QtGui import (QPainter, QPen, QBrush, QColor, QPixmap, QFont, 
                          QCursor, QIcon, QPainterPath, QTransform, QKeySequence)
from PySide6.QtSvg import QSvgRenderer
import os
import sys
import time
from typing import Optional, List, Dict, Any
from enum import Enum

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.log_sys import get_logger
from assets.modules.I18N import t
from .drawing_tools import (DrawingTool, DrawingToolFactory, EditableRectItem, 
                           EditableEllipseItem, ArrowItem, EditableTextItem, 
                           FreehandPathItem)

class EditorState:
    # Manages editor state for undo/redo functionality
    
    def __init__(self):
        self.items = []
        self.timestamp = time.time()
    
    def capture_scene(self, scene: QGraphicsScene):
        # Capture current scene state
        self.items = []
        for item in scene.items():
            if not isinstance(item, QGraphicsPixmapItem):  # Skip background image
                self.items.append(self._serialize_item(item))
    
    def _serialize_item(self, item) -> Dict[str, Any]:
        # Serialize graphics item to dictionary
        item_data = {
            'type': type(item).__name__,
            'pos': (item.pos().x(), item.pos().y()),
            'visible': item.isVisible(),
            'selected': item.isSelected()
        }
        
        # Add type-specific data
        if isinstance(item, EditableRectItem):
            item_data.update({
                'rect': (item._rect.x(), item._rect.y(), item._rect.width(), item._rect.height()),
                'pen_color': item._pen.color().name(),
                'pen_width': item._pen.width()
            })
        elif isinstance(item, EditableTextItem):
            item_data.update({
                'text': item.toPlainText(),
                'font_family': item.font().family(),
                'font_size': item.font().pointSize(),
                'color': item.defaultTextColor().name()
            })
        
        return item_data

class ModernToolButton(QToolButton):
    # Material Design 3 styled tool button
    
    def __init__(self, icon_path: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setStyleSheet(self._get_button_style())
        
        # Load SVG icon if exists
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

class FloatingToolbar(QFrame):
    # Floating Material Design 3 toolbar
    
    tool_changed = Signal(DrawingTool)
    color_changed = Signal(QColor)
    size_changed = Signal(int)
    undo_requested = Signal()
    redo_requested = Signal()
    paste_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger()
        self.current_tool = DrawingTool.SELECT
        self.current_color = QColor(255, 0, 0)  # Default red color
        self.current_size = 3
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet(self._get_toolbar_style())
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # Tool buttons group
        self.tool_group = QButtonGroup(self)
        
        # Create tool buttons
        self.select_btn = self._create_tool_button(
            "core/icons/gesture_select_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.select_tool"), DrawingTool.SELECT
        )
        
        self.circle_btn = self._create_tool_button(
            "core/icons/circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.circle_tool"), DrawingTool.CIRCLE
        )
        
        # Use existing icons or fallbacks
        rect_icon = "core/icons/circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"  # Fallback
        self.rect_btn = self._create_tool_button(
            rect_icon, t("editor.rectangle_tool"), DrawingTool.RECTANGLE
        )
        
        arrow_icon = "core/icons/stylus_note_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"  # Fallback
        self.arrow_btn = self._create_tool_button(
            arrow_icon, t("editor.arrow_tool"), DrawingTool.ARROW
        )
        
        self.text_btn = self._create_tool_button(
            "core/icons/keyboard_external_input_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.text_tool"), DrawingTool.TEXT
        )
        
        self.pen_btn = self._create_tool_button(
            "core/icons/ink_pen_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.pen_tool"), DrawingTool.PEN
        )
        
        eraser_icon = "core/icons/stylus_note_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"  # Fallback
        self.eraser_btn = self._create_tool_button(
            eraser_icon, t("editor.eraser_tool"), DrawingTool.ERASER
        )
        
        # Add separator
        self._add_separator(layout)
        
        # Color picker
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(48, 32)
        self.color_btn.setStyleSheet(self._get_color_button_style())
        self.color_btn.setToolTip(t("editor.color_picker"))
        layout.addWidget(self.color_btn)
        
        # Size slider
        size_label = QLabel("Size:")
        size_label.setStyleSheet("color: #1C1B1F; font-size: 12px;")
        layout.addWidget(size_label)
        
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 20)
        self.size_slider.setValue(3)
        self.size_slider.setFixedWidth(80)
        self.size_slider.setToolTip(t("editor.brush_size"))
        layout.addWidget(self.size_slider)
        
        # Add separator
        self._add_separator(layout)
        
        # Action buttons
        self.undo_btn = self._create_action_button(
            "core/icons/undo_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.undo")
        )
        
        self.redo_btn = self._create_action_button(
            "core/icons/redo_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.redo")
        )
        
        # Add separator
        self._add_separator(layout)
        
        # Paste to screen
        self.paste_btn = self._create_action_button(
            "core/icons/file_copy_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
            t("editor.paste_to_screen")
        )
        
        # Set default selection
        self.select_btn.setChecked(True)
    
    def _create_tool_button(self, icon_path: str, tooltip: str, tool: DrawingTool) -> ModernToolButton:
        btn = ModernToolButton(icon_path, tooltip, self)
        btn.tool = tool
        self.tool_group.addButton(btn)
        self.layout().addWidget(btn)
        return btn
    
    def _create_action_button(self, icon_path: str, tooltip: str) -> ModernToolButton:
        btn = ModernToolButton(icon_path, tooltip, self)
        btn.setCheckable(False)
        self.layout().addWidget(btn)
        return btn
    
    def _add_separator(self, layout):
        separator = QFrame()
        separator.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        separator.setStyleSheet("color: rgba(121, 116, 126, 0.3);")
        separator.setFixedHeight(32)
        layout.addWidget(separator)
    
    def _setup_connections(self):
        # Tool selection
        for btn in self.tool_group.buttons():
            btn.clicked.connect(lambda checked, b=btn: self._on_tool_selected(b.tool))
        
        # Other controls
        self.color_btn.clicked.connect(self._on_color_picker)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        self.undo_btn.clicked.connect(self.undo_requested.emit)
        self.redo_btn.clicked.connect(self.redo_requested.emit)
        self.paste_btn.clicked.connect(self.paste_requested.emit)
    
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

class InteractiveGraphicsView(QGraphicsView):
    # Enhanced graphics view with drawing capabilities
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger()
        self.current_tool = DrawingTool.SELECT
        self.current_color = QColor(255, 0, 0)
        self.current_size = 3
        self.drawing = False
        self.start_point = QPointF()
        self.current_item = None
        self.temp_item = None
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.NoDrag)
        
        # Style
        self.setStyleSheet("""
        QGraphicsView {
            border: none;
            background-color: #f5f5f5;
        }
        """)
    
    def set_tool(self, tool: DrawingTool):
        self.current_tool = tool
        self._update_cursor()
    
    def set_color(self, color: QColor):
        self.current_color = color
    
    def set_size(self, size: int):
        self.current_size = size
    
    def _update_cursor(self):
        if self.current_tool == DrawingTool.PEN:
            self.setCursor(Qt.CrossCursor)
        elif self.current_tool == DrawingTool.TEXT:
            self.setCursor(Qt.IBeamCursor)
        elif self.current_tool == DrawingTool.ERASER:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.start_point = scene_pos
            self.drawing = True
            
            if self.current_tool == DrawingTool.SELECT:
                super().mousePressEvent(event)
            elif self.current_tool == DrawingTool.TEXT:
                self._start_text_input(scene_pos)
            elif self.current_tool == DrawingTool.PEN:
                self._start_freehand_drawing(scene_pos)
            else:
                self._start_shape_drawing(scene_pos)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() & Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            
            if self.current_tool == DrawingTool.PEN:
                self._continue_freehand_drawing(scene_pos)
            elif self.current_tool not in [DrawingTool.SELECT, DrawingTool.TEXT]:
                self._update_shape_preview(scene_pos)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            scene_pos = self.mapToScene(event.pos())
            self.drawing = False
            
            if self.current_tool not in [DrawingTool.SELECT, DrawingTool.TEXT, DrawingTool.PEN]:
                self._finish_shape_drawing(scene_pos)
            
            self._cleanup_temp_item()
        
        super().mouseReleaseEvent(event)
    
    def _start_text_input(self, pos: QPointF):
        text, ok = QInputDialog.getText(self, t("editor.text_tool"), "Enter text:")
        if ok and text:
            text_item = DrawingToolFactory.create_text(pos, text)
            # Use the custom setTextColor method to ensure visibility
            if hasattr(text_item, 'setTextColor'):
                text_item.setTextColor(self.current_color)
            else:
                # Fallback: ensure text is never white or too light
                if self.current_color.lightness() > 240:
                    text_item.setDefaultTextColor(QColor(0, 0, 0))  # Black
                else:
                    text_item.setDefaultTextColor(self.current_color)
            
            # Add item to scene and save state for undo
            self.scene().addItem(text_item)
            self._save_state()
            
            # Force scene update to ensure text is visible
            self.scene().update()
    
    def _start_freehand_drawing(self, pos: QPointF):
        pen = QPen(self.current_color, self.current_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self.current_item = DrawingToolFactory.create_freehand_path(pen)
        self.current_item.add_point(pos)
        self.scene().addItem(self.current_item)
    
    def _continue_freehand_drawing(self, pos: QPointF):
        if self.current_item and isinstance(self.current_item, FreehandPathItem):
            self.current_item.add_point(pos)
    
    def _start_shape_drawing(self, pos: QPointF):
        # Remove any existing temp item
        self._cleanup_temp_item()
    
    def _update_shape_preview(self, pos: QPointF):
        # Remove previous temp item
        self._cleanup_temp_item()
        
        # Create preview item
        pen = QPen(self.current_color, self.current_size)
        brush = QBrush()  # Transparent fill
        
        if self.current_tool == DrawingTool.RECTANGLE:
            self.temp_item = DrawingToolFactory.create_rectangle(self.start_point, pos, pen, brush)
        elif self.current_tool == DrawingTool.CIRCLE:
            self.temp_item = DrawingToolFactory.create_circle(self.start_point, pos, pen, brush)
        elif self.current_tool == DrawingTool.ARROW:
            self.temp_item = DrawingToolFactory.create_arrow(self.start_point, pos, pen)
        
        if self.temp_item:
            self.temp_item.setOpacity(0.7)  # Semi-transparent preview
            self.scene().addItem(self.temp_item)
    
    def _finish_shape_drawing(self, pos: QPointF):
        # Remove temp item
        self._cleanup_temp_item()
        
        # Create final item
        pen = QPen(self.current_color, self.current_size)
        brush = QBrush()
        
        final_item = None
        if self.current_tool == DrawingTool.RECTANGLE:
            final_item = DrawingToolFactory.create_rectangle(self.start_point, pos, pen, brush)
        elif self.current_tool == DrawingTool.CIRCLE:
            final_item = DrawingToolFactory.create_circle(self.start_point, pos, pen, brush)
        elif self.current_tool == DrawingTool.ARROW:
            final_item = DrawingToolFactory.create_arrow(self.start_point, pos, pen)
        
        if final_item:
            self.scene().addItem(final_item)
    
    def _cleanup_temp_item(self):
        if self.temp_item:
            self.scene().removeItem(self.temp_item)
            self.temp_item = None

class EnhancedScreenshotEditor(QWidget):
    # Main enhanced screenshot editor
    
    def __init__(self, screenshot: QPixmap, parent=None):
        super().__init__(parent)
        self.logger = get_logger()
        self.screenshot = screenshot
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_levels = 20
        
        self._setup_ui()
        self._setup_connections()
        self._save_initial_state()
    
    def _setup_ui(self):
        self.setWindowTitle(t("editor.screenshot_editor"))
        self.setMinimumSize(800, 600)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Toolbar
        self.toolbar = FloatingToolbar(self)
        layout.addWidget(self.toolbar)
        
        # Graphics view
        self.graphics_view = InteractiveGraphicsView(self)
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)
        
        # Add screenshot to scene
        self.pixmap_item = QGraphicsPixmapItem(self.screenshot)
        self.graphics_scene.addItem(self.pixmap_item)
        self.graphics_scene.setSceneRect(self.screenshot.rect())
        
        layout.addWidget(self.graphics_view)
        
        # Set window icon
        self.setWindowIcon(QIcon("core/icons/stylus_note_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
    
    def _setup_connections(self):
        self.toolbar.tool_changed.connect(self.graphics_view.set_tool)
        self.toolbar.color_changed.connect(self.graphics_view.set_color)
        self.toolbar.size_changed.connect(self.graphics_view.set_size)
        self.toolbar.undo_requested.connect(self._undo)
        self.toolbar.redo_requested.connect(self._redo)
        self.toolbar.paste_requested.connect(self._paste_to_clipboard)
    
    def _save_initial_state(self):
        # Save initial state for undo functionality
        initial_state = EditorState()
        initial_state.capture_scene(self.graphics_scene)
        self.undo_stack.append(initial_state)
    
    def _save_state(self):
        # Save current state to undo stack
        try:
            if len(self.undo_stack) >= self.max_undo_levels:
                self.undo_stack.pop(0)  # Remove oldest state
            
            state = EditorState()
            state.capture_scene(self.graphics_scene)
            self.undo_stack.append(state)
            
            # Clear redo stack when new action is performed
            self.redo_stack.clear()
            
            self.logger.debug(f"State saved, undo stack size: {len(self.undo_stack)}")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def _undo(self):
        if len(self.undo_stack) > 1:  # Keep at least initial state
            # Move current state to redo stack
            current_state = self.undo_stack.pop()
            self.redo_stack.append(current_state)
            
            # Restore previous state
            previous_state = self.undo_stack[-1]
            self._restore_state(previous_state)
            
            self.logger.debug("Undo performed")
    
    def _redo(self):
        if self.redo_stack:
            # Move state from redo to undo stack
            next_state = self.redo_stack.pop()
            self.undo_stack.append(next_state)
            
            # Restore next state
            self._restore_state(next_state)
            
            self.logger.debug("Redo performed")
    
    def _restore_state(self, state: EditorState):
        # Clear current items (except background)
        items_to_remove = []
        for item in self.graphics_scene.items():
            if not isinstance(item, QGraphicsPixmapItem):
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.graphics_scene.removeItem(item)
        
        # Restore items from state
        # This is a simplified implementation
        # In a full implementation, you would recreate items from serialized data
    
    def _paste_to_clipboard(self):
        try:
            # Render scene to pixmap
            scene_rect = self.graphics_scene.sceneRect()
            pixmap = QPixmap(scene_rect.size().toSize())
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            self.graphics_scene.render(painter)
            painter.end()
            
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            
            self.logger.debug("Screenshot copied to clipboard")
            QMessageBox.information(self, t("editor.success"), t("editor.pasted_to_clipboard"))
            
        except Exception as e:
            self.logger.error(f"Failed to copy to clipboard: {e}")
            QMessageBox.warning(self, t("editor.error"), t("editor.paste_failed"))

def create_enhanced_editor(screenshot: QPixmap) -> EnhancedScreenshotEditor:
    # Factory function
    return EnhancedScreenshotEditor(screenshot)

if __name__ == "__main__":
    # Test the enhanced editor
    app = QApplication(sys.argv)
    
    # Create test pixmap
    test_pixmap = QPixmap(800, 600)
    test_pixmap.fill(Qt.white)
    
    editor = EnhancedScreenshotEditor(test_pixmap)
    editor.show()
    
    sys.exit(app.exec())