from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
def utcnow(): return datetime.now(timezone.utc).isoformat()
@dataclass(frozen=True)
class OrganizationUnit: unit_id:str; name:str; kind:str; parent_id:str|None=None
@dataclass(frozen=True)
class AgentCapability: agent_id:str; name:str; department_id:str; capabilities:tuple[str,...]; status:str="OPERATIONAL"
@dataclass
class Mission: mission_id:str; instruction:str; department_id:str; case_id:str|None=None; status:str="RECEIVED"; created_at:str=field(default_factory=utcnow)
@dataclass
class CorporateState:
 case_id:str; status:str="RECEIVED"; version:int=1; updated_at:str=field(default_factory=utcnow); history:list[dict]=field(default_factory=list)
 def transition(self,status,reason): self.status=status;self.updated_at=utcnow();self.history.append({"at":self.updated_at,"status":status,"reason":reason})
 def as_dict(self): return asdict(self)
