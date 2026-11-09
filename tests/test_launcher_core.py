"""Tests for command construction; run on Windows and Linux."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from launcher_core import build_run_spec, command_as_text


class RunSpecTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name) / "Simulation with spaces"
        directory.mkdir()
        self.exe = Path(self.temp.name) / "LIGGGHTS executable.exe"
        self.exe.write_text("", encoding="utf-8")
        self.input_file = directory / "vibrating_screen.txt"
        self.input_file.write_text("run 100", encoding="utf-8")

    def test_serial_uses_input_directory(self):
        spec = build_run_spec(str(self.exe), str(self.input_file))
        self.assertEqual(spec.working_directory, self.input_file.parent.resolve())
        self.assertEqual(spec.command, [str(self.exe.resolve()), "-in", "vibrating_screen.txt"])

    def test_echo_argument(self):
        spec = build_run_spec(str(self.exe), str(self.input_file), echo=True)
        self.assertEqual(spec.command[-4:], ["-echo", "screen", "-in", "vibrating_screen.txt"])

    def test_parallel_argument_order(self):
        mpiexec = Path(self.temp.name) / "mpiexec.exe"
        mpiexec.write_text("", encoding="utf-8")
        spec = build_run_spec(str(self.exe), str(self.input_file),
                              parallel=True, processes=8, mpiexec=str(mpiexec))
        self.assertEqual(spec.command[:3], [str(mpiexec.resolve()), "-n", "8"])
        self.assertEqual(spec.command[-3:], [str(self.exe.resolve()), "-in", "vibrating_screen.txt"])

    def test_parallel_on_path(self):
        with patch("launcher_core.shutil.which", return_value="C:/MPI/mpiexec.exe"):
            spec = build_run_spec(str(self.exe), str(self.input_file),
                                  parallel=True, mpiexec="mpiexec")
        self.assertEqual(spec.command[0], "C:/MPI/mpiexec.exe")

    def test_invalid_processes(self):
        for value in (0, -1, 1025):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    build_run_spec(str(self.exe), str(self.input_file),
                                   parallel=True, processes=value, mpiexec="mpiexec")

    def test_missing_input(self):
        with self.assertRaises(FileNotFoundError):
            build_run_spec(str(self.exe), str(self.input_file) + ".missing")

    def test_missing_executable(self):
        with self.assertRaises(FileNotFoundError):
            build_run_spec(str(self.exe) + ".missing", str(self.input_file))

    def test_missing_mpi(self):
        with patch("launcher_core.shutil.which", return_value=None):
            with self.assertRaises(FileNotFoundError):
                build_run_spec(str(self.exe), str(self.input_file),
                               parallel=True, mpiexec="mpiexec")

    def test_command_string_keeps_paths_intact(self):
        spec = build_run_spec(str(self.exe), str(self.input_file))
        text = command_as_text(spec.command)
        self.assertIn("LIGGGHTS executable.exe", text)
        self.assertIn("vibrating_screen.txt", text)


if __name__ == "__main__":
    unittest.main()
