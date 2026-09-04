from .evidence import EvidenceCore
from .governance import HumanGate,Observability
from .inference import MockInferenceGateway
from .models import AgentCapability,OrganizationUnit,CorporateState
from .registries import AgentRegistry,MissionRegistry,OrganizationRegistry
class CorporatePlatform:
 def __init__(self,gateway=None):self.organizations=OrganizationRegistry();self.agents=AgentRegistry();self.missions=MissionRegistry();self.evidence=EvidenceCore();self.human_gate=HumanGate();self.observability=Observability();self.gateway=gateway or MockInferenceGateway();self.states={}
 def register_case(self,mission_id,case_id,paths):
  mission=self.missions.get(mission_id);mission.case_id=case_id;mission.status="CASE_CREATED";state=CorporateState(case_id);state.transition("CASE_CREATED","Case Manager created local case");self.states[case_id]=state;evidence=self.evidence.register(case_id,paths);self.observability.record("CASE_REGISTERED",case_id=case_id,evidence_count=len(evidence));return {"state":state.as_dict(),"evidence":evidence}
def build_mgc_platform(gateway=None):
 p=CorporatePlatform(gateway);p.organizations.register(OrganizationUnit("LNH","Latitud Norte Holding","holding"));p.organizations.register(OrganizationUnit("MGC","Miner Global Connect","company","LNH"));p.organizations.register(OrganizationUnit("MGC-05","MGC-05 Operaciones y PMO","department","MGC"))
 p.agents.register(AgentCapability("AGIA-MGC-014","Control de Proyectos y PMO","MGC-05",("proyecto","pmo","hito","dependencia")));p.agents.register(AgentCapability("AGIA-MGC-015","Procesos, SOP y Mejora Continua","MGC-05",("proceso","sop","checklist","mejora")));p.agents.register(AgentCapability("AGIA-MGC-016","Comercio Exterior y Logística","MGC-05",("logística","embarque","incoterm","puerto","seguro")));return p
