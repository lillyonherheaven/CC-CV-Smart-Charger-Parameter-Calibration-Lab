"""Numerical verification and data-contract tests. Run with unittest."""
import io
import unittest
from dataclasses import replace
import numpy as np
import pandas as pd
from charger.model import Parameters, exact, exact_events, exact_target_time
from charger.solvers import solve, convergence
from charger.analysis import calibrate
from charger.data import sample_data, load_csv


class LabTests(unittest.TestCase):
    def setUp(self):
        self.p = Parameters()

    def test_switch_continuity(self):
        ts, _ = exact_events(self.p)
        values = exact(self.p, np.array([ts-1e-6, ts, ts+1e-6]), False)
        self.assertLess(np.ptp(values["voltage_v"]), 1e-8)
        self.assertAlmostEqual(values["voltage_v"][1], self.p.vmax_v)
        self.assertAlmostEqual(values["current_a"][1], self.p.current_a)

    def test_cc_is_exact_for_all_methods(self):
        p = replace(self.p, mode="CC")
        for method in ("Euler", "Heun", "RK4"):
            sim = solve(p, 1200, 73, method)
            np.testing.assert_allclose(sim.soc, exact(p, sim.time)["soc_est"], atol=1e-14)
            self.assertIsNone(sim.switch_time)

    def test_event_split_and_grid_delay(self):
        ts, _ = exact_events(self.p)
        for method in ("Euler", "Heun", "RK4"):
            event = solve(self.p, 8000, 211, method, "Event-aware", False)
            grid = solve(self.p, 8000, 211, method, "Grid-delayed", False)
            self.assertAlmostEqual(event.switch_time, ts, places=8)
            self.assertGreaterEqual(grid.switch_time-ts, -1e-9)
            self.assertLess(grid.switch_time-ts, 211)
            self.assertTrue(np.all(np.diff(event.time) > 0))

    def test_orders_on_smooth_cv(self):
        # Begin in CV: no switching or event interpolation to obscure order.
        p = replace(self.p, soc0=.9)
        rows = convergence(p, 1600, [160, 80, 40])
        for method, expected in (("Euler", 1), ("Heun", 2), ("RK4", 4)):
            subset = [r for r in rows if r["policy"] == "Event-aware" and r["method"] == method]
            self.assertAlmostEqual(subset[-1]["observed_order"], expected, delta=.2)

    def test_termination_and_target(self):
        _, stop = exact_events(self.p)
        sim = solve(self.p, 9000, 31, "RK4", terminate=True)
        self.assertAlmostEqual(sim.stop_time, stop, delta=.001)
        self.assertAlmostEqual(sim.soc[-1], self.p.stop_soc)
        ref = exact(self.p, [stop-1, stop+1])
        self.assertGreater(ref["current_a"][0], 0)
        self.assertEqual(ref["current_a"][1], 0)
        self.assertIsNone(exact_target_time(self.p, .999, True))
        self.assertAlmostEqual(exact_target_time(self.p, .95, False),
                               exact_target_time(self.p, .95, True))

    def test_start_in_cv_and_already_terminated(self):
        p = replace(self.p, soc0=.995)
        sim = solve(p, 500, 60, terminate=True)
        self.assertEqual(sim.stop_time, 0.)
        np.testing.assert_allclose(sim.soc, p.soc0)
        np.testing.assert_allclose(exact(p, sim.time)["soc_est"], p.soc0)

    def test_unstable_euler_visible(self):
        p = replace(self.p, soc0=.9)
        sim = solve(p, 6000, 3000, "Euler", terminate=False)
        self.assertGreater(np.max(sim.soc), p.equilibrium)
        self.assertLess(np.min(sim.observations(p)["current_a"]), 0)

    def test_noise_free_parameter_recovery(self):
        true = replace(self.p, capacity_ah=2.3, resistance_ohm=.2, soc0=.25)
        times = np.arange(0, 9001, 120.)
        frame = pd.DataFrame({"time_sec": times, **exact(true, times, False)})
        fitted, info = calibrate(frame, self.p)
        self.assertTrue(info["success"])
        self.assertEqual(info["jacobian_rank"], 3)
        for n in ("capacity_ah", "resistance_ohm", "soc0"):
            self.assertAlmostEqual(getattr(fitted, n), getattr(true, n), places=7)

    def test_noisy_recovery(self):
        frame, true = sample_data()
        fitted, info = calibrate(frame, self.p)
        for name, tolerance in (("capacity_ah", .03), ("resistance_ohm", .01), ("soc0", .01)):
            self.assertAlmostEqual(getattr(fitted, name), getattr(true, name), delta=tolerance)

    def test_voltage_only_cv_nonidentifiability(self):
        p = replace(self.p, soc0=.9)
        times = np.arange(0, 1000, 100.)
        frame = pd.DataFrame({"time_sec": times, "voltage_v": exact(p, times, False)["voltage_v"]})
        _, info = calibrate(frame, p)
        self.assertLess(info["jacobian_rank"], 3)
        self.assertTrue(info["warnings"])

    def test_csv_validation_and_missing_channels(self):
        frame, _ = sample_data()
        parsed = load_csv(io.StringIO(frame[["time_sec", "voltage_v"]].to_csv(index=False)))
        self.assertEqual(len(parsed), len(frame))
        for bad in ("time_sec,voltage_v\n0,3\n0,3\n2,3\n3,3", "time_sec,soc_est\n0,20\n1,30\n2,40\n3,50"):
            with self.assertRaises(ValueError):
                load_csv(io.StringIO(bad))

    def test_horizon_and_invalid_inputs(self):
        sim = solve(self.p, 1000, 333, terminate=False)
        self.assertEqual(sim.time[-1], 1000.)
        with self.assertRaises(ValueError):
            solve(self.p, dt=0)
        with self.assertRaises(ValueError):
            replace(self.p, vmax_v=4.3).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
