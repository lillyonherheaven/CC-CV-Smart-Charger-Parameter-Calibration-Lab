"""Exercise the actual Streamlit script and its calibration/state transitions."""
import io
import json
import unittest
import zipfile
from pathlib import Path
from streamlit.testing.v1 import AppTest


class AppSmokeTest(unittest.TestCase):
    def test_independent_sections_fit_and_export(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path), default_timeout=90).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.metric), 4)
        self.assertEqual(len(app.tabs), 5)
        def submit(label):
            next(x for x in app.button if x.label == label).click().run()
            self.assertEqual(len(app.exception), 0)
        submit("Auto-calibrate")
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Calibration applied" in x.value for x in app.success))
        before = app.session_state["last_export_report"]
        self.assertAlmostEqual(before["sections"]["simulation"]["parameters"]["resistance_ohm"], .15)
        self.assertAlmostEqual(before["sections"]["calibration"]["parameters"]["resistance_ohm"], .18, delta=.01)
        # Changing another lab does not overwrite the calibration or simulation.
        app.number_input(key="lab_dt").set_value(120.)
        submit("Calculate convergence")
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Calibration applied" in x.value for x in app.success))
        self.assertEqual(app.session_state["last_export_report"]["sections"]["simulation"], before["sections"]["simulation"])
        app.selectbox(key="sim_mode").select("CC")
        submit("Calculate simulation")
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Calibration applied" in x.value for x in app.success))
        self.assertTrue(any("Unregulated CC" in x.value for x in app.warning))
        # A local calibration-assumption change invalidates only its own fit.
        app.number_input(key="fit_r").set_value(.2)
        submit("Calculate overlay")
        self.assertFalse(any("Calibration applied" in x.value for x in app.success))
        # Inspect the exact downloadable archive, not a mock export.
        with zipfile.ZipFile(io.BytesIO(app.session_state["last_export_bytes"])) as archive:
            self.assertIsNone(archive.testzip())
            for name in ["summary.md", "summary.txt", "tables/calibrated_parameters.csv", "tables/convergence.csv",
                         "figures/physics_relationships.png", "figures/residuals.png", "source/app.py", "source/PRESENTATION.md"]:
                self.assertIn(name, archive.namelist())
            payload = json.loads(archive.read("diagnostics.json"))
            self.assertEqual(payload["sections"]["simulation"]["parameters"]["mode"], "CC")
            self.assertEqual(payload["sections"]["numerical"]["parameters"]["mode"], "CC/CV")
        app.radio(key="fit_source").set_value("No overlay").run()
        self.assertEqual(len(app.exception), 0)

    def test_invalid_section_does_not_block_other_sections(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path), default_timeout=90).run()
        app.number_input(key="sim_vmax").set_value(4.35)
        next(x for x in app.button if x.label == "Calculate simulation").click().run()
        self.assertEqual(len(app.exception), 0)
        payload = app.session_state["last_export_report"]
        self.assertIn("simulation", payload["errors"])
        self.assertIn("numerical", payload["sections"])
        self.assertIn("physics", payload["sections"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
