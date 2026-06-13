from __future__ import annotations

import os
import threading

from PySide6 import QtCore, QtGui, QtWidgets

from quick_actions import ActionError, open_path, open_web, run_command, run_command_in_terminal
from settings import load_notes, load_settings, save_notes, save_settings
from system_info import get_system_snapshot

_LIGHT_QSS = """
QWidget {
  font-family: "Segoe UI Variable", "Segoe UI", "Inter", sans-serif;
  font-size: 13px;
  color: #1c2433;
}
QMainWindow { background: #eef2f7; }
QGroupBox {
  background: #ffffff;
  border: 1px solid rgba(27, 39, 64, 0.12);
  border-radius: 12px;
  margin-top: 10px;
  padding: 12px;
}
QGroupBox::title {
  subcontrol-origin: margin;
  left: 10px;
  padding: 0 6px 0 6px;
  color: #1c2433;
  font-weight: 600;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit, QListWidget {
  border: 1px solid rgba(27, 39, 64, 0.14);
  border-radius: 10px;
  padding: 7px 10px;
  background: #ffffff;
}
QPushButton {
  border-radius: 18px;
  padding: 7px 14px;
  background: #2b7cff;
  color: white;
  font-weight: 600;
}
QPushButton:disabled { background: rgba(120, 140, 170, 0.5); }
"""

_DARK_QSS = """
QWidget {
  font-family: "Segoe UI Variable", "Segoe UI", "Inter", sans-serif;
  font-size: 13px;
  color: #e6e9f2;
}
QMainWindow { background: #1b1f2a; }
QGroupBox {
  background: #232a36;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  margin-top: 10px;
  padding: 12px;
}
QGroupBox::title {
  subcontrol-origin: margin;
  left: 10px;
  padding: 0 6px 0 6px;
  color: #e6e9f2;
  font-weight: 600;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit, QListWidget {
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 10px;
  padding: 7px 10px;
  background: #1f2430;
  color: #e6e9f2;
}
QPushButton {
  border-radius: 18px;
  padding: 7px 14px;
  background: #3f7bff;
  color: white;
  font-weight: 600;
}
QPushButton:disabled { background: rgba(120, 140, 170, 0.45); }
"""


