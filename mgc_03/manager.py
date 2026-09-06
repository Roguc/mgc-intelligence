"""Managerial orchestration for MGC-03; it never acts as a market specialist."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable

from corporate.models import Mission, OrganizationUnit
from corporate.platform import build_mgc_platform

FLOOR_ID = "MGC-03"
FLOOR_NAME = "MGC-03 Inteligencia de Mercado"
FUTURE_AGENT_SLOTS = ("AGIA-MGC-005", "AGIA-MGC-006", "AGIA-MGC-007", "AGIA-MGC-008")

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class MarketWorkPlan:
    mission_id: str
    selected_agents: tuple[str, ...]
    sequence: tuple[str, ...]
    handoffs: tuple[dict, ...]
    staffing_gap: tuple[str, ...]
    state: str

class MGC03FloorManager:
    """Coordinates registered MGC-03 specialists and escalates gaps to Human Gate."""
    def __init__(self, platform=None):
        self.platform = platform or build_mgc_platform()
        try:
            self.platform.organizations.get(FLOOR_ID)
        except KeyError:
            self.platform.organizations.register(OrganizationUnit(FLOOR_ID, FLOOR_NAME, "department", "MGC"))

    def receive_mission(self, mission_text: str, case_id: str, documents: Iterable[Path] = ()) -> dict:
        if not mission_text or not mission_text.strip():
            raise ValueError("La misión es obligatoria.")
        mission = self.platform.missions.register(Mission(f"MISSION-{case_id}", mission_text.strip(), FLOOR_ID))
        case = self.platform.register_case(mission.mission_id, case_id, list(documents))
        self.platform.states[case_id].transition("MGC03_MISSION_RECEIVED", "MGC-03 Floor Manager received mission.")
        return {"mission": mission, "case": case}

    def select_specialists(self, mission_text: str) -> list[str]:
        candidates = [agent for agent in self.platform.agents.for_capabilities([mission_text]) if agent.department_id == FLOOR_ID]
        return [agent.agent_id for agent in candidates if agent.status == "OPERATIONAL"]

    def plan(self, mission_id: str) -> MarketWorkPlan:
        mission = self.platform.missions.get(mission_id)
        selected = tuple(self.select_specialists(mission.instruction))
        if not selected:
            return MarketWorkPlan(mission_id, (), (), (), FUTURE_AGENT_SLOTS, "HUMAN_GATE_REQUIRED")
        handoffs = tuple({"origin": source, "destination": destination, "reason": "Coordinación entre especialistas registrados; no sustituye su juicio profesional."} for source, destination in zip(selected, selected[1:]))
        return MarketWorkPlan(mission_id, selected, selected, handoffs, (), "SPECIALIST_EXECUTION_PENDING")

    def supervise(self, case_id: str, plan: MarketWorkPlan, specialist_outputs: Iterable[dict] = ()) -> dict:
        outputs = list(specialist_outputs)
        if not plan.selected_agents:
            state, missing = "HUMAN_GATE_REQUIRED", list(plan.staffing_gap)
        elif not outputs:
            state, missing = "SPECIALIST_EXECUTION_PENDING", list(plan.selected_agents)
        else:
            state, missing = "CONSOLIDATION_PENDING", []
        self.platform.states[case_id].transition(state, "MGC-03 managerial supervision recorded technical execution state.")
        return {"state": state, "outputs_received": outputs, "missing": missing}

    def consolidate(self, case_id: str, plan: MarketWorkPlan, specialist_outputs: Iterable[dict]) -> dict:
        outputs = list(specialist_outputs)
        if not outputs:
            return {"state": "HUMAN_GATE_REQUIRED", "consolidated": False, "reason": "No hay informes de especialistas MGC-03 registrados."}
        by_subject: dict[str, set[str]] = {}
        for item in outputs:
            for claim in item.get("claims", []):
                subject, classification = claim.get("subject"), claim.get("classification")
                if subject and classification:
                    by_subject.setdefault(subject, set()).add(classification)
        contradictions = [{"subject": subject, "classifications": sorted(values), "status": "REQUIERE REVISIÓN HUMANA"} for subject, values in by_subject.items() if len(values) > 1]
        self.platform.states[case_id].transition("HUMAN_GATE_REQUIRED", "MGC-03 consolidation ready for human decision.")
        return {"state": "HUMAN_GATE_REQUIRED", "consolidated": True, "reports": outputs, "contradictions": contradictions, "handoffs": list(plan.handoffs)}

    def human_gate(self, case_id: str, rationale: str) -> dict:
        return self.platform.human_gate.decision(case_id, "REQUIERE_DECISIÓN_HUMANA", rationale, self.platform.states[case_id].version)

    def materialize_case(self, root: Path, case_id: str, mission_text: str, documents: Iterable[Path] = ()) -> Path:
        case_dir = root / case_id
        case_dir.mkdir(parents=True, exist_ok=False)
        received = self.receive_mission(mission_text, case_id, documents)
        plan = self.plan(received["mission"].mission_id)
        supervision = self.supervise(case_id, plan)
        gate = self.human_gate(case_id, "La dotación de MGC-03 debe ser incorporada por decisión de LNH antes de ejecución especializada.")
        payload = {"at": _now(), "floor": FLOOR_ID, "organization": [unit.__dict__ for unit in self.platform.organizations.all()], "mission": received["mission"].__dict__, "plan": asdict(plan), "supervision": supervision, "human_gate": gate, "corporate_state": self.platform.states[case_id].as_dict()}
        (case_dir / "MGC03_TECHNICAL_EXECUTION_RECORD.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return case_dir
