from datetime import datetime, timezone
def now():return datetime.now(timezone.utc).isoformat()
def initialize(case_id,documents,runtime="PENDIENTE"):
 sources=[{"source_id":f"SRC-{i:03d}","document":x["name"],"hash":x["sha256"],"path":x["path"],"timestamp":now()} for i,x in enumerate(documents,1)]
 evidence=[{"evidence_id":f"EVD-{i:03d}","source_id":x["source_id"],"hash":x["hash"],"locator":"PENDIENTE","extraction_method":"PENDIENTE","agent":"PENDIENTE","timestamp":now()} for i,x in enumerate(sources,1)]
 return {"case_id":case_id,"sources":sources,"evidence":evidence,"findings":[],"outputs":[],"lineage":[{"from":"MISSION","to":"SOURCES","relation":"uses","timestamp":now()}],"audit":[{"event":"MISSION_REGISTERED","timestamp":now()}],"tco":{"budget":{"authorized":"PENDIENTE","committed":"PENDIENTE","actual":0.0 if runtime=="rules" else "PENDIENTE","forecast":"PENDIENTE","eac":"PENDIENTE"},"usage":{"gpu_hours":0.0 if runtime=="rules" else "PENDIENTE","inference_calls":0,"rule_executions":0,"storage_services":"PENDIENTE","retries":0}}}
def record_execution(ledger,version,reports,contradictions,runtime="PENDIENTE"):
 ledger["audit"].append({"event":"FLOOR_MANAGER_PLANNED","version":version,"timestamp":now()})
 for item in reports:
  ledger["outputs"].append({"output_id":f"OUT-{len(ledger['outputs'])+1:03d}","agent":item["agent"],"document":item["report"],"classification":"INFERENCIA","timestamp":now()});ledger["lineage"].append({"from":item["agent"],"to":item["report"],"relation":"produces","timestamp":now()});ledger["audit"].append({"event":"AGENT_OUTPUT_REGISTERED","agent":item["agent"],"timestamp":now()})
 for item in contradictions:ledger["findings"].append({"finding_id":f"FND-{len(ledger['findings'])+1:03d}","classification":"HALLAZGO","subject":item["subject"],"status":item["departmental_status"],"timestamp":now()})
 ledger["outputs"].append({"output_id":f"OUT-{len(ledger['outputs'])+1:03d}","agent":"MGC-05 FLOOR MANAGER","document":"MGC-05_DEPARTMENT_REPORT.md","classification":"RESULTADO CONSOLIDADO","timestamp":now()});ledger["audit"].append({"event":"CONSOLIDATED_OUTPUT_REGISTERED","timestamp":now()})
 if runtime=="rules":ledger["tco"]["usage"]["rule_executions"]+=len(reports)
 return ledger
def record_human_decision(ledger,decision,version):
 ledger["audit"].append({"event":"HUMAN_DECISION_REGISTERED","decision":decision,"version":version,"timestamp":now()});ledger["lineage"].append({"from":"HUMAN_GATE","to":"CASE","relation":"decides","timestamp":now()});return ledger
