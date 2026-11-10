"""Test realistic LIGGGHTS output samples."""
import unittest
from telemetry import Telemetry,input_target,hms

class TestTelemetry(unittest.TestCase):
    def test_thermo(self):
        p=Telemetry(40000)
        p.feed("Step Atoms KinEng",0)
        p.feed("0 0 0",1)
        m=p.feed("10000 4000 13.5",11)
        self.assertEqual(m.particles,4000)
        self.assertEqual(m.step,10000)
        self.assertEqual(m.percent,25)
        self.assertAlmostEqual(m.rate,1000)
        self.assertAlmostEqual(m.eta,30)

    def test_abort(self):
        p=Telemetry()
        p.feed("Import and parallelization of mesh body_S containing 36 triangle(s) successful",0)
        m=p.feed("aborting MPI_COMM_WORLD",1)
        self.assertEqual(m.meshes,1)
        self.assertEqual(m.last_mesh,"body_S")
        self.assertIn("MPI_COMM_WORLD",m.diagnostic)

    def test_progress_unknown(self):
        p=Telemetry()
        p.feed("Step Atoms",0)
        self.assertIsNone(p.feed("100 10",1).percent)

    def test_targets(self):
        self.assertEqual(input_target("# run 300\nrun 40000"),40000)
        self.assertIsNone(input_target("run 10\nrun 20"))
        self.assertEqual(hms(3661),"01:01:01")
