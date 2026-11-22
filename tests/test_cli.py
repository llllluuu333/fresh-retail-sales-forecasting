import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

class ForecastCLITests(unittest.TestCase):
    def test_output_requires_explicit_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            dates = pd.date_range("2024-01-01", periods=21, freq="D")
            frame = pd.DataFrame({"store_id": [1]*21, "product_id": [1]*21,
                                  "dt": dates, "sale_amount": [float(i % 7 + 1) for i in range(21)],
                                  "split": ["training"]*14 + ["validation"]*7})
            source = tmp / "input.csv"
            output = tmp / "result"
            frame.to_csv(source, index=False)
            command = [sys.executable, "-m", "forecasting.run", "--input", str(source),
                       "--output", str(output)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            metrics = output / "metrics.json"
            self.assertEqual(json.loads(metrics.read_text())["baseline"]["n"], 7)
            metadata = json.loads((output / "run_metadata.json").read_text())
            self.assertEqual(metadata["input_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(metadata["window"], 7)
            self.assertTrue(metadata["pandas"])
            before = metrics.read_bytes()
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(metrics.read_bytes(), before)
            third = subprocess.run(command + ["--overwrite"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(third.returncode, 0, third.stderr)

if __name__ == "__main__":
    unittest.main()
