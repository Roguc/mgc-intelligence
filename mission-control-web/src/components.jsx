import React from 'react';
import {Icon} from './icons';
export const labels = {
  CREATED:'Expediente registrado', SUBMITTED_TO_PLATFORM:'Enviado a Platform', PLATFORM_RUNNING:'Platform en ejecución',
  RESULT_RECEIVED:'Resultado recibido', PROCESSING_RESULT:'Procesando resultado', READY_FOR_HUMAN_GATE:'Revisión humana requerida',
  APPROVED:'Aprobado', CORRECTION_REQUESTED:'Corrección solicitada', REJECTED:'Rechazado',
  PLATFORM_CONNECTION_ERROR:'Error de conexión Platform', PLATFORM_EXECUTION_ERROR:'Error de ejecución Platform',
  RECOVERY_PENDING:'Verificando Platform', INCOMPLETE:'Resultado incompleto',
  OPEN:'Abierto', CLOSED:'Cerrado', HUMAN_REVIEW_REQUIRED:'Revisión humana requerida',
  ESPERANDO_REVISION_HUMANA:'Esperando revisión humana', INFRASTRUCTURE_BLOCKED:'Infraestructura bloqueada',
  SPECIALIST_EXECUTION_BLOCKED:'Ejecución profesional incompleta', CORRECTION_IN_PROGRESS:'Corrección en curso',
  HUMAN_GATE_REQUIRED:'Intervención humana requerida', SPECIALIST_EXECUTION_PENDING:'Ejecución especializada pendiente',
  running:'En curso', completed:'Finalizada', failed:'Fallida', interrupted:'Interrumpida', recovery:'Verificando Platform',
  APROBADO:'Aprobado', RECHAZADO:'Rechazado', OPERATIONAL:'Operativo', CASE_CREATED:'Expediente registrado', VERSION_CREATED:'Versión registrada', HANDOFFS_COMPLETED:'Coordinación registrada', HUMAN_DECISION:'Decisión humana registrada', HUMAN_CORRECTION_REQUESTED:'Corrección solicitada', APROBAR:'Aprobar', CORREGIR:'Corregir', RECHAZAR:'Rechazar', EJECUTAR:'Ejecutar',
  Activo:'Activo', Operativo:'Operativo', 'En construcción':'En construcción',
  'Diseñado - pendiente de aprobación':'No habilitado',
};
export const label = value => labels[value] || value;
export const date = value => value ? new Date(value).toLocaleString('es-CL', {dateStyle:'short', timeStyle:'short'}) : 'Fecha no registrada';

export function caseStamp(id) {
  const m = String(id || '').match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/);
  if (!m) return null;
  const d = new Date(`${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}`);
  return Number.isNaN(d.getTime()) ? null : d;
}

const ok = new Set(['CLOSED','APPROVED','Operativo','Operativa','Activo','Activa','completed','APROBADO','Aprobado','Resultado materializado','OPERATIONAL','READY_FOR_HUMAN_GATE']);
const danger = new Set(['INFRASTRUCTURE_BLOCKED','SPECIALIST_EXECUTION_BLOCKED','PLATFORM_CONNECTION_ERROR','PLATFORM_EXECUTION_ERROR','INCOMPLETE','failed','interrupted','RECHAZADO','REJECTED','Rechazado','No habilitado']);
const info = new Set(['running','recovery','OPEN','EJECUTAR','Seleccionado','RECOVERY_PENDING','SUBMITTED_TO_PLATFORM','PLATFORM_RUNNING','Verificando Platform']);
const muted = new Set(['Diseñado - pendiente de aprobación','En plan','Sin resultado materializado']);

export function tone(value) {
  if (ok.has(value)) return 'ok';
  if (danger.has(value)) return 'danger';
  if (muted.has(value)) return 'muted';
  if (info.has(value)) return 'info';
  return 'warn';
}

export function Badge({children}) {
  return <span className={`badge ${tone(children)}`}>{label(children)}</span>;
}

export function Empty({title='Sin información materializada',text='Aún no se ha registrado información para esta vista.'}) {
  return <section className="empty"><b>{title}</b><p>{text}</p></section>;
}

export function Hero({e,t,p,aside}) {
  return (
    <section className="hero">
      <div>
        {e && <small>{e}</small>}
        <h1>{t}</h1>
        {p && <p>{p}</p>}
      </div>
      {aside}
    </section>
  );
}

export function Notice({children,error=false}) {
  return children ? <div className={`notice ${error?'error':''}`} role={error?'alert':'status'}>{children}</div> : null;
}

export function Metric({label:l, value, note, icon, tone:t='info'}) {
  return (
    <article className={`kpi kpi-${t}`}>
      {icon && <span className="kpi-icon"><Icon name={icon}/></span>}
      <div>
        <small>{l}</small>
        <b>{value}</b>
        <span>{note}</span>
      </div>
    </article>
  );
}

export function Unit({t,p,s}) {
  return (
    <article className="unit">
      <h3>{t}</h3>
      <p>{p}</p>
      {s != null && <Badge>{s}</Badge>}
    </article>
  );
}

