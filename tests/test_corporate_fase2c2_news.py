"""Fase 2C-2 — Executive news with mocked RSS HTTP."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from corporate.web_api import CorporateWebAPI
from corporate_engine.executive_intel import news as exec_news


RSS_BBC = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>BBC Business</title>
<item>
  <title>Copper demand rises on energy transition</title>
  <link>https://www.bbc.co.uk/news/articles/copper-test-1</link>
  <pubDate>Thu, 17 Sep 2026 12:00:00 GMT</pubDate>
</item>
<item>
  <title>Global trade outlook updates</title>
  <link>https://www.bbc.co.uk/news/articles/trade-test-2</link>
  <pubDate>Thu, 17 Sep 2026 11:00:00 GMT</pubDate>
</item>
</channel></rss>
"""

RSS_CNBC = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>CNBC</title>
<item>
  <title>Markets watch central banks</title>
  <link>https://www.cnbc.com/2026/09/17/markets-test.html</link>
  <pubDate>Thu, 17 Sep 2026 10:00:00 GMT</pubDate>
</item>
</channel></rss>
"""

RSS_GNEWS_NAC = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Google News</title>
<item>
  <title>Inversión extranjera acelera en Chile - Diario Financiero</title>
  <link>https://news.google.com/rss/articles/ABC123</link>
  <pubDate>Thu, 17 Sep 2026 15:00:00 GMT</pubDate>
  <source url="https://www.df.cl">Diario Financiero</source>
</item>
<item>
  <title>Inversión extranjera acelera en Chile - Diario Financiero</title>
  <link>https://news.google.com/rss/articles/ABC123-DUP</link>
  <pubDate>Thu, 17 Sep 2026 15:00:00 GMT</pubDate>
  <source url="https://www.df.cl">Diario Financiero</source>
</item>
<item>
  <title>Regulación bancaria avanza en Congreso - Emol</title>
  <link>https://news.google.com/rss/articles/REG456</link>
  <pubDate>Thu, 17 Sep 2026 14:00:00 GMT</pubDate>
  <source url="https://www.emol.com">Emol</source>
</item>
</channel></rss>
"""

RSS_GNEWS_MIN = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title>Chile prevé caída en producción de cobre - Bloomberg Línea</title>
  <link>https://news.google.com/rss/articles/MIN789</link>
  <pubDate>Thu, 17 Sep 2026 16:00:00 GMT</pubDate>
  <source url="https://www.bloomberglinea.com">Bloomberg Línea</source>
</item>
</channel></rss>
"""

RSS_GNEWS_RE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title>Mercado inmobiliario de Santiago se estabiliza - La Tercera</title>
  <link>https://news.google.com/rss/articles/RE101</link>
  <pubDate>Thu, 17 Sep 2026 13:00:00 GMT</pubDate>
  <source url="https://www.latercera.com">La Tercera</source>
</item>
</channel></rss>
"""


def _fake_text(url, **kwargs):
    u = url.lower()
    if "bbci.co.uk" in u:
        return RSS_BBC
    if "cnbc.com" in u:
        return RSS_CNBC
    if "news.google.com" in u and "inmobiliario" in u:
        return RSS_GNEWS_RE
    if "news.google.com" in u and ("miner" in u or "cobre" in u or "copper" in u or "codelco" in u):
        return RSS_GNEWS_MIN
    if "news.google.com" in u and "gl=cl" in u:
        return RSS_GNEWS_NAC
    if "news.google.com" in u:
        return RSS_BBC
    raise AssertionError(f"unexpected url {url}")


def _fake_resolve(url, **kwargs):
    mapping = {
        "https://news.google.com/rss/articles/ABC123": "https://www.df.cl/economia/inversion-test",
        "https://news.google.com/rss/articles/ABC123-DUP": "https://www.df.cl/economia/inversion-test",
        "https://news.google.com/rss/articles/REG456": "https://www.emol.com/noticias/economia/regulacion-test",
        "https://news.google.com/rss/articles/MIN789": "https://www.bloomberglinea.com/2026/09/17/cobre-test",
        "https://news.google.com/rss/articles/RE101": "https://www.latercera.com/negocios/inmobiliario-test",
    }
    return mapping.get(url, url)


def _api(folder: Path) -> CorporateWebAPI:
    return CorporateWebAPI(folder / "mgc05", folder / "mgc03", folder / "lnh_corporate")


class ExecutiveNewsMockTests(unittest.TestCase):
    def test_news_board_fields_dedupe_and_platform_zero(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "lnh_corporate"
            root.mkdir()
            with patch("corporate_engine.executive_intel.news.http_get_text", side_effect=_fake_text), \
                 patch("corporate_engine.executive_intel.news.http_resolve_url", side_effect=_fake_resolve):
                board = exec_news.fetch_executive_news(corporate_root=root, force=True, limit=10)
                self.assertEqual(board["block"], "F2C-2")
                self.assertEqual(board["platform_calls"], 0)
                self.assertEqual(board["status"], "ACTUALIZADO")
                for cat in ("nacional", "internacional", "mineria", "inmobiliario"):
                    section = board["by_category"][cat]
                    self.assertGreaterEqual(section["item_count"], 1)
                    self.assertEqual(section["status"], "ACTUALIZADO")
                    for item in section["items"]:
                        for field in ("title", "source", "url", "published_at", "captured_at", "category", "status"):
                            self.assertIn(field, item)
                            self.assertTrue(item[field] not in (None, "") or field == "published_at")
                        self.assertTrue(str(item["url"]).startswith("http"))
                        self.assertNotIn("inventado", item["title"].lower())
                # Nacional dedupe: two google links same title/publisher article -> one kept after resolve
                nac = board["by_category"]["nacional"]
                self.assertGreaterEqual(nac["deduped_dropped"], 1)
                titles = [i["title"] for i in nac["items"]]
                self.assertEqual(len(titles), len(set(titles)))

    def test_web_api_news_endpoint_shape(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "lnh_corporate").mkdir()
            api = _api(folder)
            with patch("corporate_engine.executive_intel.news.http_get_text", side_effect=_fake_text), \
                 patch("corporate_engine.executive_intel.news.http_resolve_url", side_effect=_fake_resolve):
                payload = api.executive_news({"category": ["mineria"], "limit": ["5"], "force": ["1"]})
                self.assertEqual(payload["block"], "F2C-2")
                self.assertIn("mineria", payload["by_category"])
                self.assertEqual(payload["platform_calls"], 0)
                item = payload["by_category"]["mineria"]["items"][0]
                self.assertIn("cobre", item["title"].lower())


if __name__ == "__main__":
    unittest.main()
