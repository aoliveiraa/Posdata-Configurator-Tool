# PATCH FOR app_ui.py
# Add this import with the other imports:
import threading

# Add this method inside PosDataConfiguratorUI:

def request_kvs_selection(
    self,
    machine,
    expected_service,
    candidates,
):
    """Open a modal KVS selection dialog on the Tk main thread."""
    completed = threading.Event()
    result = {"candidate": None}

    def show_dialog():
        dialog = tk.Toplevel(self.root)
        dialog.title("KVS Resolution Required")
        dialog.configure(bg=self.BG)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        tk.Label(
            dialog,
            text="KVS Resolution Required",
            bg=self.BG,
            fg=self.TEXT,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=22, pady=(20, 4))

        tk.Label(
            dialog,
            text=(
                f"Machine: {machine}\n"
                f"Expected service: KVS{expected_service}"
            ),
            bg=self.BG,
            fg=self.MUTED,
            justify="left",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=22, pady=(0, 14))

        list_frame = tk.Frame(dialog, bg=self.PANEL)
        list_frame.pack(fill="both", expand=True, padx=22, pady=(0, 14))

        listbox = tk.Listbox(
            list_frame,
            width=76,
            height=min(18, max(6, len(candidates))),
            bg=self.ENTRY,
            fg=self.TEXT,
            selectbackground=self.PRIMARY,
            selectforeground=self.TEXT,
            relief="flat",
            font=("Consolas", 10),
            exportselection=False,
        )
        listbox.pack(fill="both", expand=True, padx=10, pady=10)

        for candidate in candidates:
            state = (
                "ACTIVE"
                if candidate.get("startonload", False)
                else "INACTIVE"
            )
            source_file = candidate.get("source_file") or "UNKNOWN FILE"
            listbox.insert(
                tk.END,
                f"KVS{candidate['service']} | {source_file} | {state}",
            )

        if candidates:
            listbox.selection_set(0)
            listbox.activate(0)

        button_frame = tk.Frame(dialog, bg=self.BG)
        button_frame.pack(fill="x", padx=22, pady=(0, 20))

        def finish(candidate=None):
            result["candidate"] = candidate
            dialog.grab_release()
            dialog.destroy()
            completed.set()

        def confirm():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning(
                    "KVS Resolution",
                    "Select a KVS candidate before continuing.",
                    parent=dialog,
                )
                return
            finish(candidates[selection[0]])

        tk.Button(
            button_frame,
            text="Cancel",
            command=lambda: finish(None),
            bg=self.PANEL_ALT,
            fg=self.TEXT,
            relief="flat",
            padx=18,
            pady=8,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            button_frame,
            text="Use Selected KVS",
            command=confirm,
            bg=self.PRIMARY,
            fg=self.TEXT,
            relief="flat",
            padx=18,
            pady=8,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

        dialog.protocol("WM_DELETE_WINDOW", lambda: finish(None))
        dialog.update_idletasks()

        x = self.root.winfo_rootx() + (
            self.root.winfo_width() - dialog.winfo_width()
        ) // 2
        y = self.root.winfo_rooty() + (
            self.root.winfo_height() - dialog.winfo_height()
        ) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    self.root.after(0, show_dialog)
    completed.wait()
    return result["candidate"]

# In execute_backend(), pass the callback to main():

runtime = main(
    selected_lab=self.execution_options["selected_lab"],
    current_posdata_folder=self.execution_options["current_posdata_folder"],
    new_posdata_folder=self.execution_options["new_posdata_folder"],
    kvs_selection_function=self.request_kvs_selection,
)
