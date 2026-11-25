import io
import json
from pathlib import Path
import unittest
import zipfile
import numpy as np
from PIL import Image
from charger.model import Parameters
from charger.plots import physics_tables, physics_figure, png_bytes
from charger.analysis import local_defects
from charger.export import build_bundle, parameter_table
import matplotlib.pyplot as plt


class RelationshipsAndExportTests(unittest.TestCase):
    def test_physical_slopes_and_nonlinear_ocv(self):
        p = Parameters()
        tables = physics_tables(p, fixed_soc=.5, curvature=.6)
        r = tables["ohms_law"]
        self.assertAlmostEqual(np.polyfit(r.current_magnitude_a, r.charge_terminal_v, 1)[0], p.resistance_ohm)
        self.assertAlmostEqual(np.polyfit(r.current_magnitude_a, r.discharge_terminal_v, 1)[0], -p.resistance_ohm)
        self.assertAlmostEqual(np.polyfit(r.current_magnitude_a, r.charge_soc_rate_per_sec, 1)[0], p.eta/(3600*p.capacity_ah))
        ocv = tables["ocv"]
        np.testing.assert_allclose(ocv.affine_ocv_v.iloc[[0,-1]], ocv.illustrative_nonlinear_ocv_v.iloc[[0,-1]])
        self.assertTrue((np.diff(ocv.illustrative_nonlinear_ocv_v) > 0).all())
        self.assertGreater(np.max(abs(ocv.illustrative_nonlinear_ocv_v-ocv.affine_ocv_v)), .1)
        taper = tables["cv_taper"]
        self.assertAlmostEqual(np.polyfit(taper.time_since_cv_sec, np.log(taper.current_a), 1)[0], -1/p.tau)

    def test_local_defect_orders(self):
        table = local_defects(Parameters(), [160,80,40])
        for method, expected in [("Euler",2), ("Heun",3), ("RK4",5)]:
            self.assertAlmostEqual(table[table.method==method].iloc[-1].observed_local_order, expected, delta=.15)

    def test_complete_bundle_and_resolution(self):
        p = Parameters()
        fig, _ = physics_figure(p)
        try: png = png_bytes(fig)
        finally: plt.close(fig)
        root = Path(__file__).resolve().parents[1]
        payload = build_bundle({"test_value": float("nan")}, {"parameters": parameter_table(p,"test")},
                               {"physics_relationships": png}, root=root)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIsNone(json.loads(archive.read("diagnostics.json"))["test_value"])
            self.assertIn("source/charger/solvers.py", archive.namelist())
            self.assertFalse(any(".venv" in n or "/.git/" in n for n in archive.namelist()))
            with Image.open(io.BytesIO(archive.read("figures/physics_relationships.png"))) as image:
                self.assertAlmostEqual(image.info["dpi"][0], 300, delta=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
