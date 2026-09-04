"""MGC-05 floor manager: plans and coordinates; specialists retain judgement."""
from dataclasses import asdict, dataclass
from corporate.platform import build_mgc_platform
from .managerial import build_managerial_record, render_department_report
ORDER = ("proyecto", "proceso", "logística")
@dataclass(frozen=True)
class WorkPlan: mission:str; agent_ids:tuple[str,...]; dependencies:tuple[dict,...]
class FloorManager:
 def __init__(self,platform=None):self.platform=platform or build_mgc_platform()
 def plan(self,mission):
  selected=self.platform.agents.for_capabilities([mission]);selected.sort(key=lambda a:next((i for i,x in enumerate(ORDER) if x in a.capabilities),len(ORDER)))
  if not selected:selected=[self.platform.agents.get("AGIA-MGC-014")]
  ids=tuple(a.agent_id for a in selected);deps=tuple({"before":ids[i],"after":ids[i+1],"reason":"El siguiente especialista recibe el resultado anterior sólo para coordinación y contraste."} for i in range(len(ids)-1));return WorkPlan(mission,ids,deps)
 def coordination_record(self,outputs):return build_managerial_record(outputs)
 def consolidate(self,case_id,mission,outputs):
  record=self.coordination_record(outputs);return record,render_department_report(case_id,mission,outputs,record)
 def serialise_plan(self,plan):return asdict(plan)
