import tkinter as tk
from tkinter import messagebox, ttk

from quick_actions import ActionError, open_path, open_web, run_command
from settings import load_notes, load_settings, save_notes, save_settings
from system_info import get_system_snapshot

THEMES = {
    "dark": {
        "root": "#0f172a",
        "panel": "#111827",
        "card": "#0b1220",
        "line": "#1f2937",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "entry": "#020617",
        "entry_fg": "#dbeafe",
        "accent": "#2563eb",
        "accent_hover": "#3b82f6",
        "accent_press": "#1d4ed8",
        "accent_text": "#eff6ff",
        "select": "#2563eb",
    },
    "light": {
        "root": "#f1f5f9",
        "panel": "#ffffff",
        "card": "#f8fafc",
        "line": "#dbe3ee",
        "text": "#0f172a",
        "muted": "#475569",
        "entry": "#ffffff",
        "entry_fg": "#0f172a",
        "accent": "#2563eb",
        "accent_hover": "#3b82f6",
        "accent_press": "#1d4ed8",
        "accent_text": "#eff6ff",
        "select": "#93c5fd",
    },
}


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=110, height=34, radius=14):
        super().__init__(parent, width=width, height=height, bd=0, highlightthickness=0, relief="flat", cursor="hand2")
        self.command = command
        self.text = text
        self.width = width
        self.height = height
        self.radius = radius
        self.enabled = True
        self.pressed = False
        self.colors = {
            "bg": "#2563eb",
            "hover": "#3b82f6",
            "press": "#1d4ed8",
            "fg": "#eff6ff",
            "container": "#0f172a",
            "disabled": "#475569",
        }
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def configure_theme(self, palette, container_bg):
        self.colors.update(
            {
                "bg": palette["accent"],
                "hover": palette["accent_hover"],
                "press": palette["accent_press"],
                "fg": palette["accent_text"],
                "container": container_bg,
            }
        )
        self._draw()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self.config(cursor="hand2" if enabled else "arrow")
        self._draw()

    def _rounded(self, color):
        w, h, r = self.width, self.height, self.radius
        self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=90, fill=color, outline=color)
        self.create_arc(w - 2 * r, 0, w, 2 * r, start=0, extent=90, fill=color, outline=color)
        self.create_arc(0, h - 2 * r, 2 * r, h, start=180, extent=90, fill=color, outline=color)
        self.create_arc(w - 2 * r, h - 2 * r, w, h, start=270, extent=90, fill=color, outline=color)
        self.create_rectangle(r, 0, w - r, h, fill=color, outline=color)
        self.create_rectangle(0, r, w, h - r, fill=color, outline=color)

    def _draw(self):
        self.delete("all")
        self.configure(bg=self.colors["container"])
        if not self.enabled:
            color = self.colors["disabled"]
        elif self.pressed:
            color = self.colors["press"]
        else:
            color = self.colors["bg"]
        self._rounded(color)
        self.create_text(self.width // 2, self.height // 2, text=self.text, fill=self.colors["fg"], font=("Adwaita Sans", 10, "bold"))

    def _on_enter(self, _event):
        if self.enabled and not self.pressed:
            self.delete("all")
            self.configure(bg=self.colors["container"])
            self._rounded(self.colors["hover"])
            self.create_text(self.width // 2, self.height // 2, text=self.text, fill=self.colors["fg"], font=("Adwaita Sans", 10, "bold"))

    def _on_leave(self, _event):
        self.pressed = False
        self._draw()

    def _on_press(self, _event):
        if self.enabled:
            self.pressed = True
            self._draw()

    def _on_release(self, _event):
        if not self.enabled:
            return
        run = self.pressed
        self.pressed = False
        self._draw()
        if run:
            self.command()


class MiniOSHelperApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Mini OS Helper")
        self.root.geometry("1060x700")
        self.root.minsize(900, 600)

        self.settings = load_settings()
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "dark"))
        self.refresh_interval_var = tk.IntVar(value=self.settings.get("refresh_interval_ms", 1000))
        self.auto_refresh_var = tk.BooleanVar(value=self.settings.get("auto_refresh", True))

        self._auto_refresh_id = None
        self._interval_debounce_id = None

        self._build_ui()
        self.apply_theme(self.theme_var.get())
        self._refresh_system_once(set_status=False)
        if self.auto_refresh_var.get():
            self._schedule_auto_refresh()

    def _build_ui(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.header = tk.Frame(self.root, padx=14, pady=12)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(1, weight=1)

        self.title = tk.Label(self.header, text="Mini OS Helper", font=("Adwaita Sans", 22, "bold"))
        self.title.grid(row=0, column=0, sticky="w")
        self.subtitle = tk.Label(self.header, text="Quick tools, live metrics, and automation", font=("Adwaita Sans", 10))
        self.subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.theme_box = ttk.Combobox(
            self.header,
            textvariable=self.theme_var,
            values=("dark", "light"),
            state="readonly",
            width=10,
            style="App.TCombobox",
        )
        self.theme_box.grid(row=0, column=2, rowspan=2, sticky="e")
        self.theme_box.bind("<<ComboboxSelected>>", self._on_theme_change)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))

        self._build_dashboard_tab()
        self._build_actions_tab()
        self._build_notes_tab()

        self.status_var = tk.StringVar(value="Ready")
        self.status = tk.Label(self.root, textvariable=self.status_var, anchor="w", padx=14, pady=8, font=("Adwaita Sans", 10))
        self.status.grid(row=2, column=0, sticky="ew")

        self._build_context_menus()

    def _build_dashboard_tab(self):
        tab = tk.Frame(self.notebook)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        self.notebook.add(tab, text="Dashboard")

        controls = tk.Frame(tab, padx=12, pady=10)
        controls.grid(row=0, column=0, sticky="ew")

        self.refresh_btn = RoundedButton(controls, "Refresh Now", self.refresh_system, width=112)
        self.refresh_btn.pack(side="left")

        self.auto_check = ttk.Checkbutton(
            controls,
            text="Auto Refresh",
            variable=self.auto_refresh_var,
            command=self._on_auto_refresh_toggle,
            style="App.TCheckbutton",
        )
        self.auto_check.pack(side="left", padx=(12, 8))

        self.interval_label = tk.Label(controls, text="Interval (ms):", font=("Adwaita Sans", 10, "bold"))
        self.interval_label.pack(side="left", padx=(6, 6))

        self.interval_scale = ttk.Scale(
            controls,
            from_=100,
            to=2000,
            variable=self.refresh_interval_var,
            command=self._on_interval_slider,
            style="App.Horizontal.TScale",
            length=220,
        )
        self.interval_scale.pack(side="left", padx=(0, 8))

        self.interval_spin = ttk.Spinbox(
            controls,
            from_=100,
            to=2000,
            increment=50,
            textvariable=self.refresh_interval_var,
            width=7,
            command=self._on_interval_spin,
            style="App.TSpinbox",
        )
        self.interval_spin.pack(side="left")
        self.interval_spin.bind("<Return>", lambda _e: self._on_interval_spin())
        self.interval_spin.bind("<FocusOut>", lambda _e: self._on_interval_spin())

        self.system_text = tk.Text(tab, wrap="word", font=("Adwaita Mono", 11), state="disabled")
        self.system_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _build_actions_tab(self):
        tab = tk.Frame(self.notebook)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(3, weight=1)
        self.notebook.add(tab, text="Quick Actions")

        self.path_buttons_frame = tk.LabelFrame(tab, text="Folders", padx=10, pady=8)
        self.path_buttons_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        self.web_buttons_frame = tk.LabelFrame(tab, text="Web Shortcuts", padx=10, pady=8)
        self.web_buttons_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=6)

        run_frame = tk.LabelFrame(tab, text="Run Command", padx=10, pady=8)
        run_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        run_frame.columnconfigure(0, weight=1)

        self.cmd_var = tk.StringVar()
        self.cmd_entry = ttk.Entry(run_frame, textvariable=self.cmd_var, style="App.TEntry")
        self.cmd_entry.grid(row=0, column=0, sticky="ew")
        self.cmd_entry.bind("<Return>", lambda _e: self._run_command())
        self.cmd_entry.bind("<Button-3>", self._show_cmd_context)

        self.run_btn = RoundedButton(run_frame, "Run", self._run_command, width=78)
        self.run_btn.grid(row=0, column=1, padx=(6, 0))

        self.cmd_output = tk.Text(tab, wrap="word", font=("Adwaita Mono", 10), state="disabled")
        self.cmd_output.grid(row=3, column=0, sticky="nsew", padx=12, pady=(6, 12))
        self.cmd_output.bind("<Button-3>", self._show_output_context)

        self._populate_action_buttons()

    def _build_notes_tab(self):
        tab = tk.Frame(self.notebook)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        self.notebook.add(tab, text="Notes")

        self.notes_text = tk.Text(tab, wrap="word", font=("Adwaita Mono", 11))
        self.notes_text.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.notes_text.insert("1.0", load_notes())
        self.notes_text.bind("<Button-3>", self._show_notes_context)

        bottom = tk.Frame(tab, padx=12, pady=6)
        bottom.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.save_notes_btn = RoundedButton(bottom, "Save Notes", self._save_notes, width=110)
        self.save_notes_btn.pack(side="left")

    def _build_context_menus(self):
        self.notes_menu = tk.Menu(self.root, tearoff=False)
        self.notes_menu.add_command(label="Cut", command=lambda: self.notes_text.event_generate("<<Cut>>"))
        self.notes_menu.add_command(label="Copy", command=lambda: self.notes_text.event_generate("<<Copy>>"))
        self.notes_menu.add_command(label="Paste", command=lambda: self.notes_text.event_generate("<<Paste>>"))
        self.notes_menu.add_separator()
        self.notes_menu.add_command(label="Select All", command=lambda: self._select_all(self.notes_text))

        self.output_menu = tk.Menu(self.root, tearoff=False)
        self.output_menu.add_command(label="Copy", command=lambda: self.cmd_output.event_generate("<<Copy>>"))
        self.output_menu.add_command(label="Select All", command=lambda: self._select_all(self.cmd_output))
        self.output_menu.add_separator()
        self.output_menu.add_command(label="Clear", command=self._clear_output)

        self.cmd_menu = tk.Menu(self.root, tearoff=False)
        self.cmd_menu.add_command(label="Cut", command=lambda: self.cmd_entry.event_generate("<<Cut>>"))
        self.cmd_menu.add_command(label="Copy", command=lambda: self.cmd_entry.event_generate("<<Copy>>"))
        self.cmd_menu.add_command(label="Paste", command=lambda: self.cmd_entry.event_generate("<<Paste>>"))

    def _show_notes_context(self, event):
        self._show_menu(self.notes_menu, event)

    def _show_output_context(self, event):
        self._show_menu(self.output_menu, event)

    def _show_cmd_context(self, event):
        self._show_menu(self.cmd_menu, event)

    def _show_menu(self, menu: tk.Menu, event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _select_all(self, widget):
        widget.tag_add("sel", "1.0", "end")

    def _clear_output(self):
        self.cmd_output.configure(state="normal")
        self.cmd_output.delete("1.0", tk.END)
        self.cmd_output.configure(state="disabled")

    def _populate_action_buttons(self):
        for child in self.path_buttons_frame.winfo_children():
            child.destroy()
        for child in self.web_buttons_frame.winfo_children():
            child.destroy()

        p = THEMES.get(self.theme_var.get(), THEMES["dark"])

        col = 0
        for name, path in self.settings.get("favorites", {}).items():
            btn = RoundedButton(self.path_buttons_frame, name, lambda pth=path: self._open_path(pth), width=max(90, 10 * len(name)))
            btn.grid(row=0, column=col, padx=4, pady=2)
            btn.configure_theme(p, self.path_buttons_frame.cget("bg"))
            col += 1

        col = 0
        for name, url in self.settings.get("web_shortcuts", {}).items():
            btn = RoundedButton(self.web_buttons_frame, name, lambda u=url: self._open_web(u), width=max(90, 10 * len(name)))
            btn.grid(row=0, column=col, padx=4, pady=2)
            btn.configure_theme(p, self.web_buttons_frame.cget("bg"))
            col += 1

    def _refresh_system_once(self, set_status: bool = True):
        data = get_system_snapshot(cpu_interval=0.0)
        lines = [
            f"OS: {data['os']}",
            f"Python: {data['python']}",
            f"Uptime: {data['uptime']}",
            f"CPU: {data['cpu']}",
            f"RAM: {data['ram']}",
            f"Disk: {data['disk']}",
            f"Battery: {data['battery']}",
            f"Processes: {data['processes']}",
        ]

        self.system_text.configure(state="normal")
        self.system_text.delete("1.0", tk.END)
        self.system_text.insert("1.0", "\n".join(lines))
        self.system_text.configure(state="disabled")
        if set_status:
            self.status_var.set(f"System info refreshed ({self.refresh_interval_var.get()} ms)")

    def refresh_system(self):
        self._refresh_system_once(set_status=True)

    def _schedule_auto_refresh(self):
        if self._auto_refresh_id is not None:
            self.root.after_cancel(self._auto_refresh_id)
            self._auto_refresh_id = None
        if not self.auto_refresh_var.get():
            return
        interval = max(100, min(2000, int(self.refresh_interval_var.get())))
        self._auto_refresh_id = self.root.after(interval, self._tick_auto_refresh)

    def _tick_auto_refresh(self):
        self._auto_refresh_id = None
        if not self.auto_refresh_var.get():
            return
        self._refresh_system_once(set_status=False)
        self._schedule_auto_refresh()

    def _persist_refresh_settings(self):
        interval = max(100, min(2000, int(self.refresh_interval_var.get())))
        self.refresh_interval_var.set(interval)
        self.settings["refresh_interval_ms"] = interval
        self.settings["auto_refresh"] = bool(self.auto_refresh_var.get())
        save_settings(self.settings)

    def _on_interval_slider(self, _value=None):
        if self._interval_debounce_id is not None:
            self.root.after_cancel(self._interval_debounce_id)
        self._interval_debounce_id = self.root.after(180, self._on_interval_spin)

    def _on_interval_spin(self):
        self._persist_refresh_settings()
        self._schedule_auto_refresh()

    def _on_auto_refresh_toggle(self):
        self._persist_refresh_settings()
        if self.auto_refresh_var.get():
            self.status_var.set("Auto refresh enabled")
            self._schedule_auto_refresh()
        else:
            if self._auto_refresh_id is not None:
                self.root.after_cancel(self._auto_refresh_id)
                self._auto_refresh_id = None
            self.status_var.set("Auto refresh disabled")

    def _open_path(self, path: str):
        try:
            open_path(path)
            self.status_var.set(f"Opened {path}")
        except ActionError as exc:
            messagebox.showerror("Open Path Failed", str(exc))

    def _open_web(self, url: str):
        try:
            open_web(url)
            self.status_var.set(f"Opened {url}")
        except ActionError as exc:
            messagebox.showerror("Open Web Failed", str(exc))

    def _run_command(self):
        cmd = self.cmd_var.get().strip()
        if not cmd:
            return
        try:
            code, output = run_command(cmd)
        except ActionError as exc:
            messagebox.showerror("Command Failed", str(exc))
            return

        self.cmd_output.configure(state="normal")
        self.cmd_output.delete("1.0", tk.END)
        self.cmd_output.insert("1.0", f"Exit code: {code}\n\n{output or '(no output)'}")
        self.cmd_output.configure(state="disabled")
        self.status_var.set(f"Command finished with code {code}")

    def _save_notes(self):
        content = self.notes_text.get("1.0", tk.END)
        save_notes(content)
        self.status_var.set("Notes saved")

    def _on_theme_change(self, _event=None):
        self.apply_theme(self.theme_var.get())

    def apply_theme(self, theme_name: str):
        if theme_name not in THEMES:
            theme_name = "dark"
        self.theme_var.set(theme_name)
        self.settings["theme"] = theme_name
        save_settings(self.settings)

        p = THEMES[theme_name]

        self.style.configure("TFrame", background=p["root"])
        self.style.configure("TNotebook", background=p["root"], borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=[10, 6], font=("Adwaita Sans", 10, "bold"))
        self.style.configure(
            "App.TCombobox",
            fieldbackground=p["entry"],
            foreground=p["entry_fg"],
            bordercolor=p["line"],
            arrowsize=14,
            padding=4,
            font=("Adwaita Sans", 10),
        )
        self.style.map("App.TCombobox", fieldbackground=[("readonly", p["entry"])], foreground=[("readonly", p["entry_fg"])])
        self.style.configure(
            "App.TEntry",
            fieldbackground=p["entry"],
            foreground=p["entry_fg"],
            bordercolor=p["line"],
            insertcolor=p["entry_fg"],
            padding=6,
            font=("Adwaita Sans", 10),
        )
        self.style.configure(
            "App.TSpinbox",
            fieldbackground=p["entry"],
            foreground=p["entry_fg"],
            bordercolor=p["line"],
            insertcolor=p["entry_fg"],
            padding=4,
            font=("Adwaita Sans", 10),
        )
        self.style.configure(
            "App.TCheckbutton",
            background=p["panel"],
            foreground=p["text"],
            font=("Adwaita Sans", 10, "bold"),
            indicatorcolor=p["entry"],
        )
        self.style.map("App.TCheckbutton", background=[("active", p["panel"])])
        self.style.configure("App.Horizontal.TScale", background=p["panel"], troughcolor=p["card"])

        self.root.configure(bg=p["root"])
        self.header.configure(bg=p["root"])
        self.title.configure(bg=p["root"], fg=p["text"])
        self.subtitle.configure(bg=p["root"], fg=p["muted"])
        self.status.configure(bg=p["root"], fg=p["muted"])

        for frame in (self.path_buttons_frame, self.web_buttons_frame):
            frame.configure(bg=p["panel"], fg=p["text"], highlightbackground=p["line"], highlightthickness=1)

        self.interval_label.configure(bg=p["panel"], fg=p["text"])

        for text_widget in (self.system_text, self.cmd_output, self.notes_text):
            text_widget.configure(
                bg=p["card"],
                fg=p["text"],
                insertbackground=p["text"],
                selectbackground=p["select"],
                selectforeground=p["text"],
            )

        for btn in (self.refresh_btn, self.run_btn, self.save_notes_btn):
            btn.configure_theme(p, btn.master.cget("bg"))

        self.theme_box.configure(style="App.TCombobox")
        self.interval_spin.configure(style="App.TSpinbox")

        for menu in (self.notes_menu, self.output_menu, self.cmd_menu):
            menu.configure(
                bg=p["panel"],
                fg=p["text"],
                activebackground=p["select"],
                activeforeground=p["text"],
                relief="flat",
                borderwidth=1,
            )

        self._populate_action_buttons()
        self._persist_refresh_settings()
