from .models import utcnow
class HumanGate:
 def decision(self,case_id,decision,rationale,version):return {"case_id":case_id,"decision":decision,"rationale":rationale,"version":version,"at":utcnow(),"human_required":True}
class Observability:
 def __init__(self):self.events=[]
 def record(self,event,**data):item={"event":event,"at":utcnow(),**data};self.events.append(item);return item
 def costs(self):return {"calls":len([x for x in self.events if x["event"]=="INFERENCE_COMPLETED"]),"cost_usd":sum(x.get("cost_usd",0.0) for x in self.events)}
