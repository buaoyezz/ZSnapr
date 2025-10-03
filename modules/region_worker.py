import sys
import json
import os
import traceback

# Ensure we can import from the parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Add utils to path for resource management
utils_path = os.path.join(parent_dir, "utils")
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)

from PySide6.QtWidgets import QApplication
from modules.region_selector_with_drawing import RegionSelectorWithDrawing

def _stdout_json(obj):
    try:
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()
    except Exception:
        pass

def _write_result(obj):
    out_path = os.environ.get("ZSNAPR_REGION_OUT", "").strip()
    data = json.dumps(obj, ensure_ascii=False)
    if out_path:
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            return
        except Exception as e:
            try:
                sys.stderr.write(f"[worker] failed to write file: {e}\n")
                sys.stderr.flush()
            except Exception:
                pass
    _stdout_json(obj)

def main():
    try:
        os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.*=false")
        os.environ.setdefault("QT_LOGGING_TO_CONSOLE", "0")

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        selector = RegionSelectorWithDrawing()
        outcome = selector.select_region()

        if outcome is None:
            _write_result({"ok": False, "reason": "cancel"})
            return 0

        png_path = None
        if isinstance(outcome, tuple) and len(outcome) == 3 and isinstance(outcome[1], str) and isinstance(outcome[2], (str, type(None))):
            region, action, png_path = outcome
        elif isinstance(outcome, tuple) and len(outcome) == 2 and isinstance(outcome[1], str):
            region, action = outcome
        else:
            region, action = outcome, "copy"

        # Enhanced validation to prevent unpacking errors
        if region is None or not isinstance(region, (tuple, list)) or len(region) != 4:
            _write_result({"ok": False, "reason": "invalid_region_data"})
            return 1

        x, y, w, h = region
        
        if w <= 0 or h <= 0 or x < 0 or y < 0:
            _write_result({"ok": False, "reason": "invalid_coordinates"})
            return 1
        payload = {"ok": True, "x": x, "y": y, "w": w, "h": h, "action": action}
        if isinstance(png_path, str) and png_path:
            payload["png"] = png_path
        _write_result(payload)
        return 0
    except Exception as e:
        try:
            traceback.print_exc(file=sys.stderr)
        except Exception:
            pass
        _write_result({"ok": False, "reason": f"error:{e}"})
        return 1

if __name__ == "__main__":
    sys.exit(main())