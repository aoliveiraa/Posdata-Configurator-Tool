from pathlib import Path
import re

path = Path('app_ui.py')
if not path.exists():
    raise SystemExit('app_ui.py not found in the current folder.')

source = path.read_text(encoding='utf-8')
backup = path.with_suffix('.py.before_discovery_filters')
backup.write_text(source, encoding='utf-8')

# State required by filtering.
needle = '        self.execution_options = {}\n'
addition = '''        self.execution_options = {}\n        self.discovery_pos_items = []\n        self.discovery_kvs_items = []\n        self.pos_search_var = tk.StringVar()\n        self.pos_role_filter_var = tk.StringVar(value="ALL")\n        self.kvs_search_var = tk.StringVar()\n        self.kvs_status_filter_var = tk.StringVar(value="ALL")\n'''
if 'self.discovery_pos_items = []' not in source:
    if needle not in source:
        raise SystemExit('Could not find execution_options in __init__.')
    source = source.replace(needle, addition, 1)

build_start = source.find('    def build_discovery_view(self):')
build_end = source.find('    def build_text_view(', build_start)
if build_start < 0 or build_end < 0:
    raise SystemExit('Could not locate build_discovery_view().')

build_code = r'''    def build_discovery_view(self):
        frame, body = self.page_shell(
            "Discovery",
            "Search and filter POS sources, KVS services and target mappings.",
        )
        body.grid_rowconfigure(0, weight=0)
        body.grid_rowconfigure(1, weight=0)
        body.grid_rowconfigure(2, weight=1)
        body.grid_columnconfigure(0, weight=1)

        summary = tk.Frame(body, bg=self.PANEL)
        summary.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        self.discovery_page_values = {}
        for column, (key, title, color) in enumerate((
            ("POS", "POS Sources", self.INFO),
            ("KVS", "KVS Services", self.SUCCESS),
            ("ITONAS", "Active Itonas", "#b886ff"),
            ("WAY", "WAY Files", self.WARNING),
            ("PRODUCTION", "Production", "#40d5d9"),
        )):
            summary.grid_columnconfigure(column, weight=1, uniform="discovery")
            card = tk.Frame(summary, bg=self.PANEL_ALT,
                            highlightbackground=color, highlightthickness=1)
            card.grid(row=0, column=column, sticky="nsew", padx=5)
            value = tk.Label(card, text="-", bg=self.PANEL_ALT, fg=color,
                             font=("Segoe UI", 20, "bold"))
            value.pack(pady=(12, 1))
            tk.Label(card, text=title, bg=self.PANEL_ALT, fg=self.MUTED,
                     font=("Segoe UI", 9)).pack(pady=(0, 12))
            self.discovery_page_values[key] = value

        filters = tk.Frame(body, bg=self.PANEL_ALT,
                           highlightbackground=self.BORDER, highlightthickness=1)
        filters.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        filters.grid_columnconfigure(1, weight=1)
        filters.grid_columnconfigure(5, weight=1)

        tk.Label(filters, text="POS", bg=self.PANEL_ALT, fg=self.INFO,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=(12, 6), pady=10)
        pos_search = tk.Entry(filters, textvariable=self.pos_search_var,
                              bg=self.ENTRY, fg=self.TEXT, insertbackground=self.TEXT,
                              relief="flat", font=("Segoe UI", 9))
        pos_search.grid(row=0, column=1, sticky="ew", ipady=7)
        pos_search.bind('<KeyRelease>', self.apply_discovery_filters)
        tk.OptionMenu(filters, self.pos_role_filter_var, "ALL", "FC", "DT",
                      command=lambda _value: self.apply_discovery_filters()).grid(
                          row=0, column=2, padx=6)
        tk.Button(filters, text="Clear POS", command=self.clear_pos_filters,
                  bg="#0d3765", fg=self.TEXT, relief="flat", cursor="hand2",
                  padx=10, pady=7).grid(row=0, column=3, padx=(0, 14))

        tk.Label(filters, text="KVS", bg=self.PANEL_ALT, fg=self.SUCCESS,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=4, padx=(12, 6))
        kvs_search = tk.Entry(filters, textvariable=self.kvs_search_var,
                              bg=self.ENTRY, fg=self.TEXT, insertbackground=self.TEXT,
                              relief="flat", font=("Segoe UI", 9))
        kvs_search.grid(row=0, column=5, sticky="ew", ipady=7)
        kvs_search.bind('<KeyRelease>', self.apply_discovery_filters)
        tk.OptionMenu(filters, self.kvs_status_filter_var, "ALL", "MAPPED", "UNUSED",
                      command=lambda _value: self.apply_discovery_filters()).grid(
                          row=0, column=6, padx=6)
        tk.Button(filters, text="Clear KVS", command=self.clear_kvs_filters,
                  bg="#0d3765", fg=self.TEXT, relief="flat", cursor="hand2",
                  padx=10, pady=7).grid(row=0, column=7, padx=(0, 12))

        self.discovery_filter_count = tk.Label(
            filters, text="Run configuration to load data", bg=self.PANEL_ALT,
            fg=self.MUTED, font=("Segoe UI", 8)
        )
        self.discovery_filter_count.grid(row=1, column=0, columnspan=8,
                                         sticky="w", padx=12, pady=(0, 8))

        details = tk.Frame(body, bg=self.PANEL)
        details.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        for column in range(3):
            details.grid_columnconfigure(column, weight=1, uniform="details")
        details.grid_rowconfigure(0, weight=1)
        self.discovery_pos_text = self.build_discovery_detail_panel(
            details, 0, "POS Sources", "Filter by file, role, node or status"
        )
        self.discovery_kvs_text = self.build_discovery_detail_panel(
            details, 1, "KVS Services", "Filter by ID, Itona, source or usage"
        )
        self.discovery_mapping_text = self.build_discovery_detail_panel(
            details, 2, "Target Mapping", "Target node and selected source"
        )
        return frame

    def build_discovery_detail_panel(self, parent, column, title, subtitle):
        panel = tk.Frame(parent, bg=self.PANEL_ALT,
                         highlightbackground=self.BORDER, highlightthickness=1)
        panel.grid(row=0, column=column, sticky="nsew",
                   padx=(0 if column == 0 else 6, 0))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)
        tk.Label(panel, text=title, bg=self.PANEL_ALT, fg=self.TEXT,
                 font=("Segoe UI", 11, "bold")).grid(
                     row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        tk.Label(panel, text=subtitle, bg=self.PANEL_ALT, fg=self.MUTED,
                 font=("Segoe UI", 8)).grid(
                     row=1, column=0, sticky="w", padx=14, pady=(0, 8))
        widget = scrolledtext.ScrolledText(
            panel, bg="#08111c", fg="#b9c8d8", insertbackground=self.TEXT,
            relief="flat", bd=0, font=("Consolas", 9), wrap=tk.WORD,
            padx=10, pady=10,
        )
        widget.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        widget.insert(tk.END, "Run the configuration to load discovery data.\n")
        widget.configure(state=tk.DISABLED)
        return widget

'''
source = source[:build_start] + build_code + source[build_end:]

