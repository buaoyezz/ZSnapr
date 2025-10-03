import os
import platform
import json
import flet as ft
from config import APP_NAME, APP_VERSION, APP_CHANNEL

# 使用健壮的翻译助手
try:
    from translation_helper import t
    print(f"[about_page.py] Using translation_helper")
except ImportError:
    try:
        from config import t
        print(f"[about_page.py] Using config translation")
    except ImportError:
        def t(key, **kwargs):
            print(f"[about_page.py] Translation fallback: {key}")
            return key

def _get_flet_version():
    # Get Flet version that works even after packaging
    try:
        # First try the direct attribute
        return ft.__version__
    except AttributeError:
        try:
            # Use modern importlib.metadata (Python 3.8+)
            import importlib.metadata
            return importlib.metadata.version("flet")
        except Exception:
            try:
                # Fallback: try to read from installed packages
                import importlib.util
                spec = importlib.util.find_spec("flet")
                if spec and hasattr(spec, 'submodule_search_locations'):
                    # Try to find version in package files
                    for path in spec.submodule_search_locations or []:
                        version_file = os.path.join(path, "_version.py")
                        if os.path.exists(version_file):
                            with open(version_file, 'r') as f:
                                content = f.read()
                                if '__version__' in content:
                                    # Extract version from _version.py
                                    import re
                                    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                                    if match:
                                        return match.group(1)
                return "Unknown"
            except Exception:
                return "Unknown"

def _get_platform_info():
    # Get friendly platform name and architecture
    system = platform.system()
    arch = platform.machine()
    
    if system == "Windows":
        return f"Windows {arch}"
    elif system == "Darwin":
        return f"macOS {arch}"
    elif system == "Linux":
        return f"Linux {arch}"
    else:
        return f"{system} {arch}"

