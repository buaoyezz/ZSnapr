#!/usr/bin/env python3
# Custom Color Dialog with Modern Design

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
                               QPushButton, QLabel, QLineEdit, QFrame)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap, QFont

class ColorButton(QPushButton):
    # Custom color button widget
    colorSelected = Signal(QColor)
    
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(32, 32)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.name()};
                border: 2px solid rgba(0, 0, 0, 20);
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border: 2px solid rgba(0, 0, 0, 40);
                transform: scale(1.05);
            }}
            QPushButton:pressed {{
                border: 3px solid #333333;
            }}
        """)
        self.clicked.connect(lambda: self.colorSelected.emit(self.color))

class CustomColorDialog(QDialog):
    # Modern custom color picker dialog
    
    def __init__(self, current_color=QColor(255, 0, 0), parent=None):
        super().__init__(parent)
        self.selected_color = current_color
        self.setWindowTitle("Choose Color")
        self.setFixedSize(400, 320)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        # Apply modern styling
        self.setStyleSheet("""
            QDialog {
                background: #f8f9ff;
                border-radius: 12px;
            }
            QLabel {
                color: #333333;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton {
                background: #ffffff;
                color: #333333;
                border: 1px solid rgba(0, 0, 0, 20);
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: 500;
                min-width: 60px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 5);
                border: 1px solid rgba(0, 0, 0, 30);
            }
            QPushButton:pressed {
                background: rgba(0, 0, 0, 10);
            }
            QLineEdit {
                background: #ffffff;
                color: #333333;
                border: 1px solid rgba(0, 0, 0, 20);
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 2px solid #6750a4;
            }
            QFrame {
                background: rgba(0, 0, 0, 8);
                border: none;
                max-height: 1px;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Setup the dialog UI
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Select Color")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(title_label)
        
        # Basic colors section
        basic_label = QLabel("Basic Colors")
        layout.addWidget(basic_label)
        
        # Basic colors grid
        basic_grid = QGridLayout()
        basic_grid.setSpacing(6)
        
        basic_colors = [
            # Row 1
            [QColor(255, 0, 0), QColor(255, 128, 0), QColor(255, 255, 0), QColor(128, 255, 0),
             QColor(0, 255, 0), QColor(0, 255, 128), QColor(0, 255, 255), QColor(0, 128, 255)],
            # Row 2
            [QColor(0, 0, 255), QColor(128, 0, 255), QColor(255, 0, 255), QColor(255, 0, 128),
             QColor(128, 128, 128), QColor(192, 192, 192), QColor(0, 0, 0), QColor(255, 255, 255)]
        ]
        
        for row, colors in enumerate(basic_colors):
            for col, color in enumerate(colors):
                btn = ColorButton(color)
                btn.colorSelected.connect(self._on_color_selected)
                basic_grid.addWidget(btn, row, col)
        
        basic_widget = QWidget()
        basic_widget.setLayout(basic_grid)
        layout.addWidget(basic_widget)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)
        
        # Custom color section
        custom_label = QLabel("Custom Color")
        layout.addWidget(custom_label)
        
        # Color preview and hex input
        color_info_layout = QHBoxLayout()
        
        # Color preview
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(48, 32)
        self.color_preview.setStyleSheet(f"""
            QLabel {{
                background-color: {self.selected_color.name()};
                border: 2px solid rgba(0, 0, 0, 20);
                border-radius: 6px;
            }}
        """)
        color_info_layout.addWidget(self.color_preview)
        
        # Hex input
        hex_layout = QVBoxLayout()
        hex_label = QLabel("Hex:")
        self.hex_input = QLineEdit(self.selected_color.name())
        self.hex_input.setMaxLength(7)
        self.hex_input.textChanged.connect(self._on_hex_changed)
        hex_layout.addWidget(hex_label)
        hex_layout.addWidget(self.hex_input)
        color_info_layout.addLayout(hex_layout)
        
        # System color picker button
        system_btn = QPushButton("More Colors...")
        system_btn.clicked.connect(self._open_system_picker)
        color_info_layout.addWidget(system_btn)
        
        color_info_layout.addStretch()
        layout.addLayout(color_info_layout)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        layout.addWidget(separator2)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #6750a4;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background: #5a47a0;
            }
            QPushButton:pressed {
                background: #4a3d8a;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def _on_color_selected(self, color):
        # Handle color selection from buttons
        self.selected_color = color
        self._update_preview()
    
    def _on_hex_changed(self, hex_text):
        # Handle hex input changes
        if hex_text.startswith('#') and len(hex_text) == 7:
            try:
                color = QColor(hex_text)
                if color.isValid():
                    self.selected_color = color
                    self._update_preview()
            except:
                pass
    
    def _update_preview(self):
        # Update color preview and hex input
        self.color_preview.setStyleSheet(f"""
            QLabel {{
                background-color: {self.selected_color.name()};
                border: 2px solid rgba(0, 0, 0, 20);
                border-radius: 6px;
            }}
        """)
        self.hex_input.setText(self.selected_color.name())
    
    def _open_system_picker(self):
        # Open system color picker as fallback
        from PySide6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.selected_color, self)
        if color.isValid():
            self.selected_color = color
            self._update_preview()
    
    def get_color(self):
        # Get the selected color
        return self.selected_color
    
    @staticmethod
    def get_color_from_user(current_color=QColor(255, 0, 0), parent=None):
        # Static method to get color from user
        print("DEBUG: Creating CustomColorDialog...")
        try:
            dialog = CustomColorDialog(current_color, parent)
            print("DEBUG: Dialog created successfully")
            result = dialog.exec()
            print(f"DEBUG: Dialog exec result: {result}")
            if result == QDialog.Accepted:
                color = dialog.get_color()
                print(f"DEBUG: Returning selected color: {color}")
                return color
            else:
                print("DEBUG: Dialog was cancelled")
                return None
        except Exception as e:
            print(f"DEBUG: Error in get_color_from_user: {e}")
            import traceback
            traceback.print_exc()
            return None