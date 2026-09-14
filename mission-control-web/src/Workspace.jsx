import React, {useEffect, useRef, useState} from 'react';
import {caseDetail, executeCase, humanGate, artifactUrl} from './api';
import {Badge, Empty, Hero, Notice, Records, Report, date, label, splitReport} from './components';

export const tabs = ['Resumen', 'Plan', 'Equipo', 'Actividad', 'Fuentes/Evidencia', 'Resultados', 'Revisión Gerencial', 'Human Gate', 'Historial'];
const tabLabel = {
  Resumen: 'Resumen',
  Plan: 'Plan de trabajo',
  Equipo: 'Especialistas',
  Actividad: 'Ejecución',
  'Fuentes/Evidencia': 'Evidencia',
  Resultados: 'Resultado final',
  'Revisión Gerencial': 'Revisión gerencial',
  'Human Gate': 'Human Gate',
  Historial: 'Historial',
};
const STAGES = [
  ['Plan', '01 Plan'],
  ['Actividad', '02 Ejecución'],
  ['Revisión Gerencial', '03 Revisión'],
  ['Resultados', '04 Resultado final'],
  ['Human Gate', '05 Human Gate'],
];

export function Workspace({floor, id, tab = 'Resumen', version = '', navigate, onChange}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [posting, setPosting] = useState(false);
  const [rationale, setRationale] = useState('');
  const [planView, setPlanView] = useState('plan');
  const [resultView, setResultView] = useState('resumen');
  const inFlight = useRef(false);
  const refresh = useRef(null);

  useEffect(() => {
    let stopped = false, timer, controller;
    setData(null); setError(''); setNotice(''); setRationale('');
    const load = async () => {
      clearTimeout(timer);
      controller?.abort();
      controller = new AbortController();
      try {
        const detail = await caseDetail(floor.id, id, version, controller.signal);
        if (!stopped) { setData(detail); setError(''); }
      } catch (e) {
        if (!stopped && e.name !== 'AbortError') setError(e.message);
      } finally {
        if (!stopped) timer = setTimeout(load, 2000);
      }
    };
    refresh.current = load;
    load();
    return () => { stopped = true; clearTimeout(timer); controller?.abort(); };
  }, [floor.id, id, version]);

  const current = data && data.selected.version === data.latest.version;
  const busy = posting || data?.jobs.some(j => j.status === 'running');
  const go = (next, ver = version) => navigate('case', floor.id, id, next, ver);

  const operate = async action => {
    if (inFlight.current) return;
    inFlight.current = true;
    setPosting(true);
    setError('');
    setNotice('');
    try {
      const job = action === 'EJECUTAR'
        ? await executeCase(floor.id, id, data.latest.version ?? null)
        : await humanGate(floor.id, id, action, rationale, data.latest.version ?? null);
      setNotice(`${label(action)}: solicitud registrada. El estado se actualiza automáticamente.`);
      setData(old => ({...old, jobs: [...old.jobs, job]}));
      setRationale('');
      await refresh.current();
      onChange();
    } catch (e) {
      setError(e.message);
      await refresh.current();
      setError(e.message);
    } finally {
      setPosting(false);
      inFlight.current = false;
    }
  };

  const job = data?.jobs.at(-1);
  const jobState = job?.status;
  useEffect(() => { if (jobState && jobState !== 'running') onChange(); }, [jobState, onChange]);
  const download = (path, title) => path ? <a className="download" href={artifactUrl(floor.id, id, path)} target="_blank" rel="noreferrer">{title || 'Descargar'}</a> : null;
  const professional = data?.professional_reports || [];
  const professionalButtons = professional.length ? (
    <div className="gate-actions">
      {professional.map(item => (
        <a key={item.path} className="download" href={artifactUrl(floor.id, id, item.path)} target="_blank" rel="noreferrer">{item.label || (item.format === 'pdf' ? 'Ver/Descargar informe PDF' : 'Ver/Descargar informe Word')}</a>
      ))}
    </div>
  ) : null;

  if (!data) {
    return (
      <>
        <Notice error>{error}</Notice>
        <Empty title={error ? 'No se pudo abrir el expediente' : 'Cargando expediente'} text={error ? 'Revise la conexión y vuelva a intentar.' : 'Consultando documentos, versiones y registros.'}/>
        <button type="button" onClick={() => refresh.current?.()}>Reintentar</button>
      </>
    );
  }

  const selected = data.selected;
  const plan = data.plan;
  const agents = plan?.agent_ids || plan?.selected_agents || selected.routes?.map(a => a.startsWith('AGIA-') ? a : `AGIA-MGC-${a}`) || [];
  const consolidated = data.outputs['MGC-05_DEPARTMENT_REPORT.md'] || data.outputs['MGC-03_CONSOLIDATION.md'];
  const consolidationFile = data.outputs['MGC-03_CONSOLIDATION.md'] ? 'MGC-03_CONSOLIDATION.md' : 'MGC-05_DEPARTMENT_REPORT.md';
  const activeTab = tabs.includes(tab) ? tab : 'Resumen';
  const sequence = plan?.sequence || plan?.agent_ids || [];

  let body;
  if (activeTab === 'Resumen') {
    body = (
      <>
        <section className="panel">
          <h2>Instrucción al gerente</h2>
          <p className="preserve">{data.mission}</p>
          <div className="facts">
            <div><small>Destino</small><b>{floor.manager}</b></div>
            <div><small>Documentos registrados</small><b>{data.documents.length}</b></div>
            <div><small>Versiones registradas</small><b>{data.versions.length}</b></div>
            <div><small>Resultados de esta versión</small><b>{data.reports.filter(r => r.content).length}</b></div>
          </div>
        </section>
        <section className="panel">
          <h2>Estado de trabajo</h2>
          <Badge>{data.status}</Badge>
          <p>{data.status === 'RECOVERY_PENDING' || job?.status === 'recovery' ? 'Conexión interrumpida después del envío. Verificando el estado de la ejecución en Platform.' : busy ? 'Hay una operación en curso. Puede consultar el expediente mientras se completa.' : !data.latest.version ? 'El expediente está registrado. Ejecute al gerente para producir el plan y los resultados.' : data.status === 'CLOSED' ? 'La decisión humana de aprobación quedó registrada.' : consolidated ? 'El consolidado está disponible en Revisión Gerencial. Consulte los resultados y registre su decisión en Human Gate.' : 'No hay consolidado disponible para esta versión. Consulte la actividad y los errores materializados.'}</p>
          {data.outputs['MGC-05_EXECUTION_STATUS.md'] && <Report text={data.outputs['MGC-05_EXECUTION_STATUS.md']}/>}
        </section>
      </>
    );
  }
  if (activeTab === 'Plan') {
    const deps = plan?.dependencies || plan?.handoffs || selected.handoffs;
    const objective = plan?.mission || data.mission;
    body = (
      <section className="stage-panel">
        <header className="stage-head">
          <div>
            <small>ETAPA 01</small>
            <h2>Plan de trabajo del gerente</h2>
            <p>{selected.version ? `Versión ${selected.version} materializada por el gerente.` : 'Registro inicial. El plan completo aparece cuando el gerente ejecuta la misión.'}</p>
          </div>
          <Badge>{busy ? 'running' : data.status}</Badge>
        </header>
        <nav className="subtabs" aria-label="Secciones del plan">
          {[['plan', 'Plan'], ['especialistas', 'Especialistas'], ['dependencias', 'Dependencias'], ['evidencia', 'Evidencia requerida']].map(([key, name]) => (
            <button type="button" key={key} className={planView === key ? 'on' : ''} onClick={() => setPlanView(key)}>{name}</button>
          ))}
        </nav>
        {planView === 'plan' && (
          <div className="plan-stack">
            <div className="plan-block featured">
              <small>OBJETIVO INTERPRETADO</small>
              <p className="preserve">{objective}</p>
              <p className="muted">El backend registra la misión recibida. No se genera un objetivo adicional no materializado.</p>
            </div>
            {agents.length > 0 && (
              <>
                <h3>Especialistas seleccionados</h3>
                <div className="grid cards-3">
                  {agents.map(a => {
                    const agent = floor.agents.find(x => x.id === a);
                    return (
                      <article className="unit specialist" key={a}>
                        <small>{a}</small>
                        <h3>{agent?.name || a}</h3>
                        <Badge>Seleccionado</Badge>
                      </article>
                    );
                  })}
                </div>
              </>
            )}
            <h3>Plan de trabajo</h3>
            {sequence.length ? (
              <ol className="work-plan">
                {sequence.map((item, i) => <li key={i}><span>{String(i + 1).padStart(2, '0')}</span><b>{item}</b></li>)}
              </ol>
            ) : <Empty title="Sin plan ordenado materializado" text="La secuencia aparece cuando el gerente ejecuta y registra el plan."/>}
          </div>
        )}
        {planView === 'especialistas' && (
          agents.length
            ? <div className="grid cards-3">{agents.map(a => {
              const agent = floor.agents.find(x => x.id === a);
              return <article className="unit specialist" key={a}><small>ESPECIALISTA SELECCIONADO</small><h3>{a}</h3><p>{agent?.name || 'Especialista registrado en el plan'}</p><Badge>Seleccionado</Badge></article>;
            })}</div>
            : <Empty title="Sin especialistas materializados" text="La dotación del piso no implica selección para esta misión."/>
        )}
        {planView === 'dependencias' && <Records value={deps}/>}
        {planView === 'evidencia' && (
          data.documents.length
            ? <div className="document-list">{data.documents.map((d, i) => <article key={i}><div><b>{d.original_name || d.name}</b><small>Documento de evidencia registrado en el expediente</small></div></article>)}</div>
            : <Empty title="Sin evidencia documental adjunta" text="El gerente planificó con la instrucción registrada. No hay documentos adicionales en este expediente."/>
        )}
      </section>
    );
  }
  if (activeTab === 'Equipo') {
    body = (
      <section className="panel">
        <h2>Equipo seleccionado para la misión</h2>
        {agents.length ? (
          <div className="grid cards-3">
            {agents.map(a => {
              const agent = floor.agents.find(x => x.id === a);
              const report = data.reports.find(r => r.agent === a);
              const failure = selected.errors?.find(e => e.agent === a);
              return (
                <article className="unit" key={a}>
                  <small>ESPECIALISTA</small>
                  <h3>{a}</h3>
                  <p>{agent?.name || 'Especialista registrado en el plan'}</p>
                  <Badge>{failure ? 'SPECIALIST_EXECUTION_BLOCKED' : report?.content ? 'Resultado materializado' : 'Sin resultado materializado'}</Badge>
                </article>
              );
            })}
          </div>
        ) : <Empty title="Sin selección materializada" text="La dotación del piso no implica que sus especialistas hayan sido seleccionados o ejecutados para esta misión."/>}
        <h2>Coordinación registrada</h2>
        <Records value={selected.handoffs || plan?.handoffs || plan?.dependencies}/>
      </section>
    );
  }
  if (activeTab === 'Actividad') {
    const live = data.evidence?.live || {};
    const findings = live.findings ?? (Array.isArray(data.evidence?.findings) ? data.evidence.findings.length : 0);
    const sources = live.sources_located ?? (Array.isArray(data.evidence?.sources) ? data.evidence.sources.length : data.documents.length);
    const accepted = live.sources_accepted ?? '—';
    const discarded = live.sources_discarded ?? '—';
    const contradictions = Array.isArray(selected.contradictions) ? selected.contradictions.length : 0;
    const pending = Array.isArray(selected.human_decisions) ? selected.human_decisions.length : 0;
    const events = Array.isArray(data.activity) ? [...data.activity].reverse() : [];
    const phaseLabel = {manager_plan: 'Gerente planificando', manager_review: 'Gerente revisando', specialist_research: 'Especialista investigando', manager_deepen: 'Profundización ordenada'}[live.phase] || (busy ? 'Operación en curso' : 'Sin operación en curso');
    body = (
      <section className="stage-panel">
        <header className="stage-head">
          <small>ETAPA 02</small>
          <h2>Ejecución en tiempo real</h2>
          <p>Eventos materializados del piso. Sin porcentaje inventado ni cadena de razonamiento.</p>
        </header>
        <div className="execution-card live">
          <div>
            <small>{busy ? 'EN CURSO' : 'ESTADO DE EJECUCIÓN'}</small>
            <b>{live.actor || (busy ? label(job?.action || 'EJECUTAR') : 'Sin operación en curso')}</b>
            <p>{phaseLabel}{live.round ? ` · ronda ${live.round}` : ''}{live.updated_at ? ` · ${date(live.updated_at)}` : ''}</p>
          </div>
          {busy && <div className="progress indeterminate" role="progressbar" aria-label="Operación en curso"/>}
        </div>
        <div className="stat-grid exec-stats">
          <article className="st-info"><small>Fuentes localizadas</small><b>{sources ?? 0}</b></article>
          <article className="st-ok"><small>Fuentes aceptadas</small><b>{accepted}</b></article>
          <article className="st-danger"><small>Descartadas</small><b>{discarded}</b></article>
          <article className="st-info"><small>Hallazgos</small><b>{findings ?? 0}</b></article>
          <article className="st-warn"><small>Contradicciones</small><b>{contradictions}</b></article>
          <article><small>Pendientes</small><b>{pending}</b></article>
        </div>
        <h3>Especialistas en esta versión</h3>
        {agents.length ? (
          <div className="grid cards-3">
            {agents.map(a => {
              const report = data.reports.find(r => r.agent === a);
              const failure = selected.errors?.find(e => e.agent === a);
              const running = busy && !report?.content && !failure;
              return (
                <article className="unit specialist" key={a}>
                  <small>{a}</small>
                  <h3>{floor.agents.find(x => x.id === a)?.name || a}</h3>
                  <Badge>{failure ? 'SPECIALIST_EXECUTION_BLOCKED' : report?.content ? 'Resultado materializado' : running ? 'running' : 'Sin resultado materializado'}</Badge>
                  {running && <div className="progress indeterminate compact" role="progressbar" aria-label="En ejecución"/>}
                </article>
              );
            })}
          </div>
        ) : <Empty title="Sin ejecución especializada" text="Ejecute al gerente para producir trabajo de especialistas."/>}
        <h3>Actividad reciente</h3>
        {events.length ? (
          <ol className="timeline live-log">
            {events.slice(0, 40).map((item, i) => (
              <li key={item.at || i}>
                <b>{label(item.kind || item.event || item)}</b>
                <p>{item.summary || ''}{item.at ? ` · ${date(item.at)}` : ''}{item.round ? ` · ronda ${item.round}` : ''}</p>
              </li>
            ))}
          </ol>
        ) : <Empty title="Sin actividad materializada"/>}
        <h3>Operaciones del workspace</h3>
        <JobList jobs={data.jobs}/>
        {selected.errors?.length > 0 && <><h3>Errores de especialistas</h3><Records value={selected.errors.map(({agent, error, at}) => ({agent, error, at}))}/></>}
      </section>
    );
  }
  if (activeTab === 'Fuentes/Evidencia') {
    body = (
      <>
        <section className="panel">
          <h2>Fuentes consultadas</h2>
          {Array.isArray(data.evidence?.sources) && data.evidence.sources.length ? (
            <div className="document-list">
              {data.evidence.sources.map((s, i) => (
                <article key={s.source_id || i}>
                  <div><b>{s.document || s.locator || s.source_id}</b><small>{[s.source_id, s.method].filter(Boolean).join(' · ')}</small></div>
                </article>
              ))}
            </div>
          ) : <Empty title="Sin fuentes consultadas" text="Las fuentes aparecen cuando el especialista materializa evidencia pública."/>}
          <h2>Documentos originales</h2>
          {data.documents.length ? (
            <div className="document-list">
              {data.documents.map((d, i) => (
                <article key={i}>
                  <div><b>{d.original_name || d.name}</b><small className="hash">SHA-256 · {d.sha256 || 'No registrado'}</small></div>
                  {download(`documents/${d.name}`, 'Descargar documento')}
                </article>
              ))}
            </div>
          ) : <Empty title="Sin documentos adjuntos" text="Esta instrucción se registró sin evidencia documental adicional."/>}
        </section>
        <section className="panel">
          <h2>Trazabilidad de la versión seleccionada</h2>
          {data.traces.length ? data.traces.map(t => (
            <details key={t.path}>
              <summary>{t.path.split('/').at(-1)}</summary>
              {download(t.path, 'Descargar traza')}
              <Records value={t.data}/>
            </details>
          )) : <Empty title="Sin trazas de inferencia materializadas" text="No se atribuyen citas, extracción ni conclusiones que el backend no haya registrado."/>}
          <h2>Auditoría técnica del expediente</h2>
          <p className="muted">JSON de trazabilidad interna. El resultado ejecutivo está en Resultados y en el informe PDF/Word.</p>
          {data.evidence ? (
            <>
              <details><summary>Fuentes y evidencia</summary><Records value={{sources: data.evidence.sources, evidence: data.evidence.evidence}}/></details>
              <details><summary>Hallazgos y relaciones</summary><Records value={{findings: data.evidence.findings, lineage: data.evidence.lineage}}/></details>
            </>
          ) : <Empty/>}
        </section>
      </>
    );
  }
  const reportSections = splitReport(consolidated);
  const RESULT_TABS = [['resumen','Resumen'],['hallazgos','Hallazgos'],['riesgos','Riesgos'],['oportunidades','Oportunidades'],['plan','Plan de acción'],['fuentes','Fuentes']];
  const can = key => data.capabilities[key];
  const gateForm = (
    floor.id !== 'MGC-05' && floor.id !== 'MGC-03' ? <Empty title="Human Gate no ejecutable en este piso" text={data.availability}/> :
    !current ? <Empty title="Versión histórica de sólo consulta" text="Seleccione Última versión para registrar una decisión."/> :
    data.status === 'CLOSED' ? <Empty title="Expediente cerrado" text="La aprobación quedó registrada. Consulte las decisiones y el historial."/> :
    !data.latest.version ? <Empty title="Todavía no hay una versión para revisar" text="Ejecute al gerente y consulte los resultados antes de registrar una decisión."/> : (
    <form className="gate-form" onSubmit={e => e.preventDefault()}>
      <fieldset disabled={busy}>
        <legend>Human Gate · versión {data.latest.version}</legend>
        {!can('approve') && <p className="muted">Aprobación no disponible: se requiere un consolidado profesional en estado de revisión humana.</p>}
        <label htmlFor="rationale">Fundamento / observación para el gerente</label>
        <textarea id="rationale" required value={rationale} onChange={e => setRationale(e.target.value)} placeholder="Documente el fundamento de su decisión."/>
        <div className="gate-actions">
          <button type="button" className="approve" disabled={!rationale.trim() || !can('approve')} onClick={() => operate('APROBAR')}>APROBAR<span>Resultado final</span></button>
          <button type="button" className="correct" disabled={!rationale.trim() || !can('correct')} onClick={() => operate('CORREGIR')}>CORREGIR<span>Solicitar ajustes</span></button>
          <button type="button" className="reject" disabled={!rationale.trim() || !can('reject')} onClick={() => operate('RECHAZAR')}>RECHAZAR<span>No aprobado</span></button>
        </div>
      </fieldset>
    </form>
    )
  );
  const consolidatedBody = (
    <section className="stage-panel gate-stage">
      <header className="stage-head">
        <small>ETAPA 04 · 05</small>
        <h2>Resultado consolidado</h2>
        <p>Navegación sobre el informe departamental materializado. Human Gate queda como decisión protagonista.</p>
        {professionalButtons}
      </header>
      <nav className="subtabs result-tabs" aria-label="Secciones del consolidado">
        {RESULT_TABS.map(([key, name]) => (
          <button type="button" key={key} className={resultView === key ? 'on' : ''} onClick={() => setResultView(key)}>{name}</button>
        ))}
      </nav>
      {consolidated ? (
        reportSections[resultView].length
          ? reportSections[resultView].map((chunk, i) => <Report key={i} text={chunk}/>)
          : <Empty title={`Sin sección de ${RESULT_TABS.find(x => x[0] === resultView)?.[1]?.toLowerCase()}`} text="El consolidado materializado no declara esta sección. No se completa con contenido inventado."/>
      ) : <Empty title="Sin consolidado gerencial" text="No existe un informe departamental materializado para esta versión."/>}
      {resultView === 'fuentes' && data.evidence?.sources && (
        <div className="document-list">
          {data.evidence.sources.map((s, i) => <article key={i}><div><b>{s.document || s.source_id}</b><small>{s.source_id}</small></div></article>)}
        </div>
      )}
      <div className="human-gate-hero">
        <h2>Human Gate</h2>
        <p>La decisión se aplica a la última versión. CORREGIR devuelve la observación al gerente y genera una nueva ejecución versionada.</p>
        {gateForm}
      </div>
      <h3>Decisiones registradas</h3>
      <Records value={data.decisions}/>
    </section>
  );
  if (activeTab === 'Resultados' || activeTab === 'Human Gate') {
    body = consolidatedBody;
  }
  if (activeTab === 'Revisión Gerencial') {
    const first = data.reports.find(r => r.content);
    const failed = selected.errors || [];
    const returned = data.decisions?.slice().reverse().find(d => d.decision === 'CORREGIR' || d.action === 'CORREGIR');
    body = (
      <div className="review-layout">
        <section className="stage-panel">
          <header className="stage-head">
            <small>ETAPA 03</small>
            <h2>Resultado y revisión gerencial</h2>
            <p>Resultado individual materializado, fuentes y hallazgos disponibles. La decisión humana se registra en Human Gate.</p>
            {professionalButtons}
          </header>
          <div className="stat-grid">
            <article><small>Fuentes</small><b>{Array.isArray(data.evidence?.sources) ? data.evidence.sources.length : data.documents.length}</b></article>
            <article><small>Hallazgos</small><b>{Array.isArray(data.evidence?.findings) ? data.evidence.findings.length : 0}</b></article>
            <article><small>Informes</small><b>{data.reports.filter(r => r.content).length}</b></article>
          </div>
          {first ? (
            <details className="result result-card" open>
              <summary>{first.agent} · resultado individual</summary>
              {download(first.path, 'Descargar informe')}
              <Report text={first.content}/>
            </details>
          ) : consolidated ? (
            <>
              {download(`${data.version_directory}/${consolidationFile}`, 'Descargar consolidado')}
              <Report text={consolidated}/>
            </>
          ) : <Empty title="Sin resultado individual materializado" text="No existe un informe materializado para esta versión."/>}
        </section>
        <section className="stage-panel review-side">
          <h2>Evaluación del gerente</h2>
          <Badge>{data.status}</Badge>
          {failed.length > 0 && (
            <div className="eval-box warn">
              <b>Insuficiente</b>
              <ul>{failed.map(item => <li key={item.agent}>{item.agent}: {item.error}</li>)}</ul>
            </div>
          )}
          {data.status === 'INFRASTRUCTURE_BLOCKED' && (
            <div className="eval-box warn">
              <b>Infraestructura bloqueada</b>
              <p>No existe informe profesional ni resultado para aprobar.</p>
            </div>
          )}
          {(failed.length > 0 || returned) && (
            <div className="eval-box return">
              <b>{returned ? 'Trabajo devuelto al gerente para profundización' : 'Profundización requerida'}</b>
              <p>{failed.length ? `Especialista(s) con ejecución incompleta: ${failed.map(x => x.agent).join(', ')}.` : 'Queda registrada una corrección humana sobre este expediente.'}</p>
              <p>El backend no reenvía un especialista de forma aislada. CORREGIR en Human Gate genera una nueva versión a través del gerente.</p>
              {can('correct') && <button type="button" className="correct" onClick={() => go('Human Gate')}>Ir a Human Gate para devolver</button>}
            </div>
          )}
          {consolidated && ['HUMAN_REVIEW_REQUIRED', 'HUMAN_GATE_REQUIRED', 'READY_FOR_HUMAN_GATE'].includes(data.status) && !failed.length && (
            <div className="eval-box ready">
              <b>Listo para Human Gate</b>
              <p>El consolidado está disponible. Revise el informe y registre APROBAR, CORREGIR o RECHAZAR.</p>
              <button type="button" onClick={() => go('Human Gate')}>Ir a Human Gate</button>
            </div>
          )}
          <h3>Hallazgos</h3>
          {(selected.findings || data.evidence?.findings || []).length ? (
            <div className="document-list">
              {(selected.findings || data.evidence.findings).map((item, i) => (
                <article key={item.id || i}>
                  <div>
                    <b>{item.statement || item.claim || item.id}</b>
                    <small>{[item.specialist_kind || item.classification, item.confidence_label || item.sufficiency].filter(Boolean).join(' · ')}</small>
                  </div>
                </article>
              ))}
            </div>
          ) : <Empty title="Sin hallazgos materializados"/>}
          <h3>Brechas / confirmaciones</h3>
          {(selected.gaps || []).length ? (
            <div className="document-list">{(selected.gaps || []).map((gap, i) => <article key={i}><div><b>{typeof gap === 'string' ? gap : gap.statement || gap.detail || gap.id || 'Gap materializado'}</b></div></article>)}</div>
          ) : <Empty title="Sin gaps materializados"/>}
          <h3>Contradicciones</h3>
          {(selected.contradictions || []).length ? (
            <div className="document-list">{(selected.contradictions || []).map((item, i) => <article key={i}><div><b>{typeof item === 'string' ? item : item.statement || item.detail || item.id || 'Contradicción materializada'}</b></div></article>)}</div>
          ) : <Empty title="Sin contradicciones materializadas"/>}
        </section>
      </div>
    );
  }
  if (activeTab === 'Historial') {
    body = (
      <section className="panel">
        <h2>Versiones del expediente</h2>
        {data.versions.length ? (
          <div className="rows">
            {data.versions.map(v => (
              <article key={v.version}>
                <div>
                  <b>Versión {v.version}</b>
                  <p>{date(v.at)}{v.parent_version ? ` · Derivada de versión ${v.parent_version}` : ''}</p>
                  <Badge>{v.status}</Badge>
                  {v.correction && <p className="preserve">{v.correction}</p>}
                </div>
                <button type="button" onClick={() => go('Resumen', String(v.version))}>Consultar versión {v.version}</button>
              </article>
            ))}
          </div>
        ) : <Empty title="Sin versiones de ejecución"/>}
        <h2>Decisiones humanas</h2>
        <Records value={data.decisions}/>
        <h2>Operaciones del workspace</h2>
        <JobList jobs={data.jobs}/>
        <h2>Archivos de auditoría</h2>
        <div className="document-list">
          {data.artifacts.map(a => (
            <article key={a.path}>
              <div><b>{a.path}</b><small>{a.size.toLocaleString('es-CL')} bytes</small></div>
              {download(a.path, 'Descargar archivo')}
            </article>
          ))}
        </div>
      </section>
    );
  }

  return (
    <>
      <div className="case-heading">
        <Hero e={`EXPEDIENTE · ${floor.id}`} t={id} p={data.mission} aside={<Badge>{data.status}</Badge>}/>
      </div>
      <div className="case-toolbar">
        <label>Versión consultada
          <select aria-label="Versión consultada" value={version} onChange={e => go(activeTab, e.target.value)}>
            <option value="">Última versión{data.latest.version ? ` · ${data.latest.version}` : ''}</option>
            {data.versions.map(v => <option key={v.version} value={v.version}>Versión {v.version}</option>)}
          </select>
        </label>
        <button type="button" className="secondary" onClick={() => { refresh.current?.(); onChange(); }}>Actualizar expediente</button>
        <button type="button" disabled={busy || !data.capabilities.execute} onClick={() => operate('EJECUTAR')}>
          {busy ? 'Operación en curso…' : data.latest.version ? 'Ejecutar nueva versión' : 'Ejecutar al Gerente'}
        </button>
      </div>
      {floor.id === 'MGC-03' && <Notice>{data.availability}</Notice>}
      <Notice error>{error}</Notice>
      <Notice>{notice}</Notice>
      {job && <Notice error={['failed', 'interrupted'].includes(job.status)}>{label(job.action)} · {label(job.status)}{job.case_status ? ` · ${label(job.case_status)}` : ''}{job.error ? ` — ${job.error}` : ''}</Notice>}
      {!current && <Notice>Consulta histórica. Las acciones están deshabilitadas; documentos, actividad y decisiones muestran el registro acumulado del expediente.</Notice>}
      <nav className="stages" aria-label="Etapas de trabajo">
        {STAGES.map(([key, name]) => (
          <button type="button" key={key} className={activeTab === key ? 'on' : ''} onClick={() => go(key)}>{name}</button>
        ))}
      </nav>
      <nav className="tabs" role="tablist" aria-label="Vistas del expediente">
        {tabs.map(t => (
          <button type="button" role="tab" id={`tab-${tabs.indexOf(t)}`} aria-selected={activeTab === t} aria-controls="case-panel" key={t} onClick={() => go(t)}>{tabLabel[t]}</button>
        ))}
      </nav>
      <div id="case-panel" role="tabpanel" aria-labelledby={`tab-${tabs.indexOf(activeTab)}`}>{body}</div>
    </>
  );
}

function JobList({jobs}) {
  return jobs.length ? (
    <ol className="timeline">
      {jobs.map(j => (
        <li key={j.id}>
          <b>{label(j.action)}</b> <Badge>{j.status}</Badge>
          <p>{date(j.started_at)}{j.finished_at ? ` → ${date(j.finished_at)}` : ''}</p>
          {j.error && <Notice error={['failed', 'interrupted'].includes(j.status)}>{j.error}</Notice>}
          {j.case_status && <p>Estado registrado: {label(j.case_status)}</p>}
        </li>
      ))}
    </ol>
  ) : <Empty title="Sin operaciones registradas desde el workspace"/>;
}
