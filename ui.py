from __future__ import annotations

import sys
import threading

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from quick_actions import ActionError, open_path, open_web, run_command
from qt_style import THEMES, apply_qt_theme
from settings import load_notes, load_settings, save_notes, save_settings
from system_info import get_system_snapshot


class MiniOSHelperWindow(QMainWindow):
    command_done = Signal(int, str)

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.setWindowTitle("Mini OS Helper")
        self.resize(1120, 740)
        self.setMinimumSize(980, 620)

        self.settings = load_settings()
        self.theme_name = self.settings.get("theme", "dark")
        if self.theme_name not in THEMES:
            self.theme_name = "dark"

        self.nav_buttons: list[QPushButton] = []
        self.stack: QStackedWidget | None = None
        self.theme_dropdown: QComboBox | None = None
        self.interval_spin: QSpinBox | None = None
        self.auto_check: QCheckBox | None = None
        self.status_label: QLabel | None = None
        self.system_view: QTextEdit | None = None
        self.output_view: QTextEdit | None = None
        self.notes_view: QTextEdit | None = None
        self.cmd_entry: QLineEdit | None = None
        self.path_layout: QVBoxLayout | None = None
        self.web_layout: QVBoxLayout | None = None

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(lambda: self._refresh_system_once(set_status=False))
        self.command_done.connect(self._on_command_done)

        self._build_ui()
        self._apply_settings()
        self._refresh_system_once(set_status=False)
        self._sync_auto_refresh()

    def _build_ui(self):
        apply_qt_theme(self.app, self.theme_name)

        root = QWidget()
        root.setObjectName("appRoot")
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.setCentralWidget(root)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 14, 12, 12)
        side_layout.setSpacing(8)
        shell.addWidget(sidebar)

        brand = QLabel("Mini OS Helper")
        brand.setObjectName("brandTitle")
        side_layout.addWidget(brand)

        for index, (label, page_name) in enumerate(
            (("Dashboard", "dashboard"), ("Quick Actions", "actions"), ("Notes", "notes"))
        ):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setProperty("pageName", page_name)
            button.clicked.connect(lambda _checked=False, page=index: self._set_page(page))
            side_layout.addWidget(button)
            self.nav_buttons.append(button)

        side_layout.addSpacing(10)
        line = QFrame()
        line.setObjectName("sidebarLine")
        line.setFrameShape(QFrame.Shape.HLine)
        side_layout.addWidget(line)

        theme_label = QLabel("Theme")
        theme_label.setObjectName("sidebarLabel")
        side_layout.addWidget(theme_label)

        self.theme_dropdown = QComboBox()
        self.theme_dropdown.addItems(["dark", "light"])
        self.theme_dropdown.currentTextChanged.connect(self._apply_theme)
        side_layout.addWidget(self.theme_dropdown)

        side_layout.addStretch(1)

        quit_button = QPushButton("Quit")
        quit_button.setObjectName("navButton")
        quit_button.clicked.connect(lambda _checked=False: self.app.quit())
        side_layout.addWidget(quit_button)

        content = QWidget()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(26, 22, 26, 18)
        content_layout.setSpacing(16)
        shell.addWidget(content, 1)

        title = QLabel("Mini OS Helper")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Quick tools, live metrics, and automation")
        subtitle.setObjectName("mutedText")
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_dashboard_page())
        self.stack.addWidget(self._build_actions_page())
        self.stack.addWidget(self._build_notes_page())
        content_layout.addWidget(self.stack, 1)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        content_layout.addWidget(self.status_label)

        self._set_page(0)

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        controls = QFrame()
        controls.setObjectName("panel")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(12, 12, 12, 12)
        controls_layout.setSpacing(8)
        layout.addWidget(controls)

        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.setProperty("primary", True)
        refresh_btn.clicked.connect(lambda _checked=False: self.refresh_system())
        controls_layout.addWidget(refresh_btn)

        self.auto_check = QCheckBox("Auto refresh")
        self.auto_check.stateChanged.connect(lambda _state: self._on_refresh_options_changed())
        controls_layout.addWidget(self.auto_check)

        controls_layout.addWidget(QLabel("Interval (ms)"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 2000)
        self.interval_spin.setSingleStep(100)
        self.interval_spin.valueChanged.connect(lambda _value: self._on_refresh_options_changed())
        controls_layout.addWidget(self.interval_spin)
        controls_layout.addStretch(1)

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(8)
        section = QLabel("System Snapshot")
        section.setObjectName("sectionTitle")
        panel_layout.addWidget(section)

        self.system_view = QTextEdit()
        self.system_view.setObjectName("textView")
        self.system_view.setReadOnly(True)
        self.system_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        panel_layout.addWidget(self.system_view, 1)
        layout.addWidget(panel, 1)
        return page

    def _build_actions_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        shortcuts = QHBoxLayout()
        shortcuts.setSpacing(12)
        layout.addLayout(shortcuts)

        paths_panel = self._make_shortcut_panel("Favorite Paths")
        self.path_layout = paths_panel.layout().itemAt(1).layout()  # type: ignore[union-attr]
        shortcuts.addWidget(paths_panel)

        web_panel = self._make_shortcut_panel("Web Shortcuts")
        self.web_layout = web_panel.layout().itemAt(1).layout()  # type: ignore[union-attr]
        shortcuts.addWidget(web_panel)

        command_panel = QFrame()
        command_panel.setObjectName("panel")
        command_layout = QVBoxLayout(command_panel)
        command_layout.setContentsMargins(12, 12, 12, 12)
        command_layout.setSpacing(8)

        command_title = QLabel("Command Runner")
        command_title.setObjectName("sectionTitle")
        command_layout.addWidget(command_title)

        command_row = QHBoxLayout()
        command_row.setSpacing(8)
        self.cmd_entry = QLineEdit()
        self.cmd_entry.setPlaceholderText("Enter command")
        self.cmd_entry.returnPressed.connect(self._run_command)
        command_row.addWidget(self.cmd_entry, 1)
        run_btn = QPushButton("Run")
        run_btn.setProperty("primary", True)
        run_btn.clicked.connect(lambda _checked=False: self._run_command())
        command_row.addWidget(run_btn)
        command_layout.addLayout(command_row)

        self.output_view = QTextEdit()
        self.output_view.setObjectName("textView")
        self.output_view.setReadOnly(True)
        self.output_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        command_layout.addWidget(self.output_view, 1)
        layout.addWidget(command_panel, 1)

        self._populate_action_buttons()
        return page

    def _build_notes_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        save_btn = QPushButton("Save Notes")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(lambda _checked=False: self._save_notes())
        layout.addWidget(save_btn, 0)

        self.notes_view = QTextEdit()
        self.notes_view.setObjectName("textView")
        self.notes_view.setPlainText(load_notes())
        layout.addWidget(self.notes_view, 1)
        return page

    def _make_shortcut_panel(self, title_text: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        title = QLabel(title_text)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        buttons = QVBoxLayout()
        buttons.setSpacing(6)
        layout.addLayout(buttons)
        layout.addStretch(1)
        return panel

    def _apply_settings(self):
        if self.theme_dropdown is not None:
            self.theme_dropdown.blockSignals(True)
            self.theme_dropdown.setCurrentText(self.theme_name)
            self.theme_dropdown.blockSignals(False)
        if self.interval_spin is not None:
            self.interval_spin.setValue(int(self.settings.get("refresh_interval_ms", 1000)))
        if self.auto_check is not None:
            self.auto_check.setChecked(bool(self.settings.get("auto_refresh", True)))
        self._apply_theme(self.theme_name)

    def _set_page(self, index: int):
        if self.stack is not None:
            self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)

    def _set_status(self, text: str):
        if self.status_label is not None:
            self.status_label.setText(text)

    def _set_text(self, view: QTextEdit | None, text: str):
        if view is not None:
            view.setPlainText(text)

    def _append_output(self, text: str):
        if self.output_view is not None:
            self.output_view.append(text)

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
        self._set_text(self.system_view, text)
        if set_status:
            self._set_status("System info updated")

    def refresh_system(self):
        self._refresh_system_once(set_status=True)

    def _on_refresh_options_changed(self):
        if self.interval_spin is not None:
            self.settings["refresh_interval_ms"] = int(self.interval_spin.value())
        if self.auto_check is not None:
            self.settings["auto_refresh"] = bool(self.auto_check.isChecked())
        save_settings(self.settings)
        self._sync_auto_refresh()

    def _sync_auto_refresh(self):
        self.auto_timer.stop()
        if bool(self.settings.get("auto_refresh", True)):
            self.auto_timer.start(int(self.settings.get("refresh_interval_ms", 1000)))
            self._set_status("Auto refresh enabled")
        else:
            self._set_status("Auto refresh disabled")

    def _populate_action_buttons(self):
        if self.path_layout is None or self.web_layout is None:
            return
        self._clear_layout(self.path_layout)
        self._clear_layout(self.web_layout)

        for name, path in self.settings.get("favorites", {}).items():
            button = QPushButton(f"{name}: {path}")
            button.clicked.connect(lambda _checked=False, p=path: self._open_path(p))
            self.path_layout.addWidget(button)
        self.path_layout.addStretch(1)

        for name, url in self.settings.get("web_shortcuts", {}).items():
            button = QPushButton(f"{name}: {url}")
            button.clicked.connect(lambda _checked=False, u=url: self._open_web(u))
            self.web_layout.addWidget(button)
        self.web_layout.addStretch(1)

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
        command = self.cmd_entry.text().strip()
        if not command:
            self._set_status("Enter a command first")
            return

        self._append_output(f"$ {command}")
        self._set_status("Running command...")

        def task():
            try:
                code, output = run_command(command)
                self.command_done.emit(code, output or "(no output)")
            except ActionError as exc:
                self.command_done.emit(1, str(exc))

        threading.Thread(target=task, daemon=True).start()

    def _on_command_done(self, code: int, output: str):
        self._append_output(output)
        self._set_status(f"Command finished with exit code {code}")

    def _save_notes(self):
        if self.notes_view is None:
            return
        save_notes(self.notes_view.toPlainText())
        self._set_status("Notes saved")

    def _apply_theme(self, theme_name: str):
        if theme_name not in THEMES:
            theme_name = "dark"
        self.theme_name = theme_name
        self.settings["theme"] = theme_name
        save_settings(self.settings)
        apply_qt_theme(self.app, theme_name)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                MiniOSHelperWindow._clear_layout(child_layout)  # type: ignore[arg-type]


class MiniOSHelperApp(QApplication):
    def __init__(self):
        super().__init__(sys.argv)
        self.setApplicationName("Mini OS Helper")
        self.setApplicationDisplayName("Mini OS Helper")
        self.setOrganizationName("Evans")
        self.window = MiniOSHelperWindow(self)
        self.window.setWindowIcon(QIcon("org.evans.MiniOSHelper.svg"))

    def run(self, _argv: list[str] | None = None) -> int:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        return self.exec()
