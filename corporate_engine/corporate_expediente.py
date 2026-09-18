"""Expediente Corporativo LNH — LNH-DATA-001 governance nucleus (Block 1).

Deterministic persistence, identity, versioning, audit events, and empty
containers for tasks / Platform / Directorio / decisions / evidence.
No cognitive interpretation. No Platform calls.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import shutil
from typing import Iterable
from uuid import uuid4

from corporate_engine.corporate_statuses import (
    AMBITOS,
    ENVIADO,
    PRIORIDADES,
    REGISTRADO,
    TIPOS,
    assert_state,
    assert_transition,
)
from corporate_engine.store import dump_json, load_json, now

SCHEMA = "LNH-DATA-001"
VERSION_LABEL = "v001"
ACTOR_PRESIDENCIA = "Presidencia LNH"
ACTOR_TYPE_HUMAN = "human"
ACTOR_TYPE_SYSTEM = "system"


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid4().hex}" if prefix else uuid4().hex


def expediente_id_for(asunto: str) -> str:
    slug = re.sub("[^a-z0-9]+", "-", (asunto or "").casefold()).strip("-")[:24] or "instruccion"
    stamp = now().replace("-", "").replace(":", "").replace("+", "").replace(".", "")[:15]
    return f"LNH-{stamp}-{slug}"


def normalize_ambito(value: str) -> str:
    raw = (value or "").strip()
    if raw in {"HOLDING", "Holding", "holding"}:
        return "Holding completo"
    if raw == "Holding completo":
        return raw
    if raw in AMBITOS:
        return raw
    raise ValueError("Ámbito no válido. Use LNH, MGC, LNR o Holding completo.")


def normalize_tipo(value: str) -> str:
    raw = (value or "").strip()
    if raw not in TIPOS:
        raise ValueError("Tipo de instrucción no válido según LNH-DATA-001.")
    return raw


def normalize_prioridad(value: str) -> str:
    raw = (value or "").strip().upper()
    if raw not in PRIORIDADES:
        raise ValueError("Prioridad no válida. Use P0, P1, P2 o P3.")
    return raw


def audit_event(
    *,
    expediente_id: str,
    actor: str,
    actor_type: str,
    accion: str,
    objeto_afectado: str | None = None,
    estado_anterior: str | None = None,
    estado_nuevo: str | None = None,
    referencia_version: str | None = None,
    motivo: str | None = None,
    correlation_id: str | None = None,
    payload: dict | None = None,
) -> dict:
    return {
        "event_id": _new_id("evt-"),
        "expediente_id": expediente_id,
        "timestamp": now(),
        "actor": actor,
        "actor_type": actor_type,
        "accion": accion,
        "objeto_afectado": objeto_afectado,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "referencia_version": referencia_version,
        "motivo": motivo,
        "correlation_id": correlation_id or _new_id("cor-"),
        "payload": payload or {},
    }


def document_record(
    *,
    name: str,
    path: str,
    digest: str,
    version: str,
    origen: str,
    autor: str,
    document_id: str | None = None,
) -> dict:
    return {
        "document_id": document_id or _new_id("doc-"),
        "nombre": name,
        "tipo": Path(name).suffix.lower().lstrip(".") or "bin",
        "version": version,
        "origen": origen,
        "fecha": now(),
        "autor": autor,
        "hash_sha256": digest,
        "path": path,
        "permisos": {"lectura": ["Presidencia", "Corporate Office"]},
    }


def task_record(
    *,
    expediente_id: str,
    requested_by: str,
    assigned_to: str,
    deliverable_type: str,
    objective: str,
    due_at: str | None = None,
    dependencies: list | None = None,
    status: str = "PENDIENTE",
    priority: str | None = None,
    platform_session_id: str | None = None,
    result_id: str | None = None,
    gate_after: str | None = None,
    role: str | None = None,
) -> dict:
    return {
        "task_id": _new_id("tsk-"),
        "expediente_id": expediente_id,
        "requested_by": requested_by,
        "assigned_to": assigned_to,
        "deliverable_type": deliverable_type,
        "objective": objective,
        "created_at": now(),
        "due_at": due_at,
        "priority": priority,
        "dependencies": list(dependencies or []),
        "status": status,
        "platform_session_id": platform_session_id,
        "result_id": result_id,
        "gate_after": gate_after,
        "role": role,
        "escalamiento": None,
        "blocked_by": [],
    }


def dependency_record(
    *,
    expediente_id: str,
    prerequisite_task_id: str,
    dependent_task_id: str,
    kind: str = "must_complete_before",
) -> dict:
    return {
        "dependency_id": _new_id("dep-"),
        "expediente_id": expediente_id,
        "prerequisite_task_id": prerequisite_task_id,
        "dependent_task_id": dependent_task_id,
        "kind": kind,
        "created_at": now(),
    }


def save_expediente(case: Path, master: dict) -> None:
    case = Path(case)
    dump_json(case / "expediente.json", master)
    _write_sidecar(case, master)


def platform_session_stub(**fields) -> dict:
    return {
        "platform_session_id": fields.get("platform_session_id"),
        "agent_id": fields.get("agent_id"),
        "task_id": fields.get("task_id"),
        "expediente_id": fields.get("expediente_id"),
        "started_at": fields.get("started_at"),
        "completed_at": fields.get("completed_at"),
        "status": fields.get("status"),
        "turn_event_references": list(fields.get("turn_event_references") or []),
        "result_id": fields.get("result_id"),
        "usage_cost": fields.get("usage_cost"),
        "error": fields.get("error"),
    }


def board_session_stub(**fields) -> dict:
    return {
        "board_session_id": fields.get("board_session_id") or _new_id("brd-"),
        "tipo": fields.get("tipo"),
        "fecha": fields.get("fecha"),
        "agenda": list(fields.get("agenda") or []),
        "base_version": fields.get("base_version"),
        "director_runs": list(fields.get("director_runs") or []),
        "votes": list(fields.get("votes") or []),
        "quorum_ia": fields.get("quorum_ia"),
        "human_decision": fields.get("human_decision"),
        "minutes": fields.get("minutes"),
        "expediente_ids": list(fields.get("expediente_ids") or []),
    }


def decision_record(**fields) -> dict:
    return {
        "decision_id": fields.get("decision_id") or _new_id("dec-"),
        "expediente_id": fields["expediente_id"],
        "authority": fields.get("authority") or ACTOR_PRESIDENCIA,
        "decision": fields["decision"],
        "conditions": fields.get("conditions"),
        "rationale": fields.get("rationale"),
        "decided_at": fields.get("decided_at") or now(),
        "based_on_version": fields.get("based_on_version"),
        "resulting_actions": list(fields.get("resulting_actions") or []),
        "legal_formality": fields.get("legal_formality"),
    }


def evidence_record(**fields) -> dict:
    return {
        "evidence_id": fields.get("evidence_id") or _new_id("evd-"),
        "tipo": fields.get("tipo"),
        "fuente_o_documento": fields.get("fuente_o_documento"),
        "afirmacion_o_decision": fields.get("afirmacion_o_decision"),
        "nivel_verificacion": fields.get("nivel_verificacion"),
        "expediente_id": fields.get("expediente_id"),
    }


def source_record(**fields) -> dict:
    return {
        "source_id": fields.get("source_id") or _new_id("src-"),
        "referencia": fields.get("referencia"),
        "titulo": fields.get("titulo"),
        "fecha_consulta": fields.get("fecha_consulta"),
        "agente": fields.get("agente"),
        "relacion_hallazgo": fields.get("relacion_hallazgo"),
        "expediente_id": fields.get("expediente_id"),
    }


def _empty_collections() -> dict:
    return {
        "encargos": [],
        "documentos": [],
        "fuentes": [],
        "evidencias": [],
        "platform_sessions": [],
        "board_sessions": [],
        "decisiones": [],
        "dependencias": [],
        "historial_versiones": [],
        "eventos": [],
        "resultados": [],
        "calendar_events": [],
        "communications": [],
    }


def _write_sidecar(folder: Path, master: dict) -> None:
    dump_json(folder / "events.json", master["eventos"])
    dump_json(folder / "tasks.json", master["encargos"])
    dump_json(folder / "documents_meta.json", master["documentos"])
    dump_json(folder / "sources.json", master["fuentes"])
    dump_json(folder / "evidences.json", master["evidencias"])
    dump_json(folder / "platform_sessions.json", master["platform_sessions"])
    dump_json(folder / "board_sessions.json", master["board_sessions"])
    dump_json(folder / "decisions.json", master["decisiones"])
    dump_json(folder / "dependencies.json", master["dependencias"])
    dump_json(folder / "versions_index.json", master["historial_versiones"])
    dump_json(folder / "resultados.json", master.get("resultados") or [])
    dump_json(folder / "calendar_events.json", master.get("calendar_events") or [])
    dump_json(folder / "communications.json", master.get("communications") or [])


def _persist_documents(case: Path, paths: Iterable[Path], *, version: str, autor: str) -> list[dict]:
    target_dir = case / "documents"
    target_dir.mkdir(parents=True, exist_ok=True)
    documents = []
    for source in paths:
        target = target_dir / source.name
        number = 2
        while target.exists():
            target = target_dir / f"{source.stem}-{number}{source.suffix}"
            number += 1
        shutil.copy2(source, target)
        relative = str(target.relative_to(case)).replace("\\", "/")
        digest = sha256(target.read_bytes()).hexdigest()
        documents.append(document_record(
            name=target.name,
            path=relative,
            digest=digest,
            version=version,
            origen="adjunto_presidencial",
            autor=autor,
        ))
    return documents


def _version_snapshot(master: dict) -> dict:
    return {
        "version": master["version_actual"],
        "created_at": now(),
        "estado_actual": master["estado_actual"],
        "asunto": master["asunto"],
        "document_ids": [d["document_id"] for d in master["documentos"]],
        "task_ids": [t["task_id"] for t in master["encargos"]],
        "event_ids": [e["event_id"] for e in master["eventos"]],
        "instruccion_original_sha256": sha256(
            master["instruccion_original"].encode("utf-8")
        ).hexdigest(),
    }


def open_corporate_expediente(
    root: Path,
    *,
    tipo: str,
    ambito: str,
    prioridad: str,
    asunto: str,
    instruccion_original: str,
    fecha_objetivo: str | None = None,
    creado_por: str = ACTOR_PRESIDENCIA,
    clasificacion_seguridad: str | None = None,
    expediente_padre: str | None = None,
    paths: Iterable[Path] = (),
) -> Path:
    """Create a corporate expediente at REGISTRADO after presidential send (ENVIADO)."""
    tipo = normalize_tipo(tipo)
    ambito = normalize_ambito(ambito)
    prioridad = normalize_prioridad(prioridad)
    asunto = (asunto or "").strip()
    instruccion = (instruccion_original or "").strip()
    if not asunto:
        raise ValueError("El asunto es obligatorio.")
    if not instruccion:
        raise ValueError("La instrucción de Presidencia es obligatoria.")

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    expediente_id = expediente_id_for(asunto)
    case = root / expediente_id
    if case.exists():
        raise FileExistsError(case)
    case.mkdir(parents=True, exist_ok=False)
    (case / "versions" / VERSION_LABEL).mkdir(parents=True, exist_ok=True)

    creado = now()
    correlation = _new_id("cor-")
    collections = _empty_collections()
    documents = _persist_documents(case, paths, version=VERSION_LABEL, autor=creado_por)
    collections["documentos"] = documents

    events = [
        audit_event(
            expediente_id=expediente_id,
            actor=creado_por,
            actor_type=ACTOR_TYPE_HUMAN,
            accion="ENVIADO",
            objeto_afectado="instruccion_corporativa",
            estado_anterior=None,
            estado_nuevo=ENVIADO,
            referencia_version=VERSION_LABEL,
            motivo="Presidencia confirmó envío desde Mission Control.",
            correlation_id=correlation,
        ),
        audit_event(
            expediente_id=expediente_id,
            actor="LNH Backend",
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="EXPEDIENT_CREATED",
            objeto_afectado="expediente",
            estado_anterior=ENVIADO,
            estado_nuevo=REGISTRADO,
            referencia_version=VERSION_LABEL,
            motivo="Backend creó el Expediente Corporativo LNH (LNH-DATA-001).",
            correlation_id=correlation,
        ),
    ]
    for doc in documents:
        events.append(audit_event(
            expediente_id=expediente_id,
            actor=creado_por,
            actor_type=ACTOR_TYPE_HUMAN,
            accion="DOCUMENT_ADDED",
            objeto_afectado=doc["document_id"],
            estado_anterior=REGISTRADO,
            estado_nuevo=REGISTRADO,
            referencia_version=VERSION_LABEL,
            motivo=f"Adjunto presidencial: {doc['nombre']}",
            correlation_id=correlation,
            payload={"document_id": doc["document_id"], "nombre": doc["nombre"]},
        ))
    collections["eventos"] = events

    master = {
        "schema": SCHEMA,
        "kind": "expediente_corporativo",
        "expediente_id": expediente_id,
        "tipo": tipo,
        "ambito": ambito,
        "prioridad": prioridad,
        "asunto": asunto,
        "instruccion_original": instruccion,
        "fecha_creacion": creado,
        "fecha_objetivo": fecha_objetivo or None,
        "creado_por": creado_por,
        "estado_actual": REGISTRADO,
        "version_actual": VERSION_LABEL,
        "clasificacion_seguridad": clasificacion_seguridad,
        "expediente_padre": expediente_padre,
        "platform_ready": False,
        "routing_applied": False,
        **collections,
    }
    assert_state(master["estado_actual"])
    snapshot = _version_snapshot(master)
    master["historial_versiones"] = [snapshot]
    dump_json(case / "versions" / VERSION_LABEL / "snapshot.json", snapshot)
    dump_json(case / "expediente.json", master)
    dump_json(case / "MISSION.json", {
        "expediente_id": expediente_id,
        "asunto": asunto,
        "instruccion_original": instruccion,
        "tipo": tipo,
        "ambito": ambito,
        "prioridad": prioridad,
        "fecha_creacion": creado,
        "immutable": True,
    })
    _write_sidecar(case, master)
    return case


def load_expediente(case: Path) -> dict:
    case = Path(case)
    master = load_json(case / "expediente.json")
    if not master or master.get("kind") != "expediente_corporativo":
        raise FileNotFoundError("Expediente corporativo no encontrado.")
    return master


def directory(root: Path, expediente_id: str) -> Path:
    root = Path(root).resolve()
    if not expediente_id or re.search(r"[\\/:\x00]", expediente_id) or expediente_id in (".", ".."):
        raise ValueError("Identificador de expediente no válido.")
    case = (root / expediente_id).resolve()
    if case.parent != root or not (case / "expediente.json").is_file():
        raise FileNotFoundError("Expediente corporativo no encontrado.")
    return case


def list_expedientes(root: Path) -> list[dict]:
    root = Path(root)
    if not root.is_dir():
        return []
    rows = []
    for path in sorted(root.glob("*/expediente.json"), reverse=True):
        item = load_json(path) or {}
        if item.get("kind") != "expediente_corporativo":
            continue
        rows.append({
            "expediente_id": item["expediente_id"],
            "tipo": item.get("tipo"),
            "ambito": item.get("ambito"),
            "prioridad": item.get("prioridad"),
            "asunto": item.get("asunto"),
            "estado_actual": item.get("estado_actual"),
            "version_actual": item.get("version_actual"),
            "fecha_creacion": item.get("fecha_creacion"),
            "fecha_objetivo": item.get("fecha_objetivo"),
            "creado_por": item.get("creado_por"),
            "documentos": len(item.get("documentos") or []),
            "expediente_padre": item.get("expediente_padre"),
        })
    return rows


def expediente_view(case: Path) -> dict:
    master = load_expediente(case)
    return {
        **master,
        "resumen": {
            "expediente_id": master["expediente_id"],
            "asunto": master["asunto"],
            "estado_actual": master["estado_actual"],
            "version_actual": master["version_actual"],
            "tipo": master["tipo"],
            "ambito": master["ambito"],
            "prioridad": master["prioridad"],
            "fecha_creacion": master["fecha_creacion"],
            "fecha_objetivo": master.get("fecha_objetivo"),
            "creado_por": master.get("creado_por"),
            "documentos": len(master.get("documentos") or []),
            "eventos": len(master.get("eventos") or []),
            "encargos": len(master.get("encargos") or []),
            "routing_applied": bool(master.get("routing_applied")),
        },
        "capabilities": {
            "routing": True,
            "platform_execute": True,
            "directorio": True,
            "human_gate": True,
            "calendar": True,
            "communications": True,
            "notifications": True,
            "block": "LNH-DATA-001-F2B",
        },
        "routing": master.get("routing"),
        "vencimientos": master.get("vencimientos") or [],
        "resultados": master.get("resultados") or [],
        "platform_sessions": master.get("platform_sessions") or [],
        "calendar_events": master.get("calendar_events") or [],
        "communications": master.get("communications") or [],
        "agents_mapping": None,
    }


def events_view(case: Path) -> list[dict]:
    return list(load_expediente(case).get("eventos") or [])


def apply_state(case: Path, new_state: str, *, actor: str, actor_type: str, motivo: str = "") -> dict:
    """Deterministic state transition with append-only audit (for tests / future blocks)."""
    case = Path(case)
    master = load_expediente(case)
    current = master["estado_actual"]
    assert_transition(current, new_state)
    master["estado_actual"] = new_state
    master["eventos"].append(audit_event(
        expediente_id=master["expediente_id"],
        actor=actor,
        actor_type=actor_type,
        accion="STATE_TRANSITION",
        objeto_afectado="estado_actual",
        estado_anterior=current,
        estado_nuevo=new_state,
        referencia_version=master["version_actual"],
        motivo=motivo or f"Transición {current} → {new_state}",
    ))
    dump_json(case / "expediente.json", master)
    _write_sidecar(case, master)
    return master
