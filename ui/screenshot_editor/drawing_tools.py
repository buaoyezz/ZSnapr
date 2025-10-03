#!/usr/bin/env python3
# Advanced Drawing Tools for Screenshot Editor

from PySide6.QtWidgets import (QGraphicsItem, QGraphicsEllipseItem, QGraphicsRectItem, 
                               QGraphicsLineItem, QGraphicsTextItem, QGraphicsPathItem)
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (QPen, QBrush, QColor, QPainterPath, QFont, QPainter, 
                          QPolygonF)
import math
from typing import List
from enum import Enum

class DrawingTool(Enum):
    SELECT = "select"
    RECTANGLE = "rectangle" 
    CIRCLE = "circle"
    ARROW = "arrow"
    TEXT = "text"
    PEN = "pen"
    ERASER = "eraser"

class EditableGraphicsItem(QGraphicsItem):
    # Base class for editable graphics items
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
    def set_editable(self, editable: bool):
        self.setFlag(QGraphicsItem.ItemIsSelectable, editable)
        self.setFlag(QGraphicsItem.ItemIsMovable, editable)

class EditableRectItem(EditableGraphicsItem):
    # Editable rectangle with resize handles
    
    def __init__(self, rect: QRectF, pen: QPen, brush: QBrush = QBrush(), parent=None):
        super().__init__(parent)
        self._rect = rect
        self._pen = pen
        self._brush = brush
        self.handle_size = 8
        
    def boundingRect(self) -> QRectF:
        margin = self.handle_size / 2
        return self._rect.adjusted(-margin, -margin, margin, margin)
    
    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        painter.drawRect(self._rect)
        
        if self.isSelected():
            self._draw_handles(painter)
    
    def _draw_handles(self, painter: QPainter):
        handle_pen = QPen(QColor(103, 80, 164), 2)
        handle_brush = QBrush(QColor(255, 255, 255))
        painter.setPen(handle_pen)
        painter.setBrush(handle_brush)
        
        handles = self._get_handle_rects()
        for handle in handles:
            painter.drawRect(handle)
    
    def _get_handle_rects(self) -> List[QRectF]:
        hs = self.handle_size
        rect = self._rect
        
        return [
            QRectF(rect.left() - hs/2, rect.top() - hs/2, hs, hs),
            QRectF(rect.right() - hs/2, rect.top() - hs/2, hs, hs),
            QRectF(rect.left() - hs/2, rect.bottom() - hs/2, hs, hs),
            QRectF(rect.right() - hs/2, rect.bottom() - hs/2, hs, hs),
        ]

class EditableEllipseItem(EditableGraphicsItem):
    # Editable ellipse/circle with resize handles
    
    def __init__(self, rect: QRectF, pen: QPen, brush: QBrush = QBrush(), parent=None):
        super().__init__(parent)
        self._rect = rect
        self._pen = pen
        self._brush = brush
        self.handle_size = 8
        
    def boundingRect(self) -> QRectF:
        margin = self.handle_size / 2
        return self._rect.adjusted(-margin, -margin, margin, margin)
    
    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        painter.drawEllipse(self._rect)
        
        if self.isSelected():
            self._draw_handles(painter)
    
    def _draw_handles(self, painter: QPainter):
        handle_pen = QPen(QColor(103, 80, 164), 2)
        handle_brush = QBrush(QColor(255, 255, 255))
        painter.setPen(handle_pen)
        painter.setBrush(handle_brush)
        
        handles = self._get_handle_rects()
        for handle in handles:
            painter.drawRect(handle)
    
    def _get_handle_rects(self) -> List[QRectF]:
        hs = self.handle_size
        rect = self._rect
        
        return [
            QRectF(rect.left() - hs/2, rect.top() - hs/2, hs, hs),
            QRectF(rect.right() - hs/2, rect.top() - hs/2, hs, hs),
            QRectF(rect.left() - hs/2, rect.bottom() - hs/2, hs, hs),
            QRectF(rect.right() - hs/2, rect.bottom() - hs/2, hs, hs),
        ]

class ArrowItem(EditableGraphicsItem):
    # Custom arrow graphics item
    
    def __init__(self, start_point: QPointF, end_point: QPointF, pen: QPen, parent=None):
        super().__init__(parent)
        self.start_point = start_point
        self.end_point = end_point
        self._pen = pen
        self.arrow_head_size = 15
        
    def boundingRect(self) -> QRectF:
        margin = max(self._pen.width(), self.arrow_head_size) + 5
        rect = QRectF(self.start_point, self.end_point).normalized()
        return rect.adjusted(-margin, -margin, margin, margin)
    
    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self._pen)
        
        # Draw line
        painter.drawLine(self.start_point, self.end_point)
        
        # Draw arrow head
        self._draw_arrow_head(painter)
        
        if self.isSelected():
            self._draw_handles(painter)
    
    def _draw_arrow_head(self, painter: QPainter):
        angle = math.atan2((self.end_point.y() - self.start_point.y()),
                          (self.end_point.x() - self.start_point.x()))
        
        head_len = self.arrow_head_size
        head_angle = math.pi / 6
        
        x1 = self.end_point.x() - head_len * math.cos(angle - head_angle)
        y1 = self.end_point.y() - head_len * math.sin(angle - head_angle)
        x2 = self.end_point.x() - head_len * math.cos(angle + head_angle)
        y2 = self.end_point.y() - head_len * math.sin(angle + head_angle)
        
        arrow_head = QPolygonF([
            self.end_point,
            QPointF(x1, y1),
            QPointF(x2, y2)
        ])
        
        painter.setBrush(QBrush(self._pen.color()))
        painter.drawPolygon(arrow_head)
    
    def _draw_handles(self, painter: QPainter):
        handle_pen = QPen(QColor(103, 80, 164), 2)
        handle_brush = QBrush(QColor(255, 255, 255))
        painter.setPen(handle_pen)
        painter.setBrush(handle_brush)
        
        hs = 8
        painter.drawRect(QRectF(self.start_point.x() - hs/2, self.start_point.y() - hs/2, hs, hs))
        painter.drawRect(QRectF(self.end_point.x() - hs/2, self.end_point.y() - hs/2, hs, hs))

