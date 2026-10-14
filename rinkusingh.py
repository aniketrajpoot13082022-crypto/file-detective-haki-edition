import csv
import hashlib
import os
import queue
import threading
import tkinter as tk
from collections import defaultdict
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "File Detective | Haki Edition"
CHUNK_SIZE = 1024 * 1024  # Read files in 1 MB chunks
BG = "#08090D"
PANEL = "#11131B"
PANEL_LIGHT = "#191C27"
RED = "#E11D3F"
RED_DARK = "#7F1025"
TEXT = "#F4F4F6"
MUTED = "#A5A8B5"


def calculate_hash(file_path):
    """Return a SHA-256 fingerprint of a file's contents."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def format_size(size):
    """Convert bytes into a human-readable size."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def scan_for_duplicates(folder, events):
    """Find duplicate files by size and SHA-256 hash."""
    candidates = defaultdict(list)
    walk_errors = []
    files_seen = 0
    files_hashed = 0
    skipped_files = 0

    def record_walk_error(error):
        walk_errors.append(error)

    # Pass 1: collect readable files, grouping them by size.
    for current_folder, subfolders, filenames in os.walk(
        folder, onerror=record_walk_error, followlinks=False
    ):
        subfolders[:] = [
            name for name in subfolders
            if not (Path(current_folder) / name).is_symlink()
        ]

        for filename in filenames:
            path = Path(current_folder) / filename
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                candidates[path.stat().st_size].append(path)
                files_seen += 1
            except OSError:
                skipped_files += 1

    # Unique-sized files cannot be exact copies of another file.
    possible_duplicates = {
        size: paths for size, paths in candidates.items()
        if len(paths) > 1
    }
    total_to_hash = sum(len(paths) for paths in possible_duplicates.values())
    processed = 0
    duplicate_groups = []

    # Pass 2: hash only files whose sizes match another file.
    for size, paths in sorted(possible_duplicates.items()):
        hashes = defaultdict(list)
        for path in paths:
            try:
                file_hash = calculate_hash(path)
                hashes[file_hash].append(str(path))
                files_hashed += 1
            except OSError:
                skipped_files += 1

            processed += 1
            if processed % 5 == 0 or processed == total_to_hash:
                events.put(("progress", processed, total_to_hash, path.name))

        for file_hash, matching_paths in hashes.items():
            if len(matching_paths) > 1:
                duplicate_groups.append({
                    "size": size,
                    "hash": file_hash,
                    "paths": sorted(matching_paths, key=str.casefold),
                })

    duplicate_groups.sort(key=lambda group: group["paths"][0].casefold())
    stats = {
        "files_seen": files_seen,
        "files_hashed": files_hashed,
        "skipped_files": skipped_files,
        "walk_errors": len(walk_errors),
        "total_to_hash": total_to_hash,
    }
    return duplicate_groups, stats


