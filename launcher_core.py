"""Command construction for the LIGGGHTS Windows launcher.

Author: Mishal Mohanlal
Version: 1.1.0
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "LIGGGHTS UI Basic"
APP_VERSION = "1.1.0"
APP_AUTHOR = "Mishal Mohanlal"


@dataclass(frozen=True)
class RunSpec:
    command: list[str]
    working_directory: Path
    input_file: Path


def resolve_mpi_launcher(value: str) -> str:
    """Find mpiexec on PATH, or accept an explicitly selected executable."""
    value = value.strip().strip('"')
    if not value:
        value = "mpiexec"
    if Path(value).parent == Path("."):
        found = shutil.which(value)
        if found is None:
            raise FileNotFoundError(
                "MPI launcher not found. Install/configure Microsoft MPI, or browse "
                "to mpiexec.exe (for example C:\\Program Files\\Microsoft MPI\\Bin\\mpiexec.exe)."
            )
        return found
    candidate = Path(value).expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"MPI launcher does not exist: {candidate}")
    return str(candidate)


def build_run_spec(
    executable: str,
    input_file: str,
    *,
    parallel: bool = False,
    processes: int = 2,
    mpiexec: str = "mpiexec",
    echo: bool = False,
) -> RunSpec:
    """Construct an argument list; never use a shell to launch a simulation.

    The input directory is the working directory, so relative meshes, STL files,
    and output paths used in the input script resolve as the user expects.
    """
    executable = executable.strip().strip('"')
    input_file = input_file.strip().strip('"')
    if not executable:
        raise ValueError("Select your LIGGGHTS executable.")
    if not input_file:
        raise ValueError("Select a LIGGGHTS input file.")

    exe = Path(executable).expanduser().resolve()
    inp = Path(input_file).expanduser().resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"LIGGGHTS executable not found: {exe}")
    if not inp.is_file():
        raise FileNotFoundError(f"LIGGGHTS input file not found: {inp}")

    command = [str(exe)]
    if echo:
        command.extend(["-echo", "screen"])
    command.extend(["-in", inp.name])

    if parallel:
        if not isinstance(processes, int) or not 1 <= processes <= 1024:
            raise ValueError("MPI process count must be between 1 and 1024.")
        command = [resolve_mpi_launcher(mpiexec), "-n", str(processes)] + command

    return RunSpec(command=command, working_directory=inp.parent, input_file=inp)


def command_as_text(command: list[str]) -> str:
    """Show the equivalent command using platform-appropriate quoting."""
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return " ".join(__import__("shlex").quote(part) for part in command)
