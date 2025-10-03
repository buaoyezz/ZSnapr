#!/usr/bin/env python3
"""
Screenshot Editor Launcher
用于打包环境中启动截图编辑器的脚本
"""
import sys
import os

# Add project directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Add utils to path
utils_path = os.path.join(current_dir, "utils")
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)

def main():
    try:
        # Import Qt and editor
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPixmap
        from ui.screenshot_editor import create_enhanced_editor
        
        # Get image path from command line arguments
        if len(sys.argv) < 2:
            print("Usage: launch_editor.py <image_path>")
            sys.exit(1)
            
        image_path = sys.argv[1]
        
        if not os.path.exists(image_path):
            print(f"Error: Image file not found: {image_path}")
            sys.exit(1)
        
        # Create Qt application
        app = QApplication(sys.argv)
        
        # Load image into QPixmap
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"Error: Failed to load image: {image_path}")
            sys.exit(1)
        
        # Create and show editor
        editor = create_enhanced_editor(pixmap)
        editor.show()
        
        # Run the application
        sys.exit(app.exec())
            
    except Exception as e:
        print(f"Failed to launch screenshot editor: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()