update_start = source.find('    def update_discovery_page(')
update_end = source.find('    def update_readiness_', update_start)
if update_start < 0 or update_end < 0:
    raise SystemExit('Could not locate update_discovery_page().')

filter_code = r'''    def update_discovery_page(self, runtime, mapped_kvs, unused_kvs):
        discovery = getattr(runtime, "dynamic_pos_discovery", {}) or {}
        self.discovery_pos_items = list(discovery.get("pos_files", []))

        self.discovery_kvs_items = []
        for service_id, (machine, service) in mapped_kvs.items():
            self.discovery_kvs_items.append({
                "service_id": str(service_id),
                "machine": str(machine),
                "source": service.get("source_file") or service.get("file") or "",
                "usage": "MAPPED",
            })
        for service_id, service in unused_kvs.items():
            self.discovery_kvs_items.append({
                "service_id": str(service_id),
                "machine": "",
                "source": service.get("source_file") or service.get("file") or "",
                "usage": "UNUSED",
            })

        mapping_result = getattr(runtime, "dynamic_pos_mapping", {}) or {}
        mapping_lines = []
        for item in mapping_result.get("mappings", []):
            target = item.get("target_node", "UNKNOWN")
            role = item.get("target_role") or item.get("role") or "UNKNOWN"
            source_file = item.get("source_file") or "No source"
            selection = item.get("selection_reason") or item.get("selection") or ""
            status = item.get("status", "UNKNOWN")
            text = f"{target} [{role}]\n  Source: {source_file}\n"
            if selection:
                text += f"  Selection: {selection}\n"
            mapping_lines.append(text + f"  Status: {status}\n")
        self.set_readonly_text(
            self.discovery_mapping_text,
            "\n".join(mapping_lines) if mapping_lines else "No target mappings were created.\n",
        )
        self.apply_discovery_filters()

    def apply_discovery_filters(self, _event=None):
        pos_query = self.pos_search_var.get().strip().lower()
        role_filter = self.pos_role_filter_var.get().upper()
        filtered_pos = []
        for item in self.discovery_pos_items:
            file_name = item.get("file") or item.get("file_name") or item.get("source_file") or "UNKNOWN"
            role = str(item.get("role", "UNKNOWN")).upper()
            nodes = item.get("node_candidates", []) or []
            status = item.get("role_status") or item.get("status") or "UNKNOWN"
            searchable = " ".join((file_name, role, " ".join(map(str, nodes)), str(status))).lower()
            if role_filter != "ALL" and role != role_filter:
                continue
            if pos_query and pos_query not in searchable:
                continue
            filtered_pos.append(item)

        kvs_query = self.kvs_search_var.get().strip().lower()
        usage_filter = self.kvs_status_filter_var.get().upper()
        filtered_kvs = []
        for item in self.discovery_kvs_items:
            searchable = " ".join((item["service_id"], item["machine"], item["source"], item["usage"])).lower()
            if usage_filter != "ALL" and item["usage"] != usage_filter:
                continue
            if kvs_query and kvs_query not in searchable:
                continue
            filtered_kvs.append(item)

        pos_lines = []
        for item in filtered_pos:
            file_name = item.get("file") or item.get("file_name") or item.get("source_file") or "UNKNOWN"
            role = item.get("role", "UNKNOWN")
            nodes = item.get("node_candidates", []) or []
            status = item.get("role_status") or item.get("status") or "UNKNOWN"
            pos_lines.append(
                f"{file_name}\n  Role: {role}\n  Nodes: {', '.join(map(str, nodes)) or 'No node'}\n  Status: {status}\n"
            )

        kvs_lines = []
        for item in sorted(filtered_kvs, key=lambda value: value["service_id"]):
            line = f"KVS{item['service_id']} [{item['usage']}]"
            if item["machine"]:
                line += f"  ->  {item['machine']}"
            if item["source"]:
                line += f"\n  {item['source']}"
            kvs_lines.append(line + "\n")

        self.set_readonly_text(
            self.discovery_pos_text,
            "\n".join(pos_lines) if pos_lines else "No POS sources match the current filters.\n",
        )
        self.set_readonly_text(
            self.discovery_kvs_text,
            "\n".join(kvs_lines) if kvs_lines else "No KVS services match the current filters.\n",
        )
        self.discovery_filter_count.configure(
            text=(
                f"POS: {len(filtered_pos)}/{len(self.discovery_pos_items)}  |  "
                f"KVS: {len(filtered_kvs)}/{len(self.discovery_kvs_items)}"
            )
        )

    def clear_pos_filters(self):
        self.pos_search_var.set("")
        self.pos_role_filter_var.set("ALL")
        self.apply_discovery_filters()

    def clear_kvs_filters(self):
        self.kvs_search_var.set("")
        self.kvs_status_filter_var.set("ALL")
        self.apply_discovery_filters()

'''
source = source[:update_start] + filter_code + source[update_end:]

compile(source, str(path), 'exec')
path.write_text(source, encoding='utf-8')
print(f'Updated: {path}')
print(f'Backup: {backup}')
