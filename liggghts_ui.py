"""Desktop GUI to launch LIGGGHTS simulations on Windows.

Author: Mishal Mohanlal
Version: 1.0.0
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from launcher_core import (
    APP_AUTHOR, APP_NAME, APP_VERSION, build_run_spec, command_as_text,
)

BLUE = "#102c54"
TEAL = "#007f90"
BG = "#f0f5fa"
TEXT = "#26364b"
MAX_VISIBLE_LINES = 4000


def settings_path() -> Path:
    app_data = os.environ.get("APPDATA")
    parent = Path(app_data) if app_data else Path.home() / ".config"
    return parent / "LIGGGHTS_UI_basic" / "settings.json"


def load_settings() -> dict:
    try:
        value = json.loads(settings_path().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def stop_process_tree(process: subprocess.Popen) -> None:
    """Terminate MPI ranks as well as the top-level mpiexec process on Windows."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    if process.poll() is None:
        try:
            process.terminate()
        except (OSError, ProcessLookupError):
            pass


class LiggghtsLauncher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME}  |  v{APP_VERSION}")
        self.geometry("1000x745")
        self.minsize(790, 615)
        self.configure(bg=BG)

        saved = load_settings()
        self.exe_var = tk.StringVar(value=saved.get("executable", ""))
        self.input_var = tk.StringVar(value=saved.get("input_file", ""))
        self.mpi_var = tk.StringVar(value=saved.get("mpiexec", "mpiexec"))
        self.mode_var = tk.StringVar(value=saved.get("mode", "Serial"))
        self.process_var = tk.StringVar(value=str(saved.get("processes", "4")))
        self.echo_var = tk.BooleanVar(value=bool(saved.get("echo", False)))
        self.post_var = tk.BooleanVar(value=bool(saved.get("create_post", True)))
        self.status_var = tk.StringVar(value="Ready")
        self.command_var = tk.StringVar(value="Select LIGGGHTS and an input file.")

        self.events: queue.Queue = queue.Queue(maxsize=12000)
        self.process: subprocess.Popen | None = None
        self.stop_requested = threading.Event()
        self.running = False
        self.last_log_path: Path | None = None
        self.visible_lines = 0

        self._configure_style()
        self._build_ui()
        for var in (
            self.exe_var, self.input_var, self.mpi_var, self.mode_var,
            self.process_var, self.echo_var,
        ):
            var.trace_add("write", self._update_preview)
        self._update_preview()
        self.after(80, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background=BG)
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("App.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background="#ffffff", foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Heading.TLabel", background=BG, foreground=BLUE,
                        font=("Segoe UI Semibold", 22))
        style.configure("Section.TLabel", background="#ffffff", foreground=BLUE,
                        font=("Segoe UI Semibold", 11))
        style.configure("Footer.TLabel", background=BG, foreground="#526277",
                        font=("Segoe UI", 9))
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 10),
                        padding=(17, 8), foreground="white", background=TEAL)
        style.map("Primary.TButton", background=[("active", "#006c7b"), ("disabled", "#a4b4c1")])
        style.configure("Action.TButton", font=("Segoe UI", 10), padding=(11, 8))
        style.configure("TEntry", padding=5)
        style.configure("TRadiobutton", background="#ffffff")
        style.configure("TCheckbutton", background="#ffffff")
        style.configure("TSpinbox", padding=5)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, style="App.TFrame", padding=(22, 15))
        outer.pack(fill="both", expand=True)

        title_row = ttk.Frame(outer, style="App.TFrame")
        title_row.pack(fill="x")
        ttk.Label(title_row, text="LIGGGHTS Simulation Launcher",
                  style="Heading.TLabel").pack(side="left")
        ttk.Label(title_row, text=f"Version {APP_VERSION}  |  Author: {APP_AUTHOR}",
                  style="Footer.TLabel").pack(side="right", anchor="s", pady=5)
        ttk.Label(outer,
                  text="Select your executable and input file, then run without the command prompt.",
                  style="App.TLabel").pack(anchor="w", pady=(2, 12))

        paths = ttk.Frame(outer, style="Card.TFrame", padding=15)
        paths.pack(fill="x", pady=(0, 10))
        paths.columnconfigure(1, weight=1)
        self._path_field(paths, 0, "LIGGGHTS executable", self.exe_var, self._browse_exe)
        self._path_field(paths, 1, "Simulation input file", self.input_var, self._browse_input)

        options = ttk.Frame(outer, style="Card.TFrame", padding=15)
        options.pack(fill="x", pady=(0, 10))
        options.columnconfigure(4, weight=1)
        ttk.Label(options, text="Execution settings", style="Section.TLabel").grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 10))
        ttk.Radiobutton(options, text="Serial", variable=self.mode_var,
                        value="Serial").grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(options, text="Parallel / MPI", variable=self.mode_var,
                        value="MPI").grid(row=1, column=1, sticky="w", padx=(8, 15))
        ttk.Label(options, text="Processes:", style="Card.TLabel").grid(
            row=1, column=2, sticky="e", padx=(0, 5))
        self.process_spin = ttk.Spinbox(options, from_=1, to=1024,
                                        textvariable=self.process_var, width=6)
        self.process_spin.grid(row=1, column=3, sticky="w")
        ttk.Checkbutton(options, text="Echo commands for debugging",
                        variable=self.echo_var).grid(row=2, column=0,
                                                     columnspan=3, sticky="w", pady=(12, 0))
        ttk.Checkbutton(options, text="Create post folder if missing",
                        variable=self.post_var).grid(row=2, column=3,
                                                     columnspan=2, sticky="w", pady=(12, 0), padx=(12, 0))
        ttk.Label(options, text="MPI launcher:", style="Card.TLabel").grid(
            row=3, column=0, sticky="w", pady=(12, 0))
        self.mpi_entry = ttk.Entry(options, textvariable=self.mpi_var)
        self.mpi_entry.grid(row=3, column=1, columnspan=3, sticky="ew", pady=(12, 0), padx=(8, 8))
        ttk.Button(options, text="Browse", command=self._browse_mpi).grid(
            row=3, column=4, sticky="e", pady=(12, 0))
        ttk.Label(options, text="MPI is only needed for parallel runs; mpiexec must be installed.",
                  style="Card.TLabel").grid(row=4, column=0, columnspan=5,
                                             sticky="w", pady=(8, 0))

        command_frame = ttk.Frame(outer, style="Card.TFrame", padding=(15, 11))
        command_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(command_frame, text="Command preview", style="Section.TLabel").pack(anchor="w")
        self.preview_label = tk.Label(command_frame, textvariable=self.command_var,
                                      bg="#ffffff", fg=TEXT, justify="left",
                                      anchor="w", wraplength=900, font=("Consolas", 9))
        self.preview_label.pack(fill="x", pady=(5, 0))
        self.bind("<Configure>", self._resize_preview)

        controls = ttk.Frame(outer, style="App.TFrame")
        controls.pack(fill="x", pady=(0, 8))
        self.run_button = ttk.Button(controls, text="▶  Run Simulation",
                                     style="Primary.TButton", command=self._start)
        self.run_button.pack(side="left")
        self.stop_button = ttk.Button(controls, text="■  Stop",
                                      style="Action.TButton", command=self._stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Open Simulation Folder", style="Action.TButton",
                   command=self._open_folder).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Open Full Log", style="Action.TButton",
                   command=self._open_log).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Clear Output", style="Action.TButton",
                   command=self._clear_output).pack(side="right")

        log_header = ttk.Frame(outer, style="App.TFrame")
        log_header.pack(fill="x", pady=(0, 5))
        ttk.Label(log_header, text="Simulation output", style="App.TLabel").pack(side="left")
        self.status_label = ttk.Label(log_header, textvariable=self.status_var,
                                       style="App.TLabel")
        self.status_label.pack(side="right")

        self.console = scrolledtext.ScrolledText(
            outer, wrap="word", font=("Consolas", 9), background="#101e32",
            foreground="#d9e8f7", insertbackground="#ffffff",
            selectbackground="#266a86", relief="flat", padx=11, pady=10,
            state="disabled", height=12,
        )
        self.console.pack(fill="both", expand=True)
        ttk.Label(outer, style="Footer.TLabel",
                  text="Working directory = input file's folder  |  All output is also saved to run_logs/  |  LIGGGHTS and MPI are not bundled").pack(
                      anchor="w", pady=(9, 0))

    def _resize_preview(self, _event=None) -> None:
        self.preview_label.configure(wraplength=max(350, self.winfo_width() - 100))

    def _path_field(self, parent, row, caption, variable, browse) -> None:
        ttk.Label(parent, text=caption, style="Card.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky="ew", padx=(0, 8), pady=5)
        ttk.Button(parent, text="Browse", command=browse).grid(
            row=row, column=2, sticky="e", pady=5)

    def _browse_exe(self) -> None:
        path = filedialog.askopenfilename(
            title="Select liggghts.exe",
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")],
        )
        if path:
            self.exe_var.set(path)
            self._save_settings()

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a LIGGGHTS simulation input file",
            filetypes=[("Input files", "*.txt *.in *.lmp"), ("All files", "*.*")],
        )
        if path:
            self.input_var.set(path)
            self._save_settings()

    def _browse_mpi(self) -> None:
        path = filedialog.askopenfilename(
            title="Select mpiexec.exe",
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")],
        )
        if path:
            self.mpi_var.set(path)
            self._save_settings()

    def _settings_dict(self) -> dict:
        return {
            "executable": self.exe_var.get(),
            "input_file": self.input_var.get(),
            "mpiexec": self.mpi_var.get(),
            "mode": self.mode_var.get(),
            "processes": self.process_var.get(),
            "echo": self.echo_var.get(),
            "create_post": self.post_var.get(),
        }

    def _save_settings(self) -> None:
        try:
            target = settings_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(self._settings_dict(), indent=2), encoding="utf-8")
        except OSError:
            pass  # Settings are optional; launching must still be possible.

    def _current_spec(self):
        try:
            count = int(self.process_var.get())
        except ValueError as exc:
            raise ValueError("Enter a whole number of MPI processes.") from exc
        return build_run_spec(
            self.exe_var.get(), self.input_var.get(),
            parallel=self.mode_var.get() == "MPI",
            processes=count, mpiexec=self.mpi_var.get(),
            echo=self.echo_var.get(),
        )

    def _update_preview(self, *_args) -> None:
        try:
            spec = self._current_spec()
            self.command_var.set(command_as_text(spec.command))
        except (OSError, ValueError) as exc:
            self.command_var.set(str(exc))

    def _append_line(self, message: str) -> None:
        self.console.configure(state="normal")
        self.console.insert("end", message)
        if not message.endswith("\n"):
            self.console.insert("end", "\n")
        self.visible_lines += max(1, message.count("\n"))
        if self.visible_lines > MAX_VISIBLE_LINES:
            self.console.delete("1.0", "1001.0")
            self.visible_lines -= 1000
        self.console.see("end")
        self.console.configure(state="disabled")

    def _clear_output(self) -> None:
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")
        self.visible_lines = 0

    def _emit(self, item: tuple) -> None:
        try:
            self.events.put_nowait(item)
        except queue.Full:
            # The complete output is always written to disk, even if the UI lags.
            if item[0] != "line":
                self.events.put(item, timeout=5)

    def _start(self) -> None:
        if self.running:
            return
        try:
            spec = self._current_spec()
            if self.post_var.get():
                (spec.working_directory / "post").mkdir(parents=True, exist_ok=True)
            logs = spec.working_directory / "run_logs"
            logs.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            log_path = logs / f"liggghts_{timestamp}.log"
        except (OSError, ValueError) as exc:
            messagebox.showerror("Cannot start LIGGGHTS", str(exc), parent=self)
            return

        self._save_settings()
        self._clear_output()
        self.stop_requested.clear()
        self.running = True
        self.last_log_path = log_path
        self.status_var.set("Running...")
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._append_line(f"Working directory: {spec.working_directory}")
        self._append_line(f"Command: {command_as_text(spec.command)}")
        self._append_line(f"Full log: {log_path}\n")
        thread = threading.Thread(target=self._run_worker, args=(spec, log_path), daemon=True)
        thread.start()

    def _run_worker(self, spec, log_path: Path) -> None:
        returncode = None
        error = None
        stopped = False
        try:
            with log_path.open("w", encoding="utf-8", errors="replace", buffering=1) as log:
                log.write(f"Author: {APP_AUTHOR} | Launcher v{APP_VERSION}\n")
                log.write(f"Working directory: {spec.working_directory}\n")
                log.write(f"Command: {command_as_text(spec.command)}\n\n")
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
                with subprocess.Popen(
                    spec.command, cwd=str(spec.working_directory),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, errors="replace", bufsize=1,
                    creationflags=flags,
                ) as proc:
                    self.process = proc
                    if self.stop_requested.is_set():
                        stop_process_tree(proc)
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        log.write(line)
                        self._emit(("line", line))
                    returncode = proc.wait()
                    stopped = self.stop_requested.is_set()
                    self.process = None
                log.write(f"\nExit code: {returncode}\n")
        except Exception as exc:
            error = str(exc)
        finally:
            self.process = None
            self._emit(("finished", returncode, error, stopped, str(log_path)))

    def _poll_events(self) -> None:
        for _ in range(350):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event[0] == "line":
                self._append_line(event[1])
            elif event[0] == "finished":
                _, code, error, stopped, path = event
                self.running = False
                self.run_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                if error:
                    self.status_var.set("Failed")
                    self._append_line(f"ERROR: {error}")
                elif stopped:
                    self.status_var.set("Stopped")
                    self._append_line("Simulation stopped by user.")
                elif code == 0:
                    self.status_var.set("Completed successfully")
                    self._append_line("Simulation completed successfully (exit code 0).")
                else:
                    self.status_var.set(f"Failed (exit code {code})")
                    self._append_line(f"Simulation exited with code {code}.")
                self._append_line(f"Full log: {path}")
        self.after(80, self._poll_events)

    def _stop(self) -> None:
        if not self.running:
            return
        self.stop_requested.set()
        self.status_var.set("Stopping...")
        self.stop_button.configure(state="disabled")
        proc = self.process
        if proc is not None:
            threading.Thread(target=stop_process_tree, args=(proc,), daemon=True).start()

    def _open_folder(self) -> None:
        candidate = Path(self.input_var.get().strip().strip('"'))
        if not candidate.is_file():
            messagebox.showinfo("No folder", "Select a valid simulation input file first.", parent=self)
            return
        self._open_path(candidate.parent)

    def _open_log(self) -> None:
        if self.last_log_path is None or not self.last_log_path.is_file():
            messagebox.showinfo("No log", "Run a simulation to generate a full log first.", parent=self)
            return
        self._open_path(self.last_log_path)

    def _open_path(self, path: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc), parent=self)

    def _on_close(self) -> None:
        if self.running:
            if not messagebox.askyesno(
                "Stop simulation?", "The simulation is running. Stop it and exit?", parent=self
            ):
                return
            self._stop()
        self._save_settings()
        self.destroy()


if __name__ == "__main__":
    LiggghtsLauncher().mainloop()
