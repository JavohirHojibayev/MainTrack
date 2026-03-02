from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from app.core.esmo_client import EsmoClient
from app.core.esmo_poller import _resolve_esmo_terminal


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class EsmoParserRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = EsmoClient(base_url="https://example.invalid/cab/", username="u", password="p")

    def _read_fixture(self, filename: str) -> str:
        path = BACKEND_ROOT / filename
        return path.read_text(encoding="utf-8", errors="ignore")

    def test_monitor_popup_parses_passed_and_failed_rows(self) -> None:
        html = self._read_fixture("esmo_monitor_popup.html")
        soup = BeautifulSoup(html, "lxml")

        # Network detail fetch must not be used for this regression fixture.
        with patch.object(self.client, "_fetch_exam_detail", return_value={}):
            rows = self.client._parse_exam_rows(soup)

        self.assertGreaterEqual(len(rows), 20)
        result_counts: dict[str, int] = {}
        for row in rows:
            result = str(row.get("result"))
            result_counts[result] = result_counts.get(result, 0) + 1

        self.assertGreater(result_counts.get("passed", 0), 0)
        self.assertGreater(result_counts.get("failed", 0), 0)

    def test_detail_table_vitals_are_parsed(self) -> None:
        html = self._read_fixture("esmo_mo_sample.html")
        soup = BeautifulSoup(html, "lxml")
        vitals = self.client._extract_vitals_from_detail_table(soup)

        self.assertEqual(vitals["pressure_systolic"], 105)
        self.assertEqual(vitals["pressure_diastolic"], 61)
        self.assertEqual(vitals["pulse"], 77)
        self.assertAlmostEqual(float(vitals["temperature"]), 36.1, places=1)

    def test_manual_review_marker_maps_to_review(self) -> None:
        result = self.client._detect_exam_result(
            row_text="manual review required",
            comment_text="",
            admittance_text="",
            admittance_classes="dopusk_0",
        )
        self.assertEqual(result, "review")

    def test_terminal_slot_mapping_stays_stable(self) -> None:
        mapped = _resolve_esmo_terminal("terminal [10]")
        self.assertIsNotNone(mapped)
        self.assertEqual(mapped["name"], "TKM 4-terminal")


if __name__ == "__main__":
    unittest.main()
