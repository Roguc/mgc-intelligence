"""Extract sources/findings from professional deliverable or clean assistant text."""
from __future__ import annotations

import json
import re

from corporate_engine.contracts import finding as make_finding
from corporate_engine.contracts import source as make_source

MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", re.I)
URL_RE = re.compile(r"https?://[^\s)\]>'\"<>]+", re.I)
SOURCE_ID_RE = re.compile(r"\bS(?:RC)?-?(\d{1,3})\b", re.I)
JSON_HINTS = ('"findings"', '"sources"', '"evidence"')
FUENTES_HEAD = re.compile(r"^#{1,6}\s+(fuentes|referencias|sources|bibliography|bibliograf[íi]a)\b", re.I)
FINDING_HEAD = re.compile(
    r"^\s{0,3}(?:#{1,6}\s+)?(?:hallazgo|conclusi[oó]n|finding|conclusion)\b[:.\s-]*",
    re.I,
)
REJECT_URL = (
    "google.com/search", "google.com/js", "google.com/url", "gstatic.com", "googletag",
    "bing.com/ck", "bing.com/search", "bing.com/aclick",
    "duckduckgo.com", "html.duckduckgo.com",
    "facebook.com/sharer", "x.com/intent", "twitter.com/intent",
    "linkedin.com/share", "reddit.com/submit",
    "cloudfront.net", "w3.org/2000/svg", "wp-json", "oembed",
    "doubleclick.net", "googlesyndication",
)


def is_rejected_url(url: str) -> bool:
    blob = (url or "").casefold()
    return any(token in blob for token in REJECT_URL)


def professional_corpus(run: dict) -> tuple[str, str, str | None]:
    for item in run.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or "").strip()
        if content:
            name = str(item.get("name") or item.get("path") or "deliverable")
            return content, "artifact:" + name, item.get("artifact_id") or item.get("id")
    clean = str(run.get("assistant_output_clean") or run.get("assistant_output_raw") or "")
    return clean, "assistant_output_clean", None


def _json_payload(text: str):
    blob = text or ""
    if not any(hint in blob for hint in JSON_HINTS):
        return None
    start = blob.find("{")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(blob[start:])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _links(text: str, provenance: str) -> list[dict]:
    rows = []
    seen = set()
    for title, url in MD_LINK.findall(text or ""):
        url = url.rstrip(".,;")
        if is_rejected_url(url) or url in seen:
            continue
        seen.add(url)
        rows.append({"url": url, "title": title.strip(), "origin": "markdown_link",
                     "provenance": provenance, "excerpt": title.strip()[:240], "source_id": url})
    for url in URL_RE.findall(text or ""):
        url = url.rstrip(".,;)")
        if is_rejected_url(url) or url in seen:
            continue
        seen.add(url)
        rows.append({"url": url, "title": url, "origin": "explicit_url",
                     "provenance": provenance, "excerpt": url[:400], "source_id": url})
    in_fuentes = False
    for line in (text or "").splitlines():
        if FUENTES_HEAD.match(line.strip()):
            in_fuentes = True
            continue
        if in_fuentes and line.startswith("#"):
            in_fuentes = False
        if not in_fuentes:
            continue
        for url in URL_RE.findall(line):
            url = url.rstrip(".,;)")
            if is_rejected_url(url) or url in seen:
                continue
            seen.add(url)
            rows.append({"url": url, "title": line.strip()[:240], "origin": "fuentes_section",
                         "provenance": provenance, "excerpt": line.strip()[:400], "source_id": url})
    return rows


def _source_ids(text: str, provenance: str, existing: list[dict]) -> list[dict]:
    known = {str(item.get("source_id") or "") for item in existing}
    rows = []
    for match in SOURCE_ID_RE.finditer(text or ""):
        sid = "S" + match.group(1)
        if sid in known:
            continue
        known.add(sid)
        rows.append({
            "source_id": sid, "origin": "assistant_citation", "provenance": provenance,
            "excerpt": (text[max(0, match.start() - 80): match.end() + 80]).strip()[:400],
        })
    return rows