class FileDetective:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1080x740")
        self.root.minsize(800, 590)
        self.root.configure(bg=BG)

        self.selected_folder = None
        self.results = []
        self.scanning = False
        self.events = queue.Queue()
        self.banner_phase = 0

        self.build_styles()
        self.build_interface()
        self.root.after(100, self.process_events)
        self.animate_banner()

    # -------------------- Styles and decorative banner --------------------
    def build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Haki.Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=29,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Haki.Treeview.Heading",
            background="#29202A",
            foreground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            padding=9,
            relief="flat",
        )
        style.map(
            "Haki.Treeview",
            background=[("selected", "#64172A")],
            foreground=[("selected", "#FFFFFF")],
        )
        style.configure(
            "Haki.Horizontal.TProgressbar",
            troughcolor="#24202A",
            background=RED,
            bordercolor=BG,
            lightcolor=RED,
            darkcolor=RED_DARK,
        )

    def build_banner(self, event=None):
        canvas = self.banner
        canvas.delete("all")
        width = max(canvas.winfo_width(), 800)
        height = 185
        phase_red = "#" + ("F22A4B" if self.banner_phase % 2 == 0 else "B91432")

        # Angular dark panels in the background.
        canvas.create_rectangle(0, 0, width, height, fill=BG, outline=BG)
        canvas.create_polygon(
            width * 0.55, 0, width, 0, width, height,
            width * 0.70, height, fill="#120B11", outline=""
        )
        canvas.create_polygon(
            width * 0.82, 0, width, 0, width, height * 0.58,
            fill="#210A14", outline=""
        )

        # Red diagonal slash marks, drawn as narrow polygons.
        slash_specs = [
            (0.77, 24, 90, RED_DARK),
            (0.85, 15, 100, phase_red),
            (0.93, 29, 115, "#5B0D20"),
            (1.00, 13, 80, "#A5122C"),
        ]
        for start_ratio, thickness, shift, color in slash_specs:
            x = width * start_ratio
            canvas.create_polygon(
                x, -12,
                x + thickness, -12,
                x + thickness - shift, height + 12,
                x - shift, height + 12,
                fill=color,
                outline="",
            )

        # Haki-like rings and sparks: all drawn with Tkinter shapes.
        cx, cy = width * 0.83, 86
        for radius, color, line_width in [
            (63, "#3A1020", 2),
            (48, "#701328", 2),
            (34, phase_red, 2),
        ]:
            canvas.create_oval(
                cx - radius, cy - radius,
                cx + radius, cy + radius,
                outline=color, width=line_width
            )

        canvas.create_line(
            cx - 53, cy + 25, cx + 22, cy - 48,
            fill=phase_red, width=3
        )
        canvas.create_line(
            cx - 21, cy + 51, cx + 53, cy - 25,
            fill="#8F1129", width=2
        )
        for sx, sy, length in [(-74, -25, 12), (65, -43, 10), (48, 48, 13), (-58, 49, 9)]:
            canvas.create_line(
                cx + sx, cy + sy,
                cx + sx + length, cy + sy - length,
                fill=phase_red, width=2
            )

        # Keep all important text to the left of the decorative slashes.
        canvas.create_text(
            29, 26, anchor="w",
            text="WILLPOWER // FILE INTEGRITY UNIT",
            font=("Consolas", 9, "bold"),
            fill=phase_red,
        )
        canvas.create_text(
            27, 67, anchor="w",
            text="FILE DETECTIVE",
            font=("Segoe UI", 27, "bold"),
            fill=TEXT,
        )
        canvas.create_text(
            30, 101, anchor="w",
            text="HUNT THE DUPLICATES. PROTECT YOUR DATA.",
            font=("Segoe UI", 10, "bold"),
            fill="#C6C3CC",
        )
        canvas.create_text(
            30, 145, anchor="w",
            text="CONQUEROR'S HAKI  /  DATA HUNTER MODE",
            font=("Consolas", 10, "bold"),
            fill=phase_red,
        )
        canvas.create_text(
            cx, cy + 1, text="H",
            font=("Georgia", 25, "bold"),
            fill="#F4DDE2",
        )

    def animate_banner(self):
        if not self.root.winfo_exists():
            return
        self.banner_phase += 1
        self.build_banner()
        self.root.after(650, self.animate_banner)

    # -------------------- Main interface --------------------
    def build_interface(self):
        self.banner = tk.Canvas(
            self.root, height=185, bg=BG, highlightthickness=0
        )
        self.banner.pack(fill="x")
        self.banner.bind("<Configure>", self.build_banner)

        # Thin crimson accent under the banner.
        tk.Frame(self.root, bg=RED, height=3).pack(fill="x")

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=22, pady=(12, 8))

        # Action buttons.
        action_row = tk.Frame(body, bg=BG)
        action_row.pack(fill="x", pady=(0, 10))

        self.choose_button = self.make_button(
            action_row, "＋  CHOOSE FOLDER", self.choose_folder,
            bg="#28222C", hover="#3A2934"
        )
        self.choose_button.pack(side="left")

        self.scan_button = self.make_button(
            action_row, "⚔  SCAN FOR DUPLICATES", self.start_scan,
            bg="#A9112D", hover="#D0183B", state="disabled"
        )
        self.scan_button.pack(side="left", padx=8)

        self.export_button = self.make_button(
            action_row, "↓  EXPORT CSV", self.export_csv,
            bg="#28222C", hover="#3A2934", state="disabled"
        )
        self.export_button.pack(side="left")

        # Target folder card.
        folder_card = tk.Frame(
            body, bg=PANEL, highlightbackground="#3A1824", highlightthickness=1
        )
        folder_card.pack(fill="x", pady=(0, 10))

        tk.Label(
            folder_card, text="TARGET DIRECTORY",
            font=("Consolas", 9, "bold"), bg=PANEL, fg=RED
        ).pack(anchor="w", padx=13, pady=(9, 2))

        self.folder_label = tk.Label(
            folder_card, text="No folder selected — choose a target to begin.",
            font=("Segoe UI", 9), bg=PANEL, fg=MUTED,
            anchor="w", justify="left", wraplength=960
        )
        self.folder_label.pack(fill="x", padx=13, pady=(0, 10))

        # Three summary cards.
        stats_row = tk.Frame(body, bg=BG)
        stats_row.pack(fill="x", pady=(0, 10))
        self.stat_values = {}
        self.make_stat_card(stats_row, "FILES DISCOVERED", "—", "files")
        self.make_stat_card(stats_row, "DUPLICATE GROUPS", "—", "groups")
        self.make_stat_card(stats_row, "REDUNDANT DATA", "—", "space")

        # Progress and status line.
        progress_header = tk.Frame(body, bg=BG)
        progress_header.pack(fill="x", pady=(1, 3))
        tk.Label(
            progress_header, text="SCAN PROGRESS",
            bg=BG, fg="#D0CDD5", font=("Consolas", 9, "bold")
        ).pack(side="left")
        self.progress_percent = tk.Label(
            progress_header, text="0%", bg=BG, fg=RED,
            font=("Consolas", 9, "bold")
        )
        self.progress_percent.pack(side="right")

        self.progress = ttk.Progressbar(
            body, style="Haki.Horizontal.TProgressbar",
            mode="determinate", maximum=100
        )
        self.progress.pack(fill="x", pady=(0, 6))

        self.status_label = tk.Label(
            body,
            text="READY // Choose a folder to begin your hunt.",
            font=("Consolas", 9), bg=BG, fg="#F05A73",
            anchor="w", justify="left", wraplength=980
        )
        self.status_label.pack(fill="x", pady=(0, 8))

        # Results table panel.
        results_panel = tk.Frame(
            body, bg=PANEL, highlightbackground="#3A1824", highlightthickness=1
        )
        results_panel.pack(fill="both", expand=True)

        tk.Label(
            results_panel, text="// DUPLICATE INTELLIGENCE",
            font=("Consolas", 10, "bold"), bg=PANEL, fg=TEXT
        ).pack(anchor="w", padx=12, pady=(10, 7))

        table_frame = tk.Frame(results_panel, bg=PANEL)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            table_frame,
            columns=("group", "size", "path"),
            show="headings",
            style="Haki.Treeview",
        )
        self.tree.heading("group", text="GROUP")
        self.tree.heading("size", text="FILE SIZE")
        self.tree.heading("path", text="FILE LOCATION")
        self.tree.column("group", width=130, minwidth=100, anchor="center")
        self.tree.column("size", width=110, minwidth=85, anchor="center")
        self.tree.column("path", width=630, minwidth=220, anchor="w")

        y_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        x_scroll = ttk.Scrollbar(
            results_panel, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(
            yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set
        )
        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(
            body,
            text="READ-ONLY SCAN  //  NO FILES ARE AUTOMATICALLY DELETED",
            font=("Consolas", 8), bg=BG, fg="#797985"
        ).pack(anchor="w", pady=(8, 0))

    def make_button(self, parent, text, command, bg, hover, state="normal"):
        return tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", 9, "bold"),
            bg=bg, fg=TEXT, activebackground=hover,
            activeforeground="white", disabledforeground="#6A6670",
            relief="flat", bd=0, padx=13, pady=10,
            cursor="hand2", state=state,
        )

    def make_stat_card(self, parent, title, initial, key):
        card = tk.Frame(
            parent, bg=PANEL,
            highlightbackground="#301722", highlightthickness=1
        )
        card.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(
            card, text=title, bg=PANEL, fg=MUTED,
            font=("Consolas", 8, "bold")
        ).pack(anchor="w", padx=11, pady=(9, 2))
        value_label = tk.Label(
            card, text=initial, bg=PANEL, fg=TEXT,
            font=("Segoe UI", 16, "bold")
        )
        value_label.pack(anchor="w", padx=11, pady=(0, 8))
        self.stat_values[key] = value_label

    # -------------------- Folder selection --------------------
    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose a folder to scan")
        if not folder:
            return

        self.selected_folder = folder
        self.folder_label.config(text=folder, fg=TEXT)
        self.results = []
        self.clear_table()
        self.progress["value"] = 0
        self.progress_percent.config(text="0%")
        self.export_button.config(state="disabled")
        self.scan_button.config(state="normal")
        self.stat_values["groups"].config(text="—")
        self.stat_values["space"].config(text="—")
        self.stat_values["files"].config(text="—")
        self.status_label.config(
            text="TARGET LOCKED // Click SCAN FOR DUPLICATES to begin.",
            fg="#F05A73"
        )

    # -------------------- Scanning --------------------
    def start_scan(self):
        if self.scanning:
            return
        if not self.selected_folder:
            messagebox.showwarning("No folder selected", "Choose a folder first.")
            return

        # Clear old queue messages so a previous scan cannot update this one.
        while True:
            try:
                self.events.get_nowait()
            except queue.Empty:
                break

        self.scanning = True
        self.results = []
        self.clear_table()
        self.progress["value"] = 0
        self.progress_percent.config(text="0%")
        self.export_button.config(state="disabled")
        self.scan_button.config(state="disabled")
        self.choose_button.config(state="disabled")
        self.status_label.config(
            text="HAKI SCAN ENGAGED // Mapping files and analysing duplicates...",
            fg="#FF5C78"
        )

        worker = threading.Thread(
            target=self.scan_worker,
            args=(self.selected_folder,),
            daemon=True
        )
        worker.start()

    def scan_worker(self, folder):
        try:
            results, stats = scan_for_duplicates(folder, self.events)
            self.events.put(("done", results, stats))
        except Exception as error:
            self.events.put(("error", str(error)))

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "progress":
                    _, processed, total, current_name = event
                    self.progress.configure(maximum=max(total, 1))
                    self.progress["value"] = processed
                    percent = int(processed / total * 100) if total else 100
                    self.progress_percent.config(text=f"{percent}%")
                    self.status_label.config(
                        text=f"SCANNING // {processed}/{total} hashed  •  {current_name}",
                        fg="#FF5C78"
                    )

                elif kind == "done":
                    _, self.results, stats = event
                    self.scanning = False
                    self.choose_button.config(state="normal")
                    self.scan_button.config(state="normal")
                    total = stats["total_to_hash"]
                    self.progress.configure(maximum=max(total, 1))
                    self.progress["value"] = max(total, 1)
                    self.progress_percent.config(text="100%")
                    self.display_results(stats)

                elif kind == "error":
                    self.scanning = False
                    self.choose_button.config(state="normal")
                    self.scan_button.config(state="normal")
                    messagebox.showerror("Scan failed", event[1])
                    self.status_label.config(
                        text="SCAN FAILED // Check the selected folder and try again.",
                        fg=RED
                    )

        except queue.Empty:
            pass

        self.root.after(100, self.process_events)

    # -------------------- Results --------------------
    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def display_results(self, stats):
        self.clear_table()
        duplicate_file_count = 0
        redundant_bytes = 0

        for group_number, group in enumerate(self.results, start=1):
            paths = group["paths"]
            duplicate_file_count += len(paths)
            redundant_bytes += group["size"] * (len(paths) - 1)

            for path in paths:
                self.tree.insert(
                    "", "end",
                    values=(f"GROUP {group_number}", format_size(group["size"]), path)
                )

        self.stat_values["files"].config(text=str(stats["files_seen"]))
        self.stat_values["groups"].config(text=str(len(self.results)))
        self.stat_values["space"].config(text=format_size(redundant_bytes))

        summary = (
            f"SCAN COMPLETE // {stats['files_seen']} files found  •  "
            f"{len(self.results)} duplicate groups  •  "
            f"{format_size(redundant_bytes)} potentially redundant data"
        )
        if stats["skipped_files"]:
            summary += f"  •  {stats['skipped_files']} file(s) unreadable"
        if stats["walk_errors"]:
            summary += f"  •  {stats['walk_errors']} folder access error(s)"
        if not self.results:
            summary += "  •  No duplicates found"

        self.status_label.config(text=summary, fg="#F05A73")
        self.export_button.config(
            state="normal" if self.results else "disabled"
        )

    # -------------------- CSV export --------------------
    def export_csv(self):
        if not self.results:
            messagebox.showinfo("No results", "Run a scan that finds duplicates first.")
            return

        destination = filedialog.asksaveasfilename(
            title="Save duplicate file report",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="file_detective_haki_report.csv",
        )
        if not destination:
            return

        try:
            with open(
                destination, "w", newline="", encoding="utf-8-sig"
            ) as report:
                writer = csv.writer(report)
                writer.writerow(["Group", "Size in Bytes", "SHA-256", "File Path"])
                for group_number, group in enumerate(self.results, start=1):
                    for path in group["paths"]:
                        writer.writerow([
                            group_number, group["size"], group["hash"], path
                        ])

            messagebox.showinfo(
                "Export successful", f"Your report was saved to:\n{destination}"
            )
        except OSError as error:
            messagebox.showerror("Export failed", f"Could not save the report:\n{error}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FileDetective(root)
    root.mainloop()
