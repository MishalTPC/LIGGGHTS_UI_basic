# LIGGGHTS UI Basic

A Windows desktop launcher for running LIGGGHTS simulations without manually entering command-prompt commands.

**Author:** Mishal Mohanlal  
**Version:** 1.2.0  
**Language:** Python 3 (Tkinter, standard library)

## Download the Windows application

1. Open the **Actions** tab in this repository.
2. Select **Build Windows EXE**.
3. Open the latest **successful** run on the main branch.
4. Under **Artifacts**, download **LIGGGHTS_UI_basic_Windows_v1.2.0**.
5. Unzip it and double-click **LIGGGHTS_UI_basic.exe**.

The generated program is a standalone Windows executable; no Python installation is needed to use it. GitHub may require a signed-in account to download workflow artifacts. Artifacts expire after 90 days; use **Run workflow** to build another.

**Important:** This UI does NOT contain the LIGGGHTS solver or MPI. You must have a working liggghts.exe and, for parallel runs, an MPI installation compatible with that build.

## How to use

1. Browse to the LIGGGHTS executable (liggghts.exe).
2. Browse to the simulation input file (for example vibrating_screen.txt or in.model).
3. Select Serial, or Parallel / MPI and the number of processes.
4. Optionally turn on echo (debug commands) and automatic creation of the post folder.
5. Select **Run Simulation**. Watch output and completion status in the console.
6. Use **Stop** to terminate a run. For MPI on Windows, the launcher attempts to stop the full child process tree.

The application automatically runs with its working directory set to the folder containing the selected input script. Relative STL/mesh references and output folders therefore resolve from the simulation folder, even when liggghts.exe lives elsewhere.

Each run writes a full output log to a timestamped file in the simulation folder's **run_logs** directory. The on-screen console retains only the most recent lines to keep the UI responsive. The selected paths and settings are stored in the user's AppData folder.

### Commands used

Serial:
```bat
"C:\path\to\liggghts.exe" -in input.txt
```

Parallel (8 processes):
```bat
mpiexec -n 8 "C:\path\to\liggghts.exe" -in input.txt
```

Debug mode adds **-echo screen** before **-in**. Arguments are passed directly to the operating system without invoking cmd.exe.

## Build from source

Requires Python 3.12 on Windows. Double-click **build_windows.bat**, or use:

```bat
py -3 -m pip install "pyinstaller>=6.15,<7"
py -3 -m unittest discover -s tests -v
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name LIGGGHTS_UI_basic --version-file version_info.txt liggghts_ui.py
```

Result: **dist/LIGGGHTS_UI_basic.exe**

For development, run **python liggghts_ui.py**. No third-party Python packages are needed for the GUI itself.

## Troubleshooting

- **Unable to open file post/...vtk:** Check that **Create post folder if missing** is enabled, or create the post directory yourself. This checkbox does not fix bad paths elsewhere in the input file.
- **LIGGGHTS won't start:** Test the selected binary independently, and check its required DLLs/runtime environment.
- **MPI not found:** Install the right MPI runtime for the specific LIGGGHTS build and make mpiexec discoverable, or browse to its exact path. A serial run can work even when MPI is missing.
- **Serial runs but parallel fails:** Confirm that LIGGGHTS was compiled for MPI and matches the MPI runtime. The UI cannot solve incompatible binaries.
- **Other files not found:** Keep STL/mesh files in paths referenced by the script, relative to the simulation folder.
- **Application appears to hang:** Check the full log. Some simulations buffer output; LIGGGHTS may be running even when the GUI displays no new lines.
- **Windows SmartScreen warning:** Unsigned GitHub-built executables can trigger a warning. Only run binaries from code you trust.

## Scope

This is a launcher, not a LIGGGHTS solver, pre/post-processor, or model editor. Only launch simulations you trust: LIGGGHTS input files can contain commands that modify files or run external processes.


## v1.2.0 live monitor

The GUI now includes a live elapsed timer, solver phase, timestep, particle count, mesh import tracking, estimated timesteps per second, an ETA when available, and a progress bar. Metrics are extracted from emitted LIGGGHTS thermodynamic lines, not estimated from CPU usage. Without emitted thermo lines, progress and ETA remain unknown. Some MPI builds buffer screen output; live progress cannot be guaranteed. 'log.lammps' is read internally from the simulation directory and is accessible through Open Logs. Captured command output is still saved under run_logs. An MPI abort is generally a symptom rather than a diagnosis.


## v1.2.0 — Dashboard telemetry improvements

- Show the specified `run 1000000` target in the progress caption before the first timestep is reported. The current timestep is **not** assumed to be zero.
- Follow fresh `log.lammps` output as an alternate source of timestep and atom-count telemetry, including partial lines that span several reads. Old `log.lammps` content from previous runs is ignored until the file changes.
- Keep console and native-log parsers separate to avoid double counting warnings and mesh imports.
- Throughput and ETA are calculated only after spaced, measurable timestep samples; buffered output cannot be assumed to represent real-time solver speed.
- No output for 30+ seconds is explicitly signposted as possibly initializing, buffered, or stalled; it does not imply successful time stepping.

## Version 1.2.0 — unified console and diagnostics

- Single live output console. The `log.lammps` **tab is removed**, but the native file remains on disk as produced by LIGGGHTS.
- **Open Logs** menu: captured launcher log, native `log.lammps`, or timestamped `run_logs` directory.
- Read both solver stdout and the native log internally for live dashboard metrics; do not double-count duplicated diagnostics.
- Highlight warnings, fatal/abort messages and successful mesh imports in the visible console.
- Display a dedicated **Last completed operation** line, warning count, and last diagnostic summary.
- Keep blank current timestep/particle count, speed and ETA when the solver has not emitted those measurements.

The launcher does not alter LIGGGHTS input scripts, mesh files, or solve routines.