def _load_changelog():
    # Load complete update data from update.json
    try:
        with open('assets/update/update.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception:
        return None

def _show_changelog(app, e=None):
    # Show changelog dialog
    try:
        update_data = _load_changelog()
        
        def close_dlg(ev=None):
            try:
                app.page.close(dlg)
            except Exception:
                pass

        if not update_data or not update_data.get('releases'):
            content = ft.Column([
                ft.Text(t("about.changelog_unavailable"), size=12, color=ft.Colors.GREY_600),
            ], tight=True, spacing=6)
        else:
            # Get the latest release (current version)
            latest_release = update_data['releases'][0]  # First release is the latest
            changelog = latest_release.get('changelog', {})
            
            content_items = []
            
            # Version info
            content_items.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.NEW_RELEASES, size=18, color=ft.Colors.INDIGO_600),
                    ft.Text(t("changelog.version", version=latest_release.get('version', 'Unknown')), 
                           size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_700),
                    ft.Text(f"({latest_release.get('releaseDate', 'Unknown')})", 
                           size=11, color=ft.Colors.GREY_600)
                ], spacing=8),
                padding=ft.padding.only(bottom=12)
            ))
            
            # Added features
            if changelog.get('added'):
                content_items.append(ft.Row([
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=16, color=ft.Colors.GREEN_700),
                    ft.Text(t("changelog.added"), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
                ], spacing=6))
                for item in changelog['added']:
                    content_items.append(ft.Row([
                        ft.Container(width=22),
                        ft.Icon(ft.Icons.FIBER_MANUAL_RECORD, size=8, color=ft.Colors.GREEN_600),
                        ft.Text(f"{item}", size=11, color=ft.Colors.GREEN_600, expand=True)
                    ], spacing=6))
                content_items.append(ft.Container(height=8))
            
            # Changed features  
            if changelog.get('changed'):
                content_items.append(ft.Row([
                    ft.Icon(ft.Icons.BUILD_CIRCLE_OUTLINED, size=16, color=ft.Colors.BLUE_700),
                    ft.Text(t("changelog.changed"), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                ], spacing=6))
                for item in changelog['changed']:
                    content_items.append(ft.Row([
                        ft.Container(width=22),
                        ft.Icon(ft.Icons.FIBER_MANUAL_RECORD, size=8, color=ft.Colors.BLUE_600),
                        ft.Text(f"{item}", size=11, color=ft.Colors.BLUE_600, expand=True)
                    ], spacing=6))
                content_items.append(ft.Container(height=8))
            
            # Fixed issues
            if changelog.get('fixed'):
                content_items.append(ft.Row([
                    ft.Icon(ft.Icons.BUG_REPORT_OUTLINED, size=16, color=ft.Colors.ORANGE_700),
                    ft.Text(t("changelog.fixed"), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700)
                ], spacing=6))
                for item in changelog['fixed']:
                    content_items.append(ft.Row([
                        ft.Container(width=22),
                        ft.Icon(ft.Icons.FIBER_MANUAL_RECORD, size=8, color=ft.Colors.ORANGE_600),
                        ft.Text(f"{item}", size=11, color=ft.Colors.ORANGE_600, expand=True)
                    ], spacing=6))
                content_items.append(ft.Container(height=8))
            
            # Security updates
            if changelog.get('security'):
                content_items.append(ft.Row([
                    ft.Icon(ft.Icons.SECURITY, size=16, color=ft.Colors.RED_700),
                    ft.Text(t("changelog.security"), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)
                ], spacing=6))
                for item in changelog['security']:
                    content_items.append(ft.Row([
                        ft.Container(width=22),
                        ft.Icon(ft.Icons.FIBER_MANUAL_RECORD, size=8, color=ft.Colors.RED_600),
                        ft.Text(f"{item}", size=11, color=ft.Colors.RED_600, expand=True)
                    ], spacing=6))
            
            content = ft.Column(content_items, tight=True, spacing=4, scroll=ft.ScrollMode.AUTO)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ARTICLE_OUTLINED, color=ft.Colors.INDIGO_600, size=20),
                ft.Text(t("changelog.title", version=APP_VERSION), size=14, weight=ft.FontWeight.W_600),
            ], spacing=8),
            content=ft.Container(
                content=content,
                width=500,
                height=400,
                padding=10
            ),
            actions=[
                ft.TextButton(t("changelog.close"), on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        app.page.open(dlg)
        app._update_status(t("about.changelog_loaded"), ft.Colors.GREEN)
    except Exception as e:
        print(f"Changelog error: {e}")  # Debug output
        app._update_status(t("about.changelog_error"), ft.Colors.RED)

def _check_update(app, e=None):
    # Show modal dialog using page.open to ensure compatibility
    try:
        def close_dlg(ev=None):
            try:
                app.page.close(dlg)
            except Exception:
                pass
            app._update_status(t("about.no_updates"), ft.Colors.GREY)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.BLUE_600, size=20),
                ft.Text(t("about.check_updates"), size=14, weight=ft.FontWeight.W_600),
            ], spacing=8),
            content=ft.Column([
                ft.Text(t("about.update_check_description", channel=APP_CHANNEL), size=12),
                ft.Text(f"{APP_NAME} v{APP_VERSION}", size=12, color=ft.Colors.GREY_600),
            ], tight=True, spacing=6),
            actions=[
                ft.TextButton(t("dialogs.close"), on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        app.page.open(dlg)
    except Exception:
        app._update_status(t("about.no_updates"), ft.Colors.GREY)

def build(app):
    # About page content
    return ft.Container(
        content=ft.Column([
            # About information card
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=22, color=ft.Colors.INDIGO_600),
                        ft.Text(t("about.title"), size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_800)
                    ], spacing=10),
                    ft.Divider(height=1, color=ft.Colors.INDIGO_100, thickness=1),
                    ft.Column([
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{APP_NAME}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_800),
                                ft.Text(t("app.version", version=APP_VERSION), size=13, weight=ft.FontWeight.W_500, color=ft.Colors.INDIGO_600),
                                ft.Text(t("app.description"), size=12, color=ft.Colors.GREY_600, italic=True),
                            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=ft.padding.symmetric(vertical=12, horizontal=16),
                            bgcolor=ft.Colors.INDIGO_50,
                            border_radius=10,
                            alignment=ft.alignment.center
                        ),
                    ], spacing=8),
                    ft.Row([
                        ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.LANGUAGE, size=16, color=ft.Colors.WHITE), 
                                ft.Text(t("about.website"), size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500)
                            ], spacing=8, tight=True),
                            on_click=lambda e: os.startfile("https://zzbuaoye.top"),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12), 
                                bgcolor=ft.Colors.BLUE_600,
                                elevation=3,
                                shadow_color=ft.Colors.BLUE_200
                            ),
                            height=40
                        ),
                        ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.CODE, size=16, color=ft.Colors.WHITE), 
                                ft.Text(t("about.repository"), size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500)
                            ], spacing=8, tight=True),
                            on_click=lambda e: os.startfile("https://github.com/ZZBuAoYeLyrics"),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12), 
                                bgcolor=ft.Colors.GREY_700,
                                elevation=3,
                                shadow_color=ft.Colors.GREY_300
                            ),
                            height=40
                        ),
                    ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=15),
                padding=22,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.border.all(1, ft.Colors.INDIGO_100),
                shadow=ft.BoxShadow(
                    spread_radius=2,
                    blur_radius=8,
                    color=ft.Colors.with_opacity(0.12, ft.Colors.INDIGO_300),
                    offset=ft.Offset(0, 3)
                )
            ),
            
            # System information card
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.COMPUTER, size=22, color=ft.Colors.PURPLE_600),
                        ft.Text(t("about.system_info"), size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_800)
                    ], spacing=10),
                    ft.Divider(height=1, color=ft.Colors.PURPLE_100, thickness=1),
                    ft.Column([
                        # Platform info with enhanced styling
                        ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.Icon(ft.Icons.CHANGE_HISTORY_OUTLINED, size=18, color=ft.Colors.PURPLE_500),
                                    width=30,
                                    alignment=ft.alignment.center
                                ),
                                ft.Column([
                                    ft.Text(t("about.platform"), size=11, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_600),
                                    ft.Text(_get_platform_info(), size=13, weight=ft.FontWeight.W_600, color=ft.Colors.PURPLE_700),
                                ], spacing=2, tight=True),
                            ], spacing=12),
                            padding=ft.padding.symmetric(vertical=8, horizontal=12),
                            bgcolor=ft.Colors.PURPLE_50,
                            border_radius=8,
                        ),
                        # Python version info
                        ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.Icon(ft.Icons.CODE, size=18, color=ft.Colors.BLUE_500),
                                    width=30,
                                    alignment=ft.alignment.center
                                ),
                                ft.Column([
                                    ft.Text(t("about.python_version"), size=11, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_600),
                                    ft.Text(f"{platform.python_version()}", size=13, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_700),
                                ], spacing=2, tight=True),
                            ], spacing=12),
                            padding=ft.padding.symmetric(vertical=8, horizontal=12),
                            bgcolor=ft.Colors.BLUE_50,
                            border_radius=8,
                        ),
                        # Flet version info
                        ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.Icon(ft.Icons.WIDGETS, size=18, color=ft.Colors.TEAL_500),
                                    width=30,
                                    alignment=ft.alignment.center
                                ),
                                ft.Column([
                                    ft.Text(t("about.flet_framework"), size=11, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_600),
                                    ft.Text(f"v{_get_flet_version()}", size=13, weight=ft.FontWeight.W_600, color=ft.Colors.TEAL_700),
                                ], spacing=2, tight=True),
                            ], spacing=12),
                            padding=ft.padding.symmetric(vertical=8, horizontal=12),
                            bgcolor=ft.Colors.TEAL_50,
                            border_radius=8,
                        ),
                        # Working directory with better formatting
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Icon(ft.Icons.FOLDER_OPEN, size=18, color=ft.Colors.ORANGE_500),
                                        width=30,
                                        alignment=ft.alignment.center
                                    ),
                                    ft.Text(t("about.working_directory"), size=11, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_600),
                                ], spacing=12),
                                ft.Container(
                                    content=ft.Text(
                                        f"{os.getcwd()}", 
                                        size=11, 
                                        color=ft.Colors.ORANGE_700,
                                        weight=ft.FontWeight.W_500,
                                        selectable=True
                                    ),
                                    padding=ft.padding.only(left=42),
                                ),
                            ], spacing=4, tight=True),
                            padding=ft.padding.symmetric(vertical=8, horizontal=12),
                            bgcolor=ft.Colors.ORANGE_50,
                            border_radius=8,
                        ),
                    ], spacing=10),
                ], spacing=15),
                padding=22,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.border.all(1, ft.Colors.PURPLE_100),
                shadow=ft.BoxShadow(
                    spread_radius=2,
                    blur_radius=8,
                    color=ft.Colors.with_opacity(0.12, ft.Colors.PURPLE_300),
                    offset=ft.Offset(0, 3)
                )
            ),
            
            # Update check card
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.SYSTEM_UPDATE_ALT, size=22, color=ft.Colors.GREEN_600),
                        ft.Text(t("about.update_manager"), size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800)
                    ], spacing=10),
                    ft.Divider(height=1, color=ft.Colors.GREEN_100, thickness=1),
                    ft.Column([
                        ft.Container(
                            content=ft.Column([
                                ft.Text(t("about.update_description"), 
                                       size=12, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
                                ft.Container(
                                    content=ft.Row([
                                        ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED, size=14, color=ft.Colors.GREEN_600),
                                        ft.Text(t("about.current_channel", channel=APP_CHANNEL), size=12, weight=ft.FontWeight.W_600, color=ft.Colors.GREEN_700),
                                    ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                                    padding=ft.padding.symmetric(vertical=6, horizontal=12),
                                    bgcolor=ft.Colors.GREEN_50,
                                    border_radius=20,
                                ),
                            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=ft.padding.symmetric(vertical=12, horizontal=16),
                            bgcolor=ft.Colors.GREEN_50,
                            border_radius=10,
                        ),
                    ], spacing=8),
                    ft.Row([
                        ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.REFRESH, size=16, color=ft.Colors.WHITE), 
                                ft.Text(t("about.check_updates"), size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600)
                            ], spacing=6, tight=True),
                            on_click=lambda e: _check_update(app, e),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12), 
                                bgcolor=ft.Colors.GREEN_600,
                                elevation=4,
                                shadow_color=ft.Colors.GREEN_200
                            ),
                            height=40
                        ),
                        ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ARTICLE_OUTLINED, size=16, color=ft.Colors.WHITE), 
                                ft.Text(t("about.changelog"), size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600)
                            ], spacing=6, tight=True),
                            on_click=lambda e: _show_changelog(app, e),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12), 
                                bgcolor=ft.Colors.INDIGO_600,
                                elevation=4,
                                shadow_color=ft.Colors.INDIGO_200
                            ),
                            height=40
                        ),
                    ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=15),
                padding=22,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.border.all(1, ft.Colors.GREEN_100),
                shadow=ft.BoxShadow(
                    spread_radius=2,
                    blur_radius=8,
                    color=ft.Colors.with_opacity(0.12, ft.Colors.GREEN_300),
                    offset=ft.Offset(0, 3)
                )
            ),
            
            # Flet License card
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.GAVEL, size=22, color=ft.Colors.AMBER_600),
                        ft.Text(t("about.license_info"), size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_800)
                    ], spacing=10),
                    ft.Divider(height=1, color=ft.Colors.AMBER_100, thickness=1),
                    ft.Column([
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.WIDGETS, size=20, color=ft.Colors.TEAL_600),
                                    ft.Text(t("about.flet_framework"), size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_700),
                                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                                ft.Text(
                                    t("about.flet_description", version=_get_flet_version()),
                                    size=12, 
                                    color=ft.Colors.GREY_700,
                                    text_align=ft.TextAlign.CENTER
                                ),
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text(t("about.apache_license"), size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_700),
                                        ft.Text(
                                            t("about.license_compliance"),
                                            size=11, 
                                            color=ft.Colors.GREY_600,
                                            text_align=ft.TextAlign.CENTER
                                        ),
                                    ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                    padding=ft.padding.symmetric(vertical=8, horizontal=12),
                                    bgcolor=ft.Colors.AMBER_50,
                                    border_radius=8,
                                ),
                            ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=ft.padding.symmetric(vertical=12, horizontal=16),
                            bgcolor=ft.Colors.TEAL_50,
                            border_radius=10,
                        ),
                    ], spacing=8),
                    ft.Row([
                        ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.OPEN_IN_NEW, size=16, color=ft.Colors.WHITE), 
                                ft.Text(t("about.flet_website"), size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500)
                            ], spacing=8, tight=True),
                            on_click=lambda e: os.startfile("https://flet.dev"),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12), 
                                bgcolor=ft.Colors.TEAL_600,
                                elevation=3,
                                shadow_color=ft.Colors.TEAL_200
                            ),
                            height=40
                        ),
                        ft.ElevatedButton(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ARTICLE, size=16, color=ft.Colors.WHITE), 
                                ft.Text(t("about.apache_license"), size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500)
                            ], spacing=8, tight=True),
                            on_click=lambda e: os.startfile("https://www.apache.org/licenses/LICENSE-2.0"),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12), 
                                bgcolor=ft.Colors.AMBER_600,
                                elevation=3,
                                shadow_color=ft.Colors.AMBER_200
                            ),
                            height=40
                        ),
                    ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=15),
                padding=22,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                border=ft.border.all(1, ft.Colors.AMBER_100),
                shadow=ft.BoxShadow(
                    spread_radius=2,
                    blur_radius=8,
                    color=ft.Colors.with_opacity(0.12, ft.Colors.AMBER_300),
                    offset=ft.Offset(0, 3)
                )
            )
        ], spacing=20),
        padding=20
    )