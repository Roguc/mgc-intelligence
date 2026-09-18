"""Fase 2C-3 — Executive alerts: idempotency, resolution, persistence."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from corporate.web_api import CorporateWebAPI
from corporate_engine.executive_intel import alerts as exec_alerts


def _api(folder: Path) -> CorporateWebAPI:
    return CorporateWebAPI(folder / "mgc05", folder / "mgc03", folder / "lnh_corporate")


class ExecutiveAlertsTests(unittest.TestCase):
    def test_human_gate_idempotency_and_resolution(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "lnh_corporate"
            root.mkdir()
            cases = [
                {
                    "case_id": "case-hg-1",
                    "floor_id": "MGC-03",
                    "status": "READY",
                    "requires_decision": True,
                }
            ]
            with patch.object(exec_alerts, "_collect_overdues", return_value=[]), \
                 patch.object(exec_alerts, "_collect_expediente_due", return_value=[]), \
                 patch.object(exec_alerts, "_collect_board", return_value=[]), \
                 patch.object(exec_alerts, "_collect_communications", return_value=[]), \
                 patch.object(exec_alerts, "_collect_integrations", return_value=[]), \
                 patch.object(exec_alerts, "_collect_exec_intel", return_value=[]), \
                 patch.object(exec_alerts, "_collect_indicator_changes", return_value=[]), \
                 patch.object(exec_alerts, "_collect_news_signals", return_value=[]):
                first = exec_alerts.scan_executive_alerts(root, floor_cases=cases, include_external=False)
                self.assertEqual(first["platform_calls"], 0)
                listing = exec_alerts.list_executive_alerts(root, estado="ACTIVA")
                self.assertEqual(listing["counts"]["activa"], 1)
                alert = listing["alerts"][0]
                self.assertEqual(alert["tipo"], "HUMAN_GATE_PENDIENTE")
                self.assertEqual(alert["severidad"], "ALTA")
                for field in (
                    "alert_id", "tipo", "severidad", "titulo", "descripcion", "origen",
                    "detected_at", "estado", "responsable", "accion", "history",
                ):
                    self.assertIn(field, alert)

                # Second scan same condition → still one activa (idempotent)
                exec_alerts.scan_executive_alerts(root, floor_cases=cases, include_external=False)
                listing2 = exec_alerts.list_executive_alerts(root)
                activas = [a for a in listing2["alerts"] if a["estado"] == "ACTIVA"]
                self.assertEqual(len(activas), 1)
                self.assertEqual(activas[0]["alert_id"], alert["alert_id"])

                # Condition cleared → RESUELTA, history kept
                exec_alerts.scan_executive_alerts(root, floor_cases=[], include_external=False)
                listing3 = exec_alerts.list_executive_alerts(root)
                resolved = [a for a in listing3["alerts"] if a["alert_id"] == alert["alert_id"]][0]
                self.assertEqual(resolved["estado"], "RESUELTA")
                self.assertGreaterEqual(len(resolved["history"]), 2)
                # Does not disappear
                self.assertEqual(listing3["counts"]["total"], 1)

                # Operator discard is sticky even if condition returns
                updated = exec_alerts.set_alert_state(
                    root, alert["alert_id"], estado="DESCARTADA", actor="Presidencia", note="Prueba"
                )
                self.assertEqual(updated["estado"], "DESCARTADA")
                exec_alerts.scan_executive_alerts(root, floor_cases=cases, include_external=False)
                sticky = exec_alerts.list_executive_alerts(root)["alerts"][0]
                self.assertEqual(sticky["estado"], "DESCARTADA")
                self.assertEqual(sticky["alert_id"], alert["alert_id"])

    def test_platform_error_and_web_api_scan(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "lnh_corporate").mkdir()
            (folder / "mgc03").mkdir()
            (folder / "mgc05").mkdir()
            api = _api(folder)
            cases = [{
                "case_id": "case-err",
                "floor_id": "MGC-03",
                "status": "PLATFORM_EXECUTION_ERROR",
                "requires_decision": False,
            }]
            with patch.object(api, "cases", return_value=cases), \
                 patch.object(exec_alerts, "_collect_overdues", return_value=[]), \
                 patch.object(exec_alerts, "_collect_expediente_due", return_value=[]), \
                 patch.object(exec_alerts, "_collect_board", return_value=[]), \
                 patch.object(exec_alerts, "_collect_communications", return_value=[]), \
                 patch.object(exec_alerts, "_collect_integrations", return_value=[]), \
                 patch.object(exec_alerts, "_collect_exec_intel", return_value=[]), \
                 patch.object(exec_alerts, "_collect_indicator_changes", return_value=[]), \
                 patch.object(exec_alerts, "_collect_news_signals", return_value=[]):
                payload = api.scan_executive_alerts({"limit": 20})
                self.assertEqual(payload["block"], "F2C-3")
                self.assertEqual(payload["platform_calls"], 0)
                tipos = {a["tipo"] for a in payload["alerts"] if a["estado"] == "ACTIVA"}
                self.assertIn("CASE_PLATFORM_ERROR", tipos)

    def test_indicator_change_is_informativa(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "lnh_corporate"
            root.mkdir()
            snap = {
                "values": {
                    "libra_cobre": {"value": 6.0, "label": "Cobre (libra)", "unit": "USD/lb"},
                }
            }
            from corporate_engine.store import dump_json
            dump_json(exec_alerts._indicator_snap_path(root), snap)

            markets = {
                "status": "ACTUALIZADO",
                "indicators": [{
                    "key": "libra_cobre",
                    "label": "Cobre (libra)",
                    "value": 6.36,
                    "unit": "USD/lb",
                    "observed_at": "2026-09-18T00:00:00+00:00",
                    "source": "mindicador.cl",
                }],
            }
            economy = {"status": "ACTUALIZADO", "indicators": []}
            with patch("corporate_engine.executive_intel.alerts.exec_chile.fetch_chile_economy", return_value=economy), \
                 patch("corporate_engine.executive_intel.alerts.exec_chile.fetch_copper_market", return_value=markets):
                rows = exec_alerts._collect_indicator_changes(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["severidad"], "INFORMATIVA")
            self.assertEqual(rows[0]["tipo"], "INDICADOR_CAMBIO")


if __name__ == "__main__":
    unittest.main()
