import React, {useEffect, useRef, useState} from 'react';
import {
  createCase, createCorporateExpediente, encodeFile, executeCorporateTask, corporateAgents,
  boardSessions, boardSession, createBoardSession, prepareBoardSession, freezeBoardSession,
  deliberateBoardSession, boardHumanGate, corporateExpedientes,
  calendarEvents, createCalendarEvent, communications as listCommunications, createCommunication, communication,
  syncEmailPull, linkCommunicationExpediente, markCommunicationRead,
  submitCommunicationApproval, communicationHumanGate, sendCommunication, providersStatus, runF2bSync,
  executiveBoard,
  executiveNews,
  executiveAlerts,
} from './api';
import {Badge, Cases, Empty, Hero, Metric, Notice} from './components';
import {Icon} from './icons';
import {ASSETS, AREA_FUNCTIONS, directorPhoto, areaPhoto, availabilityTone} from './assets';
import {AreaCard, AvailabilityDot, ClockWeather, CompanyBlock, DIRECTORS, ExecHero, ExecutiveAlertsPanel, ExecutiveIndicators, ExecutiveNewsPanel, LNH_FUNCTIONAL_AREAS, Panel, Shortcut, StatusLabel} from './ui';

const UNAVAILABLE = 'No existe un backend corporativo habilitado para esta vista.';
const INSTRUCTION_TYPES = ['Propuesta', 'Decisión requerida', 'Proyecto', 'Inversión', 'Compra', 'Investigación', 'Instrucción', 'Otro'];
const INSTRUCTION_SCOPES = [
  {id: 'LNH', label: 'LNH'},
  {id: 'MGC', label: 'MGC'},
  {id: 'LNR', label: 'LNR'},
  {id: 'HOLDING', label: 'Holding completo'},
];
const PRIORITIES = ['P0', 'P1', 'P2', 'P3'];

export function Home({data, list, openCase, navigate}) {
  const review = list.filter(x => x.requires_decision);
  const errors = list.filter(x => ['PLATFORM_EXECUTION_ERROR', 'PLATFORM_CONNECTION_ERROR', 'RECOVERY_PENDING', 'INCOMPLETE'].includes(x.status));
  const systemComms = [...review, ...errors].slice(0, 5);
  const [newsTab, setNewsTab] = useState('Nacional');
  const [execBoard, setExecBoard] = useState(null);
  const [execNews, setExecNews] = useState(undefined);
  const [execAlerts, setExecAlerts] = useState(undefined);

  useEffect(() => {
    let alive = true;
    executiveBoard({})
      .then(board => { if (alive) setExecBoard(board); })
      .catch(() => { if (alive) setExecBoard(null); });
    executiveNews({limit: 8})
      .then(board => { if (alive) setExecNews(board); })
      .catch(() => { if (alive) setExecNews(null); });
    executiveAlerts({limit: 20})
      .then(board => { if (alive) setExecAlerts(board); })
      .catch(() => { if (alive) setExecAlerts(null); });
    return () => { alive = false; };
  }, []);

  return (
    <div className="office">
      <div className="page-title-block">
        <h1>Mi Oficina</h1>
        <p>Presidencia <span>|</span> Latitud Norte Holding</p>
      </div>
      <section className="office-hero">
        <div className="office-hero-media" aria-hidden="true">
          <img src="/oficina-hero.jpg" alt="" />
        </div>
        <div className="office-hero-shade"/>
        <div className="office-hero-copy">
          <blockquote>Disciplina hoy, valor mañana.<cite>LATITUD NORTE HOLDING</cite></blockquote>
        </div>
        <ClockWeather weather={execBoard?.weather}/>
      </section>
      <div className="shortcut-grid">
        <Shortcut gold icon="plus" title="Nueva Instrucción Corporativa" text="Propuesta, proyecto o decisión de Presidencia" onClick={() => navigate('NuevaInstruccion')}/>
        <Shortcut icon="calendar" title="Calendario" text="Agenda de Presidencia" onClick={() => navigate('Calendario')}/>
        <Shortcut icon="communications" title="Comunicaciones" text="Mensajes y notificaciones" badge={systemComms.length || undefined} onClick={() => navigate('Comunicaciones')}/>
        <Shortcut icon="reports" title="Reportes Ejecutivos" text="Sin datos · pendiente" onClick={() => navigate('Decisiones')}/>
        <Shortcut icon="users" title="Directorio" text="Gobierno del Holding" onClick={() => navigate('Directorio')}/>
        <Shortcut icon="holding" title="Holding" text="Visión general del grupo" onClick={() => navigate('Holding')}/>
      </div>
      <div className="office-row-3">
        <ExecutiveIndicators
          title="Indicadores económicos Chile"
          boardSection={execBoard?.economy}
          emptyText="UF, UTM, USD/CLP, IPC y TPM no disponibles."
        />
        <ExecutiveIndicators
          title="Mercados relevantes"
          boardSection={execBoard?.markets}
          emptyText="Referencia de cobre no disponible."
        />
        <Panel title="Comunicaciones recientes" action={<button type="button" className="text-button" onClick={() => navigate('Comunicaciones')}>Ver todas</button>}>
          {systemComms.length ? (
            <div className="comm-feed">
              {systemComms.map(row => (
                <button type="button" className="comm-item" key={row.case_id} onClick={() => openCase(row)}>
                  <span className="comm-dot"/>
                  <span>
                    <b>{row.requires_decision ? 'Human Gate' : row.status}</b>
                    <small>{row.floor_id} · {row.case_id}</small>
                  </span>
                </button>
              ))}
            </div>
          ) : <Empty title="Sin comunicaciones" text="Revise Comunicaciones para email/WhatsApp."/>}
        </Panel>
      </div>
      <div className="office-row-3">
        <Panel title="Resumen financiero del Holding" action={<button type="button" className="text-button" onClick={() => navigate('Area', 'finanzas')}>Ver detalle</button>}>
          <div className="finance-kpis">
            {['Caja Total', 'Ingresos YTD', 'Gastos YTD', 'Resultado YTD'].map(label => (
              <article key={label}><small>{label}</small><b>Sin datos</b><span>Pendiente de integración</span></article>
            ))}
          </div>
          <div className="chart-placeholder"><Empty title="Sin serie financiera" text="No se muestran cifras demostrativas."/></div>
        </Panel>
        <Panel title="Mi Agenda" action={<button type="button" className="text-button" onClick={() => navigate('Calendario')}>Ver calendario</button>}>
          <Empty title="Agenda vacía" text="Sin eventos materializados."/>
        </Panel>
        <Panel title="Noticias" action={execNews?.status ? <span className={execNews.status === 'ACTUALIZADO' ? 'status-ok' : (execNews.status === 'DESACTUALIZADO' ? 'status-warn' : 'status-pending')}>{execNews.status}</span> : null}>
          <ExecutiveNewsPanel newsBoard={execNews} tab={newsTab} onTab={setNewsTab}/>
        </Panel>
      </div>
      <div className="office-row-3">
        <Panel title="Alertas y pendientes" action={<button type="button" className="text-button" onClick={() => navigate('Decisiones')}>Ver todas</button>}>
          <ExecutiveAlertsPanel
            alertsBoard={execAlerts}
            openCase={openCase}
            navigate={navigate}
          />
        </Panel>
        <Panel title="Accesos directos">
          <div className="mini-grid">
            {[
              ['Directorio', 'users', () => navigate('Directorio')],
              ['Finanzas', 'finance', () => navigate('Area', 'finanzas')],
              ['PMO', 'reports', () => navigate('Areas')],
              ['Mis Documentos', 'evidence', () => navigate('Decisiones')],
              ['Empresas', 'company', () => navigate('Holding')],
              ['Configuración', 'settings', () => navigate('Configuracion')],
            ].map(([label, icon, go]) => (
              <button type="button" key={label} className="mini-tile" onClick={go}>
                <Icon name={icon}/><span>{label}</span>
              </button>
            ))}
          </div>
        </Panel>
        <Panel title="Fuente de datos 2C">
          <p className="muted-note">Clima: Open-Meteo · Economía/Mercados: mindicador.cl · Noticias: BBC / CNBC / Google News · Sin OpenAI Platform.</p>
          <p className="muted-note">platform_calls: {(execBoard?.platform_calls ?? 0) + (execNews?.platform_calls ?? 0) + (execAlerts?.platform_calls ?? 0)}</p>
        </Panel>
      </div>
    </div>
  );
}

export function Holding({companies, floors, list, enter, navigate, agentBoard}) {
  const operationalFloors = floors.filter(f => f.status === 'Operativo').length;
  const agents = floors.flatMap(f => f.agents).length;
  const byArea = Object.fromEntries((agentBoard?.agents || []).map(a => [a.area_id, a]));
  return (
    <div className="holding-page">
      <section className="holding-hero">
        <div className="holding-hero-media" aria-hidden="true"/>
        <div className="holding-hero-shade"/>
        <div className="holding-hero-copy">
          <small>HOLDING</small>
          <h1>Latitud Norte Holding</h1>
          <p>Visión general del grupo. Pisos y misiones se consultan dentro de cada empresa.</p>
        </div>
        <aside className="holding-values">
          <span>Personas</span><span>Activos</span><span>Empresas</span><span>Oportunidades</span><span>Valor</span>
        </aside>
      </section>
      <div className="kpi-ribbon">
        <article><b>{companies.length}</b><small>Empresas</small></article>
        <article><b>{LNH_FUNCTIONAL_AREAS.length}</b><small>Áreas Corporativas</small></article>
        <article><b>{floors.length}</b><small>Pisos</small></article>
        <article><b>{(agentBoard?.agents || []).length || agents}</b><small>Agentes LNH</small></article>
        <article><b>{list.length}</b><small>Expedientes</small></article>
        <article><b>{operationalFloors}</b><small>Pisos operativos</small></article>
      </div>
      <h2 className="section-title">Empresas del grupo</h2>
      <div className="company-duo">
        {companies.map(company => (
          <CompanyBlock key={company.id} company={company} floors={floors} cases={list} enter={enter}/>
        ))}
      </div>
      <h2 className="section-title">Áreas corporativas</h2>
      <div className="area-grid area-grid-8">
        {LNH_FUNCTIONAL_AREAS.map(area => (
          <AreaCard
            key={area.id}
            area={area}
            agent={area.areaId ? byArea[area.areaId] : null}
            open={item => navigate(item.route || 'Area', item.route ? undefined : item.id)}
          />
        ))}
      </div>
    </div>
  );
}

