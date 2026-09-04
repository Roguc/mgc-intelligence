from datetime import datetime, timezone
from hashlib import sha256
import json, os, re, shutil
from pathlib import Path
from agia_mgc_014.agent import run as run_014
from agia_mgc_015.agent import run as run_015
from agia_mgc_016.agent import run as run_016
from .managerial import SpecialistOutput, build_managerial_record, render_department_report
from .floor_manager import FloorManager
from corporate.models import Mission
from corporate.platform import build_mgc_platform
EXTERNAL=('email','whatsapp','pago','payment','contrato','contract','firmar','publicar')
def now(): return datetime.now(timezone.utc).isoformat()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def inference_healthcheck(url='http://127.0.0.1:11435/api/tags',timeout=5):
 import urllib.request
 try:
  with urllib.request.urlopen(url,timeout=timeout) as response:
   body=json.loads(response.read().decode('utf-8'))
  models=[item.get('name') for item in body.get('models',[])]
  return {'ok':'qwen3:14b' in models,'models':models,'url':url}
 except Exception as exc:
  return {'ok':False,'models':[],'url':url,'error':str(exc)}
def route(mission,names):
 return [agent_id.rsplit('-',1)[-1] for agent_id in FloorManager().plan(mission).agent_ids]
def create_case(mission,paths,root):
 if any(x in mission.casefold() for x in EXTERNAL): raise ValueError('Acción externa bloqueada: sólo análisis interno.')
 cid=datetime.now().strftime('%Y%m%d%H%M%S')+'-'+re.sub('[^a-z0-9]+','-',mission.casefold()).strip('-')[:24]; case=root/cid; docs=case/'documents'; docs.mkdir(parents=True)
 reg=[]
 for s in paths:
  d=docs/s.name; shutil.copy2(s,d); reg.append({'name':s.name,'path':str(d),'sha256':sha256(d.read_bytes()).hexdigest()})
 state={'case_id':cid,'mission':mission,'documents':reg,'status':'OPEN','versions':[],'audit':[{'at':now(),'event':'CASE_CREATED'}]}
 platform=build_mgc_platform(); corporate_mission=platform.missions.register(Mission('MISSION-'+cid,mission,'MGC-05')); corporate=platform.register_case(corporate_mission.mission_id,cid,[Path(x['path']) for x in reg])
 state['corporate_mission_id']=corporate_mission.mission_id;dump(case/'corporate_case.json',corporate);dump(case/'case.json',state); return case
ROLE_BRIEFS={
 '014':'Actúa exclusivamente como Control de Proyectos y PMO. Identifica hitos, dependencias, responsables, riesgos, desviaciones y datos faltantes; no inventes baseline, fechas ni responsables.',
 '015':'Actúa exclusivamente como Analista de Procesos, SOP y Mejora Continua. Reconstruye el proceso documentado, controles, vacíos, contradicciones y mejoras propuestas; no sustituyas análisis legal, financiero ni logístico.',
 '016':'Actúa exclusivamente como Coordinador de Operaciones de Comercio Exterior y Logística. Reconstruye expedientes, Incoterm, documentos, transporte, seguro, custodia, entrega, incidencias y alertas; no vincules documentos sin evidencia.'}
def execute(case,mission,paths,correction=None):
 s=load(case/'case.json'); n=len(s['versions'])+1; out=case/f'v{n:03d}'; out=out if not out.exists() else case/f'v{n:03d}-retry-{datetime.now().strftime("%H%M%S")}'; out.mkdir(); manager=FloorManager(); plan=manager.plan(mission); agents=[agent_id.rsplit('-',1)[-1] for agent_id in plan.agent_ids];dump(out/'plan.json',manager.serialise_plan(plan)); runs={'014':run_014,'015':run_015,'016':run_016}; reports=[]; errors=[]
 health={'ok':True,'skipped':'rules runtime'} if os.environ.get('MGC_INFERENCE_MODE')=='rules' else inference_healthcheck()
 if not health['ok']:
  v={'version':n,'at':now(),'routes':agents,'reports':[],'errors':[],'correction':correction,'status':'INFRASTRUCTURE_BLOCKED','health_check':health,'handoffs':[],'contradictions':[],'human_decisions':[]}
  dump(out/'version.json',v);s['versions'].append(v);s['status']='INFRASTRUCTURE_BLOCKED';s['audit'].append({'at':now(),'event':'INFRASTRUCTURE_BLOCKED','version':n,'health_check':health});dump(case/'case.json',s);return out,v
 for a in agents:
  try:
   delegated=f'{ROLE_BRIEFS[a]}\n\nMisión departamental:\n{mission}\n\nUse íntegramente los documentos originales adjuntos como fuente de verdad.'
   p,i=runs[a](delegated,paths,out); reports.append({'agent':'AGIA-MGC-'+a,'report':p.name,'issues':i,'evidence':[p.name,p.name.replace('.md','_LOCAL_INFERENCE_TRACE.json')]})
  except Exception as e: errors.append({'agent':'AGIA-MGC-'+a,'error':str(e)})
 outputs=[SpecialistOutput(item['agent'],(out/item['report']).read_text(encoding='utf-8'),tuple(item['evidence'])) for item in reports]
 record,text=manager.consolidate(s['case_id'],mission,outputs)
 for item in reports:item['handoff']='Resultado profesional registrado para coordinación; ver handoffs.json.'
 dump(out/'handoffs.json',record['handoffs']);dump(out/'contradictions.json',record['contradictions']);dump(out/'human_decisions_required.json',record['human_decisions'])
 if errors:text+='\n\n## Alertas de ejecución\n'+'\n'.join('- '+x['agent']+': '+x['error'] for x in errors)
 (out/'MGC-05_DEPARTMENT_REPORT.md').write_text(text,encoding='utf-8'); v={'version':n,'at':now(),'routes':agents,'reports':reports,'errors':errors,'correction':correction,'status':record['departmental_status'],'health_check':health,'handoffs':record['handoffs'],'contradictions':record['contradictions'],'human_decisions':record['human_decisions']}; dump(out/'version.json',v); s['versions'].append(v);s['status']=record['departmental_status'];s['audit'].append({'at':now(),'event':'HANDOFFS_COMPLETED','version':n});s['audit'].append({'at':now(),'event':'VERSION_CREATED','version':n});dump(case/'case.json',s);return out,v
def run_case(case):
 s=load(case/'case.json');return execute(case,s['mission'],[Path(x['path']) for x in s['documents']])
def correct_case(case,correction):
 if not correction.strip():raise ValueError('Corrección humana obligatoria.')
 s=load(case/'case.json');s['audit'].append({'at':now(),'event':'HUMAN_CORRECTION','text':correction});dump(case/'case.json',s);return execute(case,s['mission']+'\nCorrección humana:\n'+correction,[Path(x['path']) for x in s['documents']],correction)
def approve_case(case,decision,rationale):
 s=load(case/'case.json')
 if not s['versions']:raise ValueError('No existe versión.')
 r={'decision':decision,'rationale':rationale,'at':now(),'version':s['versions'][-1]['version']};dump(case/'HUMAN_DECISION_RECORD.json',r);s['status']='CLOSED' if decision.casefold()=='aprobado' else 'OPEN';s['audit'].append({'at':now(),'event':'HUMAN_DECISION','decision':decision});dump(case/'case.json',s);return r
