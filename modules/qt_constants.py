#!/usr/bin/env python3
# Qt Constants compatibility layer for region selector

from PySide6.QtCore import Qt

# Mouse button constants
LEFT_BUTTON = Qt.MouseButton.LeftButton if hasattr(Qt, 'MouseButton') else Qt.LeftButton

# Cursor constants
CROSS_CURSOR = Qt.CursorShape.CrossCursor if hasattr(Qt, 'CursorShape') else Qt.CrossCursor
ARROW_CURSOR = Qt.CursorShape.ArrowCursor if hasattr(Qt, 'CursorShape') else Qt.ArrowCursor
OPEN_HAND_CURSOR = Qt.CursorShape.OpenHandCursor if hasattr(Qt, 'CursorShape') else Qt.OpenHandCursor
CLOSED_HAND_CURSOR = Qt.CursorShape.ClosedHandCursor if hasattr(Qt, 'CursorShape') else Qt.ClosedHandCursor

# Size cursors
SIZE_F_DIAG_CURSOR = Qt.CursorShape.SizeFDiagCursor if hasattr(Qt, 'CursorShape') else Qt.SizeFDiagCursor
SIZE_B_DIAG_CURSOR = Qt.CursorShape.SizeBDiagCursor if hasattr(Qt, 'CursorShape') else Qt.SizeBDiagCursor
SIZE_VER_CURSOR = Qt.CursorShape.SizeVerCursor if hasattr(Qt, 'CursorShape') else Qt.SizeVerCursor
SIZE_HOR_CURSOR = Qt.CursorShape.SizeHorCursor if hasattr(Qt, 'CursorShape') else Qt.SizeHorCursor

# Window flags
WINDOW_STAYS_ON_TOP = Qt.WindowType.WindowStaysOnTopHint if hasattr(Qt, 'WindowType') else Qt.WindowStaysOnTopHint
FRAMELESS_WINDOW = Qt.WindowType.FramelessWindowHint if hasattr(Qt, 'WindowType') else Qt.FramelessWindowHint
TOOL_WINDOW = Qt.WindowType.Tool if hasattr(Qt, 'WindowType') else Qt.Tool

# Pen styles
SOLID_LINE = Qt.PenStyle.SolidLine if hasattr(Qt, 'PenStyle') else Qt.SolidLine
DASH_LINE = Qt.PenStyle.DashLine if hasattr(Qt, 'PenStyle') else Qt.DashLine

# Brush styles
NO_BRUSH = Qt.BrushStyle.NoBrush if hasattr(Qt, 'BrushStyle') else Qt.NoBrush
TRANSPARENT = Qt.GlobalColor.transparent if hasattr(Qt, 'GlobalColor') else Qt.transparent

# Dialog codes
DIALOG_ACCEPTED = 1  # QDialog.Accepted equivalent

# Font weights
FONT_BOLD = 75  # QFont.Bold equivalent

# Text flags
TEXT_WORD_WRAP = Qt.TextFlag.TextWordWrap if hasattr(Qt, 'TextFlag') else Qt.TextWordWrap

# Painter render hints
ANTIALIASING = 1  # QPainter.RenderHint.Antialiasing
SMOOTH_PIXMAP_TRANSFORM = 2  # QPainter.RenderHint.SmoothPixmapTransform
TEXT_ANTIALIASING = 4  # QPainter.RenderHint.TextAntialiasing