export function Companies({companies, floors, list, enter}) {
  return (
    <div className="holding-page">
      <div className="page-title-block">
        <h1>Empresas</h1>
        <p>Holding <span>|</span> Latitud Norte Holding</p>
      </div>
      <div className="company-duo">
        {companies.map(company => (
          <CompanyBlock key={company.id} company={company} floors={floors} cases={list} enter={enter}/>
        ))}
      </div>
      <Panel title="Indicadores por empresa (YTD)">
        <div className="company-duo">
          {companies.map(company => (
            <article key={company.id} className="panel" style={{margin:0}}>
              <h3>{company.name}</h3>
              <Empty title="Sin datos" text="Indicadores financieros pendientes de integración. No se muestran cifras demostrativas."/>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}

export function CompanyPage({company, floors, work, openFloor, instruct, openCase}) {
  const isMgc = company.id === 'MGC';
  const rows = floors.filter(f => f.company === company.id);
  const executable = rows.find(f => f.id === 'MGC-03');
  const active = work.filter(c => c.status !== 'CLOSED' && c.status !== 'APPROVED');
  const gates = work.filter(c => c.requires_decision);
  const [tab, setTab] = useState('Resumen');
  const tabs = isMgc
    ? ['Resumen', 'Pisos', 'Misiones', 'Proyectos', 'Mercados', 'Operaciones', 'Expedientes', 'Documentos', 'Human Gate', 'Actividad']
    : ['Resumen', 'Departamentos', 'Proyectos', 'Portafolio', 'Mercado', 'Expedientes', 'Documentos', 'Actividad', 'Human Gate'];
  const heroImg = isMgc ? ASSETS.mgc.hero : ASSETS.lnre.hero;
  const brandLogo = isMgc ? ASSETS.mgc.logoOficial : ASSETS.lnre.logoOficial;
  const map = isMgc ? ASSETS.mgc.worldMap : ASSETS.lnre.worldMap;
  const micros = isMgc ? ASSETS.mgc.micros : ASSETS.lnre.micros;
  const subtitle = isMgc
    ? 'Conectando recursos con el mundo.'
    : 'Desarrollo e inversión inmobiliaria de alto valor.';
  const quote = isMgc
    ? 'Minería hoy.\nOportunidades mañana.'
    : 'Espacios que generan valor\ny futuro.';

  return (
    <div className={`company-page theme-${company.id.toLowerCase()}`}>
      <ExecHero
        breadcrumb={`LNH › ${company.id}`}
        brandLogo={brandLogo}
        subtitle={subtitle}
        quote={quote}
        image={heroImg}
        aside={executable ? (
          <button type="button" className="primary gold-btn" onClick={() => instruct(executable.id)}>+ Nueva Misión</button>
        ) : null}
        className={`company-exec-hero company-hero-${company.id.toLowerCase()}`}
      />
      <nav className="tabs exec-tabs" role="tablist">
        {tabs.map(name => (
          <button type="button" role="tab" key={name} aria-selected={tab === name} onClick={() => setTab(name)}>{name}</button>
        ))}
      </nav>

      {tab === 'Resumen' && (
        <>
          <section className="company-status-bar">
            <div><small>Estado operativo</small><Badge>{company.status || 'Registrado'}</Badge></div>
            <div><small>Pisos / departamentos</small><b>{rows.length || '—'}</b></div>
            <div><small>Expedientes activos</small><b>{active.length || '—'}</b></div>
            <div><small>Human Gate</small><b>{gates.length || '—'}</b></div>
            <div className="company-map" style={{backgroundImage: `url(${map})`}} aria-hidden="true"/>
          </section>
          <div className="company-split">
            <Panel title={isMgc ? 'Identidad operativa' : 'Identidad inmobiliaria'}>
              <div className="micro-row">
                {micros.map((src, i) => (
                  <figure key={src} className="micro-card">
                    <img src={src} alt="" />
                    <figcaption>Recurso visual {i + 1}</figcaption>
                  </figure>
                ))}
              </div>
              <p className="muted">Las microfotografías son assets visuales. No representan proyectos, minas ni propiedades registradas.</p>
            </Panel>
            <Panel title="Actividad reciente">
              {!work.length && <Empty title="Sin actividad registrada" text="Cuando existan expedientes o hitos en el backend, aparecerán aquí."/>}
              {!!work.length && (
                <ul className="exec-list">
                  {work.slice(0, 6).map(c => (
                    <li key={c.id}>
                      <b>{c.subject || c.mission?.slice?.(0, 80) || c.id}</b>
                      <small>{c.status} · {c.floor_id || company.id}</small>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        </>
      )}

      {(tab === 'Pisos' || tab === 'Departamentos') && (
        <>
          <h2 className="section-title">{isMgc ? 'Pisos' : 'Departamentos'}</h2>
          <FloorRows rows={rows} open={openFloor}/>
          {!isMgc && !rows.length && (
            <Empty title="Sin departamentos registrados" text="La estructura de agentes de LNRE se habilitará cuando exista en el backend. CaptaPropIA permanece asociada a LNRE según arquitectura."/>
          )}
        </>
      )}

      {tab === 'Misiones' && (
        executable
          ? (
            <Panel title="Misiones" action={<button type="button" className="gold-btn" onClick={() => instruct(executable.id)}>+ Nueva Misión</button>}>
              <Cases rows={work.filter(c => c.floor_id === 'MGC-03')} open={openCase || (() => {})} emptyTitle="Sin misiones registradas" emptyText="Cree una misión desde MGC-03. No se inventan misiones."/>
            </Panel>
          )
          : <Empty title="Sin canal de misiones" text="No hay piso ejecutor habilitado para esta empresa."/>
      )}

      {(tab === 'Proyectos' || tab === 'Portafolio') && (
        <Empty
          title={isMgc ? 'Sin proyectos registrados' : (tab === 'Portafolio' ? 'Sin portafolio registrado' : 'Sin proyectos registrados')}
          text="No se muestran nombres ni cifras de la referencia visual. Solo datos reales del backend."
        />
      )}

      {(tab === 'Mercados' || tab === 'Mercado' || tab === 'Operaciones') && (
        <Empty title={`Sin ${tab.toLowerCase()} registrados`} text="Cuando el backend publique información real, se mostrará en este módulo."/>
      )}

      {tab === 'Expedientes' && (
        <Panel title="Expedientes">
          <Cases rows={work} open={openCase || (() => {})} emptyTitle="Sin expedientes" emptyText="No hay expedientes asociados a esta empresa."/>
        </Panel>
      )}

      {tab === 'Documentos' && (
        <Empty title="Sin documentos registrados" text="Los documentos viven en el expediente correspondiente."/>
      )}

      {tab === 'Human Gate' && (
        <Panel title="Human Gate">
          <Cases rows={gates} open={openCase || (() => {})} emptyTitle="Sin decisiones pendientes" emptyText="No hay consolidado listo para decisión humana."/>
        </Panel>
      )}

      {tab === 'Actividad' && (
        <Panel title={isMgc ? 'Actividad reciente' : 'Actividad / hitos'}>
          {!work.length && <Empty title="Sin actividad registrada" text="Sin hitos materializados en el sistema."/>}
          {!!work.length && (
            <ul className="exec-list">
              {work.map(c => (
                <li key={c.id}>
                  <b>{c.subject || c.id}</b>
                  <small>{c.status} · {c.updated_at || c.created_at || '—'}</small>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}
    </div>
  );
}

export function FloorRows({rows, open}) {
  if (!rows.length) return <Empty title="Sin pisos habilitados" text="Esta empresa no tiene departamentos registrados."/>;
  return (
    <div className="rows floors">
      {rows.map(x => (
        <button type="button" className="floor-row" key={x.id} onClick={() => open(x.id)}>
          <div className="mark sq"><Icon name="floors"/></div>
          <div className="floor-id">{x.id}</div>
          <div>
            <b>{x.name.replace(`${x.id} `, '')}</b>
            <p>Gerente: {x.manager}</p>
          </div>
          <Badge>{x.status}</Badge>
          <span className="chevron" aria-hidden="true"><Icon name="chevron"/></span>
        </button>
      ))}
    </div>
  );
}

export function FloorPage({floor, work, openCase, instruct}) {
  const pending = work.filter(c => c.requires_decision);
  const code = floor.id.replace(/^[A-Z]+-/, '');
  return (
    <>
      <Hero e="PISO OPERATIVO" t={`${floor.id} — ${floor.name.replace(`${floor.id} `, '')}`} p={floor.availability} aside={<button type="button" className="primary gold-btn" onClick={instruct}>+ Nueva Misión</button>}/>
      <section className="manager">
        <div className="mark lg">{code === '03' ? 'M3' : code === '05' ? 'M5' : code}</div>
        <div>
          <small>GERENTE DEL PISO</small>
          <b>{floor.manager}</b>
          <Badge>{floor.status}</Badge>
        </div>
      </section>
      <section className="panel agents-panel">
        <h2>Agentes del piso</h2>
        <div className="agent-list">
          {floor.agents.map(a => (
            <article className="agent-row" key={a.id}>
              <div className="mark sq sm"><Icon name="agents"/></div>
              <div>
                <b>{a.id}</b>
                <p>{a.name}</p>
              </div>
              <Badge>{a.status}</Badge>
            </article>
          ))}
        </div>
      </section>
      <section className="panel">
        <h2>Expedientes del piso</h2>
        <Cases rows={work} open={openCase}/>
      </section>
      {['MGC-05', 'MGC-03'].includes(floor.id) && pending.length > 0 && (
        <section className="panel">
          <h2>Human Gate pendiente</h2>
          <Cases rows={pending} open={openCase}/>
        </section>
      )}
    </>
  );
}

function composeMission({subject, mission, priority, due, company, floor}) {
  return [
    subject && `Asunto: ${subject}`,
    company && `Empresa: ${company}`,
    floor && `Piso: ${floor}`,
    priority && `Prioridad: ${priority}`,
    due && `Fecha objetivo: ${due}`,
    '',
    mission,
  ].filter(line => line !== undefined).join('\n').trim();
}

export function Instruction({floor, created, cancel, company}) {
  return (
    <MissionForm
      mode="mission"
      floor={floor}
      company={company}
      cancel={cancel}
      onSubmit={async ({subject, mission, priority, due, files}) => {
        const documents = await Promise.all(files.map(encodeFile));
        created(await createCase(composeMission({
          subject, mission, priority, due, company: company?.id || floor.company, floor: floor.id,
        }), floor.id, documents));
      }}
    />
  );
}

export function CorporateInstruction({cancel, created}) {
  return (
    <MissionForm
      mode="instruction"
      cancel={cancel}
      onSubmit={async ({type, scope, subject, mission, priority, due, files}) => {
        if (!subject.trim()) throw new Error('El asunto es obligatorio.');
        if (!mission.trim()) throw new Error('La instrucción de Presidencia es obligatoria.');
        const documents = await Promise.all(files.map(encodeFile));
        const expediente = await createCorporateExpediente({
          tipo: type,
          ambito: scope,
          prioridad: priority,
          asunto: subject.trim(),
          instruccion_original: mission.trim(),
          fecha_objetivo: due || null,
          creado_por: 'Presidencia LNH',
          documents,
        });
        created(expediente);
      }}
    />
  );
}

export function CorporateExpedienteView({expediente, onBack, onRefresh}) {
  const [busyTask, setBusyTask] = useState('');
  const [execError, setExecError] = useState('');
  if (!expediente) {
    return <Empty title="Expediente corporativo" text="No se encontró el expediente solicitado."/>;
  }
  const r = expediente.resumen || expediente;
  const docs = expediente.documentos || [];
  const events = (expediente.eventos || []).slice().reverse();
  const routing = expediente.routing || {};
  const destinations = routing.destinations || [];
  const tasks = expediente.encargos || [];
  const deps = expediente.dependencias || [];
  const overdue = expediente.vencimientos || [];
  const sessions = expediente.platform_sessions || [];
  const results = expediente.resultados || [];
  const runTask = async taskId => {
    setExecError('');
    setBusyTask(taskId);
    try {
      await executeCorporateTask(expediente.expediente_id, taskId, {
        idempotency_key: `mc-${taskId}`,
        actor: 'Presidencia LNH',
      });
      if (onRefresh) await onRefresh();
    } catch (err) {
      setExecError(err.message);
    } finally {
      setBusyTask('');
    }
  };
  return (
    <div>
      <section className="page-head">
        <small>EXPEDIENTE CORPORATIVO LNH</small>
        <h1>{r.asunto || expediente.asunto}</h1>
        <p>Gobierno LNH-DATA-001 · Routing LNH-WF-001 · Ejecución Platform Bloque 3.</p>
      </section>
      {execError && <Notice tone="warn">{execError}</Notice>}
      <div className="office-row-3" style={{marginBottom: 16}}>
        <Panel title="Identificación">
          <p><b>ID:</b> {expediente.expediente_id}</p>
          <p><b>Estado:</b> {expediente.estado_actual}</p>
          <p><b>Versión:</b> {expediente.version_actual}</p>
          <p><b>Tipo:</b> {expediente.tipo}</p>
          <p><b>Ámbito:</b> {expediente.ambito}</p>
          <p><b>Prioridad:</b> {expediente.prioridad}</p>
        </Panel>
        <Panel title="Registro">
          <p><b>Creado:</b> {expediente.fecha_creacion}</p>
          <p><b>Fecha objetivo:</b> {expediente.fecha_objetivo || 'Sin fecha objetivo'}</p>
          <p><b>Creador:</b> {expediente.creado_por}</p>
          <p><b>Padre:</b> {expediente.expediente_padre || '—'}</p>
          <p><b>Documentos:</b> {docs.length}</p>
          <p><b>Eventos:</b> {(expediente.eventos || []).length}</p>
        </Panel>
        <Panel title="Capacidades Bloque 3">
          <p>Routing: {expediente.routing_applied ? 'aplicado' : 'pendiente'}</p>
          <p>Platform execute: disponible</p>
          <p>Directorio: {routing.directorio?.candidate ? 'candidato / disponible Fase 2A' : 'no marcado'}</p>
          <p>Human Gate Presidencia: vía Sesión Directorio</p>
          <button type="button" className="text-button" onClick={onBack}>Volver a Inicio</button>
          {onRefresh && <button type="button" className="text-button" onClick={onRefresh}>Actualizar</button>}
        </Panel>
      </div>
      <Panel title="Instrucción original">
        <pre style={{whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit'}}>{expediente.instruccion_original}</pre>
      </Panel>
      <div className="section-title">Routing y destinos</div>
      {!expediente.routing_applied && <Empty title="Sin routing" text="El expediente aún no tiene routing aplicado."/>}
      {!!expediente.routing_applied && (
        <Panel title={routing.rule_id || 'Regla WF-001'}>
          <p><b>Clasificación requerida:</b> {routing.requires_classification ? 'Sí → LNH-03' : 'No'}</p>
          {routing.classification_reason && <p>{routing.classification_reason}</p>}
          <p><b>Próximo gate:</b> {routing.next_gate || '—'}</p>
          <p><b>Urgencia:</b> {routing.urgency?.escalamiento || expediente.prioridad}</p>
          <ul className="plain-list">
            {destinations.map(d => (
              <li key={`${d.assigned_to}-${d.role}`}>{d.label} · {d.role} · {d.deliverable_type}</li>
            ))}
          </ul>
        </Panel>
      )}
      <div className="section-title">Encargos</div>
      {!tasks.length && <Empty title="Sin encargos" text="No hay tareas registradas."/>}
      {!!tasks.length && (
        <ul className="plain-list">
          {tasks.map(t => (
            <li key={t.task_id}>
              <b>{t.assigned_to}</b> · {t.status} · prioridad {t.priority || '—'}
              · vence {t.due_at || '—'}
              {t.platform_session_id ? ` · sesión ${t.platform_session_id}` : ''}
              {t.result_id ? ` · result ${t.result_id}` : ''}
              {t.last_error ? ` · error: ${t.last_error}` : ''}
              <div>{t.objective}</div>
              {['PENDIENTE', 'EN_CURSO'].includes(t.status) && (
                <button
                  type="button"
                  className="text-button"
                  disabled={!!busyTask}
                  onClick={() => runTask(t.task_id)}
                >
                  {busyTask === t.task_id ? 'Ejecutando en Platform…' : 'Ejecutar en Platform'}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      <div className="section-title">Sesiones Platform</div>
      {!sessions.length && <Empty title="Sin sesiones" text="Aún no hay Managed Sessions vinculadas."/>}
      {!!sessions.length && (
        <ul className="plain-list">
          {sessions.map((s, idx) => (
            <li key={s.platform_session_id || idx}>
              {s.agent_id} · {s.status} · session {s.platform_session_id || '—'}
              · task {s.task_id}
              {s.error ? ` · ${s.error_kind || 'error'}: ${s.error}` : ''}
              {s.result_id ? ` · result ${s.result_id}` : ''}
            </li>
          ))}
        </ul>
      )}
      <div className="section-title">Informes / resultados</div>
      {!results.length && <Empty title="Sin informes" text="No hay productos Platform persistidos."/>}
      {!!results.length && results.map(res => (
        <Panel key={res.result_id} title={`${res.agent_id} · ${res.result_id}`}>
          <p><b>Fecha:</b> {res.fecha} · <b>Estado:</b> {res.estado} · <b>Task:</b> {res.task_id}</p>
          <p><b>Sesión:</b> {res.platform_session_id || '—'}</p>
          <pre style={{whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit', maxHeight: 240, overflow: 'auto'}}>{res.contenido}</pre>
          {!!(res.fuentes_evidencias || []).length && (
            <ul className="plain-list">
              {(res.fuentes_evidencias || []).map((f, i) => (
                <li key={i}>{f.referencia || f.url || f.title || JSON.stringify(f)}</li>
              ))}
            </ul>
          )}
        </Panel>
      ))}
      <div className="section-title">Dependencias</div>
      {!deps.length && <Empty title="Sin dependencias" text="No hay prerrequisitos registrados."/>}
      {!!deps.length && (
        <ul className="plain-list">
          {deps.map(d => (
            <li key={d.dependency_id}>{d.prerequisite_task_id} → debe completarse antes de → {d.dependent_task_id}</li>
          ))}
        </ul>
      )}
      <div className="section-title">Vencimientos</div>
      {!overdue.length && <Empty title="Sin vencidos" text="No hay encargos vencidos registrados."/>}
      {!!overdue.length && (
        <ul className="plain-list">
          {overdue.map(item => (
            <li key={item.task_id}>{item.assigned_to} · {item.due_at} · {item.status}</li>
          ))}
        </ul>
      )}
      <div className="section-title">Documentos</div>
      {!docs.length && <Empty title="Sin adjuntos" text="La instrucción se registró sin documentación adjunta."/>}
      {!!docs.length && (
        <ul className="plain-list">
          {docs.map(d => (
            <li key={d.document_id}>{d.nombre} · v{d.version} · {d.hash_sha256?.slice(0, 12)}…</li>
          ))}
        </ul>
      )}
      <div className="section-title">Calendario / eventos</div>
      {!(expediente.calendar_events || []).length && (
        <Empty title="Sin eventos" text="No hay eventos de calendario vinculados a este expediente."/>
      )}
      {!!(expediente.calendar_events || []).length && (
        <ul className="plain-list">
          {(expediente.calendar_events || []).map(ev => (
            <li key={ev.event_id}>
              <b>{ev.title || ev.event_id}</b> · {ev.event_type} · {ev.status}
              · sync {ev.sync_status || 'LOCAL_ONLY'}
              {ev.provider ? ` · ${ev.provider}` : ''}
              {ev.external_id ? ` · ext ${ev.external_id}` : ''}
              · {ev.start_at || '—'}
            </li>
          ))}
        </ul>
      )}
      <div className="section-title">Comunicaciones</div>
      {!(expediente.communications || []).length && (
        <Empty title="Sin comunicaciones" text="No hay comunicaciones vinculadas a este expediente."/>
      )}
      {!!(expediente.communications || []).length && (
        <ul className="plain-list">
          {(expediente.communications || []).map(c => (
            <li key={c.communication_id}>
              <b>{c.channel}</b> · {c.status}
              {c.human_gate_status ? ` · HG ${c.human_gate_status}` : ''}
              {c.provider ? ` · ${c.provider}` : ''}
              {c.external_id ? ` · ext ${c.external_id}` : ''}
              · {c.subject || c.summary || c.communication_id}
              · {c.created_at || '—'}
            </li>
          ))}
        </ul>
      )}
      <div className="section-title">Notificaciones</div>
      {!(expediente.notifications || []).length && (
        <Empty title="Sin notificaciones" text="No hay notificaciones internas relacionadas con este expediente."/>
      )}
      {!!(expediente.notifications || []).length && (
        <ul className="plain-list">
          {(expediente.notifications || []).map(n => (
            <li key={n.notification_id}>
              <b>{n.type}</b> · {n.status} · {n.title}
              · {n.created_at || '—'}
            </li>
          ))}
        </ul>
      )}
      <div className="section-title">Eventos de auditoría</div>
      <ul className="plain-list">
        {events.map(e => (
          <li key={e.event_id}>
            <b>{e.accion}</b> · {e.estado_anterior || '—'} → {e.estado_nuevo || '—'} · {e.timestamp}
            {e.motivo ? ` · ${e.motivo}` : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}

function MissionForm({mode, floor, company, cancel, onSubmit, notice}) {
  const isMission = mode === 'mission';
  const [type, setType] = useState(isMission ? 'Investigación' : 'Instrucción');
  const [scope, setScope] = useState(company?.id === 'LNRE' ? 'LNR' : company?.id === 'MGC' ? 'MGC' : 'LNH');
  const [subject, setSubject] = useState('');
  const [mission, setMission] = useState('');
  const [priority, setPriority] = useState('P2');
  const [due, setDue] = useState('');
  const [files, setFiles] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);
  const sending = useRef(false);
  const addFiles = list => {
    const next = [...files];
    for (const file of list) {
      if (!next.some(x => x.name === file.name && x.size === file.size)) next.push(file);
    }
    setFiles(next);
  };
  const send = async e => {
    e.preventDefault();
    if (sending.current) return;
    sending.current = true;
    setBusy(true);
    setError('');
    try {
      if (files.reduce((n, f) => n + f.size, 0) > 28 * 1024 * 1024) throw new Error('Los adjuntos deben sumar como máximo 28 MB.');
      if (files.length > 50) throw new Error('Seleccione como máximo 50 documentos.');
      await onSubmit({type, scope, subject, mission, priority, due, files});
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      sending.current = false;
    }
  };
  return (
    <div className={isMission ? '' : 'modal-layer'}>
      {!isMission && <button type="button" className="modal-backdrop" aria-label="Cerrar" onClick={cancel}/>}
      <div className={isMission ? '' : 'modal-sheet'}>
      <Hero
        e={isMission ? 'NUEVA MISIÓN EMPRESARIAL' : 'NUEVA INSTRUCCIÓN CORPORATIVA'}
        t={isMission ? 'Nueva misión' : 'Instrucción de Presidencia'}
        p={isMission
          ? `Empresa → piso ${floor.id} → ${floor.manager}. Se registra el expediente existente; la ejecución en Platform es un paso posterior.`
          : 'Presidencia → gobierno LNH / Directorio / área. Distinto de una misión empresarial de piso.'}
      />
      {!isMission && (
        <ol className="form-steps">
          <li className="on">1. Información</li>
          <li>2. Archivos</li>
          <li>3. Confirmar</li>
        </ol>
      )}
      <form className="mission instruction-form" onSubmit={send}>
        <fieldset disabled={busy}>
          <div className="form-grid">
            <label>Tipo de instrucción
              <select value={type} onChange={e => setType(e.target.value)}>
                {INSTRUCTION_TYPES.map(item => <option key={item}>{item}</option>)}
              </select>
            </label>
            <label>Empresa / ámbito
              <select value={isMission ? (company?.id === 'LNRE' ? 'LNR' : 'MGC') : scope} onChange={e => setScope(e.target.value)} disabled={isMission}>
                {INSTRUCTION_SCOPES.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            {isMission && (
              <label>Piso / gerencia
                <input value={`${floor.id} · ${floor.manager}`} readOnly/>
              </label>
            )}
            <label>Prioridad
              <div className="priority-row">
                {PRIORITIES.map(item => (
                  <button type="button" key={item} className={`prio ${item.toLowerCase()} ${priority === item ? 'on' : ''}`} onClick={() => setPriority(item)}>{item}</button>
                ))}
              </div>
            </label>
            <label>Fecha objetivo
              <input type="date" value={due} onChange={e => setDue(e.target.value)}/>
            </label>
          </div>
          <label htmlFor="subject">Asunto</label>
          <input id="subject" required maxLength={180} value={subject} onChange={e => setSubject(e.target.value)} placeholder="Título ejecutivo"/>
          <label htmlFor="mission">{isMission ? 'Misión' : 'Instrucción de Presidencia'}</label>
          <textarea id="mission" required maxLength={2000} value={mission} onChange={e => setMission(e.target.value)} placeholder="Describa objetivo, alcance y resultado requerido."/>
          <div className="counter">{mission.length}/2000</div>
          <label htmlFor="documents">Adjuntar documentación</label>
          <div
            className={`dropzone ${over ? 'over' : ''}`}
            onDragOver={e => { e.preventDefault(); setOver(true); }}
            onDragLeave={() => setOver(false)}
            onDrop={e => { e.preventDefault(); setOver(false); addFiles(e.dataTransfer.files); }}
          >
            <Icon name="upload"/>
            <b>Arrastre documentos o haga clic para seleccionar</b>
            <p>PDF, DOCX, TXT, MD, CSV y XLSX · hasta 50 archivos · máximo 28 MB.</p>
            <input id="documents" type="file" multiple accept=".txt,.md,.pdf,.docx,.csv,.xlsx" onChange={e => addFiles(e.target.files)}/>
          </div>
          {files.length > 0 && (
            <ul className="file-list">{files.map((f, i) => (
              <li key={i}>{f.name} · {Math.ceil(f.size / 1024)} KB <button type="button" className="text-button" onClick={() => setFiles(files.filter((_, n) => n !== i))}>Quitar</button></li>
            ))}</ul>
          )}
          {floor?.id === 'MGC-03' && <p className="muted">El GER registra la misión en OpenAI Platform. LNH no despacha especialistas.</p>}
          <div className="form-actions">
            <button type="button" className="secondary" onClick={cancel}>Cancelar</button>
            <button disabled={!mission.trim() || !subject.trim()} type="submit" className="gold-btn">{busy ? 'Procesando…' : (isMission ? 'Confirmar' : 'Siguiente →')}</button>
          </div>
        </fieldset>
        <Notice error>{error}</Notice>
        <Notice>{notice}</Notice>
      </form>
      </div>
    </div>
  );
}

function shortLabel(text, max = 64) {
  const s = String(text || '').replace(/\s+/g, ' ').trim();
  if (!s) return '—';
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

function CompactGateRow({row, open}) {
  const id = row.case_id || row.id || '—';
  const title = shortLabel(row.subject || row.mission || id, 56);
  return (
    <li className="dir-compact-row">
      <span className={`dir-status-pill ${String(row.status || '').includes('APPROVED') ? 'ok' : row.requires_decision ? 'warn' : ''}`}>
        {row.requires_decision ? 'PENDIENTE' : (row.status || '—')}
      </span>
      <div className="dir-compact-body">
        <b title={row.mission || title}>{title}</b>
        <small>{id} · {row.floor_id || '—'}</small>
      </div>
      <button type="button" className="text-button" onClick={() => open && open(row)}>Abrir</button>
    </li>
  );
}

export function Directorio({list, openCase, agentBoard, navigate}) {
  const decisions = list.filter(x => ['APPROVED', 'REJECTED', 'CLOSED'].includes(x.status));
  const pending = list.filter(x => x.requires_decision);
  const directors = (agentBoard && agentBoard.directors) || DIRECTORS.map(item => ({...item}));
  const [sessions, setSessions] = useState([]);
  const [corpList, setCorpList] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [tipo, setTipo] = useState('ordinaria');
  const [selectedExp, setSelectedExp] = useState('');
  const [sessTab, setSessTab] = useState('proximas');
  const [expTab, setExpTab] = useState('todos');
  const [composerOpen, setComposerOpen] = useState(false);
  const refreshSessions = () => boardSessions().then(setSessions).catch(e => setMsg(e.message));
  useEffect(() => {
    refreshSessions();
    corporateExpedientes().then(setCorpList).catch(() => setCorpList([]));
  }, []);
  const createSession = async () => {
    setBusy(true); setMsg('');
    try {
      const created = await createBoardSession({
        tipo,
        agenda: selectedExp ? [{punto: 'Punto de agenda', expediente_id: selectedExp}] : [],
        expediente_ids: selectedExp ? [selectedExp] : [],
      });
      await refreshSessions();
      setComposerOpen(false);
      if (navigate) navigate('BoardSession', created.board_session_id);
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy(false);
    }
  };

  const doneStates = new Set(['CERRADA', 'CERRADO', 'FINALIZADA', 'APROBADA', 'RECHAZADA', 'CLOSED']);
  const draftStates = new Set(['BORRADOR', 'DRAFT', 'PREPARACION', 'PREPARACIÓN', 'NUEVA']);
  const proximas = sessions.filter(s => !doneStates.has(String(s.estado || '').toUpperCase()) && !draftStates.has(String(s.estado || '').toUpperCase()));
  const realizadas = sessions.filter(s => doneStates.has(String(s.estado || '').toUpperCase()));
  const extraordinarias = sessions.filter(s => String(s.tipo || '').toLowerCase().includes('extraord'));
  const borradores = sessions.filter(s => draftStates.has(String(s.estado || '').toUpperCase()));
  const sessView = sessTab === 'realizadas' ? realizadas
    : sessTab === 'extraordinarias' ? extraordinarias
    : sessTab === 'borradores' ? borradores
    : proximas;

  const expPend = corpList.filter(e => {
    const st = String(e.estado_actual || '').toUpperCase();
    return st.includes('PEND') || st.includes('EVAL') || st.includes('ANALISIS') || st.includes('ANÁLISIS');
  });
  const expDelib = corpList.filter(e => {
    const st = String(e.estado_actual || '').toUpperCase();
    return st.includes('DELIBER') || st.includes('DIRECTORIO') || st.includes('VOTO') || e.board_session_id;
  });
  const expEnDir = corpList.filter(e => {
    const st = String(e.estado_actual || e.status || '').toUpperCase();
    return st.includes('DIRECTORIO') || st.includes('DELIBER') || e.board_session_id;
  });
  const expPool = expTab === 'directorio' ? expEnDir
    : expTab === 'pendientes' ? expPend
    : expTab === 'deliberados' ? expDelib
    : corpList;

  const voteProgress = (item) => {
    const votes = item.votes || item.consolidation?.votes || [];
    if (Array.isArray(votes) && votes.length) return `${votes.length}/5`;
    const runs = item.director_runs || [];
    if (runs.length) {
      const done = runs.filter(r => ['DONE', 'COMPLETED', 'OK', 'VOTADO'].includes(String(r.status || '').toUpperCase())).length;
      return `${done}/5`;
    }
    if (item.deliberation_progress) return String(item.deliberation_progress);
    return null;
  };

  const approvedN = decisions.filter(d => d.status === 'APPROVED').length;
  const rejectedN = decisions.filter(d => d.status === 'REJECTED').length;
  const closedN = decisions.filter(d => d.status === 'CLOSED').length;
  const hasDist = decisions.length > 0;

  return (
    <div className="directorio-page">
      <ExecHero
        className="dir-hero"
        breadcrumb="LNH › Directorio"
        title="Directorio"
        subtitle="Visión. Estrategia. Valor. Futuro."
        quote="Gobernanza para un crecimiento sin límites."
        pillars={['ESTRATEGIA', 'CAPITAL', 'EMPRESAS', 'PERSONAS', 'IMPACTO']}
        image={ASSETS.lnh.directorio.hero}
      />

      <section className="dir-directors">
        <div className="dir-section-head">
          <h2>Directores IA</h2>
        </div>
        <div className="dir-director-row">
          {DIRECTORS.map(base => {
            const item = directors.find(d => (d.id || d.director_id) === base.id) || base;
            const id = base.id;
            return (
              <article className="dir-director-card" key={id}>
                <div className="dir-director-photo-wrap">
                  <span className="dir-director-id">{id}</span>
                  <img
                    className={`dir-director-photo dir-photo-${id.toLowerCase()}`}
                    src={directorPhoto(id)}
                    alt=""
                    decoding="async"
                  />
                </div>
                <div className="dir-director-meta">
                  <b>{id}</b>
                  <p>{base.mandate}</p>
                  <AvailabilityDot agent={item}/>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {msg && <Notice error>{msg}</Notice>}

      <section className="dir-main-row">
        <Panel
          className="dir-panel"
          title="Sesiones de Directorio"
          action={(
            <button type="button" className="gold-btn dir-gold" disabled={busy} onClick={() => setComposerOpen(v => !v)}>
              {composerOpen ? 'Cerrar' : '+ Nueva sesión'}
            </button>
          )}
        >
          {composerOpen && (
            <div className="dir-composer">
              <label>Tipo
                <select value={tipo} onChange={e => setTipo(e.target.value)}>
                  <option value="ordinaria">Ordinaria</option>
                  <option value="extraordinaria">Extraordinaria</option>
                  <option value="periodica">Periódica</option>
                </select>
              </label>
              <label>Expediente
                <select value={selectedExp} onChange={e => setSelectedExp(e.target.value)}>
                  <option value="">— opcional —</option>
                  {corpList.map(item => (
                    <option key={item.expediente_id} value={item.expediente_id}>
                      {shortLabel(item.asunto || item.expediente_id, 40)}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="gold-btn dir-gold" disabled={busy} onClick={createSession}>
                {busy ? 'Creando…' : 'Crear sesión'}
              </button>
            </div>
          )}
          <nav className="dir-tabs" role="tablist">
            {[
              ['proximas', 'Próximas'],
              ['realizadas', 'Realizadas'],
              ['extraordinarias', 'Extraordinarias'],
              ['borradores', 'Borradores'],
            ].map(([id, label]) => (
              <button type="button" key={id} aria-selected={sessTab === id} onClick={() => setSessTab(id)}>{label}</button>
            ))}
          </nav>
          {!sessView.length && (
            <div className="dir-empty">
              <b>Sin sesiones</b>
              <p>Cree una sesión para preparar agenda y deliberar.</p>
            </div>
          )}
          {!!sessView.length && (
            <ul className="dir-session-list">
              {sessView.slice(0, 5).map(s => {
                const d = s.fecha ? new Date(s.fecha) : null;
                const day = d && !Number.isNaN(d.getTime()) ? String(d.getDate()).padStart(2, '0') : '—';
                const mon = d && !Number.isNaN(d.getTime())
                  ? d.toLocaleDateString('es-CL', {month: 'short'}).replace('.', '').toUpperCase()
                  : '';
                const progress = voteProgress(s);
                return (
                  <li key={s.board_session_id}>
                    <div className="dir-sess-date"><strong>{day}</strong><span>{mon}</span></div>
                    <div className="dir-sess-body">
                      <b>{shortLabel(`${s.tipo || 'Sesión'} · ${s.estado || '—'}`, 42)}</b>
                      <p>{shortLabel((s.agenda?.[0]?.punto) || (s.expediente_ids?.length ? `${s.expediente_ids.length} expediente(s)` : 'Sin agenda'), 48)}</p>
                    </div>
                    <div className="dir-sess-meta">
                      {progress && <span className="dir-progress">{progress}</span>}
                      <button type="button" className="text-button" onClick={() => navigate && navigate('BoardSession', s.board_session_id)}>Abrir</button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>

        <Panel className="dir-panel" title="Expedientes en Directorio">
          <nav className="dir-tabs" role="tablist">
            {[
              ['todos', 'Todos'],
              ['directorio', 'En Directorio'],
              ['pendientes', 'Pendientes'],
              ['deliberados', 'Deliberados'],
            ].map(([id, label]) => (
              <button type="button" key={id} aria-selected={expTab === id} onClick={() => setExpTab(id)}>{label}</button>
            ))}
          </nav>
          {!expPool.length && (
            <div className="dir-empty">
              <b>Sin expedientes</b>
              <p>Use Nueva Instrucción Corporativa.</p>
            </div>
          )}
          {!!expPool.length && (
            <ul className="dir-exp-list">
              {expPool.slice(0, 6).map(item => {
                const progress = voteProgress(item);
                return (
                  <li key={item.expediente_id}>
                    <div className="dir-exp-body">
                      <small>{shortLabel(item.expediente_id, 28)}</small>
                      <b>{shortLabel(item.asunto || item.expediente_id, 48)}</b>
                    </div>
                    <div className="dir-exp-meta">
                      {progress && <span className="dir-progress">{progress}</span>}
                      <span className="dir-status-pill">{shortLabel(item.estado_actual || '—', 16)}</span>
                      <button type="button" className="text-button" onClick={() => navigate && navigate('ExpedienteCorporativo', item.expediente_id)}>Abrir</button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>

        <Panel className="dir-panel" title="Indicadores del Directorio">
          <div className="dir-kpi-top">
            <article><b>{sessions.length}</b><small>Sesiones registradas</small></article>
            <article><b>{realizadas.length}</b><small>Realizadas</small></article>
            <article><b>{corpList.length}</b><small>Expedientes LNH</small></article>
          </div>
          <div className="dir-kpi-grid dense">
            <article><b>{pending.length}</b><small>Pendientes humanos</small></article>
            <article><b>{decisions.length}</b><small>Decisiones de piso</small></article>
            <article><b>{extraordinarias.length}</b><small>Extraordinarias</small></article>
            <article><b>{borradores.length}</b><small>Borradores</small></article>
          </div>
          {hasDist && (
            <div className="dir-dist">
              <small>Distribución de decisiones (piso)</small>
              <ul>
                <li><i className="ok"/>Aprobados <b>{approvedN}</b></li>
                <li><i className="warn"/>Cerrados <b>{closedN}</b></li>
                <li><i className="danger"/>Rechazados <b>{rejectedN}</b></li>
              </ul>
            </div>
          )}
        </Panel>
      </section>

      <section className="dir-second-row">
        <Panel className="dir-panel dir-panel-slim" title="Agenda / Calendario">
          {!proximas.length && <div className="dir-empty slim"><b>Sin programación</b></div>}
          {!!proximas.length && (
            <ul className="dir-agenda-list">
              {proximas.slice(0, 4).map(s => (
                <li key={s.board_session_id}>
                  <b>{shortLabel(s.fecha || 'Sin fecha', 18)}</b>
                  <span>{shortLabel(`${s.tipo} · ${s.estado}`, 36)}</span>
                  <button type="button" className="text-button" onClick={() => navigate && navigate('BoardSession', s.board_session_id)}>Abrir</button>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel className="dir-panel dir-panel-slim" title="Human Gate">
          {!pending.length && <div className="dir-empty slim"><b>Sin pendientes</b></div>}
          {!!pending.length && (
            <ul className="dir-compact-list">
              {pending.slice(0, 4).map(row => (
                <CompactGateRow key={`${row.floor_id}/${row.case_id}`} row={row} open={openCase}/>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          className="dir-panel dir-panel-slim"
          title="Últimas decisiones"
          action={decisions.length ? <button type="button" className="text-button" onClick={() => navigate && navigate('Decisiones')}>Ver historial</button> : null}
        >
          {!decisions.length && <div className="dir-empty slim"><b>Sin decisiones registradas</b></div>}
          {!!decisions.length && (
            <ul className="dir-compact-list">
              {decisions.slice(0, 4).map(row => (
                <CompactGateRow key={`${row.floor_id}/${row.case_id}`} row={row} open={openCase}/>
              ))}
            </ul>
          )}
        </Panel>
      </section>
    </div>
  );
}

export function BoardSessionView({sessionId, navigate}) {
  const [session, setSession] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [rationale, setRationale] = useState('');
  const [conditions, setConditions] = useState('');
  const load = () => boardSession(sessionId)
    .then(item => { setSession(item); setError(''); })
    .catch(e => setError(e.message));
  useEffect(() => { load(); }, [sessionId]);
  const run = async (label, fn) => {
    setBusy(label); setError('');
    try {
      await fn();
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  };
  if (!session && !error) return <Empty title="Cargando sesión" text="Consultando Directorio LNH."/>;
  if (!session) return <Empty title="Sesión no disponible" text={error}/>;
  const missing = session.capabilities?.directors_ids_missing || [];
  const votes = session.votes || [];
  const consolidation = session.consolidation || {};
  return (
    <div>
      <section className="page-head">
        <small>SESIÓN DE DIRECTORIO</small>
        <h1>{session.board_session_id}</h1>
        <p>{session.tipo} · {session.estado} · base {session.base_version || 'sin congelar'}</p>
      </section>
      {error && <Notice error>{error}</Notice>}
      <div className="office-row-3" style={{marginBottom: 16}}>
        <Panel title="Agenda y expedientes">
          <ul className="plain-list">
            {(session.agenda || []).map((a, i) => <li key={i}>{a.punto || JSON.stringify(a)}</li>)}
          </ul>
          <p><b>Expedientes:</b> {(session.expediente_ids || []).join(', ') || '—'}</p>
          <p><b>Fecha:</b> {session.fecha}</p>
        </Panel>
        <Panel title="Antecedentes">
          <p>Checklist: {session.antecedentes_checklist ? (session.antecedentes_checklist.completo ? 'completo' : 'con faltantes') : 'no preparado'}</p>
          {!!session.antecedentes_checklist?.items?.length && (
            <ul className="plain-list">
              {session.antecedentes_checklist.items.map(item => (
                <li key={item.expediente_id}>{item.expediente_id}: {(item.faltantes || []).join('; ') || 'OK'}</li>
              ))}
            </ul>
          )}
          <button type="button" className="text-button" disabled={!!busy} onClick={() => run('prepare', () => prepareBoardSession(sessionId))}>Preparar antecedentes</button>
          <button type="button" className="text-button" disabled={!!busy} onClick={() => run('freeze', () => freezeBoardSession(sessionId))}>Cerrar y congelar base</button>
        </Panel>
        <Panel title="Acciones">
          <button type="button" className="primary" disabled={!!busy || !session.frozen_pack} onClick={() => run('deliberate', () => deliberateBoardSession(sessionId, {}))}>
            {busy === 'deliberate' ? 'Deliberando…' : 'Iniciar deliberación independiente'}
          </button>
          <p className="muted">No se ejecuta Platform al crear la reunión. Deliberación = 5 sesiones aisladas.</p>
          {!!missing.length && <p>IDs Director pendientes: {missing.join(', ')}. Configure DIR_0N_AGENT_ID.</p>}
          {session.resultado?.blocked && <p><StatusLabel label="BLOQUEADO"/> {session.resultado.reason}</p>}
          <button type="button" className="text-button" onClick={() => navigate && navigate('Directorio')}>Volver al Directorio</button>
        </Panel>
      </div>
      <div className="section-title">Directores / runs</div>
      <ul className="plain-list">
        {(session.director_runs || session.participantes || []).map((r, idx) => (
          <li key={r.director_id || r.id || idx}>
            <b>{r.director_id || r.id}</b> · {r.status || r.id_status || '—'}
            {r.isolation ? ` · aislamiento OK · base ${r.isolation.shared_base_version}` : ''}
            {r.error_kind ? ` · ${r.error_kind}` : ''}
            {r.platform_session_id ? ` · sesión ${r.platform_session_id}` : ''}
          </li>
        ))}
      </ul>
      <div className="section-title">Votos consultivos</div>
      {!votes.length && <Empty title="Sin votos" text="Aún no hay deliberación registrada. No se fabrican votos."/>}
      {!!votes.length && (
        <ul className="plain-list">
          {votes.map((v, i) => (
            <li key={i}>{v.director_id}: <b>{v.voto}</b> · {v.fundamento || '—'}</li>
          ))}
        </ul>
      )}
      <div className="section-title">Consolidación mecánica</div>
      {!consolidation.vote_counts && <Empty title="Sin consolidación" text="Disponible tras primera ronda completa."/>}
      {!!consolidation.vote_counts && (
        <Panel title="Conteo (sin reinterpretación)">
          {Object.entries(consolidation.vote_counts).map(([k, v]) => <p key={k}>{k}: {v}</p>)}
          <p>Quorum IA técnico: {session.quorum_ia ? 'sí' : 'no'}</p>
        </Panel>
      )}
      {session.estado === 'PENDIENTE_PRESIDENCIA' && (
        <Panel title="Human Gate Presidencia">
          <label>Fundamento<textarea value={rationale} onChange={e => setRationale(e.target.value)} rows={3}/></label>
          <label>Condiciones<input value={conditions} onChange={e => setConditions(e.target.value)}/></label>
          <div className="form-actions">
            {['APROBAR', 'APROBAR CON CONDICIONES', 'CORREGIR', 'RECHAZAR'].map(dec => (
              <button
                key={dec}
                type="button"
                className={dec === 'APROBAR' ? 'primary' : 'secondary'}
                disabled={!!busy}
                onClick={() => run('gate', () => boardHumanGate(sessionId, {decision: dec, rationale, conditions}))}
              >
                {dec}
              </button>
            ))}
          </div>
        </Panel>
      )}
      {session.decision_presidencia && (
        <Panel title="Decisión Presidencia">
          <p>{session.decision_presidencia.decision} · {session.decision_presidencia.decided_at}</p>
          <p>{session.decision_presidencia.rationale}</p>
        </Panel>
      )}
      <div className="section-title">Eventos de sesión</div>
      <ul className="plain-list">
        {(session.events || []).slice().reverse().map(e => (
          <li key={e.event_id}><b>{e.accion}</b> · {e.timestamp}</li>
        ))}
      </ul>
    </div>
  );
}

function useAgentBoard() {
  const [board, setBoard] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    corporateAgents()
      .then(data => {
        if (!alive) return;
        // Compat: API may return list (legacy) or status_board object.
        if (Array.isArray(data)) {
          setBoard({agents: data, directors: DIRECTORS.map(d => ({...d, config_status: 'CONFIGURADO', workflow_status: 'WORKFLOW PENDIENTE DE INTEGRACIÓN'})), platform_calls: 0});
        } else {
          setBoard(data);
        }
        setError('');
      })
      .catch(err => { if (alive) setError(err.message); });
    return () => { alive = false; };
  }, []);
  return {board, error};
}

function agentByArea(board, areaId) {
  return (board?.agents || []).find(a => a.area_id === areaId);
}

export function CorporateOffice({agentBoard, navigate, list = []}) {
  const local = useAgentBoard();
  const board = agentBoard || local.board;
  const agent = agentByArea(board, 'LNH-03');
  const [corpList, setCorpList] = useState([]);
  useEffect(() => {
    corporateExpedientes().then(setCorpList).catch(() => setCorpList([]));
  }, []);
  const pending = list.filter(x => x.requires_decision);
  const activeCorp = corpList.filter(e => {
    const st = String(e.estado_actual || '').toUpperCase();
    return st && !['CLOSED', 'CERRADO', 'ARCHIVADO', 'APPROVED'].includes(st);
  });

  const activity = [
    ...corpList.slice(0, 8).map(item => ({
      key: item.expediente_id,
      id: item.expediente_id,
      title: item.asunto || item.expediente_id,
      status: item.estado_actual || '—',
      when: item.updated_at || item.created_at || item.fecha || '',
      open: () => navigate && navigate('ExpedienteCorporativo', item.expediente_id),
      kind: 'expediente',
    })),
    ...pending.slice(0, 4).map(row => ({
      key: `${row.floor_id}/${row.case_id}`,
      id: row.case_id,
      title: row.subject || row.mission || row.case_id,
      status: 'HUMAN_GATE',
      when: row.updated_at || '',
      open: () => openCaseFriendly(navigate, row),
      kind: 'gate',
    })),
  ].slice(0, 8);

  const functions = [
    {t: 'Planificación Corporativa', icon: 'calendar', go: () => navigate && navigate('NuevaInstruccion')},
    {t: 'Control de Gestión', icon: 'finance', go: () => navigate && navigate('Area', 'finanzas')},
    {t: 'Desarrollo Corporativo', icon: 'holding', go: () => navigate && navigate('Area', 'desarrollo')},
    {t: 'Inteligencia Empresarial', icon: 'reports', go: () => navigate && navigate('Area', 'bi')},
    {t: 'Transformación Digital', icon: 'agents', go: () => navigate && navigate('Area', 'ia')},
    {t: 'Soporte a Empresas', icon: 'company', go: () => navigate && navigate('Holding')},
  ];

  return (
    <div className="corporate-office-page">
      <ExecHero
        className="co-hero"
        breadcrumb="LNH › Corporate Office"
        title="Corporate Office"
        subtitle="Estrategia. Control. Desarrollo. Soporte al holding."
        quote="Un solo sistema. Un mayor futuro."
        pillars={[
          'PLANIFICACIÓN',
          'CONTROL DE GESTIÓN',
          'INTELIGENCIA EMPRESARIAL',
          'DESARROLLO CORPORATIVO',
          'TECNOLOGÍA E IA',
          'GOBIERNO CORPORATIVO',
        ]}
        image={ASSETS.lnh.corporateOffice.hero}
      />
      {local.error && <Notice error>{local.error}</Notice>}

      <section className="co-functions">
        <div className="dir-section-head"><h2>Funciones principales</h2></div>
        <div className="co-function-row">
          {functions.map(item => (
            <button type="button" className="co-mod" key={item.t} onClick={item.go}>
              <span className="co-mod-icon"><Icon name={item.icon}/></span>
              <b>{item.t}</b>
            </button>
          ))}
        </div>
      </section>

      <section className="co-ops-row">
        <Panel className="co-panel co-activity" title="Actividad reciente">
          {!activity.length && <div className="dir-empty slim"><b>Sin actividad registrada</b></div>}
          {!!activity.length && (
            <ul className="co-activity-list">
              {activity.map(row => (
                <li key={row.key}>
                  <span className="co-act-icon"><Icon name={row.kind === 'gate' ? 'decisions' : 'instruction'}/></span>
                  <div className="co-act-body">
                    <small>{shortLabel(row.id, 26)}</small>
                    <b title={row.title}>{shortLabel(row.title, 58)}</b>
                  </div>
                  <span className="dir-status-pill">{shortLabel(row.status, 14)}</span>
                  <small className="co-act-when">{shortLabel(row.when, 12)}</small>
                  <button type="button" className="text-button" onClick={row.open}>Abrir</button>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel className="co-panel co-kpis" title="Indicadores Corporate Office">
          <div className="co-kpi-grid">
            <article><b>{corpList.length}</b><small>Expedientes LNH</small></article>
            <article><b>{activeCorp.length}</b><small>Expedientes activos</small></article>
            <article><b>{pending.length}</b><small>Human Gate</small></article>
            <article><b>{LNH_FUNCTIONAL_AREAS.length}</b><small>Áreas corporativas</small></article>
            <article><b>{agent?.active_tasks ?? 0}</b><small>Encargos activos</small></article>
            <article>
              <b><AvailabilityDot agent={agent}/></b>
              <small>LNH-03</small>
            </article>
          </div>
        </Panel>
      </section>

      <section
        className="co-footer-strip"
        style={{backgroundImage: `url(${ASSETS.lnh.corporateOffice.atmosphere || ASSETS.lnh.corporateOffice.hero})`}}
        aria-label="Identidad Corporate Office"
      >
        <div className="co-footer-shade"/>
        <img src={ASSETS.lnh.logo} alt="" className="co-footer-logo"/>
        <div className="co-footer-words">
          <span>ESTRATEGIA</span><i>|</i><span>DISCIPLINA</span><i>|</i><span>RESULTADOS</span>
        </div>
      </section>

      <section className="co-areas-sec">
        <div className="dir-section-head">
          <h2>Acceso a áreas LNH</h2>
          <button type="button" className="text-button" onClick={() => navigate && navigate('Areas')}>Ver todas</button>
        </div>
        <div className="area-grid area-grid-8 co-areas-grid">
          {LNH_FUNCTIONAL_AREAS.map(area => (
            <AreaCard
              key={area.id}
              area={area}
              agent={agentByArea(board, area.areaId)}
              open={item => navigate(item.route || 'Area', item.route ? undefined : item.id)}
            />
          ))}
        </div>
      </section>

      <section className="co-lnh03-detail">
        <AreaView
          code="LNH-03"
          title="Corporate Office"
          areaId="LNH-03"
          agent={agent}
          summary={AREA_FUNCTIONS['LNH-03']}
          loadError={local.error}
          navigate={navigate}
          list={list}
          openCase={(row) => openCaseFriendly(navigate, row)}
          embedded
        />
      </section>
    </div>
  );
}

function openCaseFriendly(navigate, row) {
  if (!navigate || !row) return;
  if (row.floor_id && row.case_id) navigate('case', row.floor_id, row.case_id, 'Resumen');
  else navigate('Decisiones');
}

export function Areas({navigate, agentBoard, list = []}) {
  const local = useAgentBoard();
  const board = agentBoard || local.board;
  const [corpList, setCorpList] = useState([]);
  useEffect(() => {
    corporateExpedientes().then(setCorpList).catch(() => setCorpList([]));
  }, []);

  const areaStats = LNH_FUNCTIONAL_AREAS.reduce((acc, area) => {
    const tone = availabilityTone(agentByArea(board, area.areaId));
    if (tone.dot === 'ok') acc.operativas += 1;
    else if (tone.dot === 'warn') acc.espera += 1;
    else acc.pendientes += 1;
    return acc;
  }, {operativas: 0, espera: 0, pendientes: 0});
  const areaTotal = LNH_FUNCTIONAL_AREAS.length;
  const donutStops = (() => {
    if (!areaTotal) return 'rgba(109,128,144,.35) 0 100%';
    const pOp = (areaStats.operativas / areaTotal) * 100;
    const pEs = (areaStats.espera / areaTotal) * 100;
    const a = pOp;
    const b = pOp + pEs;
    return `#3f9a6a 0 ${a}%, #c9a24d ${a}% ${b}%, #6d8090 ${b}% 100%`;
  })();

  const activity = [
    ...corpList.slice(0, 8).map(item => {
      const areaCode = String(item.responsable_area || item.area_id || item.routing_area || '')
        .match(/LNH-0[3-9]|LNH-10/)?.[0] || 'LNH';
      return {
        key: item.expediente_id,
        areaCode,
        title: item.asunto || item.expediente_id,
        status: item.estado_actual || '—',
        when: item.updated_at || item.created_at || item.fecha || '',
        open: () => navigate && navigate('ExpedienteCorporativo', item.expediente_id),
      };
    }),
    ...list.filter(x => x.requires_decision).slice(0, 4).map(row => ({
      key: `${row.floor_id}/${row.case_id}`,
      areaCode: String(row.floor_id || '').startsWith('LNH') ? String(row.floor_id).slice(0, 6) : 'GATE',
      title: row.subject || row.mission || row.case_id,
      status: 'HUMAN_GATE',
      when: row.updated_at || '',
      open: () => openCaseFriendly(navigate, row),
    })),
  ].slice(0, 8);

  return (
    <div className="areas-page">
      <ExecHero
        className="areas-hero"
        breadcrumb="LNH › Áreas Corporativas"
        title="Áreas Corporativas"
        subtitle="Talento. Procesos. Tecnología. Al servicio del crecimiento."
        quote={"El talento convierte\nla estrategia\nen realidad."}
        aside={<p className="areas-hero-tagline">Sistemas que impulsan resultados.</p>}
        image={ASSETS.lnh.areas.hero}
      />
      {local.error && <Notice error>{local.error}</Notice>}

      <section className="areas-grid" aria-label="Áreas LNH-03 a LNH-10">
        {LNH_FUNCTIONAL_AREAS.map(area => {
          const agent = agentByArea(board, area.areaId);
          return (
            <button
              type="button"
              className="areas-tile"
              key={area.id}
              onClick={() => navigate(area.route || 'Area', area.route ? undefined : area.id)}
            >
              <span className="areas-tile-photo" style={{backgroundImage: `url(${areaPhoto(area.areaId)})`}} aria-hidden="true"/>
              <span className="areas-tile-meta">
                <small>{area.code}</small>
                <b>{area.name}</b>
                <AvailabilityDot agent={agent}/>
              </span>
            </button>
          );
        })}
      </section>

      <section className="areas-ops-row">
        <Panel className="areas-panel areas-activity" title="Actividad corporativa">
          {!activity.length && (
            <div className="dir-empty slim">
              <b>Sin actividad registrada</b>
              <p>La actividad corporativa aparece cuando hay expedientes o pendientes reales.</p>
            </div>
          )}
          {!!activity.length && (
            <ul className="areas-activity-list">
              {activity.map(row => (
                <li key={row.key}>
                  <span className="areas-act-icon"><Icon name="instruction"/></span>
                  <small className="areas-act-code">{row.areaCode}</small>
                  <b title={row.title}>{shortLabel(row.title, 52)}</b>
                  <span className="dir-status-pill">{shortLabel(row.status, 14)}</span>
                  <small className="areas-act-when">{shortLabel(row.when, 12)}</small>
                  <button type="button" className="text-button" onClick={row.open}>Abrir</button>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel className="areas-panel areas-status" title="Estado general de áreas">
          <div className="areas-status-body">
            <div className="areas-donut" style={{background: `conic-gradient(${donutStops})`}} aria-hidden="true">
              <div className="areas-donut-core">
                <b>{areaTotal}</b>
                <small>Áreas</small>
              </div>
            </div>
            <ul className="areas-status-legend">
              <li><i className="dot-ok"/><b>{areaStats.operativas}</b><span>Operativas</span></li>
              <li><i className="dot-warn"/><b>{areaStats.espera}</b><span>En espera</span></li>
              <li><i className="dot-muted"/><b>{areaStats.pendientes}</b><span>Pendientes</span></li>
            </ul>
          </div>
        </Panel>
      </section>
    </div>
  );
}

export function AreaView({code, title, summary, list = [], openCase, areaId, agent, loadError, navigate, embedded}) {
  const [tab, setTab] = useState('Resumen');
  const [corpList, setCorpList] = useState([]);
  useEffect(() => {
    if (!areaId) return undefined;
    let alive = true;
    corporateExpedientes()
      .then(rows => {
        if (!alive) return;
        const related = (agent?.related_expedientes || []);
        const filtered = rows.filter(r =>
          related.includes(r.expediente_id)
          || String(r.responsable_area || r.area_id || r.routing_area || '').includes(areaId)
        );
        setCorpList(filtered.length ? filtered : (related.length ? rows.filter(r => related.includes(r.expediente_id)) : []));
      })
      .catch(() => setCorpList([]));
    return () => { alive = false; };
  }, [areaId, agent]);

  const tabs = ['Resumen', 'Actividad', 'Expedientes', 'Encargos', 'Informes', 'Documentos', 'Pendientes', 'Decisiones', 'Indicadores'];
  const photo = areaId ? areaPhoto(areaId) : null;
  const fn = summary || AREA_FUNCTIONS[areaId] || title;

  return (
    <div className={`area-view-page ${embedded ? 'embedded' : 'exec-surface'}`}>
      {!embedded && (
        <ExecHero
          breadcrumb={`LNH › Áreas › ${code || title}`}
          title={code ? `${code} | ${title}` : title}
          subtitle={fn}
          image={photo || ASSETS.lnh.areas.hero}
        />
      )}
      {embedded && <h2 className="section-title">Detalle {code || 'LNH-03'}</h2>}
      {loadError && <Notice error>{loadError}</Notice>}
      <div className="area-head-row">
        <AvailabilityDot agent={agent}/>
        <span className="muted">{fn}</span>
      </div>
      <nav className="tabs exec-tabs" role="tablist">
        {tabs.map(name => (
          <button type="button" role="tab" key={name} aria-selected={tab === name} onClick={() => setTab(name)}>{name}</button>
        ))}
      </nav>
      {tab === 'Resumen' && (
        <div className="kpis">
          <Metric label="Área" value={areaId || code || '—'} note={title}/>
          <Metric label="Disponibilidad" value={agent ? availabilityLabel(agent) : '—'} note="Estado ejecutivo"/>
          <Metric label="Encargos activos" value={agent?.active_tasks ?? '—'} note="Desde backend local"/>
          <Metric label="Expedientes" value={agent?.related_expedientes_count ?? corpList.length ?? '—'} note="Vinculados al área"/>
        </div>
      )}
      {tab === 'Actividad' && (
        <Panel title="Actividad">
          {!corpList.length && !(agent?.related_expedientes || []).length && (
            <Empty title="Sin actividad registrada" text="La actividad del área se materializa con encargos y expedientes reales."/>
          )}
          <ul className="exec-list">
            {corpList.slice(0, 8).map(item => (
              <li key={item.expediente_id}>
                <b>{item.asunto || item.expediente_id}</b>
                <small>{item.estado_actual}</small>
              </li>
            ))}
          </ul>
        </Panel>
      )}
      {tab === 'Expedientes' && (
        corpList.length || (agent?.related_expedientes || []).length
          ? (
            <ul className="exec-list">
              {(corpList.length ? corpList : (agent.related_expedientes || []).map(id => ({expediente_id: id}))).map(item => (
                <li key={item.expediente_id || item}>
                  <b>{item.asunto || item.expediente_id || item}</b>
                  <small>{item.estado_actual || '—'}</small>
                  {navigate && item.expediente_id && (
                    <button type="button" className="text-button" onClick={() => navigate('ExpedienteCorporativo', item.expediente_id)}>Abrir</button>
                  )}
                </li>
              ))}
            </ul>
          )
          : <Empty title="Sin expedientes de área" text="Aún no hay expedientes corporativos vinculados a este agente."/>
      )}
      {tab === 'Encargos' && (
        <Empty title="Sin encargos visibles" text="Los encargos se ejecutan desde el Expediente Corporativo (Bloque 3)."/>
      )}
      {tab === 'Informes' && <Empty title="Sin informes registrados" text="No hay informes de área materializados."/>}
      {tab === 'Documentos' && <Empty title="Sin documentos de área" text="Los documentos se conservan en el expediente correspondiente."/>}
      {tab === 'Pendientes' && (
        list?.filter?.(c => c.requires_decision)?.length
          ? (
            <ul className="dir-compact-list">
              {list.filter(c => c.requires_decision).slice(0, 8).map(row => (
                <CompactGateRow key={`${row.floor_id}/${row.case_id}`} row={row} open={openCase}/>
              ))}
            </ul>
          )
          : <Empty title="Sin pendientes" text="No hay pendientes materializados para esta área."/>
      )}
      {tab === 'Decisiones' && (
        <Empty title="Sin decisiones de área" text="Las decisiones y gates relacionados aparecen cuando el expediente lo registra."/>
      )}
      {tab === 'Indicadores' && (
        <div className="dir-kpi-grid">
          <article><b>{agent?.active_tasks ?? '—'}</b><small>Encargos activos</small></article>
          <article><b>{agent?.related_expedientes_count ?? corpList.length ?? '—'}</b><small>Expedientes</small></article>
          <article><b>{agent ? availabilityLabel(agent) : '—'}</b><small>Disponibilidad</small></article>
        </div>
      )}
    </div>
  );
}

function availabilityLabel(agent) {
  const op = String(agent?.operational_status || '');
  if (op.includes('CRÉDITO') || op.includes('BLOQUEADO')) return 'En espera';
  if (op.includes('ERROR')) return 'Atención';
  if (String(agent?.connection_status || '').includes('CONECTADO')) return 'Disponible';
  return 'Registrado';
}

export function Configuracion({data}) {
  const agents = data.floors.flatMap(f => f.agents.map(a => ({...a, floor: f.id, company: f.company})));
  const [tab, setTab] = useState('Usuarios');
  const modules = ['Usuarios', 'Roles y permisos', 'Agentes IA', 'Integraciones', 'Parámetros', 'Seguridad', 'Sistema'];
  return (
    <>
      <Hero e="SISTEMA" t="Configuración" p="Centro administrativo de Mission Control. Solo se muestran controles reales; el resto queda identificado como pendiente."/>
      <nav className="tabs" role="tablist">
        {modules.map(name => (
          <button type="button" role="tab" key={name} aria-selected={tab === name} onClick={() => setTab(name)}>{name}</button>
        ))}
      </nav>
      {tab === 'Usuarios' && (
        <Panel title="Usuarios">
          <div className="user-row">
            <span className="avatar">VP</span>
            <div><b>Presidencia LNH</b><small>Sesión local de Mission Control</small></div>
            <Badge>Activo</Badge>
          </div>
          <button type="button" className="secondary" disabled>+ Nuevo usuario</button>
          <p className="muted">Alta de usuarios: pendiente de integración de identidad.</p>
        </Panel>
      )}
      {tab === 'Roles y permisos' && <Empty title="Pendiente de integración" text="No hay un motor de roles distinto de la sesión local de Presidencia."/>}
      {tab === 'Agentes IA' && (
        <div className="rows">
          {agents.map(a => (
            <article key={`${a.floor}-${a.id}`}>
              <div>
                <b>{a.id}</b>
                <p>{a.name} · {a.company} · {a.floor}</p>
                <Badge>{a.status}</Badge>
              </div>
            </article>
          ))}
        </div>
      )}
      {tab === 'Integraciones' && (
        <div className="connector-row">
          <article className="connector"><small>EMAIL</small><b>Correo</b><span>Gmail (ver Proveedores)</span></article>
          <article className="connector"><small>MENSAJERÍA</small><b>WhatsApp</b><span>Meta Cloud API (ver Proveedores)</span></article>
          <article className="connector"><small>CLIMA</small><b>Meteorología</b><span>No conectado</span></article>
          <article className="connector"><small>FINANZAS</small><b>Sistema financiero</b><span>Pendiente de integración</span></article>
        </div>
      )}
      {tab === 'Parámetros' && <Empty title="Pendiente de integración" text="No hay parámetros corporativos editables en esta fase."/>}
      {tab === 'Seguridad' && <Empty title="Pendiente de integración" text="La sesión actual es local. Políticas de seguridad corporativa no están expuestas en API."/>}
      {tab === 'Sistema' && <Empty title="Respaldos pendientes de integración" text="Los expedientes se conservan en el filesystem corporativo. No hay consola de backup en esta vista."/>}
    </>
  );
}

export function Unavailable({title, eyebrow = 'CORPORATIVO'}) {
  return <><Hero e={eyebrow} t={title} p="Capacidad no habilitada."/><Empty title="No disponible" text={UNAVAILABLE}/></>;
}

const COMMUNICATION_TABS = ['Todas', 'Email', 'WhatsApp', 'Internas'];

function fmtDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('es-CL', {day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'});
  } catch {
    return String(value);
  }
}

function ymd(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function startOfWeek(date) {
  const d = new Date(date);
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  d.setHours(0, 0, 0, 0);
  return d;
}

function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export function Communications({navigate, openCommunicationId}) {
  const [tab, setTab] = useState('Todas');
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [provider, setProvider] = useState(null);
  const [linkExp, setLinkExp] = useState('');
  const [form, setForm] = useState({channel: 'EMAIL', subject: '', body: '', expediente_id: '', recipients: ''});
  const [busy, setBusy] = useState(false);
  const [syncInfo, setSyncInfo] = useState('');

  const load = async () => {
    setError('');
    try {
      const params = {};
      if (tab === 'Email') params.canal = 'EMAIL';
      if (tab === 'WhatsApp') params.canal = 'WHATSAPP';
      if (tab === 'Internas') params.canal = 'INTERNAL';
      const [data, board] = await Promise.all([listCommunications(params), providersStatus().catch(() => null)]);
      setRows(Array.isArray(data) ? data : []);
      setProvider(board);
    } catch (err) {
      setError(err.message);
      setRows([]);
    }
  };

  const pullInbox = async () => {
    setBusy(true);
    setError('');
    setSyncInfo('');
    try {
      const result = await syncEmailPull({query: 'in:inbox', max_results: 25});
      setSyncInfo(
        `Inbox: ${result.created || 0} nuevos · ${result.duplicates || 0} ya registrados`
        + (result.errors ? ` · ${result.errors} errores` : ''),
      );
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        await syncEmailPull({query: 'in:inbox', max_results: 25}).catch(() => null);
      } finally {
        if (alive) await load();
      }
    })();
    return () => { alive = false; };
  }, [tab]);

  useEffect(() => {
    if (!openCommunicationId) return;
    openDetail({communication_id: openCommunicationId});
  }, [openCommunicationId]);

  const gmailLabel = (() => {
    const status = provider?.email?.status || provider?.google_oauth?.status || 'NOT_CONFIGURED';
    if (status === 'CONNECTED') return 'Gmail · Conectado';
    if (status === 'ERROR') return 'Gmail · Error';
    return 'Gmail · No configurado';
  })();

  const whatsappLabel = (() => {
    const status = provider?.whatsapp?.status || provider?.whatsapp_meta?.status || 'NOT_CONFIGURED';
    if (status === 'CONNECTED') return 'WhatsApp · Conectado';
    if (status === 'PENDING_AUTH') return 'WhatsApp · Pendiente token';
    if (status === 'ERROR') return 'WhatsApp · Error';
    return 'WhatsApp · No configurado';
  })();

  const needsHumanGate = channel => channel === 'EMAIL' || channel === 'WHATSAPP';
  const sendLabel = channel => (channel === 'WHATSAPP' ? 'Enviar (WhatsApp)' : 'Enviar (Gmail)');

  const openDetail = async item => {
    try {
      const full = await communication(item.communication_id);
      setSelected(full);
      setLinkExp(full.expediente_id || '');
      if (full.direction === 'INBOUND' && full.read_status !== 'READ') {
        await markCommunicationRead(full.communication_id, {}).catch(() => null);
        await load();
        setSelected(await communication(item.communication_id));
      }
    } catch {
      setSelected(item);
    }
  };

  const createDraft = async e => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await createCommunication({
        channel: form.channel,
        direction: form.channel === 'INTERNAL' ? 'INTERNAL' : 'OUTBOUND',
        subject: form.subject,
        body: form.body,
        expediente_id: form.expediente_id || null,
        recipients: form.recipients ? form.recipients.split(',').map(s => s.trim()).filter(Boolean) : [],
        status: 'DRAFT',
        summary: form.body.slice(0, 160),
        requires_human_gate: needsHumanGate(form.channel),
      });
      setShowForm(false);
      setForm({channel: 'EMAIL', subject: '', body: '', expediente_id: '', recipients: ''});
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const runGate = async (id, decision) => {
    setBusy(true);
    try {
      if (decision === 'SUBMIT') await submitCommunicationApproval(id, {});
      else await communicationHumanGate(id, {decision});
      await load();
      if (selected?.communication_id === id) {
        setSelected(await communication(id));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const linkSelected = async () => {
    if (!selected?.communication_id || !linkExp.trim()) return;
    setBusy(true);
    setError('');
    try {
      await linkCommunicationExpediente(selected.communication_id, {expediente_id: linkExp.trim()});
      setSelected(await communication(selected.communication_id));
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const createExpedienteFromEmail = async () => {
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      const expediente = await createCorporateExpediente({
        tipo: 'Instrucción',
        ambito: 'LNH',
        prioridad: 'P2',
        asunto: selected.subject || 'Comunicación recibida',
        instruccion_original:
          `Origen: comunicación ${selected.communication_id}\n`
          + `Canal: ${selected.channel} · Remitente: ${selected.sender || '—'}\n`
          + `external_id: ${selected.external_id || '—'}\n\n`
          + (selected.body || selected.summary || ''),
      });
      const expedienteId = expediente.expediente_id || expediente.id;
      await linkCommunicationExpediente(selected.communication_id, {expediente_id: expedienteId});
      setSelected(await communication(selected.communication_id));
      await load();
      if (navigate) navigate('ExpedienteCorporativo', expedienteId);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Hero e="MI OFICINA" t="Comunicaciones" p="Centro corporativo de comunicaciones del holding (entrantes y salientes)."/>
      <p className="provider-chip muted-note">{gmailLabel} · {whatsappLabel}</p>
      {error && <Notice tone="warn">{error}</Notice>}
      {syncInfo && <p className="muted-note">{syncInfo}</p>}
      <div className="inbox-toolbar">
        {['Todas', 'Email', 'WhatsApp', 'Internas'].map(id => (
          <button type="button" key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{id}</button>
        ))}
        <button type="button" disabled={busy} onClick={pullInbox}>Sincronizar Gmail</button>
        <button type="button" className="primary" onClick={() => setShowForm(v => !v)}>Nueva comunicación</button>
      </div>
      <p className="muted-note">
        Entrantes email: Gmail → Mission Control. Salientes EMAIL/WHATSAPP: DRAFT → Human Gate → proveedor.
        WhatsApp Cloud API: sin webhook de producción aún; DELIVERED/READ requieren evidencia Meta.
      </p>
      {showForm && (
        <form className="panel form-grid" onSubmit={createDraft}>
          <label>Canal
            <select value={form.channel} onChange={e => setForm({...form, channel: e.target.value})}>
              <option value="EMAIL">EMAIL</option>
              <option value="WHATSAPP">WHATSAPP</option>
              <option value="INTERNAL">INTERNAL</option>
            </select>
          </label>
          <label>Asunto
            <input required value={form.subject} onChange={e => setForm({...form, subject: e.target.value})}/>
          </label>
          <label>Expediente (opcional)
            <input value={form.expediente_id} onChange={e => setForm({...form, expediente_id: e.target.value})} placeholder="LNH-…"/>
          </label>
          <label>{form.channel === 'WHATSAPP' ? 'Destinatario (E.164, ej. +569…)' : 'Destinatarios (email, separados por coma)'}
            <input value={form.recipients} onChange={e => setForm({...form, recipients: e.target.value})} required={needsHumanGate(form.channel)}/>
          </label>
          <label className="full">Cuerpo / contenido
            <textarea required rows={4} value={form.body} onChange={e => setForm({...form, body: e.target.value})}/>
          </label>
          <div className="full">
            <button type="submit" className="primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar DRAFT'}</button>
            <button type="button" className="text-button" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </form>
      )}
      {!rows.length ? (
        <Empty title="Sin comunicaciones" text="No hay comunicaciones materializadas para este filtro. Use «Sincronizar Gmail» para traer la bandeja."/>
      ) : (
        <section className="panel">
          {rows.map(item => (
            <article className={`comm-row ${item.direction === 'INBOUND' && item.read_status !== 'READ' ? 'unread' : ''}`} key={item.communication_id}>
              <div>
                <b>{item.subject || item.summary || item.communication_id}</b>
                <small>
                  {item.channel} · {item.direction || '—'} · {item.status}
                  {item.read_status ? ` · ${item.read_status}` : ''}
                  {item.sender ? ` · de ${item.sender}` : ''}
                  {(item.recipients || []).length ? ` · a ${(item.recipients || []).join(', ')}` : ''}
                  {item.human_gate_status ? ` · HG ${item.human_gate_status}` : ''}
                  {item.provider ? ` · ${item.provider}` : ''}
                  {item.provider_error ? ` · error` : ''}
                  {item.external_id ? ` · id ${item.external_id}` : ''}
                  {item.expediente_id ? ` · ${item.expediente_id}` : ''}
                  {' · '}{fmtDate(item.effective_at || item.received_at || item.sent_at || item.created_at)}
                </small>
              </div>
              <div className="row-actions">
                <button type="button" onClick={() => openDetail(item)}>Ver</button>
                {item.expediente_id && (
                  <button type="button" onClick={() => navigate && navigate('ExpedienteCorporativo', item.expediente_id)}>Abrir expediente</button>
                )}
              </div>
            </article>
          ))}
        </section>
      )}
      {selected && (
        <Panel title={selected.subject || selected.communication_id}>
          <p><b>Canal:</b> {selected.channel} · <b>Dirección:</b> {selected.direction || '—'} · <b>Estado:</b> {selected.status}</p>
          <p><b>Remitente:</b> {selected.sender || '—'} · <b>Destinatarios:</b> {(selected.recipients || []).join(', ') || '—'}</p>
          <p><b>Leído:</b> {selected.read_status || '—'} · <b>Plantilla:</b> {selected.template_name || selected.template?.name || '—'}</p>
          <p><b>Human Gate:</b> {selected.human_gate_status || '—'} · <b>Proveedor:</b> {selected.provider || '—'}</p>
          <p><b>external_id:</b> {selected.external_id || '—'} · <b>thread:</b> {selected.thread_id || '—'}</p>
          <p><b>Expediente:</b> {selected.expediente_id || '—'}</p>
          {selected.provider_error && <p><b>Error proveedor:</b> {selected.provider_error}</p>}
          <p><small>
            created {fmtDate(selected.created_at)}
            {selected.sent_at ? ` · sent ${fmtDate(selected.sent_at)}` : ''}
            {selected.received_at ? ` · received ${fmtDate(selected.received_at)}` : ''}
            {selected.approved_at ? ` · approved ${fmtDate(selected.approved_at)}` : ''}
          </small></p>
          <pre style={{whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit'}}>{selected.body || selected.summary || 'Sin cuerpo.'}</pre>
          <div className="form-grid" style={{marginTop: 12}}>
            <label className="full">Vincular a expediente existente
              <input value={linkExp} onChange={e => setLinkExp(e.target.value)} placeholder="LNH-…"/>
            </label>
          </div>
          <div className="row-actions" style={{marginTop: 12}}>
            <button type="button" disabled={busy || !linkExp.trim()} onClick={linkSelected}>Vincular expediente</button>
            {selected.direction === 'INBOUND' && (
              <button type="button" disabled={busy} onClick={createExpedienteFromEmail}>Crear expediente desde comunicación</button>
            )}
            {needsHumanGate(selected.channel) && selected.direction !== 'INBOUND' && selected.status === 'DRAFT' && (
              <button type="button" disabled={busy} onClick={() => runGate(selected.communication_id, 'SUBMIT')}>Enviar a aprobación</button>
            )}
            {selected.status === 'PENDIENTE_APROBACION' && (
              <>
                <button type="button" disabled={busy} onClick={() => runGate(selected.communication_id, 'APROBAR')}>APROBAR</button>
                <button type="button" disabled={busy} onClick={() => runGate(selected.communication_id, 'CORREGIR')}>CORREGIR</button>
                <button type="button" disabled={busy} onClick={() => runGate(selected.communication_id, 'RECHAZAR')}>RECHAZAR</button>
              </>
            )}
            {selected.status === 'APROBADO' && needsHumanGate(selected.channel) && (
              <button type="button" disabled={busy} onClick={async () => {
                setBusy(true);
                try {
                  await sendCommunication(selected.communication_id, {});
                  await load();
                  setSelected(await communication(selected.communication_id));
                } catch (err) {
                  setError(err.message);
                } finally {
                  setBusy(false);
                }
              }}>{sendLabel(selected.channel)}</button>
            )}
            <button type="button" className="text-button" onClick={() => setSelected(null)}>Cerrar</button>
          </div>
        </Panel>
      )}
    </>
  );
}

export function CalendarAgenda({navigate}) {
  const [mode, setMode] = useState('Mes');
  const [cursor, setCursor] = useState(() => new Date());
  const [events, setEvents] = useState([]);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [provider, setProvider] = useState(null);
  const [form, setForm] = useState({
    title: '',
    event_type: 'REUNION',
    start_at: '',
    end_at: '',
    expediente_id: '',
    description: '',
  });

  const load = async () => {
    setError('');
    try {
      await runF2bSync({}).catch(() => null);
      const [data, board] = await Promise.all([
        calendarEvents({}),
        providersStatus().catch(() => null),
      ]);
      setEvents(Array.isArray(data) ? data : []);
      setProvider(board);
    } catch (err) {
      setError(err.message);
      setEvents([]);
    }
  };

  useEffect(() => { load(); }, []);

  const googleCalLabel = (() => {
    const status = provider?.calendar?.status || provider?.google_oauth?.status || 'NOT_CONFIGURED';
    if (status === 'CONNECTED') return 'Google Calendar · Conectado';
    if (status === 'ERROR') return 'Google Calendar · Error';
    return 'Google Calendar · No configurado';
  })();

  const shift = delta => {
    const next = new Date(cursor);
    if (mode === 'Mes') next.setMonth(next.getMonth() + delta);
    else if (mode === 'Semana') next.setDate(next.getDate() + (7 * delta));
    else next.setDate(next.getDate() + delta);
    setCursor(next);
  };

  const goToday = () => setCursor(new Date());

  const visibleEvents = events.filter(ev => {
    if (!ev.start_at) return false;
    const d = new Date(ev.start_at);
    if (mode === 'Hoy' || mode === 'Día') return sameDay(d, cursor);
    if (mode === 'Semana') {
      const start = startOfWeek(cursor);
      const end = new Date(start);
      end.setDate(end.getDate() + 6);
      end.setHours(23, 59, 59, 999);
      return d >= start && d <= end;
    }
    return d.getMonth() === cursor.getMonth() && d.getFullYear() === cursor.getFullYear();
  });

  const upcoming = events
    .filter(ev => ev.start_at && new Date(ev.start_at) >= new Date(new Date().setHours(0, 0, 0, 0)))
    .slice(0, 8);
  const byType = type => events.filter(ev => ev.event_type === type).slice(0, 6);

  const createEvent = async e => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await createCalendarEvent({
        title: form.title,
        event_type: form.event_type,
        start_at: form.start_at ? new Date(form.start_at).toISOString() : undefined,
        end_at: form.end_at ? new Date(form.end_at).toISOString() : (form.start_at ? new Date(form.start_at).toISOString() : undefined),
        description: form.description,
        expediente_id: form.expediente_id || null,
        status: 'PROGRAMADO',
        company_scope: 'LNH',
      });
      setShowForm(false);
      setForm({title: '', event_type: 'REUNION', start_at: '', end_at: '', expediente_id: '', description: ''});
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Hero e="MI OFICINA" t="Calendario Corporativo" p="Agenda, reuniones, vencimientos y seguimiento del holding."/>
      <p className="provider-chip muted-note">{googleCalLabel}</p>
      {error && <Notice tone="warn">{error}</Notice>}
      <div className="inbox-toolbar">
        {['Hoy', 'Semana', 'Mes'].map(id => (
          <button type="button" key={id} className={mode === id ? 'active' : ''} onClick={() => { setMode(id); if (id === 'Hoy') goToday(); }}>{id}</button>
        ))}
        <button type="button" onClick={() => shift(-1)}>Anterior</button>
        <button type="button" onClick={() => shift(1)}>Siguiente</button>
        <button type="button" onClick={goToday}>Hoy</button>
        <button type="button" className="primary" onClick={() => setShowForm(v => !v)}>+ Nuevo evento</button>
      </div>
      <p className="muted-note">
        {cursor.toLocaleDateString('es-CL', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'})}
        {' · '}{visibleEvents.length} evento(s) en vista
      </p>
      {showForm && (
        <form className="panel form-grid" onSubmit={createEvent}>
          <label>Título
            <input required value={form.title} onChange={e => setForm({...form, title: e.target.value})}/>
          </label>
          <label>Tipo
            <select value={form.event_type} onChange={e => setForm({...form, event_type: e.target.value})}>
              {['REUNION', 'DIRECTORIO', 'VENCIMIENTO', 'SEGUIMIENTO', 'HUMAN_GATE', 'TAREA', 'HITO', 'OTRO'].map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <label>Inicio
            <input required type="datetime-local" value={form.start_at} onChange={e => setForm({...form, start_at: e.target.value})}/>
          </label>
          <label>Fin
            <input type="datetime-local" value={form.end_at} onChange={e => setForm({...form, end_at: e.target.value})}/>
          </label>
          <label>Expediente (opcional)
            <input value={form.expediente_id} onChange={e => setForm({...form, expediente_id: e.target.value})} placeholder="EXP-…"/>
          </label>
          <label className="full">Descripción
            <textarea rows={3} value={form.description} onChange={e => setForm({...form, description: e.target.value})}/>
          </label>
          <div className="full">
            <button type="submit" className="primary" disabled={busy}>{busy ? 'Guardando…' : 'Crear evento'}</button>
            <button type="button" className="text-button" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </form>
      )}
      <div className="calendar-layout">
        <section className="panel cal-panel">
          {mode === 'Mes' ? (
            <MonthGrid date={cursor} events={events} onSelectDay={d => { setCursor(d); setMode('Hoy'); }}/>
          ) : !visibleEvents.length ? (
            <Empty title="Sin eventos" text="No hay citas registradas para esta vista. No se inventan reuniones."/>
          ) : (
            <ul className="plain-list">
              {visibleEvents.map(ev => (
                <li key={ev.event_id}>
                  <b>{ev.title}</b> · {ev.event_type} · {ev.status} · {fmtDate(ev.start_at)}
                  {ev.expediente_id ? (
                    <> · <button type="button" className="text-button" onClick={() => navigate && navigate('ExpedienteCorporativo', ev.expediente_id)}>{ev.expediente_id}</button></>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {mode === 'Mes' && !!visibleEvents.length && (
            <ul className="plain-list" style={{marginTop: 16}}>
              {visibleEvents.map(ev => (
                <li key={`list-${ev.event_id}`}>
                  <b>{ev.title}</b> · {ev.event_type} · {fmtDate(ev.start_at)}
                </li>
              ))}
            </ul>
          )}
        </section>
        <aside className="calendar-side">
          <Panel title="Próximos eventos">
            {!upcoming.length && <Empty title="Vacío" text="Sin próximos eventos materializados."/>}
            {upcoming.map(ev => <p key={ev.event_id}><b>{ev.title}</b><br/><small>{fmtDate(ev.start_at)} · {ev.event_type}</small></p>)}
          </Panel>
          <Panel title="Vencimientos">
            {!byType('VENCIMIENTO').length && <Empty title="Vacío" text="Sin vencimientos registrados."/>}
            {byType('VENCIMIENTO').map(ev => <p key={ev.event_id}><b>{ev.title}</b><br/><small>{fmtDate(ev.start_at)}</small></p>)}
          </Panel>
          <Panel title="Sesiones de Directorio">
            {!byType('DIRECTORIO').length && <Empty title="Vacío" text="Sin sesiones programadas."/>}
            {byType('DIRECTORIO').map(ev => <p key={ev.event_id}><b>{ev.title}</b><br/><small>{fmtDate(ev.start_at)}</small></p>)}
          </Panel>
          <Panel title="Human Gates">
            {!byType('HUMAN_GATE').length && <Empty title="Vacío" text="Sin eventos Human Gate."/>}
            {byType('HUMAN_GATE').map(ev => <p key={ev.event_id}><b>{ev.title}</b><br/><small>{fmtDate(ev.start_at)}</small></p>)}
          </Panel>
          <Panel title="Seguimientos">
            {!byType('SEGUIMIENTO').length && <Empty title="Vacío" text="Sin seguimientos."/>}
            {byType('SEGUIMIENTO').map(ev => <p key={ev.event_id}><b>{ev.title}</b><br/><small>{fmtDate(ev.start_at)}</small></p>)}
          </Panel>
        </aside>
      </div>
    </>
  );
}

function MonthGrid({date, events = [], onSelectDay}) {
  const year = date.getFullYear();
  const month = date.getMonth();
  const first = new Date(year, month, 1).getDay();
  const days = new Date(year, month + 1, 0).getDate();
  const offset = (first + 6) % 7;
  const cells = [...Array(offset).fill(null), ...Array.from({length: days}, (_, i) => i + 1)];
  const today = new Date();
  const countFor = day => {
    if (!day) return 0;
    const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return events.filter(ev => String(ev.start_at || '').startsWith(key)).length;
  };
  return (
    <div className="month-grid">
      {['L', 'M', 'X', 'J', 'V', 'S', 'D'].map(d => <span className="dow" key={d}>{d}</span>)}
      {cells.map((day, i) => {
        const count = countFor(day);
        const isToday = day && sameDay(new Date(year, month, day), today);
        return (
          <button
            type="button"
            className={`day ${isToday ? 'today' : ''} ${count ? 'has-events' : ''}`}
            key={i}
            disabled={!day}
            onClick={() => day && onSelectDay && onSelectDay(new Date(year, month, day))}
          >
            <span>{day || ''}</span>
            {count > 0 && <em>{count}</em>}
          </button>
        );
      })}
    </div>
  );
}

export function EvidenceCatalog({list, openCase}) {
  const withDocs = list.filter(x => x.documents > 0);
  return (
    <>
      <Hero e="EXPEDIENTES" t="Evidencia" p="La evidencia documental permanece en cada expediente. Esta vista solo lista expedientes que ya tienen documentos registrados."/>
      <Cases rows={withDocs} open={openCase} emptyTitle="Sin documentos materializados" emptyText="No hay expedientes con documentos de evidencia registrados."/>
    </>
  );
}

export function SearchResults({query, list, floors, companies, openCase, navigate}) {
  const q = query.trim().toLowerCase();
  if (!q) return null;
  const casesHit = list.filter(c => [c.case_id, c.mission, c.floor_id, c.status].join(' ').toLowerCase().includes(q));
  const floorHit = floors.filter(f => [f.id, f.name, f.manager].join(' ').toLowerCase().includes(q));
  const companyHit = companies.filter(c => [c.id, c.name].join(' ').toLowerCase().includes(q));
  return (
    <Panel title={`Búsqueda: ${query}`}>
      {!casesHit.length && !floorHit.length && !companyHit.length && <Empty title="Sin coincidencias" text="La búsqueda usa únicamente catálogo y expedientes reales."/>}
      {companyHit.map(c => <button type="button" className="search-hit" key={c.id} onClick={() => navigate('Empresa', c.id)}>{c.name}</button>)}
      {floorHit.map(f => <button type="button" className="search-hit" key={f.id} onClick={() => navigate('Piso', f.id)}>{f.id} · {f.name}</button>)}
      {casesHit.slice(0, 12).map(c => <button type="button" className="search-hit" key={c.case_id} onClick={() => openCase(c)}>{c.floor_id} · {c.case_id}</button>)}
    </Panel>
  );
}
