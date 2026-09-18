"""Recover specialist-authored artifacts from turn events. Never invent content."""
from __future__ import annotations

import re
from pathlib import Path

from corporate_engine.classify import looks_like_runtime_pollution
from corporate_engine.contracts import artifact as make_artifact

WORKSPACE_FILE = re.compile(
    r"/workspace/outputs/([A-Za-z0-9][A-Za-z0-9._-]{0,180}\.(?:md|csv|txt|json))",
    re.I,
)
HEREDOC = re.compile(
    r"""(?:cat|tee)\s+>\s*([^\s<>]+)\s*<<[-]?['"]?(\w+)['"]?\n(.*)\n\2""",
    re.S,
)
COPY_TO_OUTPUTS = re.compile(
    r"""\b(?:cp|mv)\s+(\S+)\s+(/workspace/outputs/[A-Za-z0-9._-]+\.(?:md|csv|txt|json))""",
    re.I,
)
CAT_WORKSPACE = re.compile(
    r"""\b(?:cat|less|head|tail)\s+(/workspace/outputs/[A-Za-z0-9._-]+\.(?:md|csv|txt|json))""",
    re.I,
)


def cited_output_paths(text: str) -> list[str]:
    seen = []
    for match in WORKSPACE_FILE.finditer(text or ""):
        path = "/workspace/outputs/" + match.group(1)
        if path not in seen:
            seen.append(path)
    return seen


def _heredocs(blob: str) -> dict[str, str]:
    found = {}
    for match in HEREDOC.finditer(blob or ""):
        path = match.group(1).strip().strip("'\"")
        body = match.group(3)
        if path and body.strip():
            found[path] = body
    return found


def is_professional_markdown(text: str) -> bool:
    blob = (text or "").strip()
    if len(blob) < 400 or looks_like_runtime_pollution(blob):
        return False
    if blob.lstrip().startswith("{") and '"ok"' in blob[:80]:
        return False
    headings = blob.count("\n# ") + blob.count("\n## ") + (1 if blob.startswith("# ") else 0)
    return headings >= 2 or ("| ---" in blob and "\n# " in blob) or blob.count("\n## ") >= 2


def capture_artifacts(events: list, assistant_text: str, *, case_id: str = "", specialist_id: str = "",
                      run_id: str = "", workstream_id: str = "") -> tuple[list[dict], list[str]]:
    cited = cited_output_paths(assistant_text)
    for event in events or []:
        cited.extend(cited_output_paths(str(event.get("name") or "")))
        cited.extend(cited_output_paths(str(event.get("text") or "")))
    cited = list(dict.fromkeys(cited))
    written: dict[str, str] = {}
    copies: list[tuple[str, str]] = []
    for event in events or []:
        itype = str(event.get("type") or "").casefold()
        kind = str(event.get("kind") or "")
        if kind not in {"shell", "http", "system", "runtime", "error"} and itype != "command_execution":
            continue
        blob = "\n".join([str(event.get("name") or ""), str(event.get("text") or "")])
        written.update(_heredocs(blob))
        for match in COPY_TO_OUTPUTS.finditer(blob):
            copies.append((match.group(1), match.group(2)))
        stdout = str(event.get("text") or "")
        if stdout.strip() and is_professional_markdown(stdout):
            for match in CAT_WORKSPACE.finditer(blob):
                written[match.group(1)] = stdout
    for src, dst in copies:
        if src in written and dst not in written:
            written[dst] = written[src]
        src_name = Path(src).name
        for path, body in list(written.items()):
            if Path(path).name == src_name and dst not in written:
                written[dst] = body
    artifacts = []
    missing = []
    seen = set()
    targets = cited or [path for path in written if path.startswith("/workspace/outputs/")]
    for path in targets:
        name = Path(path).name
        if name in seen:
            continue
        body = written.get(path)
        if not body:
            for candidate, content in written.items():
                if Path(candidate).name == name:
                    body = content
                    break
        if not body or not is_professional_markdown(body):
            if path in cited or name in {Path(item).name for item in cited}:
                missing.append("deliverable:" + name)
            continue
        seen.add(name)
        artifacts.append(make_artifact(
            case_id=case_id, specialist_id=specialist_id, run_id=run_id, workstream_id=workstream_id,
            name=name, content=body, path=path, origin="specialist_authored_workspace_file",
        ))
    return artifacts, missing
