"""Fase 2C-2 — Executive news feeds (fetch / normalize / dedupe / cache only).

No AI analysis, scoring or recommendations. platform_calls remain 0.
"""
from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import quote_plus, urlparse

from corporate_engine.executive_intel import (
    NEWS_CATEGORIES,
    STATUS_ACTUALIZADO,
    STATUS_DESACTUALIZADO,
    STATUS_NO_DISPONIBLE,
    STALE_NEWS_SEC,
    TTL_NEWS_SEC,
)
from corporate_engine.executive_intel import cache as intel_cache
from corporate_engine.executive_intel.http_util import ProviderHttpError, http_get_text, http_resolve_url
from corporate_engine.store import now

CATEGORY_LABELS = {
    "nacional": "Nacional",
    "internacional": "Internacional",
    "mineria": "Minería",
    "inmobiliario": "Inmobiliario",
}

# Verified working public feeds (probed 2026-09-18). Google News aggregates recognized publishers.
FEEDS = {
    "nacional": [
        {
            "id": "gnews-cl-economia",
            "name": "Google News — economía Chile",
            "url": (
                "https://news.google.com/rss/search?q="
                + quote_plus("economía OR empresas OR regulación OR inversión Chile")
                + "&hl=es-419&gl=CL&ceid=CL:es-419"
            ),
            "publisher_hint": "Google News",
        },
    ],
    "internacional": [
        {
            "id": "bbc-business",
            "name": "BBC News Business",
            "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
            "publisher_hint": "BBC News",
        },
        {
            "id": "cnbc-world-economy",
            "name": "CNBC World Economy",
            "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
            "publisher_hint": "CNBC",
        },
        {
            "id": "gnews-intl-economy",
            "name": "Google News — economía internacional",
            "url": (
                "https://news.google.com/rss/search?q="
                + quote_plus(
                    '"world economy" OR "international trade" OR "central bank" OR IMF OR WTO OR "interest rates" OR geopolitics economy'
                )
                + "&hl=en-US&gl=US&ceid=US:en"
            ),
            "publisher_hint": "Google News",
        },
    ],
    "mineria": [
        {
            "id": "gnews-mining-copper",
            "name": "Google News — minería y cobre",
            "url": (
                "https://news.google.com/rss/search?q="
                + quote_plus('minería OR cobre OR commodities OR Codelco OR Cochilco OR "copper price"')
                + "&hl=es-419&gl=CL&ceid=CL:es-419"
            ),
            "publisher_hint": "Google News",
        },
    ],
    "inmobiliario": [
        {
            "id": "gnews-real-estate-cl",
            "name": "Google News — inmobiliario Chile",
            "url": (
                "https://news.google.com/rss/search?q="
                + quote_plus(
                    '"mercado inmobiliario" OR "sector inmobiliario" OR "bienes raíces" '
                    'OR construcción viviendas OR CChC Chile'
                )
                + "&hl=es-419&gl=CL&ceid=CL:es-419"
            ),
            "publisher_hint": "Google News",
        },
    ],
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(value: str) -> str:
    text = unescape(_TAG_RE.sub(" ", value or ""))
    return _WS_RE.sub(" ", text).strip()


def _parse_pubdate(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            return dt.isoformat() + "Z"
        return dt.astimezone().isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def _normalize_title(title: str, source: str | None = None) -> str:
    clean = _strip_html(title)
    if source:
        suffix = f" - {source}"
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)].strip()
        # Google sometimes prefixes source with "- "
        alt = f" - - {source.lstrip('- ').strip()}"
        if clean.endswith(alt):
            clean = clean[: -len(alt)].strip()
    return clean


def _title_fingerprint(title: str) -> str:
    base = re.sub(r"[^a-z0-9áéíóúñü]+", "", title.lower())
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:20]


def _url_fingerprint(url: str) -> str:
    parsed = urlparse(url or "")
    # Drop query noise for google/news redirect stability when already resolved
    key = f"{parsed.netloc.lower()}{parsed.path}".rstrip("/").lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]