class MiniOSHelperWindow(QtWidgets.QMainWindow):
    command_done = QtCore.Signal(object, object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini OS Helper")
        self.resize(1050, 760)

        self.settings = load_settings()
        self.auto_timer = QtCore.QTimer(self)
        self.auto_timer.timeout.connect(self._refresh_system_once)
        self.command_done.connect(self._on_command_done)

        self._build_ui()
        self._apply_settings()

    def _build_ui(self):
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)

        outer = QtWidgets.QVBoxLayout(root)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(10)

        self.title_label = QtWidgets.QLabel("Mini OS Helper")
        self.title_label.setStyleSheet("font-size: 26px; font-weight: 700;")
        self.subtitle_label = QtWidgets.QLabel("Quick tools, live metrics, and automation")
        outer.addWidget(self.title_label)
        outer.addWidget(self.subtitle_label)

        top_controls = QtWidgets.QHBoxLayout()
        outer.addLayout(top_controls)

        top_controls.addWidget(QtWidgets.QLabel("Theme"))
        self.theme_box = QtWidgets.QComboBox()
        self.theme_box.addItems(["light", "dark"])
        self.theme_box.currentIndexChanged.connect(self._on_theme_changed)
        top_controls.addWidget(self.theme_box)

        top_controls.addWidget(QtWidgets.QLabel("Auto Refresh"))
        self.auto_refresh_check = QtWidgets.QCheckBox()
        self.auto_refresh_check.stateChanged.connect(self._on_auto_refresh_changed)
        top_controls.addWidget(self.auto_refresh_check)

        top_controls.addWidget(QtWidgets.QLabel("Interval (ms)"))
        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setRange(100, 5000)
        self.interval_spin.setSingleStep(100)
        self.interval_spin.valueChanged.connect(self._on_interval_changed)
        top_controls.addWidget(self.interval_spin)

        self.refresh_btn = QtWidgets.QPushButton("Refresh Now")
        self.refresh_btn.clicked.connect(self._refresh_system_once)
        top_controls.addWidget(self.refresh_btn)
        top_controls.addStretch(1)

        self.tabs = QtWidgets.QTabWidget()
        outer.addWidget(self.tabs, 1)

        self._build_dashboard_tab()
        self._build_actions_tab()
        self._build_notes_tab()

        self.status_label = QtWidgets.QLabel("Ready")
        outer.addWidget(self.status_label)

    def _build_dashboard_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        box = QtWidgets.QGroupBox("System Snapshot")
        box_layout = QtWidgets.QVBoxLayout(box)
        self.system_text = QtWidgets.QTextEdit()
        self.system_text.setReadOnly(True)
        box_layout.addWidget(self.system_text)
        layout.addWidget(box)

        self.tabs.addTab(tab, "Dashboard")

    def _build_actions_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        fav_box = QtWidgets.QGroupBox("Favorite Paths")
        self.favorite_buttons_layout = QtWidgets.QVBoxLayout(fav_box)
        layout.addWidget(fav_box)

        web_box = QtWidgets.QGroupBox("Web Shortcuts")
        self.web_buttons_layout = QtWidgets.QVBoxLayout(web_box)
        layout.addWidget(web_box)

        cmd_box = QtWidgets.QGroupBox("Command Runner")
        cmd_layout = QtWidgets.QVBoxLayout(cmd_box)
        cmd_row = QtWidgets.QHBoxLayout()
        self.command_entry = QtWidgets.QLineEdit()
        self.command_entry.setPlaceholderText("Enter command")
        self.command_entry.returnPressed.connect(self._run_command)
        cmd_row.addWidget(self.command_entry, 1)
        run_btn = QtWidgets.QPushButton("Run")
        run_btn.clicked.connect(self._run_command)
        cmd_row.addWidget(run_btn)
        cmd_layout.addLayout(cmd_row)

        self.command_output = QtWidgets.QTextEdit()
        self.command_output.setReadOnly(True)
        cmd_layout.addWidget(self.command_output)
        layout.addWidget(cmd_box, 1)

        self.tabs.addTab(tab, "Quick Actions")

    def _build_notes_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        save_btn = QtWidgets.QPushButton("Save Notes")
        save_btn.clicked.connect(self._save_notes)
        layout.addWidget(save_btn)

        self.notes_text = QtWidgets.QTextEdit()
        layout.addWidget(self.notes_text, 1)

        self.tabs.addTab(tab, "Notes")

    def _apply_settings(self):
        theme = self.settings.get("theme", "light")
        self.theme_box.setCurrentIndex(0 if theme == "light" else 1)
        self._apply_theme(theme)

        self.auto_refresh_check.setChecked(bool(self.settings.get("auto_refresh", True)))
        self.interval_spin.setValue(int(self.settings.get("refresh_interval_ms", 1000)))
        self.notes_text.setPlainText(load_notes())

        self._populate_action_buttons()
        self._refresh_system_once()
        self._sync_auto_refresh()

    def _apply_theme(self, theme: str):
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        if theme == "dark":
            app.setStyle("Fusion")
            app.setStyleSheet(_DARK_QSS)
            self.title_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #e6e9f2;")
            self.subtitle_label.setStyleSheet("color: rgba(230,233,242,0.72);")
            self.status_label.setStyleSheet("color: rgba(230,233,242,0.68);")
        else:
            app.setStyle("Fusion")
            app.setStyleSheet(_LIGHT_QSS)
            self.title_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #1f2a44;")
            self.subtitle_label.setStyleSheet("color: rgba(30,40,60,0.72);")
            self.status_label.setStyleSheet("color: rgba(30,40,60,0.68);")

    def _populate_action_buttons(self):
        self._clear_layout(self.favorite_buttons_layout)
        self._clear_layout(self.web_buttons_layout)

        for name, path in self.settings.get("favorites", {}).items():
            btn = QtWidgets.QPushButton(f"{name}: {path}")
            btn.clicked.connect(lambda _=None, p=path: self._open_path(p))
            self.favorite_buttons_layout.addWidget(btn)
        self.favorite_buttons_layout.addStretch(1)

        for name, url in self.settings.get("web_shortcuts", {}).items():
            btn = QtWidgets.QPushButton(f"{name}: {url}")
            btn.clicked.connect(lambda _=None, u=url: self._open_web(u))
            self.web_buttons_layout.addWidget(btn)
        self.web_buttons_layout.addStretch(1)

    def _set_status(self, text: str):
        self.status_label.setText(text)

    def _refresh_system_once(self):
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
        self.system_text.setPlainText(text)
        self._set_status("System info updated")

    def _run_command(self):
        command = self.command_entry.text().strip()
        if not command:
            self._set_status("Enter a command first")
            return

        if os.name == "nt":
            try:
                run_command_in_terminal(command)
                self.command_output.append(f"$ {command}")
                self.command_output.append("(launched in dedicated cmd window)")
                self._set_status("Command opened in new cmd window")
            except ActionError as exc:
                self.command_output.append(f"$ {command}")
                self.command_output.append(str(exc))
                self._set_status(f"Command launch failed: {exc}")
            return

        self.command_output.append(f"$ {command}")
        self._set_status("Running command...")

        def task():
            try:
                code, output = run_command(command)
                self.command_done.emit(code, output or "(no output)")
            except ActionError as exc:
                self.command_done.emit(1, str(exc))

        threading.Thread(target=task, daemon=True).start()

    def _on_command_done(self, code: int, output: str):
        self.command_output.append(output)
        self._set_status(f"Command finished with exit code {code}")

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

    def _save_notes(self):
        save_notes(self.notes_text.toPlainText())
        self._set_status("Notes saved")

    def _on_theme_changed(self):
        theme = self.theme_box.currentText()
        self.settings["theme"] = theme
        save_settings(self.settings)
        self._apply_theme(theme)

    def _on_auto_refresh_changed(self):
        self.settings["auto_refresh"] = bool(self.auto_refresh_check.isChecked())
        save_settings(self.settings)
        self._sync_auto_refresh()

    def _on_interval_changed(self):
        self.settings["refresh_interval_ms"] = int(self.interval_spin.value())
        save_settings(self.settings)
        self._sync_auto_refresh()

    def _sync_auto_refresh(self):
        if self.auto_refresh_check.isChecked():
            self.auto_timer.start(int(self.interval_spin.value()))
            self._set_status("Auto refresh enabled")
        else:
            self.auto_timer.stop()
            self._set_status("Auto refresh disabled")

    @staticmethod
    def _clear_layout(layout: QtWidgets.QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


class MiniOSHelperQtApp:
    @staticmethod
    def run_app():
        app = QtWidgets.QApplication([])
        app.setStyle("Fusion")
        window = MiniOSHelperWindow()
        icon_path = os.path.join(os.path.dirname(__file__), "org.evans.MiniOSHelper.svg")
        if os.path.exists(icon_path):
            window.setWindowIcon(QtGui.QIcon(icon_path))
        window.show()
        app.exec()
