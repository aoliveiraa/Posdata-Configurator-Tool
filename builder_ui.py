"""PosData Builder graphical interface."""

from __future__ import annotations

import re
import tkinter as tk

from tkinter import (
    filedialog,
    messagebox,
    ttk,
)
from typing import Any, Dict

from src.builder.assignment_proposal_engine import (
    build_assignment_proposal,
)
from src.builder.builder_assignment_phase import (
    MAX_KVS_PER_ITONA,
    NONE_VALUE,
    available_pos_options,
    build_itona_candidate_index,
    confirm_itona_assignments,
    confirm_pos_assignments,
    initial_itona_selections,
    itona_candidate_display,
)
from src.builder.builder_context import (
    BuilderContext,
)
from src.builder.builder_discovery_phase import (
    run_builder_discovery_phase,
)
from src.builder.builder_generation_adapter import (
    build_builder_runtime_context,
)
from src.builder.builder_inputs import (
    validate_builder_inputs,
)
from src.builder.template_repository import (
    TemplateRepository,
)

from tkinter import messagebox

from src.builder.builder_generation_phase import (
    run_builder_generation_phase,
)


APP_TITLE = "PosData Builder v0.1.0"

COLORS = {
    "nav": "#17365D",
    "accent": "#1F8080",
    "background": "#F4F7FA",
    "card": "#FFFFFF",
    "text": "#243447",
    "muted": "#5B6573",
    "success": "#2E7D32",
    "warning": "#B26A00",
    "danger": "#B3261E",
}


class PosDataBuilderApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(1000, 680)
        self.configure(
            bg=COLORS["background"]
        )

        self.context: BuilderContext | None = None
        self.builder_runtime = None

        self.proposal: Dict[str, Any] = {}

        self.slot_vars: Dict[
            str,
            tk.StringVar,
        ] = {}

        self.extra_vars: Dict[
            str,
            tk.StringVar,
        ] = {}

        self.itona_selections: Dict[
            str,
            list[str],
        ] = {}

        self.itona_summary_vars: Dict[
            str,
            tk.StringVar,
        ] = {}

        self.user_created_itona_slots: set[str] = set()
        self._template_itonas_limited = False

        self.lab_var = tk.StringVar(
            value="BR"
        )

        self.template_var = tk.StringVar(
            value="CA"
        )

        self.source_var = tk.StringVar(
            value="samples/new_posdata"
        )

        self.status_var = tk.StringVar(
            value="Ready"
        )

        self.summary_var = tk.StringVar(
            value="Configure the build inputs."
        )

        self._configure_styles()
        self._build_shell()
        self.show_setup()

    # ==========================================================
    # STYLE
    # ==========================================================

    def _configure_styles(self) -> None:

        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "TFrame",
            background=COLORS["background"],
        )

        style.configure(
            "Card.TFrame",
            background=COLORS["card"],
        )

        style.configure(
            "Title.TLabel",
            background=COLORS["background"],
            foreground=COLORS["nav"],
            font=(
                "Segoe UI",
                20,
                "bold",
            ),
        )

        style.configure(
            "Subtitle.TLabel",
            background=COLORS["background"],
            foreground=COLORS["muted"],
            font=(
                "Segoe UI",
                10,
            ),
        )

        style.configure(
            "CardTitle.TLabel",
            background=COLORS["card"],
            foreground=COLORS["nav"],
            font=(
                "Segoe UI",
                12,
                "bold",
            ),
        )

        style.configure(
            "CardText.TLabel",
            background=COLORS["card"],
            foreground=COLORS["text"],
            font=(
                "Segoe UI",
                10,
            ),
        )

        style.configure(
            "Effective.TLabel",
            background=COLORS["card"],
            foreground=COLORS["accent"],
            font=(
                "Segoe UI",
                12,
                "bold",
            ),
        )

        style.configure(
            "Customized.TLabel",
            background=COLORS["card"],
            foreground=COLORS["warning"],
            font=(
                "Segoe UI",
                10,
                "bold",
            ),
        )

        style.configure(
            "Success.TLabel",
            background=COLORS["card"],
            foreground=COLORS["success"],
            font=(
                "Segoe UI",
                10,
                "bold",
            ),
        )

        style.configure(
            "Skipped.TLabel",
            background=COLORS["card"],
            foreground=COLORS["muted"],
            font=(
                "Segoe UI",
                10,
                "bold",
            ),
        )

        style.configure(
            "Accent.TButton",
            font=(
                "Segoe UI",
                10,
                "bold",
            ),
        )

    # ==========================================================
    # APPLICATION SHELL
    # ==========================================================

    def _build_shell(self) -> None:

        header = tk.Frame(
            self,
            bg=COLORS["nav"],
            height=68,
        )

        header.pack(
            fill="x"
        )

        header.pack_propagate(
            False
        )

        tk.Label(
            header,
            text="PosData Builder",
            bg=COLORS["nav"],
            fg="white",
            font=(
                "Segoe UI",
                18,
                "bold",
            ),
        ).pack(
            side="left",
            padx=24,
        )

        tk.Label(
            header,
            text="Builder Workflow",
            bg=COLORS["nav"],
            fg="#DDE8F3",
            font=(
                "Segoe UI",
                10,
            ),
        ).pack(
            side="right",
            padx=24,
        )

        body = tk.Frame(
            self,
            bg=COLORS["background"],
        )

        body.pack(
            fill="both",
            expand=True,
        )

        self.sidebar = tk.Frame(
            body,
            bg="#E8EEF5",
            width=190,
        )

        self.sidebar.pack(
            side="left",
            fill="y",
        )

        self.sidebar.pack_propagate(
            False
        )

        self.nav_labels: Dict[
            str,
            tk.Label,
        ] = {}

        navigation = (
            "1. Setup",
            "2. Discovery",
            "3. POS Mapping",
            "4. Itona Mapping",
            "5. Review",
        )

        for label_text in navigation:

            label = tk.Label(
                self.sidebar,
                text=label_text,
                anchor="w",
                padx=18,
                pady=13,
                bg="#E8EEF5",
                fg=COLORS["muted"],
                font=(
                    "Segoe UI",
                    10,
                    "bold",
                ),
            )

            label.pack(
                fill="x"
            )

            self.nav_labels[
                label_text
            ] = label

        tk.Label(
            self.sidebar,
            textvariable=self.summary_var,
            justify="left",
            wraplength=155,
            anchor="nw",
            bg="#E8EEF5",
            fg=COLORS["muted"],
            font=(
                "Segoe UI",
                9,
            ),
        ).pack(
            fill="x",
            padx=18,
            pady=24,
        )

        self.content = ttk.Frame(
            body
        )

        self.content.pack(
            side="left",
            fill="both",
            expand=True,
            padx=24,
            pady=20,
        )

        footer = tk.Frame(
            self,
            bg="#E8EEF5",
            height=48,
        )

        footer.pack(
            fill="x",
            side="bottom",
        )

        footer.pack_propagate(
            False
        )

        tk.Label(
            footer,
            textvariable=self.status_var,
            bg="#E8EEF5",
            fg=COLORS["text"],
            font=(
                "Segoe UI",
                9,
            ),
        ).pack(
            side="left",
            padx=20,
        )

    def _clear_content(self) -> None:

        for child in (
            self.content.winfo_children()
        ):
            child.destroy()

    def _activate_step(
        self,
        step: str,
    ) -> None:

        for text, label in (
            self.nav_labels.items()
        ):

            active = (
                text == step
            )

            label.configure(
                bg=(
                    COLORS["accent"]
                    if active
                    else "#E8EEF5"
                ),
                fg=(
                    "white"
                    if active
                    else COLORS["muted"]
                ),
            )

    def _card(
        self,
        parent,
        padding: int = 18,
    ) -> ttk.Frame:

        frame = ttk.Frame(
            parent,
            style="Card.TFrame",
            padding=padding,
        )

        frame.pack(
            fill="x",
            pady=(0, 14),
        )

        return frame

    def _scrollable_content(
        self,
    ):

        container = ttk.Frame(
            self.content
        )

        container.pack(
            fill="both",
            expand=True,
        )

        canvas = tk.Canvas(
            container,
            bg=COLORS["background"],
            highlightthickness=0,
        )

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=canvas.yview,
        )

        inner = ttk.Frame(
            canvas
        )

        window_id = (
            canvas.create_window(
                (0, 0),
                window=inner,
                anchor="nw",
            )
        )

        def update_scroll_region(
            _event=None,
        ) -> None:

            canvas.configure(
                scrollregion=(
                    canvas.bbox("all")
                )
            )

        def update_inner_width(
            event,
        ) -> None:

            canvas.itemconfigure(
                window_id,
                width=event.width,
            )

        inner.bind(
            "<Configure>",
            update_scroll_region,
        )

        canvas.bind(
            "<Configure>",
            update_inner_width,
        )

        canvas.configure(
            yscrollcommand=(
                scrollbar.set
            )
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        return inner

    # ==========================================================
    # SETUP
    # ==========================================================

    def show_setup(self) -> None:

        self._clear_content()
        self._activate_step(
            "1. Setup"
        )

        ttk.Label(
            self.content,
            text="Setup",
            style="Title.TLabel",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            self.content,
            text=(
                "Select the internal template, "
                "source PosData and target laboratory."
            ),
            style="Subtitle.TLabel",
        ).pack(
            anchor="w",
            pady=(2, 18),
        )

        card = self._card(
            self.content
        )

        ttk.Label(
            card,
            text="Build configuration",
            style="CardTitle.TLabel",
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 14),
        )

        ttk.Label(
            card,
            text="Template market",
            style="CardText.TLabel",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=7,
        )

        ttk.Combobox(
            card,
            textvariable=(
                self.template_var
            ),
            values=(
                TemplateRepository(
                    "templates"
                ).available_templates()
            ),
            state="readonly",
            width=20,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(14, 0),
            pady=7,
        )

        ttk.Label(
            card,
            text="Target laboratory",
            style="CardText.TLabel",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=7,
        )

        ttk.Combobox(
            card,
            textvariable=self.lab_var,
            values=(
                "BR",
                "RIO",
                "RENEIGH",
            ),
            state="readonly",
            width=20,
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(14, 0),
            pady=7,
        )

        ttk.Label(
            card,
            text="Source PosData",
            style="CardText.TLabel",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=7,
        )

        ttk.Entry(
            card,
            textvariable=self.source_var,
        ).grid(
            row=3,
            column=1,
            sticky="ew",
            padx=(14, 8),
            pady=7,
        )

        ttk.Button(
            card,
            text="Browse",
            command=self._browse_source,
        ).grid(
            row=3,
            column=2,
            pady=7,
        )

        card.columnconfigure(
            1,
            weight=1,
        )

        ttk.Button(
            self.content,
            text="Validate and Discover",
            style="Accent.TButton",
            command=self._run_discovery,
        ).pack(
            anchor="e",
            pady=8,
        )

        self.status_var.set(
            "Ready"
        )

    def _browse_source(self) -> None:

        selected = (
            filedialog.askdirectory(
                title=(
                    "Select Source PosData"
                )
            )
        )

        if selected:
            self.source_var.set(
                selected
            )

    def _run_discovery(self) -> None:

        self.status_var.set(
            "Running Discovery..."
        )

        self.update_idletasks()

        try:

            inputs = (
                validate_builder_inputs(
                    selected_lab=(
                        self.lab_var.get()
                    ),
                    template_market=(
                        self.template_var.get()
                    ),
                    source_posdata_folder=(
                        self.source_var.get()
                    ),
                    template_root=(
                        "templates"
                    ),
                )
            )

            self.context = BuilderContext(
                selected_lab=(
                    inputs["lab"]
                ),
                config_path=(
                    inputs["config_path"]
                ),
                template_market=(
                    inputs[
                        "template_market"
                    ]
                ),
                template_folder=(
                    inputs[
                        "template_folder"
                    ]
                ),
                source_posdata_folder=(
                    inputs[
                        "source_folder"
                    ]
                ),
                store_db_path=(
                    inputs[
                        "store_db_path"
                    ]
                ),
                screen_xml_path=(
                    inputs[
                        "screen_xml_path"
                    ]
                ),
                template_validation=(
                    inputs[
                        "template_validation"
                    ]
                ),
            )

            self.context = (
                run_builder_discovery_phase(
                    self.context
                )
            )

            self.proposal = (
                build_assignment_proposal(
                    self.context
                )
            )

            self.itona_selections = {}
            self._template_itonas_limited = False
            self.user_created_itona_slots.clear()
            self.builder_runtime = None

            country = (
                self.context.market
                or {}
            ).get(
                "country",
                "UNKNOWN",
            )

            self.summary_var.set(
                f"Lab: "
                f"{self.context.selected_lab}\n"
                f"Template: "
                f"{self.context.template_market}\n"
                f"Market: "
                f"{country}"
            )

            self.show_discovery()

        except Exception as error:

            self.status_var.set(
                "Discovery failed"
            )

            messagebox.showerror(
                "Discovery failed",
                str(error),
                parent=self,
            )

    # ==========================================================
    # DISCOVERY
    # ==========================================================

    def show_discovery(self) -> None:

        if self.context is None:
            self.show_setup()
            return

        self._clear_content()
        self._activate_step(
            "2. Discovery"
        )

        discovery = (
            self.context.source_validation
            or {}
        )

        pos_count = len(
            (
                self.context.discovered_pos
                or {}
            ).get(
                "pos_files",
                [],
            )
        )

        itona_count = len(
            self.context
            .discovered_itona_candidates
            or []
        )

        ttk.Label(
            self.content,
            text="Discovery",
            style="Title.TLabel",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            self.content,
            text=(
                "Review the source-market "
                "inventory before editing "
                "assignments."
            ),
            style="Subtitle.TLabel",
        ).pack(
            anchor="w",
            pady=(2, 18),
        )

        card = self._card(
            self.content
        )

        ttk.Label(
            card,
            text="Discovery summary",
            style="CardTitle.TLabel",
        ).pack(
            anchor="w"
        )

        summary_lines = (
            (
                "Status: "
                f"{discovery.get('status', 'UNKNOWN')}"
            ),
            (
                "POS candidates: "
                f"{pos_count}"
            ),
            (
                "Itona candidates: "
                f"{itona_count}"
            ),
            (
                "WAY files: "
                f"{len(discovery.get('way_files') or [])}"
            ),
            (
                "Production files: "
                f"{len(discovery.get('production_files') or [])}"
            ),
        )

        for line in summary_lines:

            ttk.Label(
                card,
                text=line,
                style="CardText.TLabel",
            ).pack(
                anchor="w",
                pady=2,
            )

        actions = ttk.Frame(
            self.content
        )

        actions.pack(
            fill="x",
            pady=8,
        )

        ttk.Button(
            actions,
            text="Back",
            command=self.show_setup,
        ).pack(
            side="left"
        )

        ttk.Button(
            actions,
            text="Continue to POS Mapping",
            style="Accent.TButton",
            command=self.show_pos_mapping,
        ).pack(
            side="right"
        )

        self.status_var.set(
            "Discovery: "
            f"{discovery.get('status', 'UNKNOWN')}"
        )

    # ==========================================================
    # POS MAPPING
    # ==========================================================

    def show_pos_mapping(self) -> None:

        if (
            self.context is None
            or not self.proposal
        ):
            self.show_setup()
            return

        self._clear_content()
        self._activate_step(
            "3. POS Mapping"
        )

        self.slot_vars.clear()
        self.extra_vars.clear()

        ttk.Label(
            self.content,
            text="POS Mapping",
            style="Title.TLabel",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            self.content,
            text=(
                "Any discovered POS can be placed "
                "in any laboratory POS slot. "
                "The source role becomes the "
                "effective role."
            ),
            style="Subtitle.TLabel",
        ).pack(
            anchor="w",
            pady=(2, 18),
        )

        inner = self._scrollable_content()

        card = self._card(
            inner
        )

        headers = (
            "Target",
            "Lab suggestion",
            "Source market file",
            "Effective role",
        )

        for column, header in enumerate(
            headers
        ):

            ttk.Label(
                card,
                text=header,
                style="CardTitle.TLabel",
            ).grid(
                row=0,
                column=column,
                sticky="w",
                padx=6,
                pady=(0, 10),
            )

        options = available_pos_options(
            self.context.discovered_pos
            or {}
        )

        source_index = {
            item.get("file"): item
            for item in (
                self.context.discovered_pos
                or {}
            ).get(
                "pos_files",
                [],
            )
        }

        assignments = (
            self.proposal["pos"]
            .get(
                "assignments",
                [],
            )
        )

        for row, assignment in enumerate(
            assignments,
            start=1,
        ):

            target = str(
                assignment.get(
                    "target_node"
                )
            )

            suggested = str(
                assignment.get(
                    "target_role"
                )
            )

            current = (
                assignment.get(
                    "source_file"
                )
                or NONE_VALUE
            )

            var = tk.StringVar(
                value=(
                    current
                    if current in options
                    else NONE_VALUE
                )
            )

            role_var = tk.StringVar()

            self.slot_vars[
                target
            ] = var

            def refresh_role(
                *_args,
                selected_var=var,
                output_var=role_var,
            ) -> None:

                source = source_index.get(
                    selected_var.get(),
                    {},
                )

                output_var.set(
                    source.get("role")
                    or "NONE"
                )

            var.trace_add(
                "write",
                refresh_role,
            )

            refresh_role()

            ttk.Label(
                card,
                text=target,
                style="CardText.TLabel",
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=6,
                pady=6,
            )

            ttk.Label(
                card,
                text=suggested,
                style="CardText.TLabel",
            ).grid(
                row=row,
                column=1,
                sticky="w",
                padx=6,
                pady=6,
            )

            ttk.Combobox(
                card,
                textvariable=var,
                values=options,
                state="readonly",
                width=42,
            ).grid(
                row=row,
                column=2,
                sticky="ew",
                padx=6,
                pady=6,
            )

            ttk.Label(
                card,
                textvariable=role_var,
                style="Effective.TLabel",
            ).grid(
                row=row,
                column=3,
                sticky="w",
                padx=6,
                pady=6,
            )

        card.columnconfigure(
            2,
            weight=1,
        )

        selected_files = {

            value.get()

            for value in self.slot_vars.values()

            if (
                value.get()
                and value.get() != "NONE"
            )
        }

        #
        # Original extras
        #
        extras = (
            self.proposal["pos"]
            .get(
                "extra_candidates",
                [],
            )
        )

        #
        # Files already selected
        #
        selected_files = {

            value.get()

            for value in self.slot_vars.values()

            if (
                value.get()
                and value.get() != "NONE"
            )
        }

        #
        # Keep only unassigned files
        #
        extras = [

            extra

            for extra in extras

            if (
                extra.get("file")
                not in selected_files
            )
        ]        
        if extras:

            extra_card = self._card(
                inner
            )

            ttk.Label(
                extra_card,
                text=(
                    "Unassigned POS candidates"
                ),
                style="CardTitle.TLabel",
            ).grid(
                row=0,
                column=0,
                columnspan=3,
                sticky="w",
                pady=(0, 10),
            )

            for row, extra in enumerate(
                extras,
                start=1,
            ):

                file_name = str(
                    extra.get("file")
                )

                var = tk.StringVar(
                    value="PENDING"
                )

                self.extra_vars[
                    file_name
                ] = var

                ttk.Label(
                    extra_card,
                    text=file_name,
                    style="CardText.TLabel",
                ).grid(
                    row=row,
                    column=0,
                    sticky="w",
                    padx=6,
                    pady=6,
                )

                ttk.Label(
                    extra_card,
                    text=(
                        "Role: "
                        f"{extra.get('role')}"
                    ),
                    style="CardText.TLabel",
                ).grid(
                    row=row,
                    column=1,
                    sticky="w",
                    padx=6,
                    pady=6,
                )

                ttk.Combobox(
                    extra_card,
                    textvariable=var,
                    values=(
                        "PENDING",
                        "ADD",
                        "IGNORE",
                    ),
                    state="readonly",
                    width=16,
                ).grid(
                    row=row,
                    column=2,
                    padx=6,
                    pady=6,
                )

        actions = ttk.Frame(
            self.content
        )

        actions.pack(
            fill="x",
            pady=8,
        )

        ttk.Button(
            actions,
            text="Back",
            command=self.show_discovery,
        ).pack(
            side="left"
        )

        ttk.Button(
            actions,
            text="Confirm POS Mapping",
            style="Accent.TButton",
            command=self._confirm_pos_mapping,
        ).pack(
            side="right"
        )

        self.status_var.set(
            "Review POS assignments"
        )

    def _confirm_pos_mapping(
        self,
    ) -> None:

        if self.context is None:
            return

        selections = {
            target: var.get()
            for target, var
            in self.slot_vars.items()
        }

        decisions = {
            file_name: var.get()
            for file_name, var
            in self.extra_vars.items()
        }

        selected_files = set(
            selections.values()
        )

        for file_name in decisions:

            if (
                file_name
                in selected_files
            ):
                decisions[
                    file_name
                ] = "IGNORE"

        result = confirm_pos_assignments(
            self.context,
            selections,
            decisions,
        )

        if result["errors"]:

            messagebox.showerror(
                "POS Mapping requires correction",
                "\n".join(
                    result["errors"]
                ),
                parent=self,
            )

            self.status_var.set(
                "POS Mapping: correction required"
            )

            return

        messagebox.showinfo(
            "POS Mapping confirmed",
            (
                f"Status: "
                f"{result['status']}\n"
                f"Assignments: "
                f"{len(result['assignments'])}"
            ),
            parent=self,
        )

        self.show_itona_mapping()

    # ==========================================================
    # ITONA MAPPING
    # ==========================================================

    def _itona_slot_number(
        self,
        slot,
    ) -> int:

        match = re.search(
            r"ITONA[\s_.-]*(\d+)",
            str(slot or ""),
            re.IGNORECASE,
        )

        if not match:
            return 10**9

        return int(
            match.group(1)
        )

    def _is_user_created_itona(
        self,
        assignment,
    ) -> bool:

        slot = str(
            assignment.get("slot")
            or ""
        )

        return bool(
            assignment.get(
                "user_created"
            )
            or slot
            in self.user_created_itona_slots
        )

    def _next_itona_slot_name(
        self,
    ) -> str:

        assignments = (
            self.proposal
            .setdefault(
                "itonas",
                {},
            )
            .setdefault(
                "assignments",
                [],
            )
        )

        numbers = [
            self._itona_slot_number(
                item.get("slot")
            )
            for item in assignments
        ]

        valid_numbers = [
            number
            for number in numbers
            if number < 10**9
        ]

        next_number = (
            max(
                valid_numbers,
                default=0,
            )
            + 1
        )

        return (
            f"Itona{next_number}"
        )

    def _add_itona_slot(
        self,
    ) -> None:

        if self.context is None:
            return

        slot = (
            self._next_itona_slot_name()
        )

        assignment = {
            "slot_index": (
                self._itona_slot_number(
                    slot
                )
            ),
            "slot": slot,
            "template_file": None,
            "template_path": None,
            "source_file": None,
            "source_path": None,
            "source_files": [],
            "source_paths": [],
            "source_types": [],
            "kvs_services": [],
            "selection_reason": (
                "user created an "
                "additional Itona slot"
            ),
            "selection_mode": "MANUAL",
            "status": "NEW",
            "requires_user_decision": True,
            "user_created": True,
            "warnings": [],
            "errors": [],
        }

        (
            self.proposal
            .setdefault(
                "itonas",
                {},
            )
            .setdefault(
                "assignments",
                [],
            )
            .append(
                assignment
            )
        )

        self.user_created_itona_slots.add(
            slot
        )

        self.itona_selections[
            slot
        ] = []

        self.status_var.set(
            f"{slot} included. "
            "Select up to 2 KVS files."
        )

        self.show_itona_mapping()

    def _remove_itona_slot(
        self,
        slot: str,
    ) -> None:

        assignments = (
            self.proposal
            .setdefault(
                "itonas",
                {},
            )
            .setdefault(
                "assignments",
                [],
            )
        )

        assignment = next(
            (
                item
                for item in assignments
                if str(
                    item.get("slot")
                    or ""
                ) == slot
            ),
            None,
        )

        if assignment is None:
            return

        if not self._is_user_created_itona(
            assignment
        ):

            messagebox.showwarning(
                "Template Itona",
                (
                    f"{slot} belongs to "
                    "the selected template "
                    "and cannot be removed."
                ),
                parent=self,
            )

            return

        confirmed = (
            messagebox.askyesno(
                "Remove Itona",
                (
                    f"Remove {slot} and "
                    "clear its selected "
                    "KVS files?"
                ),
                parent=self,
            )
        )

        if not confirmed:
            return

        self.proposal[
            "itonas"
        ][
            "assignments"
        ] = [
            item
            for item in assignments
            if str(
                item.get("slot")
                or ""
            ) != slot
        ]

        self.itona_selections.pop(
            slot,
            None,
        )

        self.itona_summary_vars.pop(
            slot,
            None,
        )

        self.user_created_itona_slots.discard(
            slot
        )

        self.status_var.set(
            f"{slot} removed."
        )

        self.show_itona_mapping()

    def show_itona_mapping(
        self,
    ) -> None:

        if (
            self.context is None
            or not self.proposal
        ):
            self.show_setup()
            return

        self._clear_content()
        self._activate_step(
            "4. Itona Mapping"
        )

        itona_proposal = (
            self.proposal
            .setdefault(
                "itonas",
                {},
            )
        )

        assignments = (
            itona_proposal
            .setdefault(
                "assignments",
                [],
            )
        )

        #
        # Template baseline
        #
        # The Builder starts with at most
        # the first 5 template Itonas.
        #
        # Additional slots must be added
        # explicitly by the user.
        #
        if not getattr(
            self,
            "_template_itonas_limited",
            False,
        ):

            template_slots = sorted(
                assignments,
                key=lambda item: (
                    self._itona_slot_number(
                        item.get("slot")
                    )
                )
            )

            if len(template_slots) > 5:

                assignments[:] = (
                    template_slots[:5]
                )

                #
                # Remove selections of hidden slots
                #
                for item in template_slots[5:]:

                    slot = str(
                        item.get("slot")
                        or ""
                    )

                    self.itona_selections.pop(
                        slot,
                        None,
                    )

            self._template_itonas_limited = True

        #
        # First load:
        # keep only first five template slots
        #
        if (
            not self.user_created_itona_slots
            and len(assignments) > 5
        ):

            assignments[:] = sorted(
                assignments,
                key=lambda item: (
                    self._itona_slot_number(
                        item.get("slot")
                    )
                )
            )[:5]
        if not self.itona_selections:

            self.itona_selections = (
                initial_itona_selections(
                    itona_proposal
                )
            )

        for assignment in assignments:

            slot = str(
                assignment.get("slot")
                or ""
            )

            if slot:

                self.itona_selections.setdefault(
                    slot,
                    [],
                )

        self.itona_summary_vars.clear()

        title_row = ttk.Frame(
            self.content
        )

        title_row.pack(
            fill="x"
        )

        title_group = ttk.Frame(
            title_row
        )

        title_group.pack(
            side="left",
            fill="x",
            expand=True,
        )

        ttk.Label(
            title_group,
            text="Itona Mapping",
            style="Title.TLabel",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            title_group,
            text=(
                f"Select up to "
                f"{MAX_KVS_PER_ITONA} "
                "KVS files per Itona."
            ),
            style="Subtitle.TLabel",
        ).pack(
            anchor="w",
            pady=(2, 18),
        )

        ttk.Button(
            title_row,
            text="+ Include New Itona",
            style="Accent.TButton",
            command=self._add_itona_slot,
        ).pack(
            side="right",
            anchor="n",
            padx=(12, 0),
            pady=(4, 0),
        )

        inner = self._scrollable_content()

        card = self._card(
            inner
        )

        headers = (
            "Itona",
            "Selected KVS files",
            "KVS count",
            "Actions",
        )

        for column, header in enumerate(
            headers
        ):

            ttk.Label(
                card,
                text=header,
                style="CardTitle.TLabel",
            ).grid(
                row=0,
                column=column,
                sticky="w",
                padx=6,
                pady=(0, 10),
            )

        sorted_assignments = sorted(
            assignments,
            key=lambda item: (
                self._itona_slot_number(
                    item.get("slot")
                )
            ),
        )

        for row, assignment in enumerate(
            sorted_assignments,
            start=1,
        ):

            slot = str(
                assignment.get("slot")
                or ""
            )

            if not slot:
                continue

            selected = (
                self.itona_selections
                .get(
                    slot,
                    [],
                )
            )

            summary_var = tk.StringVar(
                value=(
                    "\n".join(
                        selected
                    )
                    if selected
                    else "NONE"
                )
            )

            self.itona_summary_vars[
                slot
            ] = summary_var

            ttk.Label(
                card,
                text=slot,
                style="CardText.TLabel",
            ).grid(
                row=row,
                column=0,
                sticky="nw",
                padx=6,
                pady=8,
            )

            ttk.Label(
                card,
                textvariable=summary_var,
                style="CardText.TLabel",
                wraplength=470,
                justify="left",
            ).grid(
                row=row,
                column=1,
                sticky="nw",
                padx=6,
                pady=8,
            )

            ttk.Label(
                card,
                text=(
                    f"{len(selected)} / "
                    f"{MAX_KVS_PER_ITONA}"
                ),
                style="CardText.TLabel",
            ).grid(
                row=row,
                column=2,
                sticky="nw",
                padx=6,
                pady=8,
            )

            action_frame = ttk.Frame(
                card,
                style="Card.TFrame",
            )

            action_frame.grid(
                row=row,
                column=3,
                sticky="ne",
                padx=6,
                pady=8,
            )

            ttk.Button(
                action_frame,
                text="Select KVS...",
                command=(
                    lambda value=slot:
                    self._open_itona_selector(
                        value
                    )
                ),
            ).pack(
                side="left"
            )

            if self._is_user_created_itona(
                assignment
            ):

                ttk.Button(
                    action_frame,
                    text="Remove",
                    command=(
                        lambda value=slot:
                        self._remove_itona_slot(
                            value
                        )
                    ),
                ).pack(
                    side="left",
                    padx=(8, 0),
                )

        card.columnconfigure(
            1,
            weight=1,
        )

        actions = ttk.Frame(
            self.content
        )

        actions.pack(
            fill="x",
            pady=8,
        )

        ttk.Button(
            actions,
            text="Back",
            command=self.show_pos_mapping,
        ).pack(
            side="left"
        )

        ttk.Button(
            actions,
            text="Confirm Itona Mapping",
            style="Accent.TButton",
            command=(
                self._confirm_itona_mapping
            ),
        ).pack(
            side="right"
        )

        self.status_var.set(
            "Review Itona assignments: "
            f"{len(assignments)} slot(s)"
        )

    def _open_itona_selector(
        self,
        slot: str,
    ) -> None:

        if self.context is None:
            return

        candidate_index = (
            build_itona_candidate_index(
                self.context
                .discovered_itona_candidates
                or []
            )
        )

        window = tk.Toplevel(
            self
        )

        window.title(
            f"Select KVS for {slot}"
        )

        window.geometry(
            "800x540"
        )

        window.minsize(
            680,
            440,
        )

        window.transient(
            self
        )

        window.grab_set()

        ttk.Label(
            window,
            text=(
                f"Select KVS for {slot}"
            ),
            style="Title.TLabel",
        ).pack(
            anchor="w",
            padx=18,
            pady=(18, 4),
        )

        counter_var = tk.StringVar()

        ttk.Label(
            window,
            textvariable=counter_var,
            style="Subtitle.TLabel",
        ).pack(
            anchor="w",
            padx=18,
            pady=(0, 10),
        )

        frame = ttk.Frame(
            window,
            padding=(
                18,
                0,
                18,
                0,
            ),
        )

        frame.pack(
            fill="both",
            expand=True,
        )

        listbox = tk.Listbox(
            frame,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            font=(
                "Consolas",
                10,
            ),
        )

        scroll = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=listbox.yview,
        )

        listbox.configure(
            yscrollcommand=scroll.set
        )

        listbox.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scroll.pack(
            side="right",
            fill="y",
        )

        display_to_file: list[
            str
        ] = []

        for file_name, candidate in sorted(
            candidate_index.items()
        ):

            listbox.insert(
                tk.END,
                itona_candidate_display(
                    candidate
                ),
            )

            display_to_file.append(
                file_name
            )

        current = set(
            self.itona_selections.get(
                slot,
                [],
            )
        )

        for index, file_name in enumerate(
            display_to_file
        ):

            if file_name in current:

                listbox.selection_set(
                    index
                )

        def update_counter(
            _event=None,
        ) -> None:

            count = len(
                listbox.curselection()
            )

            counter_var.set(
                f"Selected: "
                f"{count} / "
                f"{MAX_KVS_PER_ITONA}. "
                "Use Ctrl or Shift "
                "for multiple selection."
            )

        listbox.bind(
            "<<ListboxSelect>>",
            update_counter,
        )

        update_counter()

        def apply_selection() -> None:

            selected = [
                display_to_file[index]
                for index
                in listbox.curselection()
            ]

            if (
                len(selected)
                > MAX_KVS_PER_ITONA
            ):

                messagebox.showerror(
                    "Too many KVS selected",
                    (
                        f"{slot} supports "
                        f"a maximum of "
                        f"{MAX_KVS_PER_ITONA} "
                        "KVS files."
                    ),
                    parent=window,
                )

                return

            conflicts = []

            for (
                other_slot,
                files,
            ) in (
                self.itona_selections
                .items()
            ):

                if other_slot == slot:
                    continue

                for file_name in selected:

                    if file_name in files:

                        conflicts.append(
                            f"{file_name} "
                            "is already selected "
                            f"in {other_slot}."
                        )

            if conflicts:

                messagebox.showerror(
                    "KVS already assigned",
                    "\n".join(
                        conflicts
                    ),
                    parent=window,
                )

                return

            self.itona_selections[
                slot
            ] = selected

            window.destroy()
            self.show_itona_mapping()

        def clear_selection() -> None:

            listbox.selection_clear(
                0,
                tk.END,
            )

            update_counter()

        buttons = ttk.Frame(
            window,
            padding=18,
        )

        buttons.pack(
            fill="x"
        )

        ttk.Button(
            buttons,
            text="Clear Selection",
            command=clear_selection,
        ).pack(
            side="left"
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=window.destroy,
        ).pack(
            side="right",
            padx=(8, 0),
        )

        ttk.Button(
            buttons,
            text="Apply Selection",
            style="Accent.TButton",
            command=apply_selection,
        ).pack(
            side="right"
        )

    def _confirm_itona_mapping(
        self,
    ) -> None:

        if self.context is None:
            return

        assignments = (
            self.proposal
            .setdefault(
                "itonas",
                {},
            )
            .setdefault(
                "assignments",
                [],
            )
        )

        for assignment in assignments:

            slot = str(
                assignment.get("slot")
                or ""
            )

            if slot:

                self.itona_selections.setdefault(
                    slot,
                    [],
                )

        result = (
            confirm_itona_assignments(
                self.context,
                self.itona_selections,
            )
        )

        if result["errors"]:

            messagebox.showerror(
                (
                    "Itona Mapping "
                    "requires correction"
                ),
                "\n".join(
                    result["errors"]
                ),
                parent=self,
            )

            self.status_var.set(
                "Itona Mapping: "
                "correction required"
            )

            return

        messagebox.showinfo(
            "Itona Mapping confirmed",
            (
                f"Status: "
                f"{result['status']}\n"
                f"Itonas: "
                f"{len(result['assignments'])}\n"
                f"Unassigned KVS: "
                f"{len(result['extra_candidates'])}"
            ),
            parent=self,
        )

        self.show_review()

    # ==========================================================
    # REVIEW
    # ==========================================================

    def show_review(self) -> None:

        if self.context is None:
            return

        self._clear_content()
        self._activate_step(
            "5. Review"
        )

        ttk.Label(
            self.content,
            text="Build Review",
            style="Title.TLabel",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            self.content,
            text=(
                "Review the confirmed mappings "
                "before validating the generation "
                "contract."
            ),
            style="Subtitle.TLabel",
        ).pack(
            anchor="w",
            pady=(2, 18),
        )


        inner = self._scrollable_content()

        # ------------------------------------------------------
        # POS REVIEW
        # ------------------------------------------------------

        ttk.Label(
            inner,
            text="Confirmed POS Mapping",
            style="Title.TLabel",
        ).pack(
            anchor="w",
            pady=(0, 10),
        )

        pos_assignments = (
            self.context
            .confirmed_pos_mapping
            .get(
                "assignments",
                [],
            )
        )

        for item in pos_assignments:

            source_file = (
                item.get("source_file")
                or "NONE"
            )

            expected = (
                item.get("expected_role")
                or "UNKNOWN"
            )

            effective = (
                item.get("effective_role")
                or "NONE"
            )

            if effective == "NONE":

                display_status = (
                    "SKIPPED"
                )

                status_style = (
                    "Skipped.TLabel"
                )

            elif expected != effective:

                display_status = (
                    "CUSTOMIZED"
                )

                status_style = (
                    "Customized.TLabel"
                )

            else:

                display_status = (
                    "STANDARD"
                )

                status_style = (
                    "Success.TLabel"
                )

            card = self._card(
                inner,
                padding=16,
            )

            ttk.Label(
                card,
                text=item.get(
                    "target_node",
                    "UNKNOWN POS",
                ),
                style="CardTitle.TLabel",
            ).grid(
                row=0,
                column=0,
                columnspan=2,
                sticky="w",
                pady=(0, 12),
            )

            ttk.Label(
                card,
                text="Source",
                style="CardText.TLabel",
            ).grid(
                row=1,
                column=0,
                sticky="nw",
                padx=(0, 20),
                pady=3,
            )

            ttk.Label(
                card,
                text=source_file,
                style="CardText.TLabel",
                wraplength=650,
            ).grid(
                row=1,
                column=1,
                sticky="nw",
                pady=3,
            )

            ttk.Label(
                card,
                text="Lab Suggestion",
                style="CardText.TLabel",
            ).grid(
                row=2,
                column=0,
                sticky="w",
                padx=(0, 20),
                pady=3,
            )

            ttk.Label(
                card,
                text=expected,
                style="CardText.TLabel",
            ).grid(
                row=2,
                column=1,
                sticky="w",
                pady=3,
            )

            ttk.Label(
                card,
                text="Configured As",
                style="CardText.TLabel",
            ).grid(
                row=3,
                column=0,
                sticky="w",
                padx=(0, 20),
                pady=3,
            )

            ttk.Label(
                card,
                text=effective,
                style="Effective.TLabel",
            ).grid(
                row=3,
                column=1,
                sticky="w",
                pady=3,
            )

            ttk.Label(
                card,
                text="Status",
                style="CardText.TLabel",
            ).grid(
                row=4,
                column=0,
                sticky="w",
                padx=(0, 20),
                pady=3,
            )

            ttk.Label(
                card,
                text=display_status,
                style=status_style,
            ).grid(
                row=4,
                column=1,
                sticky="w",
                pady=3,
            )

            card.columnconfigure(
                1,
                weight=1,
            )

        # ------------------------------------------------------
        # ITONA REVIEW
        # ------------------------------------------------------

        ttk.Label(
            inner,
            text="Confirmed Itona Mapping",
            style="Title.TLabel",
        ).pack(
            anchor="w",
            pady=(12, 10),
        )

        itona_assignments = (
            self.context
            .confirmed_itona_mapping
            .get(
                "assignments",
                [],
            )
        )

        for item in itona_assignments:

            sources = (
                item.get("source_files")
                or []
            )

            services = (
                item.get("kvs_services")
                or []
            )

            source_text = (
                "\n".join(
                    sources
                )
                if sources
                else "NONE"
            )

            service_text = (
                "\n".join(
                    str(service)
                    for service in services
                )
                if services
                else "NONE"
            )

            status = item.get(
                "status",
                "UNKNOWN",
            )

            card = self._card(
                inner,
                padding=16,
            )

            ttk.Label(
                card,
                text=item.get(
                    "slot",
                    "UNKNOWN ITONA",
                ),
                style="CardTitle.TLabel",
            ).grid(
                row=0,
                column=0,
                columnspan=2,
                sticky="w",
                pady=(0, 12),
            )

            ttk.Label(
                card,
                text="KVS Count",
                style="CardText.TLabel",
            ).grid(
                row=1,
                column=0,
                sticky="nw",
                padx=(0, 20),
                pady=3,
            )

            ttk.Label(
                card,
                text=(
                    f"{len(sources)} / "
                    f"{MAX_KVS_PER_ITONA}"
                ),
                style="Effective.TLabel",
            ).grid(
                row=1,
                column=1,
                sticky="nw",
                pady=3,
            )

            ttk.Label(
                card,
                text="Sources",
                style="CardText.TLabel",
            ).grid(
                row=2,
                column=0,
                sticky="nw",
                padx=(0, 20),
                pady=3,
            )

            ttk.Label(
                card,
                text=source_text,
                style="CardText.TLabel",
                justify="left",
                wraplength=650,
            ).grid(
                row=2,
                column=1,
                sticky="nw",
                pady=3,
            )

            ttk.Label(
                card,
                text="Services",
                style="CardText.TLabel",
            ).grid(
                row=3,
                column=0,
                sticky="nw",
                padx=(0, 20),
                pady=3,
            )

            ttk.Label(
                card,
                text=service_text,
                style="CardText.TLabel",
                justify="left",
            ).grid(
                row=3,
                column=1,
                sticky="nw",
                pady=3,
            )

            ttk.Label(
                card,
                text="Status",
                style="CardText.TLabel",
            ).grid(
                row=4,
                column=0,
                sticky="nw",
                padx=(0, 20),
                pady=3,
            )

            ttk.Label(
                card,
                text=status,
                style=(
                    "Skipped.TLabel"
                    if status == "SKIPPED"
                    else "Success.TLabel"
                ),
            ).grid(
                row=4,
                column=1,
                sticky="nw",
                pady=3,
            )

            card.columnconfigure(
                1,
                weight=1,
            )

        actions = ttk.Frame(
            self.content
        )

        actions.pack(
            fill="x",
            pady=8,
        )

        ttk.Button(
            actions,
            text="Back",
            command=self.show_itona_mapping,
        ).pack(
            side="left"
        )

        ttk.Button(
            actions,
            text="Validate Generation Contract",
            style="Accent.TButton",
            command=(
                self._validate_generation_contract
            ),
        ).pack(
            side="right"
        )

        self.status_var.set(
            "Mappings confirmed and ready for validation"
        )

        ttk.Button(
            actions,
            text="Generate PosData",
            style="Accent.TButton",
            command=self._generate_posdata,
        ).pack(
            side="right",
            padx=(8, 0)
        )


    # ==========================================================
    # GENERATION CONTRACT
    # ==========================================================

    def _validate_generation_contract(
        self,
    ) -> None:

        if self.context is None:

            messagebox.showerror(
                "Generation Adapter",
                (
                    "Builder context "
                    "is not available."
                ),
                parent=self,
            )

            return

        try:

            runtime = (
                build_builder_runtime_context(
                    builder_context=(
                        self.context
                    ),
                    strict=True,
                )
            )

        except Exception as error:

            self.builder_runtime = None

            messagebox.showerror(
                "Generation Contract Failed",
                str(error),
                parent=self,
            )

            self.status_var.set(
                "Generation contract: FAIL"
            )

            return

        self.builder_runtime = runtime

        pos_mappings = (
            runtime.pos_mapping
            .get(
                "mappings",
                [],
            )
        )

        kvs_mappings = (
            runtime.kvs_mapping
            .get(
                "mappings",
                [],
            )
        )

        ready_pos = sum(
            1
            for mapping in pos_mappings
            if mapping.get("status")
            == "READY"
        )

        skipped_pos = sum(
            1
            for mapping in pos_mappings
            if mapping.get("status")
            == "SKIPPED"
        )

        ready_itonas = sum(
            1
            for mapping in kvs_mappings
            if mapping.get("status")
            == "READY"
        )

        skipped_itonas = sum(
            1
            for mapping in kvs_mappings
            if mapping.get("status")
            == "SKIPPED"
        )

        total_kvs_services = sum(
            len(
                mapping.get(
                    "mapped_services",
                    [],
                )
            )
            for mapping in kvs_mappings
        )

        messagebox.showinfo(
            "Generation Contract Ready",
            (
                f"Status: "
                f"{runtime.builder_adapter_status}\n\n"

                f"POS ready: "
                f"{ready_pos}\n"

                f"POS skipped: "
                f"{skipped_pos}\n\n"

                f"Itonas ready: "
                f"{ready_itonas}\n"

                f"Itonas skipped: "
                f"{skipped_itonas}\n"

                f"KVS services mapped: "
                f"{total_kvs_services}\n\n"

                f"Reference template:\n"
                f"{runtime.current_posdata_folder}\n\n"

                f"Source PosData:\n"
                f"{runtime.new_posdata_folder}"
            ),
            parent=self,
        )

        self.status_var.set(
            "Generation contract: READY"
        )

    def _generate_posdata(
        self,
    ):
        """
        Executes the complete Builder
        generation pipeline.

        Review
            ↓
        Generation Adapter
            ↓
        Generation Phase
            ↓
        Validation Phase
            ↓
        Output Builder
        """

        if self.context is None:

            messagebox.showerror(
                "Builder",
                "No Builder context available."
            )

            return

        try:

            #
            # Make sure the confirmed
            # mappings are persisted
            #
            if not getattr(
                self.context,
                "confirmed_pos_mapping",
                None,
            ):

                messagebox.showerror(
                    "Builder",
                    "POS Mapping has not been confirmed."
                )

                return

            if not getattr(
                self.context,
                "confirmed_itona_mapping",
                None,
            ):

                messagebox.showerror(
                    "Builder",
                    "Itona Mapping has not been confirmed."
                )

                return

            #
            # Status
            #
            self.status_var.set(
                "Generating PosData..."
            )

            self.update_idletasks()

            #
            # Generation
            #
            runtime = (
                run_builder_generation_phase(
                    self.context
                )
            )

            validation_summary = (
                runtime.validation_summary
                or {}
            )

            validation_status = (
                validation_summary.get(
                    "status",
                    "UNKNOWN",
                )
            )

            generated_pos = sum(
                1
                for item in (
                    runtime.generated_pos
                    or []
                )
                if item.get(
                    "generated"
                ) is True
            )

            generated_itonas = sum(
                1
                for item in (
                    runtime.generated_itonas
                    or []
                )
                if item.get(
                    "generated"
                ) is True
            )

            generated_production = sum(
                1
                for item in (
                    runtime.generated_production
                    or []
                )
                if item.get(
                    "generated"
                ) is True
            )

            output_folder = getattr(
                runtime,
                "output_root",
                "output_builder",
            )

            self.status_var.set(
                f"Generation finished ({validation_status})"
            )

            messagebox.showinfo(
                "Builder Generation Complete",
                (
                    f"Validation: "
                    f"{validation_status}\n\n"
                    f"Generated POS: "
                    f"{generated_pos}\n"
                    f"Generated Itonas: "
                    f"{generated_itonas}\n"
                    f"Generated Production: "
                    f"{generated_production}\n\n"
                    f"Output:\n"
                    f"{output_folder}"
                )
            )

            self.runtime = runtime

            self.show_generation_summary()

            #
            # Keep runtime available
            # for future screens
            #
            self.runtime = runtime

        except Exception as error:

            self.status_var.set(
                "Generation failed"
            )

            messagebox.showerror(
                "Generation Error",
                str(error)
            )

    def show_generation_summary(
        self,
    ):
        """
        Final Builder screen.

        Displays the generation results
        and provides access to the
        generated output.
        """

        if not hasattr(
            self,
            "runtime",
        ):
            return

        runtime = self.runtime

        self._clear_content()

        self._activate_step(
            "7. Complete"
        )

        ttk.Label(
            self.content,
            text="Generation Summary",
            style="Title.TLabel",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            self.content,
            text=(
                "PosData generation completed. "
                "Review the generated artifacts "
                "and validation results below."
            ),
            style="Subtitle.TLabel",
        ).pack(
            anchor="w",
            pady=(2, 18),
        )

        #
        # Validation
        #
        validation_status = (
            runtime.validation_summary.get(
                "status",
                "UNKNOWN",
            )
        )

        summary_card = self._card(
            self.content
        )

        ttk.Label(
            summary_card,
            text="Validation",
            style="CardTitle.TLabel",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            summary_card,
            text=f"✅ {validation_status}",
            style="Success.TLabel",
        ).pack(
            anchor="w",
            pady=(6, 0),
        )

        #
        # Generation Counters
        #
        generated_pos = sum(
            1
            for item in (
                runtime.generated_pos
                or []
            )
            if item.get(
                "generated"
            ) is True
        )

        skipped_pos = sum(
            1
            for item in (
                runtime.generated_pos
                or []
            )
            if item.get(
                "generated"
            ) is not True
        )

        generated_itonas = sum(
            1
            for item in (
                runtime.generated_itonas
                or []
            )
            if item.get(
                "generated"
            ) is True
        )

        generated_production = sum(
            1
            for item in (
                runtime.generated_production
                or []
            )
            if item.get(
                "generated"
            ) is True
        )

        stats_card = self._card(
            self.content
        )

        ttk.Label(
            stats_card,
            text="Generated Artifacts",
            style="CardTitle.TLabel",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            stats_card,
            text=(
                f"StoreDB: ✅ Generated\n"
                f"POS: ✅ {generated_pos} generated\n"
                f"POS Skipped: ⚪ {skipped_pos}\n"
                f"Itonas: ✅ {generated_itonas} generated\n"
                f"Production: ✅ {generated_production} generated"
            ),
            style="CardText.TLabel",
            justify="left",
        ).pack(
            anchor="w",
            pady=(6, 0),
        )

        #
        # Output Folder
        #
        output_card = self._card(
            self.content
        )

        ttk.Label(
            output_card,
            text="Output Folder",
            style="CardTitle.TLabel",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            output_card,
            text=runtime.output_root,
            style="CardText.TLabel",
        ).pack(
            anchor="w",
            pady=(6, 10),
        )

        #
        # Actions
        #
        actions = ttk.Frame(
            self.content
        )

        actions.pack(
            fill="x",
            pady=(12, 0),
        )

        ttk.Button(
            actions,
            text="Open Output Folder",
            command=self._open_output_folder,
        ).pack(
            side="left"
        )

        ttk.Button(
            actions,
            text="Back to Review",
            command=self.show_review,
        ).pack(
            side="right"
        )

        self.status_var.set(
            "Generation completed successfully"
        )

    def _open_output_folder(
        self,
    ):
        import os

        if not hasattr(
            self,
            "runtime",
        ):
            return

        try:

            os.startfile(
                self.runtime.output_root
            )

        except Exception as error:

            messagebox.showerror(
                "Output Folder",
                str(error)
            )



if __name__ == "__main__":

    PosDataBuilderApp().mainloop()