export function Cases({rows,open,emptyTitle='Sin expedientes',emptyText='No hay expedientes materializados para esta selección.'}) {
  if (!rows.length) return <Empty title={emptyTitle} text={emptyText}/>;
  return (
    <div className="rows">
      {rows.map(x => (
        <article key={`${x.floor_id}/${x.case_id}`}>
          <div className="mark">{(x.floor_id||'').slice(-2)}</div>
          <div>
            <b>{x.mission || x.case_id}</b>
            <small>{x.case_id}</small>
            <p>{x.floor_id} · {x.documents} documentos · versión {x.latest_version ?? 'sin versión'}</p>
            <Badge>{x.status}</Badge>
            {x.busy && <Badge>running</Badge>}
            {x.requires_decision && <Badge>HUMAN_REVIEW_REQUIRED</Badge>}
          </div>
          <button type="button" onClick={() => open(x)}>Abrir expediente</button>
        </article>
      ))}
    </div>
  );
}

const names={mission:'Instrucción',agent_ids:'Especialistas seleccionados',selected_agents:'Especialistas seleccionados',sequence:'Secuencia',dependencies:'Dependencias',before:'Anterior',after:'Siguiente',reason:'Fundamento',handoffs:'Handoffs',origin:'Origen',destination:'Destino',state:'Estado',staffing_gap:'Capacidades faltantes',subject:'Asunto',status:'Estado',departmental_status:'Estado departamental',classifications:'Clasificaciones',source_version:'Versión de origen',version:'Versión',parent_version:'Versión anterior',event:'Evento',at:'Fecha',timestamp:'Fecha',rationale:'Fundamento',decision:'Decisión',agent:'Especialista',document:'Documento',locator:'Localizador',extraction_method:'Método de extracción',classification:'Clasificación',relation:'Relación',from:'Origen',to:'Destino',error:'Error',report:'Informe',name:'Nombre',page:'Página',conclusion:'Conclusión',source_id:'Fuente',evidence_id:'Evidencia',hash:'Huella digital',sha256:'SHA-256'};
export function Records({value}) {
  if(value === null || value === undefined || (Array.isArray(value) && !value.length) || (typeof value==='object' && !Object.keys(value).length)) return <Empty/>;
  if(Array.isArray(value)) return <div className="records">{value.map((v,i)=><div className="record" key={i}><Records value={v}/></div>)}</div>;
  if(typeof value==='object') return <dl className="fields">{Object.entries(value).map(([k,v])=><div key={k}><dt>{names[k]||k.replaceAll('_',' ')}</dt><dd><Records value={v}/></dd></div>)}</dl>;
  return <span className="preserve">{typeof value==='boolean'?(value?'Sí':'No'):String(label(value))}</span>;
}
function inline(text) {return String(text).split(/(\*\*[^*]+\*\*)/g).map((s,i)=>s.startsWith('**')?<strong key={i}>{s.slice(2,-2)}</strong>:s);}
export function Report({text}) {
  if(!text) return <Empty title="Informe no materializado"/>;
  const lines=text.split('\n'), blocks=[];
  for(let i=0;i<lines.length;i++) {
    const line=lines[i];
    if(!line.trim()) continue;
    if(line.includes('|') && i+1<lines.length && /^\s*\|?\s*:?-{3}/.test(lines[i+1])) {
      const cells=s=>s.trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim());
      const head=cells(line), rows=[];i+=2;
      for(;i<lines.length&&lines[i].includes('|');i++)rows.push(cells(lines[i]));i--;
      blocks.push(<div className="table-wrap" key={i}><table><thead><tr>{head.map((c,j)=><th key={j}>{inline(c)}</th>)}</tr></thead><tbody>{rows.map((r,j)=><tr key={j}>{r.map((c,k)=><td key={k}>{inline(c)}</td>)}</tr>)}</tbody></table></div>);
    } else if(/^#{1,6}\s/.test(line)) blocks.push(<h3 key={i}>{inline(line.replace(/^#+\s/,''))}</h3>);
    else if(/^\s*[-*]\s/.test(line)) blocks.push(<p className="report-bullet" key={i}>• {inline(line.replace(/^\s*[-*]\s/,''))}</p>);
    else blocks.push(<p key={i}>{inline(line)}</p>);
  }
  return <div className="report">{blocks}</div>;
}

const SECTION_KEYS = [
  ['resumen', /resumen|estado del expediente|misi[oó]n recibida|informe departamental/i],
  ['hallazgos', /hallazgo|trabajo realizado|hechos coincidentes|contradiccion|hitos y control|conclusi[oó]n/i],
  ['riesgos', /riesgo|bloqueo|informaci[oó]n faltante/i],
  ['oportunidades', /oportunidad/i],
  ['plan', /pr[oó]ximos pasos|plan de acci[oó]n/i],
  ['fuentes', /trazabilidad|anexos|evidencia|fuente|handoffs/i],
];

export function splitReport(text) {
  const buckets = {resumen: [], hallazgos: [], riesgos: [], oportunidades: [], plan: [], fuentes: []};
  if (!text) return buckets;
  const parts = String(text).split(/\n(?=##\s)/);
  for (const part of parts) {
    const heading = (part.match(/^#+\s+(.+)/) || [,''])[1];
    const match = SECTION_KEYS.find(([, re]) => re.test(heading));
    const key = match ? match[0] : 'resumen';
    buckets[key].push(part.trim());
  }
  return buckets;
}
