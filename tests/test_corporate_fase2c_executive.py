"""Fase 2C-1 — Executive intel (weather/economy/markets) with mocked HTTP."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from corporate.web_api import CorporateWebAPI
from corporate_engine.executive_intel import board as exec_board
from corporate_engine.executive_intel import chile_indicators, weather
from corporate_engine.executive_intel.http_util import ProviderHttpError


WEATHER_FIXTURE = {
    "timezone": "America/Santiago",
    "current": {
        "time": "2026-09-18T12:00",
        "temperature_2m": 14.2,
        "relative_humidity_2m": 70,
        "weather_code": 1,
        "wind_speed_10m": 8.0,
    },
    "daily": {
        "time": ["2026-09-18", "2026-09-19"],
        "weather_code": [1, 2],
        "temperature_2m_max": [18.0, 17.0],
        "temperature_2m_min": [8.0, 7.5],
        "precipitation_sum": [0.0, 1.2],
    },
}

ECONOMY_FIXTURE = {
    "uf": {"codigo": "uf", "nombre": "UF", "unidad_medida": "Pesos", "fecha": "2026-09-18T03:00:00.000Z", "valor": 40959.07},
    "utm": {"codigo": "utm", "nombre": "UTM", "unidad_medida": "Pesos", "fecha": "2026-09-01T04:00:00.000Z", "valor": 71721},
    "dolar": {"codigo": "dolar", "nombre": "Dólar", "unidad_medida": "Pesos", "fecha": "2026-09-17T03:00:00.000Z", "valor": 954.85},
    "ipc": {"codigo": "ipc", "nombre": "IPC", "unidad_medida": "Porcentaje", "fecha": "2025-12-01T03:00:00.000Z", "valor": -0.2},
    "tpm": {"codigo": "tpm", "nombre": "TPM", "unidad_medida": "Porcentaje", "fecha": "2026-09-17T03:00:00.000Z", "valor": 4.5},
}

COPPER_FIXTURE = {
    "codigo": "libra_cobre",
    "nombre": "Libra de Cobre",
    "unidad_medida": "Dólar",
    "serie": [{"fecha": "2026-09-17T03:00:00.000Z", "valor": 6.36}],
}


def _api(folder: Path) -> CorporateWebAPI:
    return CorporateWebAPI(folder / "mgc05", folder / "mgc03", folder / "lnh_corporate")


class ExecutiveIntelMockTests(unittest.TestCase):
    def test_board_with_mocks_and_cache(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "lnh_corporate"
            root.mkdir()

            def fake_get(url, **kwargs):
                if "open-meteo" in url:
                    return dict(WEATHER_FIXTURE)
                if url.endswith("/api/libra_cobre") or "libra_cobre" in url:
                    return dict(COPPER_FIXTURE)
                if url.rstrip("/").endswith("/api"):
                    return dict(ECONOMY_FIXTURE)
                raise ProviderHttpError(f"unexpected url {url}")

            with patch("corporate_engine.executive_intel.weather.http_get_json", side_effect=fake_get), \
                 patch("corporate_engine.executive_intel.chile_indicators.http_get_json", side_effect=fake_get):
                first = exec_board.executive_board(root, force=True)
                self.assertEqual(first["platform_calls"], 0)
                self.assertEqual(first["weather"]["status"], "ACTUALIZADO")
                self.assertEqual(first["weather"]["current"]["temperature_c"], 14.2)
                self.assertEqual(len(first["economy"]["indicators"]), 5)
                self.assertTrue(all(i["value"] is not None for i in first["economy"]["indicators"]))
                self.assertEqual(first["markets"]["indicators"][0]["key"], "libra_cobre")
                self.assertEqual(first["markets"]["indicators"][0]["value"], 6.36)
                # Required fields on each economy datum
                for item in first["economy"]["indicators"]:
                    for field in ("value", "unit", "source", "observed_at", "fetched_at", "status"):
                        self.assertIn(field, item)

                second = exec_board.executive_board(root, force=False)
                self.assertTrue(second["weather"].get("cache_hit"))
                self.assertTrue(second["economy"].get("cache_hit"))
                self.assertTrue(second["markets"].get("cache_hit"))

    def test_unavailable_on_http_error_without_cache(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "lnh_corporate"
            root.mkdir()
            with patch(
                "corporate_engine.executive_intel.weather.http_get_json",
                side_effect=ProviderHttpError("down", status=500),
            ):
                payload = weather.fetch_santiago_weather(corporate_root=root, force=True)
                self.assertEqual(payload["status"], "NO_DISPONIBLE")
                self.assertIsNone(payload.get("current"))
                self.assertEqual(payload["platform_calls"], 0)

    def test_api_surface(self):
        with TemporaryDirectory() as tmp:
            api = _api(Path(tmp))
            with patch("corporate_engine.executive_intel.weather.http_get_json", return_value=WEATHER_FIXTURE), \
                 patch("corporate_engine.executive_intel.chile_indicators.http_get_json", side_effect=[ECONOMY_FIXTURE, COPPER_FIXTURE]):
                board = api.executive_board({"force": ["1"]})
                self.assertEqual(board["block"], "F2C-1")
                self.assertEqual(board["platform_calls"], 0)
                wx = api.executive_weather({})
                self.assertEqual(wx["status"], "ACTUALIZADO")


if __name__ == "__main__":
    unittest.main()
