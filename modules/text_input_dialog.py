#!/usr/bin/env python3
# Text Input Dialog for Region Selector

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class TextInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Text")
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        self.resize(300, 120)
        
        # Setup UI
        layout = QVBoxLayout(self)
        
        # Label
        label = QLabel("Enter text to add:")
        label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(label)
        
        # Text input
        self.text_input = QLineEdit()
        self.text_input.setFont(QFont("Microsoft YaHei", 10))
        self.text_input.setPlaceholderText("Type your text here...")
        layout.addWidget(self.text_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        # Focus on text input
        self.text_input.setFocus()
        
        # Connect Enter key
        self.text_input.returnPressed.connect(self.accept)
    
    def get_text(self):
        return self.text_input.text().strip()