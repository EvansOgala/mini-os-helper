from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from quick_actions import ActionError, open_path, open_web, run_command
from settings import load_notes, load_settings, save_notes, save_settings
from system_info import get_system_snapshot
from gtk_style import install_material_smooth_css


class MiniOSHelperApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.evans.MiniOSHelper")
        self.window: Gtk.ApplicationWindow | None = None
        self.settings = load_settings()
        self.auto_source_id: int | None = None

        self.theme_values = ["dark", "light"]
        self.css_provider = None

        self.theme_dropdown: Gtk.DropDown | None = None
        self.interval_spin: Gtk.SpinButton | None = None
        self.auto_switch: Gtk.Switch | None = None
        self.status_label: Gtk.Label | None = None

        self.system_view: Gtk.TextView | None = None
        self.output_view: Gtk.TextView | None = None
        self.notes_view: Gtk.TextView | None = None
        self.cmd_entry: Gtk.Entry | None = None

        self.path_box: Gtk.Box | None = None
        self.web_box: Gtk.Box | None = None

    def do_activate(self):
        if self.window is None:
            self._build_ui()
            self._refresh_system_once(set_status=False)
            if bool(self.settings.get("auto_refresh", True)):
                self._schedule_auto_refresh()
        self.window.present()

    def _build_ui(self):
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("Mini OS Helper")
        self.window.set_default_size(1024, 700)
        self.css_provider = install_material_smooth_css(self.window)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)
        self.window.set_child(root)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.append(header)

        title_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header.append(title_wrap)

        title = Gtk.Label(label="Mini OS Helper")
        title.set_xalign(0.0)
        title.add_css_class("title-2")
        title_wrap.append(title)

        subtitle = Gtk.Label(label="Quick tools, live metrics, and automation")
        subtitle.set_xalign(0.0)
        subtitle.add_css_class("dim-label")
        title_wrap.append(subtitle)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        self.theme_dropdown = Gtk.DropDown.new_from_strings(self.theme_values)
        self._set_dropdown_value(self.theme_dropdown, self.theme_values, self.settings.get("theme", "dark"))
        self.theme_dropdown.connect("notify::selected", self._on_theme_changed)
        header.append(self.theme_dropdown)

        notebook = Gtk.Notebook()
        notebook.set_hexpand(True)
        notebook.set_vexpand(True)
        root.append(notebook)

        notebook.append_page(self._build_dashboard_tab(), Gtk.Label(label="Dashboard"))
        notebook.append_page(self._build_actions_tab(), Gtk.Label(label="Quick Actions"))
        notebook.append_page(self._build_notes_tab(), Gtk.Label(label="Notes"))

        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0.0)
        self.status_label.add_css_class("dim-label")
        root.append(self.status_label)

        self._apply_theme(self.settings.get("theme", "dark"))

    def _build_dashboard_tab(self) -> Gtk.Widget:
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tab.set_margin_top(10)
        tab.set_margin_bottom(10)
        tab.set_margin_start(10)
        tab.set_margin_end(10)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tab.append(controls)

        refresh_btn = Gtk.Button(label="Refresh Now")
        refresh_btn.connect("clicked", lambda _btn: self.refresh_system())
        controls.append(refresh_btn)

        auto_label = Gtk.Label(label="Auto Refresh")
        controls.append(auto_label)

        self.auto_switch = Gtk.Switch()
        self.auto_switch.set_active(bool(self.settings.get("auto_refresh", True)))
        self.auto_switch.connect("notify::active", self._on_auto_refresh_toggled)
        controls.append(self.auto_switch)

        controls.append(Gtk.Label(label="Interval (ms):"))
        self.interval_spin = Gtk.SpinButton.new_with_range(100, 2000, 100)
        self.interval_spin.set_value(int(self.settings.get("refresh_interval_ms", 1000)))
        self.interval_spin.connect("value-changed", self._on_interval_changed)
        controls.append(self.interval_spin)

        system_scroller = Gtk.ScrolledWindow()
        system_scroller.set_hexpand(True)
        system_scroller.set_vexpand(True)
        tab.append(system_scroller)

        self.system_view = Gtk.TextView()
        self.system_view.set_editable(False)
        self.system_view.set_monospace(True)
        system_scroller.set_child(self.system_view)

        return tab

    def _build_actions_tab(self) -> Gtk.Widget:
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab.set_margin_top(10)
        tab.set_margin_bottom(10)
        tab.set_margin_start(10)
        tab.set_margin_end(10)

        self.path_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        path_frame = Gtk.Frame(label="Favorite Paths")
        path_frame.set_child(self.path_box)
        tab.append(path_frame)

        self.web_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        web_frame = Gtk.Frame(label="Web Shortcuts")
        web_frame.set_child(self.web_box)
        tab.append(web_frame)

        cmd_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab.append(cmd_row)

        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.set_placeholder_text("Enter command")
        self.cmd_entry.set_hexpand(True)
        self.cmd_entry.connect("activate", lambda _entry: self._run_command())
        cmd_row.append(self.cmd_entry)

        run_btn = Gtk.Button(label="Run")
        run_btn.connect("clicked", lambda _btn: self._run_command())
        cmd_row.append(run_btn)

        out_scroller = Gtk.ScrolledWindow()
        out_scroller.set_hexpand(True)
        out_scroller.set_vexpand(True)
        tab.append(out_scroller)

        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_monospace(True)
        out_scroller.set_child(self.output_view)

        self._populate_action_buttons()
        return tab

    def _build_notes_tab(self) -> Gtk.Widget:
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tab.set_margin_top(10)
        tab.set_margin_bottom(10)
        tab.set_margin_start(10)
        tab.set_margin_end(10)

        save_btn = Gtk.Button(label="Save Notes")
        save_btn.connect("clicked", lambda _btn: self._save_notes())
        tab.append(save_btn)

        notes_scroller = Gtk.ScrolledWindow()
        notes_scroller.set_hexpand(True)
        notes_scroller.set_vexpand(True)
        tab.append(notes_scroller)

        self.notes_view = Gtk.TextView()
        self.notes_view.set_monospace(True)
        notes_buffer = self.notes_view.get_buffer()
        notes_buffer.set_text(load_notes())
        notes_scroller.set_child(self.notes_view)

        return tab

    def _populate_action_buttons(self):
        if self.path_box is None or self.web_box is None:
            return

        self._clear_box(self.path_box)
        self._clear_box(self.web_box)

        favorites = self.settings.get("favorites", {})
        for name, path in favorites.items():
            btn = Gtk.Button(label=f"{name}: {path}")
            btn.set_halign(Gtk.Align.START)
            btn.connect("clicked", lambda _btn, p=path: self._open_path(p))
            self.path_box.append(btn)

        shortcuts = self.settings.get("web_shortcuts", {})
        for name, url in shortcuts.items():
            btn = Gtk.Button(label=f"{name}: {url}")
            btn.set_halign(Gtk.Align.START)
            btn.connect("clicked", lambda _btn, u=url: self._open_web(u))
            self.web_box.append(btn)

    @staticmethod
    def _clear_box(box: Gtk.Box):
        child = box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            box.remove(child)
            child = nxt

    def _set_status(self, text: str):
        if self.status_label is not None:
            self.status_label.set_text(text)

    def _set_textview_text(self, view: Gtk.TextView | None, text: str):
        if view is None:
            return
        buffer = view.get_buffer()
        buffer.set_text(text)

    def _append_output(self, text: str):
        if self.output_view is None:
            return
        buffer = self.output_view.get_buffer()
        end_iter = buffer.get_end_iter()
        prefix = "\n\n" if buffer.get_char_count() else ""
        buffer.insert(end_iter, f"{prefix}{text}")

    def _refresh_system_once(self, set_status: bool = True):
        info = get_system_snapshot(cpu_interval=0.1)
        text = (
            f"OS: {info['os']}\n"
            f"Python: {info['python']}\n"
            f"Uptime: {info['uptime']}\n"
            f"CPU: {info['cpu']}\n"
            f"RAM: {info['ram']}\n"
            f"Disk: {info['disk']}\n"
            f"Battery: {info['battery']}\n"
            f"Processes: {info['processes']}"
        )
        self._set_textview_text(self.system_view, text)
        if set_status:
            self._set_status("System info updated")

    def refresh_system(self):
        self._refresh_system_once(set_status=True)

    def _schedule_auto_refresh(self):
        self._cancel_auto_refresh()
        interval = int(self.settings.get("refresh_interval_ms", 1000))
        self.auto_source_id = GLib.timeout_add(interval, self._on_auto_tick)

    def _cancel_auto_refresh(self):
        if self.auto_source_id is not None:
            GLib.source_remove(self.auto_source_id)
            self.auto_source_id = None

    def _on_auto_tick(self):
        self._refresh_system_once(set_status=False)
        return True

    def _persist_refresh_settings(self):
        if self.interval_spin is not None:
            self.settings["refresh_interval_ms"] = int(self.interval_spin.get_value())
        if self.auto_switch is not None:
            self.settings["auto_refresh"] = bool(self.auto_switch.get_active())
        save_settings(self.settings)

    def _on_interval_changed(self, _spin: Gtk.SpinButton):
        self._persist_refresh_settings()
        if self.auto_switch is not None and self.auto_switch.get_active():
            self._schedule_auto_refresh()

    def _on_auto_refresh_toggled(self, _switch: Gtk.Switch, _param):
        self._persist_refresh_settings()
        if self.auto_switch is not None and self.auto_switch.get_active():
            self._schedule_auto_refresh()
            self._set_status("Auto refresh enabled")
        else:
            self._cancel_auto_refresh()
            self._set_status("Auto refresh disabled")

    def _open_path(self, path: str):
        try:
            open_path(path)
            self._set_status(f"Opened path: {path}")
        except ActionError as exc:
            self._set_status(f"Open path failed: {exc}")

    def _open_web(self, url: str):
        try:
            open_web(url)
            self._set_status(f"Opened URL: {url}")
        except ActionError as exc:
            self._set_status(f"Open URL failed: {exc}")

    def _run_command(self):
        if self.cmd_entry is None:
            return
        command = self.cmd_entry.get_text().strip()
        if not command:
            self._set_status("Enter a command first")
            return

        self._append_output(f"$ {command}")
        self._set_status("Running command...")

        def task():
            try:
                code, output = run_command(command)
                result = output or "(no output)"
                GLib.idle_add(self._on_command_done, code, result)
            except ActionError as exc:
                GLib.idle_add(self._on_command_done, 1, str(exc))

        threading.Thread(target=task, daemon=True).start()

    def _on_command_done(self, code: int, output: str):
        self._append_output(output)
        self._set_status(f"Command finished with exit code {code}")
        return False

    def _save_notes(self):
        if self.notes_view is None:
            return
        buffer = self.notes_view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        content = buffer.get_text(start, end, True)
        save_notes(content)
        self._set_status("Notes saved")

    def _on_theme_changed(self, dropdown: Gtk.DropDown, _param):
        theme = self._get_dropdown_value(dropdown, self.theme_values)
        self._apply_theme(theme)

    def _apply_theme(self, theme_name: str):
        if theme_name not in {"dark", "light"}:
            theme_name = "dark"
        self.settings["theme"] = theme_name
        save_settings(self.settings)

        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings is not None:
            gtk_settings.set_property("gtk-application-prefer-dark-theme", theme_name == "dark")

    @staticmethod
    def _set_dropdown_value(dropdown: Gtk.DropDown, values: list[str], value: str):
        try:
            idx = values.index(value)
        except ValueError:
            idx = 0
        dropdown.set_selected(idx)

    @staticmethod
    def _get_dropdown_value(dropdown: Gtk.DropDown, values: list[str]) -> str:
        idx = int(dropdown.get_selected())
        if 0 <= idx < len(values):
            return values[idx]
        return values[0]
