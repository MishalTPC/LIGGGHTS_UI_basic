# LIGGGHTS UI Basic

A Windows desktop launcher for running LIGGGHTS simulations without manually entering command-prompt commands.

**Author:** Mishal Mohanlal  
**Version:** 1.0.0  
**Language:** Python 3 (Tkinter, standard library)

## Download the Windows application

1. Open the **Actions** tab in this repository.
2. Select **Build Windows EXE**.
3. Open the latest **successful** run on the main branch.
4. Under **Artifacts**, download **LIGGGHTS_UI_basic_Windows_v1.0.0**.
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
