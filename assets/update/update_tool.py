import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # 改进工具提示样式
        label = tk.Label(self.tooltip_window, text=self.text, justify=tk.LEFT,
                         background="#f0f0f0", relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", "9", "normal"), padx=5, pady=3,
                         foreground="#333333")
        label.pack(ipadx=1)

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

class UpdateTool:
    def __init__(self, root):
        self.root = root
        self.root.title("ZSnapr Update Manager")
        self.root.geometry("1200x800")

        # Set the theme
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        # Internationalization (i18n)
        self.translations = self.load_translations()
        self.current_language = "en"  # Default language

        # The path to update.json should be relative to the script's location
        self.json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update.json")
        self.data = self.load_data()

        # 创建状态栏
        self.status_bar = ttk.Label(self.root, text="", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.create_widgets()
        self.update_ui_language()
        self.populate_app_info()
        self.populate_releases_list()
        self.populate_update_settings()
        self.populate_metadata()

    def load_translations(self):
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages.json")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            messagebox.showerror(self.get_string("error"), self.get_string("failed_to_load_languages", error=e))
            self.root.quit()
            return {}

    def get_string(self, key, **kwargs):
        return self.translations.get(self.current_language, {}).get(key, key).format(**kwargs)

    def change_language(self, event):
        self.current_language = self.language_var.get()
        self.update_ui_language()

    def update_ui_language(self):
        self.root.title(self.get_string("window_title"))
        self.releases_frame.config(text=self.get_string("releases"))
        self.add_button.config(text=self.get_string("add"))
        self.edit_button.config(text=self.get_string("edit"))
        self.delete_button.config(text=self.get_string("delete"))
        self.notebook.tab(self.app_info_frame, text=self.get_string("app_info"))
        self.notebook.tab(self.release_details_frame, text=self.get_string("release_details"))
        self.notebook.tab(self.update_settings_frame, text=self.get_string("update_settings"))
        self.notebook.tab(self.metadata_frame, text=self.get_string("metadata"))

        # Re-populate tabs to update labels
        self.populate_app_info()
        self.populate_update_settings()
        self.populate_metadata()
        # Note: on_release_select will handle the details tab language update

    def load_data(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror(self.get_string("error"), self.get_string("file_not_found", file=self.json_path))
            self.root.quit()
            return {}
        except json.JSONDecodeError:
            messagebox.showerror(self.get_string("error"), self.get_string("could_not_decode_file", file=self.json_path))
            self.root.quit()
            return {}

    def create_widgets(self):
        # Main PanedWindow
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top frame for language and help
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        # Language selection
        lang_frame = ttk.Frame(top_frame)
        lang_frame.pack(side=tk.LEFT)
        
        ttk.Label(lang_frame, text=self.get_string("language")).pack(side=tk.LEFT, padx=(0, 5))
        self.language_var = tk.StringVar(value=self.current_language)
        language_menu = ttk.Combobox(lang_frame, textvariable=self.language_var, values=list(self.translations.keys()))
        language_menu.pack(side=tk.LEFT)
        language_menu.bind("<<ComboboxSelected>>", self.change_language)
        
        # Help button
        help_button = ttk.Button(top_frame, text=self.get_string("help"), command=self.show_help)
        help_button.pack(side=tk.RIGHT, padx=(5, 0))
        Tooltip(help_button, self.get_string("tooltips.help_tooltip"))
        
        # Quick start button for new users
        quick_start_button = ttk.Button(top_frame, text=self.get_string("quick_start"), command=self.show_quick_start)
        quick_start_button.pack(side=tk.RIGHT, padx=(5, 0))
        Tooltip(quick_start_button, self.get_string("tooltips.quick_start_tooltip"))

        # Left frame for releases list
        left_frame = ttk.Frame(main_pane, width=300)
        main_pane.add(left_frame, weight=1)

        # Right frame for details
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=3)

        # Releases List
        self.releases_frame = ttk.LabelFrame(left_frame, text=self.get_string("releases"))
        self.releases_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Search/Filter box
        search_frame = ttk.Frame(self.releases_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text=self.get_string("search")).pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_releases)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        Tooltip(search_entry, self.get_string("tooltips.search_tooltip"))

        # Releases listbox with scrollbar
        list_frame = ttk.Frame(self.releases_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.releases_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, exportselection=False)
        self.releases_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        releases_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.releases_listbox.yview)
        releases_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.releases_listbox.config(yscrollcommand=releases_scrollbar.set)
        self.releases_listbox.bind("<<ListboxSelect>>", self.on_release_select)

        # Release management buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.add_button = ttk.Button(button_frame, text=self.get_string("add"), command=self.add_release)
        self.add_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        Tooltip(self.add_button, self.get_string("tooltips.add_release_tooltip"))

        self.edit_button = ttk.Button(button_frame, text=self.get_string("edit"), command=self.edit_release)
        self.edit_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        Tooltip(self.edit_button, self.get_string("tooltips.edit_release_tooltip"))

        self.delete_button = ttk.Button(button_frame, text=self.get_string("delete"), command=self.delete_release)
        self.delete_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        Tooltip(self.delete_button, self.get_string("tooltips.delete_release_tooltip"))

        # Details Notebook
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # App Info Tab
        self.app_info_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.app_info_frame, text=self.get_string("app_info"))

        # Release Details Tab
        self.release_details_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.release_details_frame, text=self.get_string("release_details"))

        # Update Settings Tab
        self.update_settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.update_settings_frame, text=self.get_string("update_settings"))
        
        # Metadata Tab
        self.metadata_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.metadata_frame, text=self.get_string("metadata"))

    def populate_app_info(self):
        # Clear frame before populating
        for widget in self.app_info_frame.winfo_children():
            widget.destroy()

        # Using a frame to hold the content
        frame = ttk.Frame(self.app_info_frame, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        app_data = self.data.get("app", {})
        
        # Grid configuration
        frame.columnconfigure(1, weight=1)

        # Name
        ttk.Label(frame, text=self.get_string("name")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.app_name_var = tk.StringVar(value=app_data.get("name", ""))
        ttk.Entry(frame, textvariable=self.app_name_var).grid(row=0, column=1, sticky=tk.EW, pady=2)

        # Description
        ttk.Label(frame, text=self.get_string("description")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.app_desc_var = tk.StringVar(value=app_data.get("description", ""))
        ttk.Entry(frame, textvariable=self.app_desc_var).grid(row=1, column=1, sticky=tk.EW, pady=2)

        # Current Version
        ttk.Label(frame, text=self.get_string("current_version")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.app_current_version_var = tk.StringVar(value=app_data.get("currentVersion", ""))
        ttk.Entry(frame, textvariable=self.app_current_version_var).grid(row=2, column=1, sticky=tk.EW, pady=2)

        # Latest Version
        ttk.Label(frame, text=self.get_string("latest_version")).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.app_latest_version_var = tk.StringVar(value=app_data.get("latestVersion", ""))
        ttk.Entry(frame, textvariable=self.app_latest_version_var).grid(row=3, column=1, sticky=tk.EW, pady=2)

        # Update Available
        ttk.Label(frame, text=self.get_string("update_available")).grid(row=4, column=0, sticky=tk.W, pady=2)
        self.app_update_available_var = tk.BooleanVar(value=app_data.get("updateAvailable", False))
        ttk.Checkbutton(frame, variable=self.app_update_available_var, onvalue=True, offvalue=False).grid(row=4, column=1, sticky=tk.W, pady=2)

        # Save Button
        save_button = ttk.Button(frame, text=self.get_string("save_app_info"), command=self.save_app_info)
        save_button.grid(row=5, column=0, columnspan=2, pady=10)
        Tooltip(save_button, self.get_string("tooltips.save_app_info_tooltip"))

    def save_app_info(self):
        app_data = {
            "name": self.app_name_var.get(),
            "description": self.app_desc_var.get(),
            "currentVersion": self.app_current_version_var.get(),
            "latestVersion": self.app_latest_version_var.get(),
            "updateAvailable": self.app_update_available_var.get()
        }
        self.data["app"] = app_data
        self.save_data()

    def filter_releases(self, *args):
        search_term = self.search_var.get().lower()
        self.releases_listbox.delete(0, tk.END)
        
        for release in self.data.get("releases", []):
            # 搜索版本号和日期
            version = release.get("version", "").lower()
            date = release.get("releaseDate", "").lower()
            status = release.get("status", "").lower()
            
            if search_term in version or search_term in date or search_term in status:
                self.releases_listbox.insert(tk.END, f"{release['version']} - {release['releaseDate']}")
                
    def populate_releases_list(self):
        self.search_var.set("")  # 清空搜索框
        self.releases_listbox.delete(0, tk.END)
        for release in self.data.get("releases", []):
            self.releases_listbox.insert(tk.END, f"{release['version']} - {release['releaseDate']}")

    def on_release_select(self, event):
        # Clear the release details frame
        for widget in self.release_details_frame.winfo_children():
            widget.destroy()

        # Get selected release
        selected_indices = self.releases_listbox.curselection()
        if not selected_indices:
            return
        selected_index = selected_indices[0]
        selected_release = self.data["releases"][selected_index]

        # Create a canvas with a scrollbar
        main_frame = ttk.Frame(self.release_details_frame)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame, padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(main_frame, padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Populate the left frame with release details
        row = 0
        for key, value in selected_release.items():
            if key == "changelog":
                continue
            ttk.Label(left_frame, text=self.get_string(key.lower(), default=f"{key.title()}:")).grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
            ttk.Label(left_frame, text=str(value)).grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)
            row += 1

        # Populate the right frame with changelog
        changelog = selected_release.get("changelog", {})
        ttk.Label(right_frame, text=self.get_string("changelog"), font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        
        changelog_text = tk.Text(right_frame, wrap=tk.WORD, height=15, width=40)
        changelog_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        if changelog:
            for change_type, changes in changelog.items():
                if not changes:
                    continue
                changelog_text.insert(tk.END, f"{change_type.title()}:\n", ("bold",))
                for change in changes:
                    changelog_text.insert(tk.END, f"  - {change}\n")
                changelog_text.insert(tk.END, "\n")
        
        changelog_text.tag_configure("bold", font=("TkDefaultFont", 9, "bold"))
        changelog_text.config(state=tk.DISABLED)

    def populate_update_settings(self):
        # Clear frame before populating
        for widget in self.update_settings_frame.winfo_children():
            widget.destroy()

        frame = ttk.Frame(self.update_settings_frame, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        settings_data = self.data.get("updateSettings", {})

        self.update_settings_vars = {}
        row = 0
        for key, value in settings_data.items():
            ttk.Label(frame, text=self.get_string(key, default=f"{key.title()}:")).grid(row=row, column=0, sticky=tk.W, pady=2)
            if isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                ttk.Checkbutton(frame, variable=var).grid(row=row, column=1, sticky=tk.W, pady=2)
            else:
                var = tk.StringVar(value=str(value))
                ttk.Entry(frame, textvariable=var).grid(row=row, column=1, sticky=tk.EW, pady=2)
            self.update_settings_vars[key] = var
            row += 1

        save_button = ttk.Button(frame, text=self.get_string("save_update_settings"), command=self.save_update_settings)
        save_button.grid(row=row, column=0, columnspan=2, pady=10)
        Tooltip(save_button, self.get_string("tooltips.save_update_settings_tooltip"))

    def save_update_settings(self):
        settings_data = {}
        for key, var in self.update_settings_vars.items():
            if isinstance(var, tk.BooleanVar):
                settings_data[key] = var.get()
            else:
                # Try to convert to int if possible
                try:
                    settings_data[key] = int(var.get())
                except ValueError:
                    settings_data[key] = var.get()
        self.data["updateSettings"] = settings_data
        self.save_data()
        
    def populate_metadata(self):
        # Clear frame before populating
        for widget in self.metadata_frame.winfo_children():
            widget.destroy()

        frame = ttk.Frame(self.metadata_frame, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        metadata = self.data.get("metadata", {})

        self.metadata_vars = {}
        row = 0
        for key, value in metadata.items():
            ttk.Label(frame, text=self.get_string(key, default=f"{key.title()}:")).grid(row=row, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar(value=str(value))
            ttk.Entry(frame, textvariable=var).grid(row=row, column=1, sticky=tk.EW, pady=2)
            self.metadata_vars[key] = var
            row += 1

        save_button = ttk.Button(frame, text=self.get_string("save_metadata"), command=self.save_metadata)
        save_button.grid(row=row, column=0, columnspan=2, pady=10)
        Tooltip(save_button, self.get_string("tooltips.save_metadata_tooltip"))

    def save_metadata(self):
        metadata = {}
        for key, var in self.metadata_vars.items():
            metadata[key] = var.get()
        self.data["metadata"] = metadata
        self.save_data()

    def show_status_message(self, message, duration=3000):
        """在状态栏显示消息，并在指定时间后清除"""
        self.status_bar.config(text=message)
        # 使用after方法在指定时间后清除消息
        self.root.after(duration, lambda: self.status_bar.config(text=""))
        
    def save_data(self):
        try:
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            self.show_status_message(self.get_string("data_saved_successfully"))
        except Exception as e:
            messagebox.showerror(self.get_string("error"), self.get_string("failed_to_save_data", error=e))

    def add_release(self):
        # Create a new top-level window for the release editor
        editor = tk.Toplevel(self.root)
        editor.title(self.get_string("add_new_release"))
        editor.geometry("600x400")

        # Create a dictionary to hold the entry widgets
        entries = {}

        # Create a form for the new release
        form_frame = ttk.Frame(editor, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True)
        form_frame.columnconfigure(1, weight=1)

        # Define the fields for a new release
        fields = ["version", "releaseDate", "type", "status", "downloadUrl", "fileSize"]
        type_options = ["major", "minor", "patch"]
        form_frame.columnconfigure(2, weight=0) # Add a column for the explanation

        for i, field in enumerate(fields):
            label = ttk.Label(form_frame, text=self.get_string(field, default=f"{field.title()}:"))
            label.grid(row=i, column=0, sticky=tk.W, pady=2)
            Tooltip(label, self.get_string(f"tooltips.{field}_tooltip"))

            widget = None
            if field == "type":
                widget = ttk.Combobox(form_frame, values=type_options, state="readonly")
                widget.grid(row=i, column=1, sticky=tk.EW, pady=2)
                explanation_label = ttk.Label(form_frame, text=self.get_string("type_explanation"), foreground="gray")
                explanation_label.grid(row=i, column=2, sticky=tk.W, padx=5)
                Tooltip(explanation_label, self.get_string("tooltips.type_explanation_tooltip"))
            else:
                widget = ttk.Entry(form_frame)
                widget.grid(row=i, column=1, columnspan=2, sticky=tk.EW, pady=2)

            if field == "releaseDate":
                widget.insert(0, datetime.now().strftime("%Y-%m-%d"))

            entries[field] = widget
            Tooltip(widget, self.get_string(f"tooltips.{field}_tooltip"))

        # Save button
        def save_new_release():
            new_release = {field: entries[field].get() for field in fields}
            # Add empty changelog and other fields
            new_release["checksum"] = {"sha256": "", "md5": ""}
            new_release["changelog"] = {"added": [], "changed": [], "deprecated": [], "removed": [], "fixed": [], "security": []}
            new_release["requirements"] = {"os": [], "architecture": [], "minRam": "", "minStorage": ""}
            new_release["breaking"] = False
            new_release["critical"] = False

            self.data["releases"].insert(0, new_release) # Insert at the beginning
            self.save_data()
            self.populate_releases_list()
            editor.destroy()

        def quick_fill():
            # Suggest a new version based on the latest one
            if self.data["releases"]:
                latest_version = self.data["releases"][0]["version"]
                try:
                    parts = list(map(int, latest_version.split('.')))
                    parts[-1] += 1
                    suggested_version = '.'.join(map(str, parts))
                    entries["version"].delete(0, tk.END)
                    entries["version"].insert(0, suggested_version)
                except (ValueError, IndexError):
                    pass  # Ignore if version format is not as expected

            entries["type"].delete(0, tk.END)
            entries["type"].insert(0, "minor")
            entries["status"].delete(0, tk.END)
            entries["status"].insert(0, "stable")

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        save_button = ttk.Button(button_frame, text=self.get_string("save"), command=save_new_release)
        save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        Tooltip(save_button, self.get_string("tooltips.save_new_release_tooltip"))

        quick_fill_button = ttk.Button(button_frame, text=self.get_string("quick_fill"), command=quick_fill)
        quick_fill_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        Tooltip(quick_fill_button, self.get_string("tooltips.quick_fill_tooltip"))

    def edit_release(self):
        selected_indices = self.releases_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(self.get_string("warning"), self.get_string("select_release_to_edit_warning"))
            return

        selected_index = selected_indices[0]
        release_data = self.data["releases"][selected_index]

        editor = tk.Toplevel(self.root)
        editor.title(self.get_string("edit_release_title", version=release_data['version']))
        editor.geometry("800x600")

        entries = {}
        notebook = ttk.Notebook(editor)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # General Info Tab
        general_frame = ttk.Frame(notebook, padding="10")
        notebook.add(general_frame, text=self.get_string("general"))
        general_frame.columnconfigure(1, weight=1)

        fields = ["version", "releaseDate", "type", "status", "downloadUrl", "fileSize"]
        for i, field in enumerate(fields):
            ttk.Label(general_frame, text=self.get_string(field, default=f"{field.title()}:")).grid(row=i, column=0, sticky=tk.W, pady=2)
            entry = ttk.Entry(general_frame)
            entry.insert(0, release_data.get(field, ""))
            entry.grid(row=i, column=1, sticky=tk.EW, pady=2)
            entries[field] = entry

        # Changelog Tab
        changelog_frame = ttk.Frame(notebook, padding="10")
        notebook.add(changelog_frame, text=self.get_string("changelog"))

        # Visual Changelog Editor
        changelog_editor_frame = ttk.Frame(changelog_frame)
        changelog_editor_frame.pack(fill=tk.BOTH, expand=True)

        # Category List (Treeview)
        category_frame = ttk.Frame(changelog_editor_frame)
        category_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        ttk.Label(category_frame, text=self.get_string("categories", default="Categories")).pack(anchor=tk.W)
        self.changelog_categories = ttk.Treeview(category_frame, selectmode="browse", show="tree")
        self.changelog_categories.pack(fill=tk.Y, expand=True)
        self.changelog_categories.bind("<<TreeviewSelect>>", self.on_category_select)

        # Changes List (Listbox)
        changes_frame = ttk.Frame(changelog_editor_frame)
        changes_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(changes_frame, text=self.get_string("changes", default="Changes")).pack(anchor=tk.W)
        self.changelog_listbox = tk.Listbox(changes_frame)
        self.changelog_listbox.pack(fill=tk.BOTH, expand=True)

        # Buttons for changes
        change_button_frame = ttk.Frame(changes_frame)
        change_button_frame.pack(fill=tk.X, pady=5)
        add_change_button = ttk.Button(change_button_frame, text=self.get_string("add"), command=self.add_changelog_entry)
        add_change_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        edit_change_button = ttk.Button(change_button_frame, text=self.get_string("edit"), command=self.edit_changelog_entry)
        edit_change_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        delete_change_button = ttk.Button(change_button_frame, text=self.get_string("delete"), command=self.delete_changelog_entry)
        delete_change_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Populate the changelog editor
        self.populate_changelog_editor(release_data.get("changelog", {}))

        def save_edited_release():
            # Update general fields
            for field in fields:
                release_data[field] = entries[field].get()

            # Update changelog from the visual editor
            if hasattr(self, '_changelog_data'):
                release_data["changelog"] = self._changelog_data

            self.data["releases"][selected_index] = release_data
            self.save_data()
            self.reload_data()
            editor.destroy()

        save_button = ttk.Button(editor, text=self.get_string("save"), command=save_edited_release)
        save_button.pack(pady=10)
        Tooltip(save_button, self.get_string("tooltips.save_edited_release_tooltip"))

    def populate_changelog_editor(self, changelog_data):
        self._changelog_data = changelog_data
        self.changelog_categories.delete(*self.changelog_categories.get_children())
        for category in changelog_data.keys():
            self.changelog_categories.insert("", tk.END, text=category, open=True)

    def on_category_select(self, event):
        selected_item = self.changelog_categories.focus()
        if not selected_item:
            return
        
        category_name = self.changelog_categories.item(selected_item, "text")
        changes = self._changelog_data.get(category_name, [])
        
        self.changelog_listbox.delete(0, tk.END)
        for change in changes:
            self.changelog_listbox.insert(tk.END, change)

    def add_changelog_entry(self):
        selected_item = self.changelog_categories.focus()
        if not selected_item:
            messagebox.showwarning(self.get_string("warning"), self.get_string("select_category_warning"))
            return

        category_name = self.changelog_categories.item(selected_item, "text")
        
        new_change = tk.simpledialog.askstring(self.get_string("add_change_title"), self.get_string("enter_change_prompt"))
        
        if new_change:
            if category_name not in self._changelog_data:
                self._changelog_data[category_name] = []
            self._changelog_data[category_name].append(new_change)
            self.on_category_select(None) # Refresh the list

    def edit_changelog_entry(self):
        selected_item = self.changelog_categories.focus()
        selected_indices = self.changelog_listbox.curselection()

        if not selected_item or not selected_indices:
            messagebox.showwarning(self.get_string("warning"), self.get_string("select_change_to_edit_warning"))
            return

        category_name = self.changelog_categories.item(selected_item, "text")
        change_index = selected_indices[0]
        old_change = self._changelog_data[category_name][change_index]

        edited_change = tk.simpledialog.askstring(self.get_string("edit_change_title"), self.get_string("edit_change_prompt"), initialvalue=old_change)

        if edited_change and edited_change != old_change:
            self._changelog_data[category_name][change_index] = edited_change
            self.on_category_select(None) # Refresh the list

    def delete_changelog_entry(self):
        selected_item = self.changelog_categories.focus()
        selected_indices = self.changelog_listbox.curselection()

        if not selected_item or not selected_indices:
            messagebox.showwarning(self.get_string("warning"), self.get_string("select_change_to_delete_warning"))
            return

        category_name = self.changelog_categories.item(selected_item, "text")
        change_index = selected_indices[0]

        if messagebox.askyesno(self.get_string("confirm_delete_title"), self.get_string("confirm_delete_change_message")):
            del self._changelog_data[category_name][change_index]
            self.on_category_select(None) # Refresh the list

    def delete_release(self):
        selected_indices = self.releases_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(self.get_string("warning"), self.get_string("select_release_to_delete_warning"))
            return

        selected_index = selected_indices[0]
        release_version = self.data["releases"][selected_index]["version"]

        # 添加确认对话框以防止意外操作
        if messagebox.askyesno(self.get_string("confirm_delete_title"), self.get_string("confirm_delete_message", version=release_version)):
            del self.data["releases"][selected_index]
            self.save_data()
            self.reload_data()
            # 添加状态栏消息
            messagebox.showinfo(self.get_string("success"), self.get_string("release_deleted_successfully", version=release_version))

    def reload_data(self):
        self.data = self.load_data()
        self.populate_app_info()
        self.populate_releases_list()
        self.populate_update_settings()
        self.populate_metadata()

if __name__ == "__main__":
    root = tk.Tk()
    app = UpdateTool(root)
    root.mainloop()