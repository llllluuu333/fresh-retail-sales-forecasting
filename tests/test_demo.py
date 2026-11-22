import unittest
from forecasting.demo import run


class SyntheticDemoTests(unittest.TestCase):
    def test_demo_runs_without_external_data(self):
        result = run()
        self.assertEqual(result["metrics"]["baseline"]["n"], 14)
        self.assertEqual(result["metrics"]["adjusted"]["n"], 14)
        self.assertGreaterEqual(result["metrics"]["baseline"]["wape"], 0)
        self.assertGreaterEqual(result["metrics"]["adjusted"]["wape"], 0)
        self.assertIn("Synthetic", result["scope"])


if __name__ == "__main__":
    unittest.main()