class EditableTextItem(QGraphicsTextItem):
    # Enhanced text item with better editing capabilities
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        
        font = QFont("Arial", 14)
        font.setBold(True)  # Make text bold for better visibility
        self.setFont(font)
        
        # Set a high contrast default color (red) that's visible on most backgrounds
        self.setDefaultTextColor(QColor(255, 0, 0))
        
        # Add background for better visibility
        self.setFlag(QGraphicsItem.ItemHasNoContents, False)
        
    def setTextColor(self, color: QColor):
        # Ensure color is never white or too light on white background
        if color.lightness() > 240:  # If color is too light (close to white)
            # Use a darker version of the same hue
            darker_color = QColor(color)
            darker_color.setHsl(color.hue(), color.saturation(), 50)  # Set lightness to 50
            if not darker_color.isValid():
                darker_color = QColor(0, 0, 0)  # Fallback to black
            self.setDefaultTextColor(darker_color)
        else:
            self.setDefaultTextColor(color)
        
        # Force update to ensure color change is visible
        self.update()
    
    def paint(self, painter: QPainter, option, widget=None):
        # Draw text with outline for better visibility
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get text properties
        text_color = self.defaultTextColor()
        font = self.font()
        text = self.toPlainText()
        
        if text:
            # Draw text outline (stroke) for better visibility
            outline_pen = QPen(QColor(255, 255, 255), 2)  # White outline
            if text_color.lightness() > 128:  # If text is light, use dark outline
                outline_pen.setColor(QColor(0, 0, 0))
            
            painter.setPen(outline_pen)
            painter.setFont(font)
            
            # Draw outline by drawing text multiple times with slight offsets
            text_rect = self.boundingRect()
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    painter.drawText(text_rect.translated(dx, dy), Qt.AlignLeft | Qt.TextWordWrap, text)
            
            # Draw main text
            painter.setPen(QPen(text_color))
            painter.drawText(text_rect, Qt.AlignLeft | Qt.TextWordWrap, text)
        
        # Draw selection border if selected
        if self.isSelected():
            self._draw_selection_border(painter)
    
    def _draw_selection_border(self, painter: QPainter):
        pen = QPen(QColor(103, 80, 164), 2, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.boundingRect())

class FreehandPathItem(EditableGraphicsItem):
    # Freehand drawing path item
    
    def __init__(self, pen: QPen, parent=None):
        super().__init__(parent)
        self._pen = pen
        self._path = QPainterPath()
        self._points = []
        
    def add_point(self, point: QPointF):
        self._points.append(point)
        if len(self._points) == 1:
            self._path.moveTo(point)
        else:
            self._path.lineTo(point)
        self.update()
    
    def boundingRect(self) -> QRectF:
        if self._path.isEmpty():
            return QRectF()
        
        margin = self._pen.width() + 5
        return self._path.boundingRect().adjusted(-margin, -margin, margin, margin)
    
    def paint(self, painter: QPainter, option, widget=None):
        if not self._path.isEmpty():
            painter.setPen(self._pen)
            painter.drawPath(self._path)
            
            if self.isSelected():
                self._draw_selection_border(painter)
    
    def _draw_selection_border(self, painter: QPainter):
        pen = QPen(QColor(103, 80, 164), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.boundingRect())

class DrawingToolFactory:
    # Factory class for creating drawing tools
    
    @staticmethod
    def create_rectangle(start: QPointF, end: QPointF, pen: QPen, brush: QBrush = QBrush()) -> EditableRectItem:
        rect = QRectF(start, end).normalized()
        return EditableRectItem(rect, pen, brush)
    
    @staticmethod
    def create_circle(start: QPointF, end: QPointF, pen: QPen, brush: QBrush = QBrush()) -> EditableEllipseItem:
        rect = QRectF(start, end).normalized()
        return EditableEllipseItem(rect, pen, brush)
    
    @staticmethod
    def create_arrow(start: QPointF, end: QPointF, pen: QPen) -> ArrowItem:
        return ArrowItem(start, end, pen)
    
    @staticmethod
    def create_text(position: QPointF, text: str = "Text") -> EditableTextItem:
        text_item = EditableTextItem(text)
        text_item.setPos(position)
        return text_item
    
    @staticmethod
    def create_freehand_path(pen: QPen) -> FreehandPathItem:
        return FreehandPathItem(pen)