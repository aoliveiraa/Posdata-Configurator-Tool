import io
import os
import re
import threading
import tkinter as tk
from contextlib import redirect_stderr, redirect_stdout
from tkinter import filedialog, messagebox, scrolledtext

from app import main


class PosDataConfiguratorUI:
    BG = "#15171c"
    PANEL = "#1f2229"
    PANEL_LIGHT = "#272b33"
    ENTRY = "#111318"
    BORDER = "#343a46"
    PRIMARY = "#2563eb"
    PRIMARY_HOVER = "#1d4ed8"
    TEXT = "#f8fafc"
    MUTED = "#aeb6c2"
    SUCCESS = "#4ade80"
    WARNING = "#facc15"
    ERROR = "#f87171"
    RUNNING = "#60a5fa"
    LOG_BG = "#0d1117"

    LABS = {
        "RIO": "10.118.57",
        "RENEIGH": "10.118.51",
        "BR": "10.0.12",
    }

    SUMMARY_KEYS = (
        "POS",
        "WAY",
        "FOE",
        "COD",
        "STORE COD",
        "ITONAS",
        "OVERALL",
    )

    def __init__(self, root):
        self.root = root
        self.running = False
        self.lab_cards = {}
        self.summary_cards = {}
        self.browse_buttons = []
        self.execution_options = {}
        self.preflight_labels = {}
        self.log_visible = True

        self.project_folder = os.path.dirname(os.path.abspath(__file__))
        self.output_folder = os.path.join(self.project_folder, "output")

        self.current_folder = tk.StringVar(
            value=os.path.join(self.project_folder, "samples", "current_posdata")
        )
        self.new_folder = tk.StringVar(
            value=os.path.join(self.project_folder, "samples", "new_posdata")
        )
        self.selected_lab = tk.StringVar(value="RENEIGH")
        self.status_var = tk.StringVar(value="Ready to configure")
        self.current_folder.trace_add("write", lambda *_: self.defer_preflight_update())
        self.new_folder.trace_add("write", lambda *_: self.defer_preflight_update())

        self.configure_window()
        self.build_interface()
        self.select_lab("RENEIGH")
        self.reset_summary()
        self.update_preflight_validation()

    def configure_window(self):
        self.root.title("PosData Configurator")
        self.root.geometry("1450x920")
        self.root.minsize(1100, 760)
        self.root.configure(bg=self.BG)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(4, weight=1)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass

    def build_interface(self):
        self.build_header()
        self.build_configuration_panel()
        self.build_hero_status_card()
        self.build_summary_panel()
        self.build_log_panel()
        self.build_status_bar()

    def build_header(self):
        header = tk.Frame(self.root, bg=self.BG)
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)

        title_box = tk.Frame(header, bg=self.BG)
        title_box.grid(row=0, column=0, sticky="w")

        tk.Label(
            title_box,
            text="PosData Configurator",
            bg=self.BG,
            fg=self.TEXT,
            font=("Segoe UI", 27, "bold"),
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Multi-Lab Configuration Automation  |  Simplify  |  Validate  |  Generate",
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(3, 0))

        self.header_status_label = tk.Label(
            header,
            text="READY",
            bg=self.PANEL_LIGHT,
            fg=self.SUCCESS,
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=9,
        )
        self.header_status_label.grid(row=0, column=1, sticky="e")

    def build_configuration_panel(self):
        panel = tk.Frame(
            self.root,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        panel.grid(row=1, column=0, sticky="ew", padx=28, pady=10)
        panel.grid_columnconfigure(1, weight=1)

        tk.Label(
            panel,
            text="CONFIGURATION",
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(15, 10))

        self.current_entry = self.build_folder_row(
            panel, 1, "Current PosData Folder", self.current_folder, self.browse_current
        )
        self.new_entry = self.build_folder_row(
            panel, 2, "New PosData Folder", self.new_folder, self.browse_new
        )

        tk.Frame(panel, height=1, bg=self.BORDER).grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=20, pady=(12, 10)
        )

        tk.Label(
            panel,
            text="Target Laboratory",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=4, column=0, sticky="nw", padx=(20, 15), pady=6)

        labs = tk.Frame(panel, bg=self.PANEL)
        labs.grid(row=4, column=1, columnspan=2, sticky="w", padx=(10, 20), pady=2)

        for index, (lab, prefix) in enumerate(self.LABS.items()):
            card = tk.Button(
                labs,
                text=f"{lab}\n{prefix}",
                command=lambda name=lab: self.select_lab(name),
                width=19,
                height=3,
                bg=self.PANEL_LIGHT,
                fg=self.MUTED,
                activebackground=self.PRIMARY_HOVER,
                activeforeground=self.TEXT,
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=self.BORDER,
                cursor="hand2",
                font=("Segoe UI", 10, "bold"),
            )
            card.grid(row=0, column=index, padx=(0, 12))
            self.lab_cards[lab] = card

        actions = tk.Frame(panel, bg=self.PANEL)
        actions.grid(row=5, column=0, columnspan=3, sticky="ew", padx=20, pady=(17, 17))
        actions.grid_columnconfigure(0, weight=3)
        actions.grid_columnconfigure(1, weight=1)

        self.run_button = tk.Button(
            actions,
            text="RUN CONFIGURATION",
            command=self.run_configuration,
            bg=self.PRIMARY,
            fg=self.TEXT,
            activebackground=self.PRIMARY_HOVER,
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2,
            font=("Segoe UI", 12, "bold"),
        )
        self.run_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.output_button = tk.Button(
            actions,
            text="OPEN OUTPUT",
            command=self.open_output,
            bg=self.PANEL_LIGHT,
            fg=self.TEXT,
            activebackground=self.BORDER,
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2,
            font=("Segoe UI", 10, "bold"),
        )
        self.output_button.grid(row=0, column=1, sticky="ew")

    def build_folder_row(self, parent, row, label, variable, command):
        tk.Label(
            parent,
            text=label,
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=row, column=0, sticky="w", padx=(20, 15), pady=7)

        entry = tk.Entry(
            parent,
            textvariable=variable,
            bg=self.ENTRY,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            selectbackground=self.PRIMARY,
            selectforeground=self.TEXT,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
        )
        entry.grid(row=row, column=1, sticky="ew", padx=10, pady=7, ipady=9)

        button = tk.Button(
            parent,
            text="Browse",
            command=command,
            bg=self.PANEL_LIGHT,
            fg=self.TEXT,
            activebackground=self.BORDER,
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            cursor="hand2",
            width=13,
            font=("Segoe UI", 9, "bold"),
        )
        button.grid(row=row, column=2, padx=(0, 20), pady=7, ipady=7)
        self.browse_buttons.append(button)
        return entry

    def select_lab(self, lab_name):
        if self.running:
            return
        self.selected_lab.set(lab_name)
        for name, card in self.lab_cards.items():
            selected = name == lab_name
            card.configure(
                bg=self.PRIMARY if selected else self.PANEL_LIGHT,
                fg=self.TEXT if selected else self.MUTED,
                highlightbackground=self.RUNNING if selected else self.BORDER,
                highlightthickness=2 if selected else 1,
            )
        if hasattr(self, "lab_status_label"):
            self.lab_status_label.configure(text=f"Selected Lab: {lab_name}")
        if hasattr(self, "hero_frame") and not self.running:
            self.set_hero_status(
                "READY TO CONFIGURE",
                f"Target laboratory: {lab_name} | Network prefix: {self.LABS[lab_name]}",
                "ready",
            )
        if hasattr(self, "preflight_overall_label"):
            self.update_preflight_validation()

    def build_hero_status_card(self):
        self.hero_frame = tk.Frame(
            self.root,
            bg="#20283a",
            highlightbackground=self.PRIMARY,
            highlightthickness=2,
        )
        self.hero_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=28,
            pady=(2, 8),
        )
        self.hero_frame.grid_columnconfigure(0, weight=1)
        self.hero_frame.grid_columnconfigure(1, weight=2)

        status_box = tk.Frame(self.hero_frame, bg="#20283a")
        status_box.grid(row=0, column=0, sticky="nsew", padx=(20, 16), pady=12)

        self.hero_title_label = tk.Label(
            status_box,
            text="READY TO CONFIGURE",
            bg="#20283a",
            fg=self.SUCCESS,
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        )
        self.hero_title_label.pack(anchor="w")

        self.hero_detail_label = tk.Label(
            status_box,
            text="Select the folders and target laboratory.",
            bg="#20283a",
            fg=self.MUTED,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        self.hero_detail_label.pack(anchor="w", pady=(3, 9))

        self.preflight_overall_label = tk.Label(
            status_box,
            text="CHECKING INPUTS",
            bg="#20283a",
            fg=self.WARNING,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self.preflight_overall_label.pack(anchor="w")

        checks_box = tk.Frame(self.hero_frame, bg="#20283a")
        checks_box.grid(row=0, column=1, sticky="nsew", padx=(16, 20), pady=12)

        tk.Label(
            checks_box,
            text="PRE-FLIGHT VALIDATION",
            bg="#20283a",
            fg=self.TEXT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 7))

        checks = (
            ("current", "Current PosData"),
            ("new", "New PosData"),
            ("lab", "Laboratory"),
            ("storedb", "store-db.xml"),
            ("screen", "screen.xml"),
        )

        for index, (key, label_text) in enumerate(checks):
            row = 1 + index // 3
            column = index % 3
            label = tk.Label(
                checks_box,
                text=f"[ ] {label_text}",
                bg="#20283a",
                fg=self.MUTED,
                font=("Segoe UI", 9),
                anchor="w",
                padx=0,
            )
            label.grid(row=row, column=column, sticky="w", padx=(0, 22), pady=3)
            self.preflight_labels[key] = label

    def set_hero_status(self, title, detail, state):
        colors = {
            "ready": self.SUCCESS,
            "running": self.RUNNING,
            "success": self.SUCCESS,
            "warning": self.WARNING,
            "error": self.ERROR,
        }
        backgrounds = {
            "ready": "#20283a",
            "running": "#1e2b42",
            "success": "#183327",
            "warning": "#3a321a",
            "error": "#3b2023",
        }
        borders = {
            "ready": self.PRIMARY,
            "running": self.RUNNING,
            "success": self.SUCCESS,
            "warning": self.WARNING,
            "error": self.ERROR,
        }

        background = backgrounds[state]
        self.hero_frame.configure(
            bg=background,
            highlightbackground=borders[state],
        )
        self.hero_title_label.configure(
            text=title,
            bg=background,
            fg=colors[state],
        )
        self.hero_detail_label.configure(
            text=detail,
            bg=background,
            fg=self.TEXT if state != "ready" else self.MUTED,
        )
        for child in self.hero_frame.winfo_children():
            child.configure(bg=background)
            for nested in child.winfo_children():
                nested.configure(bg=background)

    def update_preflight_validation(self):
        current_path = self.current_folder.get().strip()
        new_path = self.new_folder.get().strip()

        checks = {
            "current": os.path.isdir(current_path),
            "new": os.path.isdir(new_path),
            "lab": self.selected_lab.get() in self.LABS,
            "storedb": os.path.isfile(os.path.join(new_path, "store-db.xml")),
            "screen": os.path.isfile(os.path.join(new_path, "screen.xml")),
        }

        labels = {
            "current": "Current PosData",
            "new": "New PosData",
            "lab": "Laboratory",
            "storedb": "store-db.xml",
            "screen": "screen.xml",
        }

        for key, valid in checks.items():
            label = self.preflight_labels.get(key)
            if label is not None:
                label.configure(
                    text=f"{'OK' if valid else 'X'}  {labels[key]}",
                    fg=self.SUCCESS if valid else self.ERROR,
                )

        ready = all(checks.values())
        if ready:
            self.preflight_overall_label.configure(
                text="READY TO RUN",
                fg=self.SUCCESS,
            )
        else:
            missing_count = sum(not value for value in checks.values())
            self.preflight_overall_label.configure(
                text=f"{missing_count} CHECK(S) REQUIRED",
                fg=self.ERROR,
            )

        if not self.running:
            self.run_button.configure(state=tk.NORMAL if ready else tk.DISABLED)

        return ready

    def refresh_preflight_from_entry(self, _event=None):
        self.update_preflight_validation()

    def build_summary_panel(self):
        panel = tk.Frame(self.root, bg=self.BG)
        panel.grid(row=3, column=0, sticky="ew", padx=28, pady=(2, 7))

        tk.Label(
            panel,
            text="LAST EXECUTION SUMMARY",
            bg=self.BG,
            fg=self.TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        cards = tk.Frame(panel, bg=self.BG)
        cards.pack(fill="x")

        icons = {
            "POS": "POS",
            "WAY": "WAY",
            "FOE": "FOE",
            "COD": "COD",
            "STORE COD": "STORE COD",
            "ITONAS": "ITONAS",
            "OVERALL": "OVERALL STATUS",
        }

        for column in range(8):
            cards.grid_columnconfigure(column, weight=1, uniform="summary")

        positions = {
            "POS": (0, 1),
            "WAY": (1, 1),
            "FOE": (2, 1),
            "COD": (3, 1),
            "STORE COD": (4, 1),
            "ITONAS": (5, 1),
            "OVERALL": (6, 2),
        }

        for key in self.SUMMARY_KEYS:
            column, span = positions[key]
            accent = key == "OVERALL"
            base_bg = "#20283a" if accent else self.PANEL
            frame = tk.Frame(
                cards,
                bg=base_bg,
                highlightbackground=self.PRIMARY if accent else self.BORDER,
                highlightthickness=2 if accent else 1,
            )
            frame.grid(
                row=0,
                column=column,
                columnspan=span,
                sticky="nsew",
                padx=(0, 8),
                ipady=4,
            )
            title = tk.Label(
                frame,
                text=icons[key],
                bg=base_bg,
                fg=self.MUTED,
                font=("Segoe UI", 9 if not accent else 10, "bold"),
            )
            title.pack(pady=(9, 2))
            value = tk.Label(
                frame,
                text="NOT RUN",
                bg=base_bg,
                fg=self.MUTED,
                font=("Segoe UI", 11 if not accent else 14, "bold"),
            )
            value.pack(pady=(0, 9))
            self.summary_cards[key] = {
                "frame": frame,
                "title": title,
                "value": value,
                "base_bg": base_bg,
            }

    def update_summary_card(self, key, value, state):
        card = self.summary_cards[key]
        colors = {
            "idle": self.MUTED,
            "running": self.RUNNING,
            "success": self.SUCCESS,
            "warning": self.WARNING,
            "error": self.ERROR,
        }
        backgrounds = {
            "idle": card["base_bg"],
            "running": "#1e2b42",
            "success": "#183327",
            "warning": "#3a321a",
            "error": "#3b2023",
        }
        bg = backgrounds[state]
        card["frame"].configure(bg=bg)
        card["title"].configure(bg=bg)
        card["value"].configure(text=value, fg=colors[state], bg=bg)

    def reset_summary(self):
        for key in self.SUMMARY_KEYS:
            self.update_summary_card(key, "NOT RUN", "idle")

    def set_summary_running(self):
        for key in self.SUMMARY_KEYS:
            self.update_summary_card(key, "RUNNING", "running")

    def parse_execution_summary(self, output_text):
        summary = {}
        block_match = re.search(
            r"EXECUTION SUMMARY(?P<body>.*?)(?:OVERALL STATUS)(?P<overall>.*?)(?:={10,}|\Z)",
            output_text,
            re.IGNORECASE | re.DOTALL,
        )
        body = block_match.group("body") if block_match else output_text
        overall = block_match.group("overall") if block_match else output_text

        patterns = {
            "POS": r"^\s*POS\s*:\s*(.+?)\s*$",
            "WAY": r"^\s*WAY\s*:\s*(.+?)\s*$",
            "FOE": r"^\s*FOE\s*:\s*(.+?)\s*$",
            "COD": r"^\s*COD\s*:\s*(.+?)\s*$",
            "STORE COD": r"^\s*STORE\s+COD\s*:\s*(.+?)\s*$",
            "ITONAS": r"^\s*ITONAS\s*:\s*(.+?)\s*$",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
            if match:
                summary[key] = match.group(1).strip()

        upper = overall.upper()
        if "SUCCESS WITH WARNINGS" in upper:
            summary["OVERALL"] = "SUCCESS WITH WARNINGS"
        elif "FAILED" in upper:
            summary["OVERALL"] = "FAILED"
        elif "SUCCESS" in upper:
            summary["OVERALL"] = "SUCCESS"
        elif "REVIEW REQUIRED" in upper:
            summary["OVERALL"] = "REVIEW REQUIRED"
        return summary

    def classify_result(self, value):
        upper = value.upper()
        if "FAILED" in upper or "NOT GENERATED" in upper or "ERROR" in upper:
            return "error"
        if "WARNING" in upper or "REVIEW" in upper or "⚠" in value:
            return "warning"
        fraction = re.search(r"(\d+)\s*/\s*(\d+)", value)
        if fraction:
            return "success" if fraction.group(1) == fraction.group(2) else "warning"
        if "SUCCESS" in upper or "GENERATED" in upper or "READY" in upper or "✅" in value:
            return "success"
        return "warning"

    def clean_summary_value(self, key, value):
        clean = value.replace("✅", "").replace("⚠", "").replace("❌", "").strip()
        fraction = re.search(r"(\d+)\s*/\s*(\d+)", clean)
        if key in ("POS", "ITONAS") and fraction:
            return f"{fraction.group(1)}/{fraction.group(2)}"
        if "NOT GENERATED" in clean.upper():
            return "FAILED"
        if "GENERATED" in clean.upper():
            return "GENERATED"
        return clean

    def update_summary_from_output(self, output_text):
        summary = self.parse_execution_summary(output_text)
        for key in self.SUMMARY_KEYS:
            value = summary.get(key)
            if value is None:
                self.update_summary_card(key, "NO RESULT", "warning")
            else:
                self.update_summary_card(
                    key,
                    self.clean_summary_value(key, value),
                    self.classify_result(value),
                )
        return summary

    def build_log_panel(self):
        panel = tk.Frame(
            self.root,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )
        self.log_panel = panel
        panel.grid(row=4, column=0, sticky="nsew", padx=28, pady=(3, 10))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        header = tk.Frame(panel, bg=self.PANEL)
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 8))
        header.grid_columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="EXECUTION LOG",
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.clear_button = tk.Button(
            header,
            text="CLEAR LOG",
            command=self.clear_log,
            bg=self.PANEL_LIGHT,
            fg=self.MUTED,
            activebackground=self.BORDER,
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=5,
            font=("Segoe UI", 9, "bold"),
        )
        self.clear_button.grid(row=0, column=2, sticky="e", padx=(8, 0))

        self.toggle_log_button = tk.Button(
            header,
            text="HIDE LOG",
            command=self.toggle_log,
            bg=self.PANEL_LIGHT,
            fg=self.MUTED,
            activebackground=self.BORDER,
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=5,
            font=("Segoe UI", 9, "bold"),
        )
        self.toggle_log_button.grid(row=0, column=1, sticky="e")

        self.log = scrolledtext.ScrolledText(
            panel,
            bg=self.LOG_BG,
            fg="#d1fae5",
            insertbackground=self.TEXT,
            selectbackground=self.PRIMARY,
            selectforeground=self.TEXT,
            font=("Consolas", 10),
            relief="flat",
            bd=0,
            wrap=tk.WORD,
            padx=14,
            pady=14,
        )
        self.log.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log.tag_configure("header", foreground=self.RUNNING, font=("Consolas", 10, "bold"))
        self.log.tag_configure("success", foreground=self.SUCCESS)
        self.log.tag_configure("error", foreground=self.ERROR)
        self.append_log("PosData Configurator ready.\n", "success")

    def toggle_log(self):
        if self.log_visible:
            self.log_panel.grid_remove()
            self.toggle_log_button.configure(text="SHOW LOG")
            self.root.grid_rowconfigure(4, weight=0)
            self.log_visible = False
        else:
            self.log_panel.grid()
            self.toggle_log_button.configure(text="HIDE LOG")
            self.root.grid_rowconfigure(4, weight=1)
            self.log_visible = True

    def build_status_bar(self):
        bar = tk.Frame(self.root, bg=self.PANEL)
        bar.grid(row=5, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self.status_label = tk.Label(
            bar,
            textvariable=self.status_var,
            bg=self.PANEL,
            fg=self.SUCCESS,
            anchor="w",
            padx=16,
            pady=8,
            font=("Segoe UI", 9),
        )
        self.status_label.grid(row=0, column=0, sticky="ew")

        self.lab_status_label = tk.Label(
            bar,
            text=f"Selected Lab: {self.selected_lab.get()}",
            bg=self.PANEL,
            fg=self.MUTED,
            padx=16,
            pady=8,
            font=("Segoe UI", 9, "bold"),
        )
        self.lab_status_label.grid(row=0, column=1, sticky="e")

    def set_status(self, text, state):
        colors = {
            "ready": self.SUCCESS,
            "running": self.RUNNING,
            "warning": self.WARNING,
            "error": self.ERROR,
            "success": self.SUCCESS,
        }
        labels = {
            "ready": "READY",
            "running": "RUNNING",
            "warning": "REVIEW REQUIRED",
            "error": "FAILED",
            "success": "SUCCESS",
        }
        self.status_var.set(text)
        self.status_label.configure(fg=colors[state])
        self.header_status_label.configure(text=labels[state], fg=colors[state])

    def defer_preflight_update(self):
        if hasattr(self, "preflight_overall_label"):
            self.root.after_idle(self.update_preflight_validation)

    def browse_current(self):
        folder = filedialog.askdirectory(
            title="Select Current PosData Folder",
            initialdir=self.current_folder.get() or self.project_folder,
        )
        if folder:
            self.current_folder.set(folder)

    def browse_new(self):
        folder = filedialog.askdirectory(
            title="Select New PosData Folder",
            initialdir=self.new_folder.get() or self.project_folder,
        )
        if folder:
            self.new_folder.set(folder)

    def append_log(self, text, tag=None):
        def write():
            self.log.insert(tk.END, text, tag or ())
            self.log.see(tk.END)
        if threading.current_thread() is threading.main_thread():
            write()
        else:
            self.root.after(0, write)

    def clear_log(self):
        if self.running:
            return
        self.log.delete("1.0", tk.END)

    def open_output(self):
        if not os.path.isdir(self.output_folder):
            messagebox.showwarning("Output Folder", "The output folder was not found.")
            return
        os.startfile(self.output_folder)

    def validate_inputs(self):
        errors = []
        if not os.path.isdir(self.current_folder.get().strip()):
            errors.append("Current PosData folder does not exist.")
        if not os.path.isdir(self.new_folder.get().strip()):
            errors.append("New PosData folder does not exist.")
        if self.selected_lab.get() not in self.LABS:
            errors.append("Select a valid laboratory.")
        if errors:
            messagebox.showerror("Configuration Validation", "\n".join(errors))
            return False
        return True

    def run_configuration(self):
        if self.running:
            return
        if not self.update_preflight_validation():
            messagebox.showwarning(
                "Pre-Flight Validation",
                "Resolve all required checks before running the configuration.",
            )
            return

        self.execution_options = {
            "selected_lab": self.selected_lab.get(),
            "current_posdata_folder": self.current_folder.get().strip(),
            "new_posdata_folder": self.new_folder.get().strip(),
        }
        self.running = True
        self.set_controls_enabled(False)
        self.set_summary_running()
        self.set_hero_status(
            "CONFIGURATION RUNNING",
            f"Processing PosData for {self.execution_options['selected_lab']}. Please wait...",
            "running",
        )
        self.set_status(
            f"Running configuration for {self.execution_options['selected_lab']}...",
            "running",
        )
        self.append_log("\n==================================================\n", "header")
        self.append_log("STARTING CONFIGURATION\n", "header")
        self.append_log("==================================================\n", "header")
        self.append_log(f"Current PosData: {self.execution_options['current_posdata_folder']}\n")
        self.append_log(f"New PosData: {self.execution_options['new_posdata_folder']}\n")
        self.append_log(f"Target Lab: {self.execution_options['selected_lab']}\n\n")

        threading.Thread(target=self.execute_backend, daemon=True).start()

    def execute_backend(self):
        buffer = io.StringIO()
        execution_error = None
        try:
            with redirect_stdout(buffer), redirect_stderr(buffer):
                main(
                    selected_lab=self.execution_options["selected_lab"],
                    current_posdata_folder=self.execution_options["current_posdata_folder"],
                    new_posdata_folder=self.execution_options["new_posdata_folder"],
                )
        except Exception as error:
            execution_error = error
        output_text = buffer.getvalue()
        if output_text:
            self.append_log(output_text)
        self.root.after(0, self.finish_execution, execution_error, output_text)

    def finish_execution(self, execution_error, output_text):
        self.running = False
        self.set_controls_enabled(True)
        self.update_preflight_validation()

        if execution_error is not None:
            self.append_log("\nEXECUTION FAILED\n", "error")
            self.append_log(f"{execution_error}\n", "error")
            for key in self.SUMMARY_KEYS:
                self.update_summary_card(key, "FAILED" if key == "OVERALL" else "INTERRUPTED", "error")
            self.set_hero_status(
                "EXECUTION FAILED",
                str(execution_error),
                "error",
            )
            self.set_status("Configuration execution failed.", "error")
            return

        summary = self.update_summary_from_output(output_text)
        overall = summary.get("OVERALL", "UNKNOWN")
        if overall == "SUCCESS":
            self.set_hero_status(
                "CONFIGURATION COMPLETED SUCCESSFULLY",
                f"All generated components for {self.execution_options['selected_lab']} passed the final checks.",
                "success",
            )
            self.set_status("Configuration completed successfully.", "success")
            self.append_log("\nConfiguration completed successfully.\n", "success")
        elif overall == "FAILED":
            self.set_hero_status(
                "CONFIGURATION FAILED",
                "The process completed with errors. Review the summary and execution log.",
                "error",
            )
            self.set_status("Configuration completed with errors.", "error")
        else:
            self.set_hero_status(
                "REVIEW REQUIRED",
                "The process completed, but one or more components require attention.",
                "warning",
            )
            self.set_status("Configuration completed. Review is required.", "warning")

    def set_controls_enabled(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.current_entry.configure(state=state)
        self.new_entry.configure(state=state)
        self.output_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.toggle_log_button.configure(state=state)
        for button in self.browse_buttons:
            button.configure(state=state)
        for card in self.lab_cards.values():
            card.configure(state=state)
        self.run_button.configure(
            state=state,
            text="RUN CONFIGURATION" if enabled else "CONFIGURATION RUNNING...",
            bg=self.PRIMARY if enabled else "#374151",
        )


def main_ui():
    root = tk.Tk()
    PosDataConfiguratorUI(root)
    root.mainloop()


if __name__ == "__main__":
    main_ui()
