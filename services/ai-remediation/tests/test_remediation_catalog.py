from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unittest

from app.remediation.catalog import load_catalog


class RemediationCatalogTests(unittest.TestCase):
    def test_restart_banking_backend_entry_is_bounded(self) -> None:
        catalog = load_catalog()
        entry = catalog["restart_banking_backend"]
        self.assertEqual(entry.risk_class, "low")
        self.assertEqual(entry.blast_radius, "low")
        self.assertTrue(entry.executable)
        self.assertEqual(entry.allowed_namespaces, ["bankapp"])
        self.assertEqual(entry.allowed_resource_kinds, ["Deployment"])
        self.assertEqual(entry.allowed_resource_names, ["banking-backend"])

    def test_non_executable_placeholders_remain_cataloged(self) -> None:
        catalog = load_catalog()
        self.assertFalse(catalog["restart_failed_pod"].executable)
        self.assertFalse(catalog["rollback_previous_revision"].executable)


if __name__ == "__main__":
    unittest.main()
