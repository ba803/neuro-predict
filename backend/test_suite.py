"""
test_suite.py
Automated validation and regression tests for NeuroPredict Alzheimer's Assessment System.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

import main
from report_generator import create_pdf_report


class TestAlzheimerModel(unittest.TestCase):

    def setUp(self):
        self.model = main.model
        self.assertIsNotNone(self.model, "Assessment model failed to load.")

    def test_feature_columns(self):
        """Verify the model utilizes only the required 5 clinical features."""
        expected_features = [
            "Functional_Assessment_Score",
            "MMSE_Score",
            "ADL_Score",
            "Memory_Complaints",
            "Behavioral_Problems"
        ]
        self.assertEqual(main.FEATURE_COLUMNS, expected_features)

    def test_key_factors_retrieval(self):
        """Ensure key factors are dynamically computed and sorted descending."""
        fi_response = main.get_key_factors()
        self.assertIn("factors", fi_response)
        self.assertIn("weights", fi_response)
        self.assertEqual(len(fi_response["factors"]), 5)

        # Verify descending order
        weights = fi_response["weights"]
        for i in range(len(weights) - 1):
            self.assertGreaterEqual(weights[i], weights[i + 1])

    def test_evaluation_lower_risk(self):
        """Verify output on a healthy clinical profile."""
        patient = main.PatientInput(
            Functional_Assessment_Score=8.8,
            MMSE_Score=28.0,
            ADL_Score=9.0,
            Memory_Complaints=0,
            Behavioral_Problems=0
        )
        res = main.predict(patient)

        self.assertEqual(res["prediction"], 0)
        self.assertEqual(res["risk_level"], "Lower Risk")
        self.assertIn("Lower Risk", res["result_headline"])
        self.assertGreater(res["other_likelihood"], 70.0)
        self.assertLess(res["alzheimers_likelihood"], 30.0)
        self.assertIn("patient_scores", res)
        self.assertIn("factors_table", res)

    def test_evaluation_higher_risk(self):
        """Verify output on an impaired clinical profile."""
        patient = main.PatientInput(
            Functional_Assessment_Score=1.5,
            MMSE_Score=10.0,
            ADL_Score=1.5,
            Memory_Complaints=1,
            Behavioral_Problems=1
        )
        res = main.predict(patient)

        self.assertEqual(res["prediction"], 1)
        self.assertEqual(res["risk_level"], "Higher Risk")
        self.assertIn("Higher Risk", res["result_headline"])
        self.assertGreater(res["alzheimers_likelihood"], 70.0)
        self.assertLess(res["other_likelihood"], 30.0)

    def test_input_validation_bounds(self):
        """Test that invalid out-of-range values raise ValidationError."""
        # MMSE > 30 should raise error
        with self.assertRaises(Exception):
            main.PatientInput(
                Functional_Assessment_Score=5.0,
                MMSE_Score=35.0, # invalid
                ADL_Score=5.0,
                Memory_Complaints=0,
                Behavioral_Problems=0
            )

        # ADL < 0 should raise error
        with self.assertRaises(Exception):
            main.PatientInput(
                Functional_Assessment_Score=5.0,
                MMSE_Score=25.0,
                ADL_Score=-1.0, # invalid
                Memory_Complaints=0,
                Behavioral_Problems=0
            )

    def test_pdf_report_compilation(self):
        """Verify that ReportLab compiles a valid, non-empty 4-page A4 clinical PDF."""
        patient = main.PatientInput(
            Functional_Assessment_Score=8.0,
            MMSE_Score=23.0,
            ADL_Score=6.0,
            Memory_Complaints=1,
            Behavioral_Problems=1
        )
        pred_res = main.predict(patient)
        pdf_bytes = create_pdf_report(pred_res)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 50000, "PDF document appears truncated or empty.")
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Invalid PDF signature.")


if __name__ == "__main__":
    unittest.main()