def _table_rows(text: str) -> list[list[str]]:
    rows = []
    lines = (text or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*-{3,}", lines[i + 1].strip().replace(":", "-")):
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if cells and not set("".join(cells)) <= set("-: "):
                    rows.append(cells)
                i += 1
            continue
        i += 1
    return rows


def _findings(text: str, provenance: str, sources: list[dict]) -> list[dict]:
    findings = []
    seen = set()
    source_urls = [item.get("url") for item in sources if item.get("url")]
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not FINDING_HEAD.match(stripped):
            continue
        statement = FINDING_HEAD.sub("", stripped).strip(" :-")
        if len(statement) < 40:
            continue
        key = statement[:180]
        if key in seen:
            continue
        seen.add(key)
        linked = [url for url in source_urls if url and url.rstrip("/") in stripped]
        findings.append({"statement": statement[:800], "origin": "deliverable_heading",
                         "provenance": provenance, "evidence_ids": linked})
    for row in _table_rows(text):
        statement = " | ".join(row)
        if len(statement) < 40:
            continue
        key = statement[:180]
        if key in seen:
            continue
        seen.add(key)
        linked = [url for url in source_urls if url and any(url.rstrip("/") in cell for cell in row)]
        findings.append({"statement": statement[:800], "origin": "deliverable_table",
                         "provenance": provenance, "evidence_ids": linked})
    return findings


def apply(run: dict) -> dict:
    case_id = str(run.get("case_id") or "")
    specialist_id = str(run.get("specialist_id") or "")
    run_id = str(run.get("run_id") or "")
    text, provenance, artifact_id = professional_corpus(run)
    parsed = _json_payload(text)
    raw_sources = []
    raw_findings = []
    if parsed:
        raw_sources.extend(list(parsed.get("sources") or []) if isinstance(parsed.get("sources"), list) else [])
        raw_findings.extend(list(parsed.get("findings") or []) if isinstance(parsed.get("findings"), list) else [])
    raw_sources.extend(_links(text, provenance))
    raw_sources.extend(_source_ids(text, provenance, raw_sources))
    raw_findings.extend(_findings(text, provenance, raw_sources))
    sources = []
    for item in raw_sources:
        if not isinstance(item, dict):
            continue
        sources.append(make_source(
            case_id=case_id, specialist_id=specialist_id, run_id=run_id,
            url=item.get("url"), title=item.get("title") or "", origin=item.get("origin") or "",
            provenance=item.get("provenance") or provenance, excerpt=item.get("excerpt") or "",
            artifact_id=artifact_id, source_id=item.get("source_id"),
        ))
    findings = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        statement = str(item.get("statement") or item.get("claim") or "").strip()
        if not statement:
            continue
        findings.append(make_finding(
            case_id=case_id, specialist_id=specialist_id, run_id=run_id, statement=statement[:800],
            origin=item.get("origin") or "", provenance=item.get("provenance") or provenance,
            evidence_ids=item.get("evidence_ids") or item.get("evidence") or [],
            artifact_id=artifact_id,
        ))
    missing = list(run.get("missing_data") or [])
    assistant = str(run.get("assistant_output_clean") or run.get("assistant_output_raw") or "")
    if not assistant.strip() and not text.strip() and "assistant_output" not in missing:
        missing.append("assistant_output")
    if not sources and "sources" not in missing:
        missing.append("sources")
    if not findings and "findings" not in missing:
        missing.append("findings")
    has_artifact = any(isinstance(item, dict) and str(item.get("content") or "").strip() for item in (run.get("artifacts") or []))
    missing_deliverable = any(str(item).startswith("deliverable:") for item in missing)
    professional = has_artifact or (
        bool(text.strip()) and not missing_deliverable and (len(text.strip()) >= 400 or bool(sources))
    )
    if run.get("errors"):
        status = "FAILED"
    elif not assistant.strip() and not has_artifact:
        status = "FAILED"
    elif professional and (sources or findings) and not missing_deliverable:
        status = "COMPLETED"
    else:
        status = "INCOMPLETE"
    run["sources"] = sources
    run["findings"] = findings
    run["missing_data"] = missing
    run["status"] = status
    run["updated_at"] = run.get("updated_at")
    return run
