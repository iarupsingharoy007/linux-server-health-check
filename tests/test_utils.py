"""Unit tests for modules.utils."""

import unittest

from modules.utils import bytes_to_human, classify, parse_float, parse_int, worst_status


class TestParsing(unittest.TestCase):
    def test_parse_float_valid(self):
        self.assertEqual(parse_float("42.5"), 42.5)

    def test_parse_float_with_percent_sign(self):
        self.assertEqual(parse_float("80%"), 80.0)

    def test_parse_float_invalid_returns_default(self):
        self.assertEqual(parse_float("not-a-number", default=1.5), 1.5)

    def test_parse_int_valid(self):
        self.assertEqual(parse_int("7"), 7)

    def test_parse_int_invalid_returns_default(self):
        self.assertEqual(parse_int("nope", default=3), 3)


class TestBytesToHuman(unittest.TestCase):
    def test_bytes(self):
        self.assertIn("B", bytes_to_human(500))

    def test_megabytes(self):
        self.assertIn("MB", bytes_to_human(5 * 1024 * 1024))

    def test_gigabytes(self):
        self.assertIn("GB", bytes_to_human(5 * 1024 ** 3))


class TestClassify(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(classify(50, warning=80, critical=90), "healthy")

    def test_warning(self):
        self.assertEqual(classify(85, warning=80, critical=90), "warning")

    def test_critical(self):
        self.assertEqual(classify(95, warning=80, critical=90), "critical")

    def test_boundary_is_warning_not_healthy(self):
        self.assertEqual(classify(80, warning=80, critical=90), "warning")

    def test_boundary_is_critical(self):
        self.assertEqual(classify(90, warning=80, critical=90), "critical")


class TestWorstStatus(unittest.TestCase):
    def test_critical_wins(self):
        self.assertEqual(worst_status("healthy", "warning", "critical"), "critical")

    def test_warning_wins_over_healthy(self):
        self.assertEqual(worst_status("healthy", "warning"), "warning")

    def test_all_healthy(self):
        self.assertEqual(worst_status("healthy", "healthy"), "healthy")

    def test_empty_returns_unknown(self):
        self.assertEqual(worst_status(), "unknown")


if __name__ == "__main__":
    unittest.main()