def _item_id(category: str, url: str, title: str) -> str:
    raw = f"{category}|{url}|{title}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def _parse_rss_items(xml_text: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise ProviderHttpError(f"Invalid RSS XML: {error}") from error
    items = []
    for node in root.findall(".//item"):
        title = _strip_html(node.findtext("title") or "")
        link = (node.findtext("link") or "").strip()
        if not title or not link:
            continue
        source_el = node.find("source")
        source_name = _strip_html(source_el.text or "") if source_el is not None else ""
        source_home = (source_el.get("url") or "").strip() if source_el is not None else ""
        pub = _parse_pubdate(node.findtext("pubDate"))
        items.append({
            "title_raw": title,
            "link": link,
            "published_at": pub,
            "source_name": source_name.lstrip("- ").strip(),
            "source_home": source_home,
        })
    return items


def _should_resolve(url: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    return "news.google.com" in host


def _build_article(category: str, feed: dict, raw: dict, captured_at: str) -> dict:
    source_name = raw.get("source_name") or feed.get("publisher_hint") or "Fuente"
    title = _normalize_title(raw.get("title_raw") or "", source_name)
    link = raw.get("link") or ""
    return {
        "id": _item_id(category, link, title),
        "title": title,
        "source": source_name,
        "source_home": raw.get("source_home") or None,
        "url": link,
        "feed_url": link,
        "published_at": raw.get("published_at"),
        "captured_at": captured_at,
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category),
        "status": STATUS_ACTUALIZADO,
        "feed_id": feed["id"],
        "feed_name": feed["name"],
        "title_fp": _title_fingerprint(title),
        "url_fp": _url_fingerprint(link),
    }


def _resolve_article_urls(items: list[dict]) -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _one(art: dict) -> dict:
        link = art.get("url") or ""
        final = http_resolve_url(link, timeout=6) if _should_resolve(link) else link
        updated = dict(art)
        updated["url"] = final or link
        updated["url_fp"] = _url_fingerprint(final or link)
        updated["id"] = _item_id(art.get("category") or "", final or link, art.get("title") or "")
        return updated

    if not items:
        return []
    if not any(_should_resolve(a.get("url") or "") for a in items):
        return items

    resolved: list[dict | None] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=min(8, len(items))) as pool:
        futures = {pool.submit(_one, art): idx for idx, art in enumerate(items)}
        for fut in as_completed(futures):
            resolved[futures[fut]] = fut.result()
    return [item for item in resolved if item is not None]


def _dedupe(articles: list[dict]) -> tuple[list[dict], int]:
    seen_url: set[str] = set()
    seen_title: set[str] = set()
    out: list[dict] = []
    dropped = 0
    for art in articles:
        ufp = art.get("url_fp") or ""
        tfp = art.get("title_fp") or ""
        if (ufp and ufp in seen_url) or (tfp and tfp in seen_title):
            dropped += 1
            continue
        if ufp:
            seen_url.add(ufp)
        if tfp:
            seen_title.add(tfp)
        out.append(art)
    return out, dropped


