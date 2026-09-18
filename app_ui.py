import io
import os
import re
import threading
import tkinter as tk
from contextlib import redirect_stderr, redirect_stdout
from tkinter import filedialog, messagebox, scrolledtext

from app import main

from src.comparison.posdata_compare import (
    compare_and_generate_release_notes,
    release_notes_text,
)

class PosDataConfiguratorUI:
    BG = "#07111f"
    SIDEBAR = "#0a1727"
    PANEL = "#0d1b2c"
    PANEL_ALT = "#101f32"
    ENTRY = "#0a1625"
    BORDER = "#29405a"
    PRIMARY = "#1677ff"
    PRIMARY_DARK = "#105fc8"
    TEXT = "#f2f6fb"
    MUTED = "#9fb0c4"
    SUCCESS = "#52d273"
    WARNING = "#f5c451"
    ERROR = "#ff6b6b"
    INFO = "#58a6ff"

    LABS = {
        "RENEIGH": "10.118.51.0/24",
        "RIO": "10.118.57.0/24",
        "BR": "10.0.12.0/24",
    }
    NAV_ITEMS = (
        "Dashboard",
        "Compare",
        "Discovery",
        "Resolutions",
        "Readiness",
        "Generation",
        "Output",
        "Settings",
    )

    STEPS = ("Discovery", "Resolutions", "Readiness", "Generation", "Output")

    def __init__(self, root):
        self.root = root
        self.running = False
        self.execution_id = 0
        self.views = {}
        self.nav_buttons = {}
        self.lab_buttons = {}
        self.progress_steps = {}
        self.progress_connectors = []
        self.readiness_rows = {}
        self.readiness_page_rows = {}
        self.execution_options = {}
        self.compare_running = False
        self.last_comparison = None
        self.last_comparison_outputs = {}
        

        self.project_folder = os.path.dirname(os.path.abspath(__file__))
        self.output_folder = os.path.join(self.project_folder, "output")
        self.current_folder = tk.StringVar(
            value=os.path.join(self.project_folder, "samples", "current_posdata")
        )
        self.new_folder = tk.StringVar(
            value=os.path.join(self.project_folder, "samples", "new_posdata")
        )
        self.selected_lab = tk.StringVar(value="RENEIGH")
        self.status_var = tk.StringVar(value="Ready")

        self.configure_window()
        self.build_shell()
        self.select_lab("RENEIGH")
        self.reset_progress()

    def configure_window(self):
        self.root.title("PosData Configurator Tool")
        self.root.geometry("1536x1024")
        self.root.minsize(1180, 760)
        self.root.configure(bg=self.BG)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass

    def build_shell(self):
        self.build_title_bar()
        self.build_sidebar()
        self.main_frame = tk.Frame(self.root, bg=self.BG)
        self.main_frame.grid(row=1, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.build_header()
        self.build_progress()
        self.build_content()
        self.build_footer()

    def build_title_bar(self):
        bar = tk.Frame(self.root, bg="#081422", height=42)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        tk.Label(bar, text="  PosData Configurator Tool", bg="#081422", fg=self.TEXT,
                 font=("Segoe UI", 10)).pack(side="left", pady=11)

    def build_sidebar(self):
        sidebar = tk.Frame(self.root, bg=self.SIDEBAR, width=230,
                           highlightbackground=self.BORDER, highlightthickness=1)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(
            len(self.NAV_ITEMS),
            weight=1,
        )
        for row, item in enumerate(self.NAV_ITEMS):
            button = tk.Button(
                sidebar, text=f"  {item}", anchor="w",
                command=lambda name=item: self.show_view(name),
                bg=self.SIDEBAR, fg=self.TEXT,
                activebackground="#123765", activeforeground="#75b7ff",
                relief="flat", bd=0, cursor="hand2", padx=20, pady=13,
                font=("Segoe UI", 11),
            )
            button.grid(row=row, column=0, sticky="ew", padx=10,
                        pady=(12 if row == 0 else 1, 0))
            self.nav_buttons[item] = button

        lab_card = self.card(sidebar)
        lab_card.grid(
            row=len(self.NAV_ITEMS) + 1,
            column=0,
            sticky="ew",
            padx=14,
            pady=(10, 12),
        )        
        tk.Label(lab_card, text="CURRENT LAB", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(14, 5))
        self.sidebar_lab = tk.Label(lab_card, text="RENEIGH", bg=self.PANEL,
                                    fg=self.SUCCESS, font=("Segoe UI", 11, "bold"))
        self.sidebar_lab.pack(anchor="w", padx=16)
        tk.Label(lab_card, text="Network Prefix", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(14, 2))
        self.sidebar_network = tk.Label(lab_card, text=self.LABS["RENEIGH"],
                                        bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 10))
        self.sidebar_network.pack(anchor="w", padx=16, pady=(0, 14))

    def build_header(self):
        header = tk.Frame(self.main_frame, bg=self.BG)
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 8))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="PosData Configurator", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 24, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(header, text="Automated configuration and generation for PosData environments",
                 bg=self.BG, fg=self.MUTED, font=("Segoe UI", 10)).grid(
                     row=1, column=0, sticky="w", pady=(2, 0))
        tk.Label(header, text="v2.1.0", bg="#0c2c50", fg="#72b8ff",
                 padx=10, pady=4, font=("Segoe UI", 9)).grid(
                     row=0, column=1, rowspan=2, sticky="e")

    def build_progress(self):
        frame = tk.Frame(self.main_frame, bg=self.BG)
        frame.grid(row=1, column=0, sticky="ew", padx=35, pady=(5, 14))
        for index, name in enumerate(self.STEPS):
            circle = tk.Label(frame, text=str(index + 1), bg=self.BORDER, fg=self.TEXT,
                              width=2, pady=5, font=("Segoe UI", 10, "bold"))
            circle.grid(row=0, column=index * 2)
            title = tk.Label(frame, text=name, bg=self.BG, fg=self.TEXT,
                             font=("Segoe UI", 9))
            title.grid(row=1, column=index * 2, pady=(4, 0))
            status = tk.Label(frame, text="PENDING", bg=self.BG, fg=self.MUTED,
                              font=("Segoe UI", 7))
            status.grid(row=2, column=index * 2)
            self.progress_steps[name] = {"circle": circle, "title": title, "status": status}
            if index < len(self.STEPS) - 1:
                frame.grid_columnconfigure(index * 2 + 1, weight=1)
                connector = tk.Frame(frame, bg=self.BORDER, height=2)
                connector.grid(row=0, column=index * 2 + 1, sticky="ew")
                self.progress_connectors.append(connector)

    def reset_progress(self):
        self.set_progress(active_step=None, completed_steps=[])

    def set_progress(self, active_step=None, completed_steps=None, failed_step=None):
        completed = set(completed_steps or [])
        for name, widgets in self.progress_steps.items():
            if name == failed_step:
                bg, text, fg = self.ERROR, "FAILED", self.ERROR
            elif name in completed:
                bg, text, fg = self.PRIMARY, "COMPLETE", self.SUCCESS
            elif name == active_step:
                bg, text, fg = self.WARNING, "RUNNING", self.WARNING
            else:
                bg, text, fg = self.BORDER, "PENDING", self.MUTED
            widgets["circle"].configure(bg=bg)
            widgets["status"].configure(text=text, fg=fg)

        for index, connector in enumerate(self.progress_connectors):
            previous_step = self.STEPS[index]
            connector.configure(bg=self.PRIMARY if previous_step in completed else self.BORDER)
        self.root.update_idletasks()

    def start_progress_sequence(self):
        self.execution_id += 1
        token = self.execution_id
        self.set_progress(active_step="Discovery")
        schedule = (
            (900, "Resolutions", ["Discovery"]),
            (1800, "Readiness", ["Discovery", "Resolutions"]),
            (2800, "Generation", ["Discovery", "Resolutions", "Readiness"]),
            (4200, "Output", ["Discovery", "Resolutions", "Readiness", "Generation"]),
        )
        for delay, active, complete in schedule:
            self.root.after(delay, self.advance_progress_if_running, token, active, complete)

    def advance_progress_if_running(self, token, active, completed):
        if self.running and token == self.execution_id:
            self.set_progress(active_step=active, completed_steps=completed)
            self.status_var.set(f"{active} running...")

    def build_content(self):
        self.content_area = tk.Frame(self.main_frame, bg=self.BG)
        self.content_area.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 12))
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.build_views()
        self.show_view("Dashboard")

    def build_views(self):
        self.views = {
            "Dashboard": self.build_dashboard_view(),
            "Compare": self.build_compare_view(),
            "Discovery": self.build_discovery_view(),
            "Resolutions": self.build_resolutions_view(),
            "Readiness": self.build_readiness_view(),
            "Generation": self.build_text_view(
                "Generation",
                "Generation results",
                "generation_page_text",
            ),
            "Output": self.build_output_view(),
            "Settings": self.build_settings_view(),
        }

    def build_dashboard_view(self):
        frame = tk.Frame(self.content_area, bg=self.BG)
        frame.grid_columnconfigure(0, weight=3)
        frame.grid_columnconfigure(1, weight=2)
        frame.grid_rowconfigure(1, weight=1)
        self.build_configuration_card(frame)
        self.build_readiness_card(frame)
        self.build_discovery_card(frame)
        self.build_log_card(frame)
        return frame

    def page_shell(self, title, subtitle):
        frame = tk.Frame(self.content_area, bg=self.BG)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        heading = tk.Frame(frame, bg=self.BG)
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        tk.Label(heading, text=title, bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(heading, text=subtitle, bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w")
        body = self.card(frame)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        return frame, body

    def build_discovery_view(self):
        frame, body = self.page_shell(
            "Discovery",
            "Files, services and mappings detected in the selected PosData."
        )

        self.discovery_page_text = scrolledtext.ScrolledText(
            body,
            bg="#08111c",
            fg="#b9c8d8",
            insertbackground=self.TEXT,
            relief="flat",
            bd=0,
            font=("Consolas", 10),
            wrap=tk.WORD,
            padx=14,
            pady=14,
        )

        self.discovery_page_text.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=14,
            pady=14,
        )

        self.discovery_page_text.insert(
            tk.END,
            "Run the configuration to load discovery data.\n"
        )

        self.discovery_page_text.configure(
            state=tk.DISABLED
        )

        return frame

    def build_compare_view(self):
        frame, body = self.page_shell(
            "Compare PosData",
            "Compare Current and New PosData and generate release notes.",
        )

        body.grid_rowconfigure(4, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=0)
        body.grid_rowconfigure(1, weight=0)
        body.grid_rowconfigure(2, weight=0)
        body.grid_rowconfigure(3, weight=1)

        # ==================================================
        # HEADER
        # ==================================================

        header = tk.Frame(
            body,
            bg=self.PANEL,
        )

        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=18,
            pady=(18, 10),
        )

        header.grid_columnconfigure(
            0,
            weight=1,
        )

        tk.Label(
            header,
            text="Current vs New PosData",
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI", 12, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.compare_status_label = tk.Label(
            header,
            text="NOT RUN",
            bg="#29394b",
            fg=self.MUTED,
            padx=10,
            pady=4,
            font=("Segoe UI", 8, "bold"),
        )

        self.compare_status_label.grid(
            row=0,
            column=1,
            padx=(8, 0),
        )

        self.compare_button = tk.Button(
            header,
            text="Generate Release Notes",
            command=self.run_posdata_comparison,
            bg=self.PRIMARY,
            fg=self.TEXT,
            activebackground=self.PRIMARY_DARK,
            activeforeground=self.TEXT,
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=8,
            font=("Segoe UI", 9, "bold"),
        )

        self.compare_button.grid(
            row=0,
            column=2,
            padx=(8, 0),
        )

        self.open_compare_output_button = tk.Button(
            header,
            text="Open Compare Output",
            command=self.open_compare_output,
            bg="#0d3765",
            fg=self.TEXT,
            activebackground=self.PRIMARY,
            activeforeground=self.TEXT,
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=8,
            state=tk.DISABLED,
            font=("Segoe UI", 9),
        )

        self.open_compare_output_button.grid(
            row=0,
            column=3,
            padx=(8, 0),
        )

        # ==================================================
        # COUNTERS
        # ==================================================

        counters = tk.Frame(
            body,
            bg=self.PANEL,
        )

        counters.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 10),
        )

        for column in range(3):
            counters.grid_columnconfigure(
                column,
                weight=1,
                uniform="compare_counter",
            )

        self.compare_added_value = self.create_compare_counter(
            parent=counters,
            column=0,
            title="Added",
            color=self.SUCCESS,
        )

        self.compare_removed_value = self.create_compare_counter(
            parent=counters,
            column=1,
            title="Removed",
            color=self.ERROR,
        )

        self.compare_modified_value = self.create_compare_counter(
            parent=counters,
            column=2,
            title="Modified",
            color=self.WARNING,
        )

        # ==================================================
        # SUMMARY
        # ==================================================

        self.compare_summary_label = tk.Label(
            body,
            text=(
                "Compare the selected Current and New PosData "
                "folders to generate release notes."
            ),
            bg=self.PANEL,
            fg=self.MUTED,
            anchor="w",
            font=("Segoe UI", 9),
        )

        self.compare_summary_label.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 8),
        )

        # ==================================================
        # RELEASE NOTES
        # ==================================================

        self.compare_release_notes_text = (
            scrolledtext.ScrolledText(
                body,
                bg="#08111c",
                fg="#b9c8d8",
                insertbackground=self.TEXT,
                relief="flat",
                bd=0,
                font=("Consolas", 9),
                wrap=tk.WORD,
                padx=12,
                pady=12,
            )
        )

        self.compare_release_notes_text.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=18,
            pady=(0, 18),
        )

        self.compare_release_notes_text.insert(
            tk.END,
            "Release notes will appear here after comparison.\n",
        )

        self.compare_release_notes_text.configure(
            state=tk.DISABLED,
        )

        return frame

    def create_compare_counter(
        self,
        parent,
        column,
        title,
        color,
    ):
        counter_card = tk.Frame(
            parent,
            bg=self.PANEL_ALT,
            highlightbackground=color,
            highlightthickness=1,
        )

        counter_card.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=5,
        )

        value_label = tk.Label(
            counter_card,
            text="0",
            bg=self.PANEL_ALT,
            fg=color,
            font=("Segoe UI", 18, "bold"),
        )

        value_label.pack(
            pady=(12, 2),
        )

        tk.Label(
            counter_card,
            text=title,
            bg=self.PANEL_ALT,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        ).pack(
            pady=(0, 10),
        )

        return value_label

    def build_text_view(self, title, subtitle, attribute):
        frame, body = self.page_shell(title, subtitle)
        widget = scrolledtext.ScrolledText(body, bg="#08111c", fg="#b9c8d8",
                                           insertbackground=self.TEXT, relief="flat", bd=0,
                                           font=("Consolas", 10), wrap=tk.WORD, padx=14, pady=14)
        widget.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        widget.insert(tk.END, "Run the configuration to load results.\n")
        widget.configure(state=tk.DISABLED)
        setattr(self, attribute, widget)
        return frame

    def build_resolutions_view(self):
        frame, body = self.page_shell("Resolutions", "Manual and automatic resolution summary")
        self.resolution_page_labels = {}
        for row, item in enumerate(("Manual KVS Resolutions", "Manual POS Resolutions",
                                    "Skipped POS", "Unresolved POS")):
            line = tk.Frame(body, bg=self.PANEL_ALT, highlightbackground=self.BORDER,
                            highlightthickness=1)
            line.grid(row=row, column=0, sticky="ew", padx=20,
                      pady=(18 if row == 0 else 5, 5))
            line.grid_columnconfigure(0, weight=1)
            tk.Label(line, text=item, bg=self.PANEL_ALT, fg=self.TEXT,
                     font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=16, pady=13)
            value = tk.Label(line, text="0", bg=self.PANEL_ALT, fg=self.SUCCESS,
                             font=("Segoe UI", 13, "bold"))
            value.grid(row=0, column=1, padx=16)
            self.resolution_page_labels[item] = value
        return frame

    def build_readiness_view(self):
        frame, body = self.page_shell("Market Readiness", "Readiness status by component")
        for row, item in enumerate(("POS", "KVS", "ITONAS", "FOE", "COD", "STOREDB", "WAY")):
            line = tk.Frame(body, bg=self.PANEL_ALT, highlightbackground=self.BORDER,
                            highlightthickness=1)
            line.grid(row=row, column=0, sticky="ew", padx=20,
                      pady=(15 if row == 0 else 4, 4))
            line.grid_columnconfigure(1, weight=1)
            tk.Label(line, text=item, bg=self.PANEL_ALT, fg=self.TEXT, width=14,
                     anchor="w", font=("Segoe UI", 11, "bold")).grid(
                         row=0, column=0, padx=16, pady=12)
            detail = tk.Label(line, text="Waiting for execution", bg=self.PANEL_ALT,
                              fg=self.MUTED, anchor="w", font=("Segoe UI", 10))
            detail.grid(row=0, column=1, sticky="w")
            state = tk.Label(line, text="PENDING", bg="#29394b", fg=self.MUTED,
                             padx=12, pady=4, font=("Segoe UI", 9, "bold"))
            state.grid(row=0, column=2, padx=16)
            self.readiness_page_rows[item] = (state, detail)
        return frame

    def build_output_view(self):
        frame, body = self.page_shell("Output", "Open the latest generated files")
        tk.Button(body, text="Open Output Folder", command=self.open_output,
                  bg=self.PRIMARY, fg=self.TEXT, activebackground=self.PRIMARY_DARK,
                  activeforeground=self.TEXT, relief="flat", cursor="hand2",
                  padx=24, pady=10, font=("Segoe UI", 10, "bold")).grid(
                      row=0, column=0, sticky="nw", padx=22, pady=22)
        tk.Label(body, text=f"Output location:\n{self.output_folder}", bg=self.PANEL,
                 fg=self.MUTED, justify="left", font=("Segoe UI", 10)).grid(
                     row=1, column=0, sticky="nw", padx=22)
        return frame

    def build_settings_view(self):
        frame, body = self.page_shell("Settings", "Current application defaults")
        tk.Label(body, text="Default Laboratory", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=24, pady=(24, 4))
        self.settings_lab_label = tk.Label(body, text=self.selected_lab.get(), bg=self.PANEL,
                                           fg=self.TEXT, font=("Segoe UI", 12, "bold"))
        self.settings_lab_label.grid(row=1, column=0, sticky="w", padx=24)
        return frame

    def show_view(self, name):
        if name not in self.views:
            return
        for view in self.views.values():
            view.grid_remove()
        self.views[name].grid(row=0, column=0, sticky="nsew")
        for nav_name, button in self.nav_buttons.items():
            active = nav_name == name
            button.configure(bg="#123765" if active else self.SIDEBAR,
                             fg="#75b7ff" if active else self.TEXT)
        self.status_var.set(f"{name} view")

    def card(self, parent):
        return tk.Frame(parent, bg=self.PANEL, highlightbackground=self.BORDER,
                        highlightthickness=1)

    def build_configuration_card(self, parent):
        card = self.card(parent)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 7))
        card.grid_columnconfigure(0, weight=1)
        tk.Label(card, text="Configuration", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 12, "bold")).grid(
                     row=0, column=0, sticky="w", padx=18, pady=(14, 10))
        form = tk.Frame(card, bg=self.PANEL)
        form.grid(row=1, column=0, sticky="ew", padx=18)
        form.grid_columnconfigure(0, weight=1)
        self.current_entry, current_button = self.folder_field(
            form, 0, "Current PosData Folder", self.current_folder, self.browse_current)
        self.new_entry, new_button = self.folder_field(
            form, 2, "New PosData Folder", self.new_folder, self.browse_new)
        self.browse_buttons = [current_button, new_button]
        tk.Label(form, text="Lab / Environment", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 9)).grid(row=4, column=0, sticky="w", pady=(11, 6))
        labs = tk.Frame(form, bg=self.PANEL)
        labs.grid(row=5, column=0, sticky="ew")
        for column, (name, network) in enumerate(self.LABS.items()):
            labs.grid_columnconfigure(column, weight=1, uniform="lab")
            button = tk.Button(labs, text=f"{name}\n{network}",
                               command=lambda lab=name: self.select_lab(lab),
                               bg=self.PANEL_ALT, fg=self.TEXT, relief="flat",
                               highlightbackground=self.BORDER, highlightthickness=1,
                               cursor="hand2", pady=8, font=("Segoe UI", 9))
            button.grid(row=0, column=column, sticky="ew", padx=(0, 8))
            self.lab_buttons[name] = button
        actions = tk.Frame(form, bg=self.PANEL)
        actions.grid(row=6, column=0, sticky="ew", pady=(14, 16))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        self.run_button = tk.Button(actions, text="Execute Configuration",
                                    command=self.run_configuration, bg=self.PRIMARY,
                                    fg=self.TEXT, relief="flat", cursor="hand2",
                                    pady=10, font=("Segoe UI", 10, "bold"))
        self.run_button.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        self.clear_button = tk.Button(actions, text="Clear Configuration",
                                      command=self.clear_configuration, bg=self.PANEL_ALT,
                                      fg=self.TEXT, relief="flat", cursor="hand2", pady=10)
        self.clear_button.grid(row=0, column=1, sticky="ew", padx=(7, 0))

    def folder_field(self, parent, row, label, variable, command):
        tk.Label(parent, text=label, bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", pady=(0, 5))
        line = tk.Frame(parent, bg=self.PANEL)
        line.grid(row=row + 1, column=0, sticky="ew", pady=(0, 7))
        line.grid_columnconfigure(0, weight=1)
        entry = tk.Entry(line, textvariable=variable, bg=self.ENTRY, fg=self.TEXT,
                         insertbackground=self.TEXT, relief="flat", font=("Segoe UI", 9))
        entry.grid(row=0, column=0, sticky="ew", ipady=8)
        button = tk.Button(line, text="Browse", command=command, bg="#0d3765",
                           fg=self.TEXT, relief="flat", cursor="hand2", padx=14, pady=7)
        button.grid(row=0, column=1, padx=(8, 0))
        return entry, button

    def build_readiness_card(self, parent):
        card = self.card(parent)
        card.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 7))
        card.grid_columnconfigure(0, weight=1)
        tk.Label(card, text="Market Readiness", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 12, "bold")).grid(
                     row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.readiness_badge = tk.Label(card, text="WAITING", bg="#29394b",
                                        fg=self.MUTED, padx=10, pady=4,
                                        font=("Segoe UI", 8, "bold"))
        self.readiness_badge.grid(row=0, column=1, sticky="e", padx=16, pady=(14, 8))
        body = tk.Frame(card, bg=self.PANEL_ALT, highlightbackground=self.BORDER,
                        highlightthickness=1)
        body.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=14, pady=(0, 12))
        for row, item in enumerate(("POS", "KVS", "ITONAS", "FOE", "COD", "STOREDB", "WAY")):
            tk.Label(body, text=item, bg=self.PANEL_ALT, fg=self.TEXT,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=12, pady=6)
            state = tk.Label(body, text="PENDING", bg="#29394b", fg=self.MUTED,
                             padx=8, pady=2, font=("Segoe UI", 8, "bold"))
            state.grid(row=row, column=1, padx=8)
            detail = tk.Label(body, text="Waiting for execution", bg=self.PANEL_ALT,
                              fg=self.MUTED, font=("Segoe UI", 8))
            detail.grid(row=row, column=2, sticky="w", padx=(4, 12))
            self.readiness_rows[item] = (state, detail)

    def build_discovery_card(self, parent):
        card = self.card(parent)
        card.grid(row=1, column=0, sticky="nsew", padx=(0, 7), pady=(7, 0))
        tk.Label(card, text="Discovery Summary", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(14, 10))
        counts = tk.Frame(card, bg=self.PANEL)
        counts.pack(fill="x", padx=14)
        self.discovery_values = {}
        for column, (key, label, color) in enumerate((
            ("POS", "POS Files", self.INFO), ("KVS", "KVS Services", self.SUCCESS),
            ("ITONAS", "Itonas", "#b886ff"), ("WAY", "WAY Files", self.WARNING),
            ("PRODUCTION", "Production", "#40d5d9"),
        )):
            counts.grid_columnconfigure(column, weight=1, uniform="count")
            box = tk.Frame(counts, bg=self.PANEL_ALT, highlightbackground=color,
                           highlightthickness=1)
            box.grid(row=0, column=column, sticky="nsew", padx=4)
            value = tk.Label(box, text="-", bg=self.PANEL_ALT, fg=color,
                             font=("Segoe UI", 16, "bold"))
            value.pack(pady=(10, 0))
            tk.Label(box, text=label, bg=self.PANEL_ALT, fg=self.MUTED,
                     font=("Segoe UI", 8)).pack(pady=(0, 10))
            self.discovery_values[key] = value

    def build_log_card(self, parent):
        card = self.card(parent)
        card.grid(row=1, column=1, sticky="nsew", padx=(7, 0), pady=(7, 0))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        tk.Label(card, text="Execution Log", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=12)
        self.log = scrolledtext.ScrolledText(card, bg="#08111c", fg="#b9c8d8",
                                             insertbackground=self.TEXT, relief="flat", bd=0,
                                             font=("Consolas", 9), wrap=tk.WORD, padx=10, pady=10)
        self.log.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log.tag_configure("success", foreground=self.SUCCESS)
        self.log.tag_configure("error", foreground=self.ERROR)
        self.log.tag_configure("info", foreground=self.INFO)
        self.append_log("PosData Configurator ready.\n", "success")

    def build_footer(self):
        footer = tk.Frame(self.main_frame, bg="#081422", highlightbackground=self.BORDER,
                          highlightthickness=1)
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        tk.Label(footer, textvariable=self.status_var, bg="#081422", fg=self.SUCCESS,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=20, pady=10)
        self.generate_button = tk.Button(footer, text="Generate All",
                                         command=self.run_configuration, bg="#155d34",
                                         fg=self.TEXT, relief="flat", cursor="hand2",
                                         padx=28, pady=8, font=("Segoe UI", 10, "bold"))
        self.generate_button.grid(row=0, column=1, padx=10, pady=6)
        tk.Button(footer, text="Open Output", command=self.open_output, bg=self.PANEL_ALT,
                  fg=self.TEXT, relief="flat", cursor="hand2", padx=22, pady=8).grid(
                      row=0, column=2, padx=(0, 20), pady=6)

    def select_lab(self, lab):
        if self.running:
            return
        self.selected_lab.set(lab)
        for name, button in self.lab_buttons.items():
            active = name == lab
            button.configure(bg="#123765" if active else self.PANEL_ALT,
                             fg="#8bc5ff" if active else self.TEXT,
                             highlightbackground=self.PRIMARY if active else self.BORDER,
                             highlightthickness=2 if active else 1)
        self.sidebar_lab.configure(text=lab)
        self.sidebar_network.configure(text=self.LABS[lab])
        self.settings_lab_label.configure(text=lab)

    def browse_current(self):
        folder = filedialog.askdirectory(initialdir=self.current_folder.get() or self.project_folder)
        if folder:
            self.current_folder.set(folder)

    def browse_new(self):
        folder = filedialog.askdirectory(initialdir=self.new_folder.get() or self.project_folder)
        if folder:
            self.new_folder.set(folder)

    def clear_configuration(self):
        if self.running:
            return
        self.current_folder.set("")
        self.new_folder.set("")
        self.reset_progress()
        self.clear_log()

    def clear_log(self):
        if not self.running:
            self.log.delete("1.0", tk.END)

    def append_log(self, text, tag=None):
        def write():
            self.log.insert(tk.END, text, tag or ())
            self.log.see(tk.END)
        if threading.current_thread() is threading.main_thread():
            write()
        else:
            self.root.after(0, write)

    def validate_inputs(self):
        errors = []
        current = self.current_folder.get().strip()
        new = self.new_folder.get().strip()
        if not os.path.isdir(current):
            errors.append("Current PosData folder does not exist.")
        if not os.path.isdir(new):
            errors.append("New PosData folder does not exist.")
        if new and not os.path.isfile(os.path.join(new, "store-db.xml")):
            errors.append("store-db.xml was not found in New PosData.")
        if new and not os.path.isfile(os.path.join(new, "screen.xml")):
            errors.append("screen.xml was not found in New PosData.")
        if errors:
            messagebox.showerror("Configuration Validation", "\n".join(errors))
            return False
        return True

    def run_configuration(self):
        if self.running or not self.validate_inputs():
            return
        self.execution_options = {
            "selected_lab": self.selected_lab.get(),
            "current_posdata_folder": self.current_folder.get().strip(),
            "new_posdata_folder": self.new_folder.get().strip(),
        }
        self.running = True
        self.set_controls(False)
        self.start_progress_sequence()
        self.status_var.set("Discovery running...")
        self.append_log("\nConfiguration started.\n", "info")
        threading.Thread(target=self.execute_backend, daemon=True).start()

    def execute_backend(self):
        buffer = io.StringIO()
        error = None
        runtime = None
        try:
            with redirect_stdout(buffer), redirect_stderr(buffer):
                runtime = main(
                    selected_lab=
                        self.execution_options[
                            "selected_lab"
                        ],

                    current_posdata_folder=
                        self.execution_options[
                            "current_posdata_folder"
                        ],

                    new_posdata_folder=
                        self.execution_options[
                            "new_posdata_folder"
                        ],
                )
        except Exception as exc:
            error = exc
        output = buffer.getvalue()
        if output:
            self.append_log(output)
        self.root.after(
            0,
            self.finish_execution,
            error,
            output,
            runtime
        )
    def finish_execution(self, error, output, runtime):
        self.running = False
        self.execution_id += 1
        self.set_controls(True)

        if error:
            self.set_progress(completed_steps=[], failed_step="Discovery")
            self.status_var.set("Execution failed")
            self.append_log(f"\nExecution failed: {error}\n", "error")
            self.readiness_badge.configure(
                text="FAILED",
                bg="#4b1f28",
                fg=self.ERROR,
            )
            return

        if runtime is None:
            self.set_progress(
                completed_steps=["Discovery", "Resolutions", "Readiness"],
                failed_step="Generation",
            )
            self.status_var.set("Runtime data was not returned")
            self.readiness_badge.configure(
                text="REVIEW REQUIRED",
                bg="#4a3a15",
                fg=self.WARNING,
            )
            self.append_log(
                "\nThe backend completed but did not return RuntimeContext.\n",
                "error",
            )
            return

        success = self.is_runtime_successful(runtime)
        self.update_dashboard_from_runtime(runtime, output)

        if success:
            self.set_progress(completed_steps=list(self.STEPS))
            self.status_var.set("Configuration completed successfully")
            self.readiness_badge.configure(
                text="READY FOR GENERATION",
                bg="#153c28",
                fg=self.SUCCESS,
            )
        else:
            self.set_progress(
                completed_steps=["Discovery", "Resolutions", "Readiness"],
                failed_step="Generation",
            )
            self.status_var.set("Review required")
            self.readiness_badge.configure(
                text="REVIEW REQUIRED",
                bg="#4a3a15",
                fg=self.WARNING,
            )

        self.append_log(
            "\nConfiguration completed.\n",
            "success" if success else "info",
        )

    def is_runtime_successful(self, runtime):
        readiness = getattr(runtime, "market_readiness", {}) or {}
        readiness_ok = (
            readiness.get("overall_status") == "READY FOR GENERATION"
        )

        generated_pos = getattr(runtime, "generated_pos", []) or []
        generated_itonas = getattr(runtime, "generated_itonas", []) or []
        generated_way = getattr(runtime, "generated_way", {}) or {}
        generated_cod = getattr(runtime, "generated_cod", {}) or {}
        generated_store_cod = (
            getattr(runtime, "generated_store_cod", {}) or {}
        )
        xmlrpccli = getattr(runtime, "xmlrpccli_result", {}) or {}

        pos_ok = bool(generated_pos) and all(
            item.get("generated", False)
            for item in generated_pos
        )
        itonas_ok = all(
            item.get("generated", False)
            for item in generated_itonas
        )

        return all((
            readiness_ok,
            pos_ok,
            itonas_ok,
            generated_way.get("generated", False),
            generated_cod.get("generated", False),
            generated_store_cod.get("generated", False),
            xmlrpccli.get("status") in {"SUCCESS", "NO CHANGES"},
        ))

    def count_kvs_services(self, runtime):
        kvs_mapping = getattr(runtime, "kvs_mapping", {}) or {}
        services = set()

        for mapping in kvs_mapping.get("mappings", []):
            for service in mapping.get("mapped_services", []):
                service_id = service.get("service")
                if service_id is not None:
                    services.add(str(service_id).strip())

        for service in kvs_mapping.get("extra_services", []):
            service_id = service.get("service")
            if service_id is not None:
                services.add(str(service_id).strip())

        return len(services)

    def update_dashboard_from_runtime(self, runtime, output):
        discovery = getattr(runtime, "dynamic_pos_discovery", {}) or {}
        pos_count = len(discovery.get("pos_files", []))
        kvs_count = self.count_kvs_services(runtime)
        itona_count = sum(
            bool(item.get("found", False))
            for item in (getattr(runtime, "itonas", []) or [])
        )
        way_result = getattr(runtime, "generated_way", {}) or {}
        way_count = 1 if way_result.get("generated", False) else 0
        production_count = len(
            getattr(runtime, "generated_production", []) or []
        )

        counters = {
            "POS": pos_count,
            "KVS": kvs_count,
            "ITONAS": itona_count,
            "WAY": way_count,
            "PRODUCTION": production_count,
        }
        for key, value in counters.items():
            self.discovery_values[key].configure(text=str(value))

        self.update_resolution_data(runtime)
        self.update_readiness_data(runtime)

        discovery_text = (
            "DISCOVERY RESULTS\n"
            + "=" * 50
            + "\n"
            + "\n".join(
                f"{key}: {value}"
                for key, value in counters.items()
            )
        )
        self.set_readonly_text(
            self.discovery_page_text,
            discovery_text,
        )

        generation_match = re.search(
            r"GENERATION REPORT[\s\S]*",
            output,
            re.IGNORECASE,
        )
        self.set_readonly_text(
            self.generation_page_text,
            generation_match.group(0)
            if generation_match
            else output,
        )

    def update_resolution_data(self, runtime):
        readiness = getattr(runtime, "market_readiness", {}) or {}
        values = {
            "Manual KVS Resolutions": readiness.get(
                "manual_kvs_resolutions", 0
            ),
            "Manual POS Resolutions": readiness.get(
                "manual_pos_resolutions", 0
            ),
            "Skipped POS": readiness.get("skipped_pos", 0),
            "Unresolved POS": readiness.get("unresolved_pos", 0),
        }
        for name, value in values.items():
            label = self.resolution_page_labels.get(name)
            if label is not None:
                label.configure(
                    text=str(value),
                    fg=self.ERROR if value else self.SUCCESS,
                )

    def update_readiness_data(self, runtime):
        readiness = getattr(runtime, "market_readiness", {}) or {}
        component_data = {
            str(component.get("name", "")).upper(): component
            for component in readiness.get("components", [])
        }

        aliases = {
            "STOREDB": "STOREDB",
            "STORE DB": "STOREDB",
        }

        normalized_components = {}
        for name, component in component_data.items():
            normalized_name = aliases.get(name, name)
            normalized_components[normalized_name] = component

        for collection in (
            self.readiness_rows,
            self.readiness_page_rows,
        ):
            for name, (state_label, detail_label) in collection.items():
                component = normalized_components.get(name.upper())
                status = (
                    component.get("status", "UNKNOWN")
                    if component
                    else "UNKNOWN"
                )
                details = component.get("details", []) if component else []

                if status == "READY":
                    text, bg, fg = "READY", "#164a30", self.SUCCESS
                elif status == "REVIEW REQUIRED":
                    text, bg, fg = "REVIEW", "#4a3a15", self.WARNING
                else:
                    text, bg, fg = "FAIL", "#4b1f28", self.ERROR

                state_label.configure(text=text, bg=bg, fg=fg)
                detail_label.configure(
                    text="; ".join(str(item) for item in details)
                    if details
                    else status.title()
                )

    def run_posdata_comparison(self):
        if self.compare_running:
            return

        current_folder = self.current_folder.get().strip()
        new_folder = self.new_folder.get().strip()

        if not os.path.isdir(current_folder):
            messagebox.showerror(
                "Compare PosData",
                "Current PosData folder does not exist.",
            )
            return

        if not os.path.isdir(new_folder):
            messagebox.showerror(
                "Compare PosData",
                "New PosData folder does not exist.",
            )
            return

        self.compare_running = True

        self.compare_button.configure(
            state=tk.DISABLED,
            text="Comparing...",
            bg="#31445a",
        )

        self.open_compare_output_button.configure(
            state=tk.DISABLED,
        )

        self.compare_status_label.configure(
            text="RUNNING",
            bg="#4a3a15",
            fg=self.WARNING,
        )

        self.compare_summary_label.configure(
            text="Comparing Current and New PosData folders..."
        )

        self.set_readonly_text(
            self.compare_release_notes_text,
            "Comparison in progress...\n",
        )

        self.status_var.set(
            "PosData comparison running..."
        )

        self.append_log(
            "\nPosData comparison started.\n",
            "info",
        )

        threading.Thread(
            target=self.execute_posdata_comparison,
            args=(
                current_folder,
                new_folder,
            ),
            daemon=True,
        ).start()


    def execute_posdata_comparison(
        self,
        current_folder,
        new_folder,
    ):
        comparison = None
        outputs = {}
        error = None

        try:
            comparison, outputs = (
                compare_and_generate_release_notes(
                    current_folder=current_folder,
                    new_folder=new_folder,
                    output_folder=os.path.join(
                        self.output_folder,
                        "compare",
                    ),
                )
            )

        except Exception as exc:
            error = exc

        self.root.after(
            0,
            self.finish_compare,
            comparison,
            outputs,
            error,
        )

    def set_readonly_text(self, widget, text):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state=tk.DISABLED)

    def set_controls(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.current_entry.configure(state=state)
        self.new_entry.configure(state=state)
        self.clear_button.configure(state=state)
        self.run_button.configure(state=state,
                                  text="Execute Configuration" if enabled else "Configuration Running...",
                                  bg=self.PRIMARY if enabled else "#31445a")
        self.generate_button.configure(state=state)
        if hasattr(self, "compare_button"):
            compare_state = (
                tk.NORMAL
                if enabled and not self.compare_running
                else tk.DISABLED
            )

            self.compare_button.configure(
                state=compare_state,
            )
        for button in self.browse_buttons:
            button.configure(state=state)
        for button in self.lab_buttons.values():
            button.configure(state=state)

    def open_output(self):
        if not os.path.isdir(self.output_folder):
            messagebox.showwarning("Output", "Output folder was not found.")
            return
        os.startfile(self.output_folder)

    def finish_compare(
        self,
        comparison,
        outputs,
        error,
    ):
        self.compare_running = False

        self.compare_button.configure(
            state=tk.NORMAL,
            text="Generate Release Notes",
            bg=self.PRIMARY,
        )

        if error is not None:
            self.compare_status_label.configure(
                text="FAILED",
                bg="#4b1f28",
                fg=self.ERROR,
            )

            self.compare_summary_label.configure(
                text="Comparison failed. Review the error below."
            )

            self.set_readonly_text(
                self.compare_release_notes_text,
                (
                    "POSDATA COMPARISON FAILED\n"
                    + "=" * 80
                    + "\n\n"
                    + f"{type(error).__name__}: {error}\n"
                ),
            )

            self.open_compare_output_button.configure(
                state=tk.DISABLED,
            )

            self.status_var.set(
                "PosData comparison failed"
            )

            self.append_log(
                f"\nPosData comparison failed: {error}\n",
                "error",
            )

            return

        if comparison is None:
            self.compare_status_label.configure(
                text="FAILED",
                bg="#4b1f28",
                fg=self.ERROR,
            )

            self.compare_summary_label.configure(
                text="Comparison completed without returning results."
            )

            self.set_readonly_text(
                self.compare_release_notes_text,
                "The comparison did not return a result object.\n",
            )

            self.open_compare_output_button.configure(
                state=tk.DISABLED,
            )

            self.status_var.set(
                "PosData comparison returned no results"
            )

            return

        self.last_comparison = comparison
        self.last_comparison_outputs = outputs or {}

        #
        # TOTALS
        #
        # PosDataComparison is an object, therefore attributes must be
        # accessed with getattr instead of comparison.get(...).
        #

        added_count = getattr(
            comparison,
            "added_count",
            None,
        )

        removed_count = getattr(
            comparison,
            "removed_count",
            None,
        )

        modified_count = getattr(
            comparison,
            "modified_count",
            None,
        )

        unchanged_count = getattr(
            comparison,
            "unchanged_count",
            0,
        ) or 0

        #
        # Obtain the collection containing the compared files.
        # Different versions may call this collection results,
        # files, file_results or comparisons.
        #

        file_results = getattr(
            comparison,
            "results",
            None,
        )

        if file_results is None:
            file_results = getattr(
                comparison,
                "files",
                None,
            )

        if file_results is None:
            file_results = getattr(
                comparison,
                "file_results",
                None,
            )

        if file_results is None:
            file_results = getattr(
                comparison,
                "comparisons",
                None,
            )

        file_results = list(file_results or [])

        #
        # Fallback:
        # calculate totals from each file result when explicit counters
        # are not available in PosDataComparison.
        #

        if (
            added_count is None
            or removed_count is None
            or modified_count is None
        ):
            calculated_added = 0
            calculated_removed = 0
            calculated_modified = 0
            calculated_unchanged = 0

            for file_result in file_results:
                status = getattr(
                    file_result,
                    "status",
                    None,
                )

                if status is None:
                    status = getattr(
                        file_result,
                        "kind",
                        None,
                    )

                if status is None:
                    status = getattr(
                        file_result,
                        "change_type",
                        None,
                    )

                status = str(status or "").strip().upper()

                if status in {
                    "ADDED",
                    "NEW",
                    "FILE_ADDED",
                }:
                    calculated_added += 1

                elif status in {
                    "REMOVED",
                    "DELETED",
                    "FILE_REMOVED",
                }:
                    calculated_removed += 1

                elif status in {
                    "MODIFIED",
                    "CHANGED",
                    "FILE_CHANGED",
                }:
                    calculated_modified += 1

                elif status in {
                    "EQUAL",
                    "UNCHANGED",
                    "SAME",
                }:
                    calculated_unchanged += 1

                else:
                    changes = getattr(
                        file_result,
                        "changes",
                        [],
                    ) or []

                    if changes:
                        calculated_modified += 1
                    else:
                        calculated_unchanged += 1

            if added_count is None:
                added_count = calculated_added

            if removed_count is None:
                removed_count = calculated_removed

            if modified_count is None:
                modified_count = calculated_modified

            if not unchanged_count:
                unchanged_count = calculated_unchanged

        added_count = int(added_count or 0)
        removed_count = int(removed_count or 0)
        modified_count = int(modified_count or 0)
        unchanged_count = int(unchanged_count or 0)

        #
        # If the result object exposes separate collections,
        # use them when the explicit counters remain zero.
        #

        added_files = getattr(
            comparison,
            "added",
            None,
        )

        if added_files is None:
            added_files = getattr(
                comparison,
                "added_files",
                None,
            )

        removed_files = getattr(
            comparison,
            "removed",
            None,
        )

        if removed_files is None:
            removed_files = getattr(
                comparison,
                "removed_files",
                None,
            )

        modified_files = getattr(
            comparison,
            "modified",
            None,
        )

        if modified_files is None:
            modified_files = getattr(
                comparison,
                "modified_files",
                None,
            )

        if added_count == 0 and added_files is not None:
            added_count = len(added_files)

        if removed_count == 0 and removed_files is not None:
            removed_count = len(removed_files)

        if modified_count == 0 and modified_files is not None:
            modified_count = len(modified_files)

        changed_files_count = (
            added_count
            + removed_count
            + modified_count
        )

        total_files_count = (
            changed_files_count
            + unchanged_count
        )

        if total_files_count == 0 and file_results:
            total_files_count = len(file_results)

        #
        # UPDATE CARDS
        #

        self.compare_added_value.configure(
            text=str(added_count)
        )

        self.compare_removed_value.configure(
            text=str(removed_count)
        )

        self.compare_modified_value.configure(
            text=str(modified_count)
        )

        #
        # RELEASE NOTES
        #

        try:
            notes = release_notes_text(
                comparison
            )
        except Exception as notes_error:
            notes = (
                "The comparison completed, but the formatted release "
                "notes could not be loaded.\n\n"
                f"{type(notes_error).__name__}: {notes_error}\n"
            )

        if not notes or not str(notes).strip():
            notes = (
                "Comparison completed successfully, but the generated "
                "release notes are empty.\n"
            )

        notes = str(notes)

        #
        # SUMMARY
        #

        errors = getattr(
            comparison,
            "errors",
            [],
        ) or []

        summary_parts = [
            f"{total_files_count} file(s) compared",
            f"{changed_files_count} changed",
            f"{unchanged_count} unchanged",
        ]

        if errors:
            summary_parts.append(
                f"{len(errors)} error(s)"
            )

        self.compare_summary_label.configure(
            text=" | ".join(summary_parts)
        )

        if errors:
            self.compare_status_label.configure(
                text="COMPLETE WITH WARNINGS",
                bg="#4a3a15",
                fg=self.WARNING,
            )

            error_section = [
                "",
                "",
                "=" * 80,
                "COMPARISON WARNINGS",
                "=" * 80,
            ]

            for comparison_error in errors:
                error_section.append(
                    f"- {comparison_error}"
                )

            notes += "\n".join(error_section)

        else:
            self.compare_status_label.configure(
                text="COMPLETE",
                bg="#153c28",
                fg=self.SUCCESS,
            )

        self.set_readonly_text(
            self.compare_release_notes_text,
            notes,
        )

        #
        # OUTPUT
        #

        compare_output_exists = bool(
            self.last_comparison_outputs
        )

        compare_folder = os.path.join(
            self.output_folder,
            "compare",
        )

        if os.path.isdir(compare_folder):
            compare_output_exists = True

        self.open_compare_output_button.configure(
            state=(
                tk.NORMAL
                if compare_output_exists
                else tk.DISABLED
            )
        )

        self.status_var.set(
            (
                "PosData comparison completed: "
                f"{total_files_count} file(s), "
                f"{changed_files_count} change(s)"
            )
        )

        self.append_log(
            (
                "\nPosData comparison completed.\n"
                f"Files compared: {total_files_count}\n"
                f"Added: {added_count}\n"
                f"Removed: {removed_count}\n"
                f"Modified: {modified_count}\n"
                f"Unchanged: {unchanged_count}\n"
            ),
            "success",
        )

    def open_compare_output(self):
        compare_folder = os.path.join(
            self.output_folder,
            "compare",
        )

        if not os.path.isdir(compare_folder):
            messagebox.showwarning(
                "Compare Output",
                (
                    "Compare output folder was not found.\n\n"
                    f"{compare_folder}"
                ),
            )
            return

        try:
            os.startfile(compare_folder)
        except OSError as exc:
            messagebox.showerror(
                "Compare Output",
                (
                    "Could not open Compare output folder.\n\n"
                    f"{exc}"
                ),
            )

def main_ui():
    root = tk.Tk()
    PosDataConfiguratorUI(root)
    root.mainloop()


if __name__ == "__main__":
    main_ui()
