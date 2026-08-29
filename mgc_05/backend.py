from datetime import datetime, timezone
from hashlib import sha256
import json, re, shutil
from pathlib import Path
from agia_mgc_014.agent import run as run_014
from agia_mgc_015.agent import run as run_015
from agia_mgc_016.agent import run as run_016
from agia_mgc_014.reader import read_document
EXTERNAL=('email','whatsapp','pago','payment','contrato','contract','firmar','publicar')
def now(): return datetime.now(timezone.utc).isoformat()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def route(mission,names):
 t=(mission+' '+' '.join(names)).casefold(); r=[]
 if any(x in t for x in ('proyecto','hito','dependencia','cronograma','pmo','baseline')): r+=['014']
 if any(x in t for x in ('proceso','sop','mejora','checklist')): r+=['015']
 if any(x in t for x in ('embarque','logística','incoterm','fob','cif','bl','b/l','puerto','seguro','vessel','aduana')): r+=['016']
 return r or ['014']
def create_case(mission,paths,root):
 if any(x in mission.casefold() for x in EXTERNAL): raise ValueError('Acción externa bloqueada: sólo análisis interno.')
 cid=datetime.now().strftime('%Y%m%d%H%M%S')+'-'+re.sub('[^a-z0-9]+','-',mission.casefold()).strip('-')[:24]; case=root/cid; docs=case/'documents'; docs.mkdir(parents=True)
 reg=[]
 for s in paths:
  d=docs/s.name; shutil.copy2(s,d); reg.append({'name':s.name,'path':str(d),'sha256':sha256(d.read_bytes()).hexdigest()})
 state={'case_id':cid,'mission':mission,'documents':reg,'status':'OPEN','versions':[],'audit':[{'at':now(),'event':'CASE_CREATED'}]}; dump(case/'case.json',state); return case
def bridge_documents(paths,folder):
 lines=['# CONTENIDO DOCUMENTAL PROPAGADO POR MGC-05']
 for path in paths:
  try: content=read_document(path)
  except Exception as error: content=f'[No extraíble: {error}]'
  lines += [f'\n## Fuente: {path.name}', content]
 text='\n'.join(lines)
 # Normalización factual para los parsers de los agentes, sin sustituir la fuente.
 facts=[]
 if re.search(r'(?i)incoterms?\s*[:=]\s*FOB',text): facts.append('Incoterm: FOB')
 if re.search(r'(?i)iron ore',text): facts.append('Producto: Iron Ore')
 if re.search(r'(?i)origin\s*[:=]\s*brazil',text): facts.append('Origen: Brazil')
 if re.search(r'(?i)porto do a[uç]u|a[uç]u port',text): facts.append('Puerto de carga: Açu Port')
 if re.search(r'(?i)gij[oó]n',text): facts.append('Puerto de descarga: Gijón')
 if re.search(r'(?i)vessel\s*\n?\s*(?:MA/YASA VENUS|YASA VENUS)',text): facts.append('Vessel: Yasa Venus')
 for path in paths: facts.append(f'Hito: Documento recibido {path.name} | Estado: DOCUMENTADO | Evidencia: {path.name}')
 bridge=folder/'DOCUMENT_CONTENT_BRIDGE.md'; safe_text=('\n'.join(facts)+'\n'+text).encode('utf-8','replace').decode('utf-8'); bridge.write_text(safe_text,encoding='utf-8'); return bridge
def execute(case,mission,paths,correction=None):
 s=load(case/'case.json'); n=len(s['versions'])+1; out=case/f'v{n:03d}'; out=out if not out.exists() else case/f'v{n:03d}-retry-{datetime.now().strftime("%H%M%S")}'; out.mkdir(); agents=route(mission,[p.name for p in paths]); runs={'014':run_014,'015':run_015,'016':run_016}; reports=[]; errors=[]
 bridge=bridge_documents(paths,out); agent_paths=paths+[bridge]
 for a in agents:
  try:
   p,i=runs[a](mission,agent_paths,out); reports.append({'agent':'AGIA-MGC-'+a,'report':p.name,'issues':i,'document_bridge':bridge.name})
  except Exception as e: errors.append({'agent':'AGIA-MGC-'+a,'error':str(e)})
 text=['# Informe departamental MGC-05',f'\n## Caso\n{s["case_id"]}',f'\n## Misión\n{mission}',f'\n## Agentes asignados\n'+', '.join('AGIA-MGC-'+a for a in agents),'\n## Consolidación']
 for r in reports:text+=['\n### '+r['agent'],(out/r['report']).read_text(encoding='utf-8')]
 if errors:text+=['\n## Alertas de ejecución','\n'.join('- '+x['agent']+': '+x['error'] for x in errors)]
 text+=['\n## Revisión humana requerida','Las correcciones generan una nueva versión. No se autorizan acciones externas.']
 (out/'MGC-05_DEPARTMENT_REPORT.md').write_text('\n'.join(text),encoding='utf-8'); v={'version':n,'at':now(),'routes':agents,'reports':reports,'errors':errors,'correction':correction,'status':'HUMAN_REVIEW_REQUIRED'}; dump(out/'version.json',v); s['versions'].append(v);s['audit'].append({'at':now(),'event':'DOCUMENT_CONTENT_PROPAGATED','version':n,'bridge':bridge.name});s['audit'].append({'at':now(),'event':'VERSION_CREATED','version':n});dump(case/'case.json',s);return out,v
def run_case(case):
 s=load(case/'case.json');return execute(case,s['mission'],[Path(x['path']) for x in s['documents']])
def correct_case(case,correction):
 if not correction.strip():raise ValueError('Corrección humana obligatoria.')
 s=load(case/'case.json');s['audit'].append({'at':now(),'event':'HUMAN_CORRECTION','text':correction});dump(case/'case.json',s);return execute(case,s['mission']+'\nCorrección humana:\n'+correction,[Path(x['path']) for x in s['documents']],correction)
def approve_case(case,decision,rationale):
 s=load(case/'case.json')
 if not s['versions']:raise ValueError('No existe versión.')
 r={'decision':decision,'rationale':rationale,'at':now(),'version':s['versions'][-1]['version']};dump(case/'HUMAN_DECISION_RECORD.json',r);s['status']='CLOSED' if decision.casefold()=='aprobado' else 'OPEN';s['audit'].append({'at':now(),'event':'HUMAN_DECISION','decision':decision});dump(case/'case.json',s);return r
