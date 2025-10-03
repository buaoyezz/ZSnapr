import os
import sys


def get_resource_base() -> str:
    """Return directory that contains bundled resources."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return meipass
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def resolve_resource(*parts: str) -> str:
    """Build absolute path inside packaged resources."""
    return os.path.join(get_resource_base(), *parts)


def resolve_asset_path(*parts: str) -> str:
    """Build absolute path inside assets directory."""
    return resolve_resource("assets", *parts)


def resource_exists(*parts: str) -> bool:
    """Check whether a resource exists."""
    return os.path.exists(resolve_resource(*parts))