def _fetch_category(category: str, *, corporate_root=None, force: bool = False, limit: int = 12) -> dict:
    cache_key = f"news_{category}"
    if not force:
        entry = intel_cache.read_entry(corporate_root, cache_key)
        age = intel_cache.age_seconds(entry)
        if entry and age is not None and age < TTL_NEWS_SEC and isinstance(entry.get("payload"), dict):
            return entry["payload"]

    captured_at = now()
    feed_errors: list[dict] = []
    collected: list[dict] = []

    for feed in FEEDS.get(category, []):
        try:
            xml_text = http_get_text(feed["url"], timeout=25)
            parsed = _parse_rss_items(xml_text)
            for raw in parsed[:20]:
                collected.append(_build_article(category, feed, raw, captured_at))
        except ProviderHttpError as error:
            feed_errors.append({"feed_id": feed["id"], "error": str(error), "url": feed["url"]})
        except Exception as error:  # noqa: BLE001 — isolate feed failures
            feed_errors.append({"feed_id": feed["id"], "error": str(error), "url": feed["url"]})

    deduped, dropped = _dedupe(collected)
    # Prefer fresher items; when tied, prefer direct publisher URLs over Google News gateways.
    deduped.sort(
        key=lambda a: (
            a.get("published_at") or "",
            0 if "news.google.com" in (urlparse(a.get("url") or "").netloc.lower()) else 1,
        ),
        reverse=True,
    )
    items = _resolve_article_urls(deduped[:limit])
    # Re-dedupe after URL resolution (same publisher article via different google links)
    items, dropped_post = _dedupe(items)
    dropped += dropped_post
    items = items[:limit]

    if items:
        payload = {
            "category": category,
            "category_label": CATEGORY_LABELS.get(category, category),
            "status": STATUS_ACTUALIZADO,
            "fetched_at": captured_at,
            "item_count": len(items),
            "deduped_dropped": dropped,
            "items": items,
            "feeds": [{"id": f["id"], "name": f["name"], "url": f["url"]} for f in FEEDS.get(category, [])],
            "errors": feed_errors,
            "platform_calls": 0,
        }
        intel_cache.write_entry(corporate_root, cache_key, payload)
        return payload

    # Fallback to cache if any
    entry = intel_cache.read_entry(corporate_root, cache_key)
    age = intel_cache.age_seconds(entry)
    if entry and isinstance(entry.get("payload"), dict) and (entry["payload"].get("items") or []):
        stale = dict(entry["payload"])
        stale["status"] = STATUS_DESACTUALIZADO if (age or 0) < STALE_NEWS_SEC else STATUS_NO_DISPONIBLE
        for item in stale.get("items") or []:
            item["status"] = stale["status"]
        stale["errors"] = feed_errors
        stale["fetched_at"] = stale.get("fetched_at") or captured_at
        stale["platform_calls"] = 0
        return stale

    payload = {
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category),
        "status": STATUS_NO_DISPONIBLE,
        "fetched_at": captured_at,
        "item_count": 0,
        "deduped_dropped": dropped,
        "items": [],
        "feeds": [{"id": f["id"], "name": f["name"], "url": f["url"]} for f in FEEDS.get(category, [])],
        "errors": feed_errors or [{"error": "Sin ítems recuperados de fuentes verificadas"}],
        "platform_calls": 0,
    }
    intel_cache.write_entry(corporate_root, cache_key, payload)
    return payload


def fetch_executive_news(
    *,
    corporate_root=None,
    force: bool = False,
    category: str | None = None,
    limit: int = 12,
) -> dict:
    """Return news board for one category or all four."""
    cats = [category] if category else list(NEWS_CATEGORIES)
    normalized = []
    for cat in cats:
        key = (cat or "").strip().lower()
        # Accept UI labels
        aliases = {
            "nacional": "nacional",
            "internacional": "internacional",
            "mineria": "mineria",
            "minería": "mineria",
            "inmobiliario": "inmobiliario",
        }
        mapped = aliases.get(key)
        if mapped:
            normalized.append(mapped)

    if not normalized:
        normalized = list(NEWS_CATEGORIES)

    by_category = {}
    for cat in normalized:
        by_category[cat] = _fetch_category(cat, corporate_root=corporate_root, force=force, limit=limit)

    statuses = [section.get("status") for section in by_category.values()]
    if statuses and all(s == STATUS_ACTUALIZADO for s in statuses):
        board_status = STATUS_ACTUALIZADO
    elif any(s in (STATUS_ACTUALIZADO, STATUS_DESACTUALIZADO) for s in statuses):
        board_status = STATUS_DESACTUALIZADO if any(s != STATUS_ACTUALIZADO for s in statuses) else STATUS_ACTUALIZADO
    else:
        board_status = STATUS_NO_DISPONIBLE

    return {
        "block": "F2C-2",
        "title": "Noticias ejecutivas — Presidencia",
        "generated_at": now(),
        "status": board_status,
        "categories": list(NEWS_CATEGORIES),
        "category_labels": dict(CATEGORY_LABELS),
        "by_category": by_category,
        "sources": [
            {"id": f["id"], "name": f["name"], "url": f["url"], "category": cat}
            for cat, feeds in FEEDS.items()
            for f in feeds
        ],
        "notes": [
            "Sin análisis inteligente ni recomendaciones en backend.",
            "Estados: ACTUALIZADO | DESACTUALIZADO | NO_DISPONIBLE.",
            "Fuentes verificadas vía RSS públicos (BBC, CNBC, Google News).",
        ],
        "platform_calls": 0,
    }
