import React, {useRef, useState} from 'react';
import {createCase, encodeFile} from './api';
import {Badge, Cases, Empty, Hero, Metric, Notice, date, caseStamp} from './components';
import {Icon} from './icons';
import {AreaCard, ClockWeather, CompanyBlock, CORPORATE_AREAS, DIRECTORS, Panel, Pending, Shortcut} from './ui';

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
  const recent = [...list].sort((a, b) => (caseStamp(b.case_id)?.getTime() || 0) - (caseStamp(a.case_id)?.getTime() || 0)).slice(0, 6);
  const [newsTab, setNewsTab] = useState('Nacional');
  return (
    <div className="office">
      <section className="office-hero">
        <div>
          <small>PRESIDENCIA · LATITUD NORTE HOLDING</small>
          <h1>Mi Oficina</h1>
          <p>Centro ejecutivo de Presidencia. Las misiones empresariales se consultan dentro de cada empresa, piso y expediente.</p>
        </div>
        <ClockWeather/>
      </section>
      <div className="shortcut-grid">
        <Shortcut gold icon="plus" title="Nueva Instrucción Corporativa" text="Inicia una propuesta, proyecto o decisión para el Directorio" onClick={() => navigate('NuevaInstruccion')}/>
        <Shortcut icon="calendar" title="Calendario" text="Reuniones y agenda de Presidencia" onClick={() => navigate('Calendario')}/>
        <Shortcut icon="communications" title="Comunicaciones" text="Mensajes, email y notificaciones" onClick={() => navigate('Comunicaciones')}/>
        <Shortcut icon="decisions" title="Decisiones" text="Human Gate y pendientes reales" onClick={() => navigate('Decisiones')}/>
        <Shortcut icon="users" title="Directorio" text="Sesiones y estructura del Directorio" onClick={() => navigate('Directorio')}/>
        <Shortcut icon="holding" title="Holding" text="Visión general del grupo" onClick={() => navigate('Holding')}/>
      </div>
      <div className="office-grid">
        <Panel title="Resumen financiero del Holding" action={<button type="button" className="text-button" onClick={() => navigate('Area', 'finanzas')}>Ver detalle</button>}>
          <Empty title="Sin datos" text="Sistema financiero pendiente de integración. No se muestran cifras demostrativas."/>
        </Panel>
        <Panel title="Mi Agenda" action={<button type="button" className="text-button" onClick={() => navigate('Calendario')}>Ver calendario</button>}>
          <Empty title="Agenda vacía" text="No hay eventos materializados. La integración de calendario externo corresponde a una fase posterior."/>
        </Panel>
        <Panel title="Comunicaciones recientes" action={<button type="button" className="text-button" onClick={() => navigate('Comunicaciones')}>Ver todas</button>}>
          <Empty title="Sin comunicaciones" text="Email y WhatsApp: No conectado. El canal Sistema no tiene eventos materializados."/>
        </Panel>
        <Panel title="Noticias">
          <div className="subtabs">
            {['Nacional', 'Internacional', 'Mercados', 'Tecnología'].map(tab => (
              <button type="button" key={tab} className={newsTab === tab ? 'on' : ''} onClick={() => setNewsTab(tab)}>{tab}</button>
            ))}
          </div>
          <Empty title={`${newsTab}: integración pendiente`} text="No hay fuente de noticias conectada. No se publican titulares ilustrativos."/>
        </Panel>
        <Panel title="Alertas y pendientes" action={<button type="button" className="text-button" onClick={() => navigate('Decisiones')}>Ver todas</button>}>
          {review.length + errors.length ? (
            <div className="alert-list">
              {review.map(row => (
                <button type="button" className="alert-row warn" key={`d-${row.case_id}`} onClick={() => openCase(row)}>
                  <b>Human Gate pendiente</b>
                  <small>{row.floor_id} · {row.case_id}</small>
                </button>
              ))}
              {errors.map(row => (
                <button type="button" className="alert-row danger" key={`e-${row.case_id}`} onClick={() => openCase(row)}>
                  <b>{row.status}</b>
                  <small>{row.floor_id} · {row.case_id}</small>
                </button>
              ))}
            </div>
          ) : <Empty title="Sin pendientes materializados" text="No hay Human Gates ni errores de Platform registrados."/>}
        </Panel>
        <Panel title="Accesos directos">
          <div className="mini-grid">
            <button type="button" onClick={() => navigate('Directorio')}>Directorio</button>
            <button type="button" onClick={() => navigate('Area', 'finanzas')}>Finanzas</button>
            <button type="button" onClick={() => navigate('Empresa', 'MGC')}>MGC</button>
            <button type="button" onClick={() => navigate('Empresa', 'LNRE')}>LNR</button>
            <button type="button" onClick={() => navigate('Configuracion')}>Configuración</button>
            <button type="button" onClick={() => navigate('Areas')}>Áreas</button>
          </div>
        </Panel>
      </div>
      {recent.length > 0 && (
        <Panel title="Actividad de expedientes">
          <div className="activity-table">
            {recent.map(row => (
              <button type="button" className="activity-row" key={`${row.floor_id}/${row.case_id}`} onClick={() => openCase(row)}>
                <span className="mark sm"><Icon name="activity"/></span>
                <span>
                  <b>{row.floor_id}</b>
                  <small>{row.mission || row.case_id}</small>
                </span>
                <time>{caseStamp(row.case_id) ? date(caseStamp(row.case_id).toISOString()) : '—'}</time>
                <Badge>{row.status}</Badge>
              </button>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

export function Holding({companies, floors, list, enter, navigate}) {
  const operationalFloors = floors.filter(f => f.status === 'Operativo').length;
  const agents = floors.flatMap(f => f.agents).length;
  return (
    <>
      <Hero e="HOLDING" t="Latitud Norte Holding" p="Visión general del grupo. Los pisos y misiones se consultan dentro de cada empresa."/>
      <div className="kpis">
        <Metric icon="company" tone="ok" label="Empresas" value={companies.length} note="Registradas en el catálogo"/>
        <Metric icon="floors" tone="info" label="Pisos" value={floors.length} note={`${operationalFloors} operativos`}/>
        <Metric icon="agents" tone="info" label="Agentes" value={agents} note="Dotación materializada"/>
        <Metric icon="missions" tone="warn" label="Expedientes" value={list.length} note="Misiones empresariales registradas"/>
      </div>
      <div className="company-duo">
        {companies.map(company => (
          <CompanyBlock key={company.id} company={company} floors={floors} cases={list} enter={enter}/>
        ))}
      </div>
      <h2 className="section-title">Áreas corporativas</h2>
      <div className="area-grid">
        {CORPORATE_AREAS.map(area => (
          <AreaCard key={area.id} area={area} open={item => navigate(item.route || 'Area', item.route ? undefined : item.id)}/>
        ))}
      </div>
    </>
  );
}

export function Companies({companies, floors, list, enter}) {
  return (
    <>
      <Hero e="EMPRESAS" t="Empresas del Holding" p="Ingrese a la empresa para operar pisos, gerentes y misiones. Layout reutilizable para futuras filiales."/>
      <div className="company-duo">
        {companies.map(company => (
          <CompanyBlock key={company.id} company={company} floors={floors} cases={list} enter={enter}/>
        ))}
      </div>
    </>
  );
}

export function CompanyPage({company, floors, work, openFloor, instruct}) {
  const rows = floors.filter(f => f.company === company.id);
  const executable = rows.find(f => f.id === 'MGC-03');
  return (
    <>
      <Hero
        e="EMPRESA"
        t={company.name}
        p={company.id === 'MGC' ? 'Pisos operativos y misiones empresariales. GER-MGC-03 permanece en OpenAI Platform.' : 'Estructura registrada. Sin pisos de agentes habilitados.'}
        aside={executable ? <button type="button" className="primary gold-btn" onClick={() => instruct(executable.id)}>+ Nueva Misión</button> : null}
      />
      <dl className="facts">
        <div><small>Estado</small><b><Badge>{company.status}</Badge></b></div>
        <div><small>Pisos</small><b>{rows.length}</b></div>
        <div><small>Expedientes activos</small><b>{work.filter(c => c.status !== 'CLOSED' && c.status !== 'APPROVED').length}</b></div>
        <div><small>Human Gate</small><b>{work.filter(c => c.requires_decision).length}</b></div>
      </dl>
      <h2 className="section-title">Pisos</h2>
      <FloorRows rows={rows} open={openFloor}/>
    </>
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

export function CorporateInstruction({cancel}) {
  const [blocked, setBlocked] = useState('');
  return (
    <MissionForm
      mode="instruction"
      cancel={cancel}
      notice={blocked}
      onSubmit={async () => {
        setBlocked('Pendiente de integración: no existe backend de expediente corporativo de Presidencia. La instrucción no se registró. Las misiones empresariales continúan en Empresa → Piso.');
      }}
    />
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
    <>
      <Hero
        e={isMission ? 'NUEVA MISIÓN EMPRESARIAL' : 'NUEVA INSTRUCCIÓN CORPORATIVA'}
        t={isMission ? 'Nueva misión' : 'Instrucción de Presidencia'}
        p={isMission
          ? `Empresa → piso ${floor.id} → ${floor.manager}. Se registra el expediente existente; la ejecución en Platform es un paso posterior.`
          : 'Presidencia → gobierno LNH / Directorio / área. Distinto de una misión empresarial de piso.'}
      />
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
                  <button type="button" key={item} className={priority === item ? 'on' : ''} onClick={() => setPriority(item)}>{item}</button>
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
            <button disabled={!mission.trim() || !subject.trim()} type="submit" className="approve">{busy ? 'Procesando…' : 'Confirmar'}</button>
          </div>
        </fieldset>
        <Notice error>{error}</Notice>
        <Notice>{notice}</Notice>
      </form>
    </>
  );
}

export function Directorio({list, openCase}) {
  const boardBound = [];
  const decisions = list.filter(x => ['APPROVED', 'REJECTED', 'CLOSED'].includes(x.status));
  const pending = list.filter(x => x.requires_decision);
  return (
    <>
      <Hero e="HOLDING" t="Directorio" p="Estructura de cinco Directores IA. La deliberación y el voto se habilitarán en una fase posterior. No se inventan sesiones ni votos."/>
      <div className="director-grid">
        {DIRECTORS.map(item => (
          <article className="director-card" key={item.id}>
            <div className="director-avatar">{item.id.slice(-2)}</div>
            <b>{item.name}</b>
            <p>{item.mandate}</p>
            <Pending label="Pendiente de habilitación"/>
          </article>
        ))}
      </div>
      <div className="office-grid two">
        <Panel title="Expedientes enviados al Directorio">
          {boardBound.length
            ? <Cases rows={boardBound} open={openCase}/>
            : <Empty title="Sin envíos al Directorio" text="No existe un flujo de derivación al Directorio en el backend actual. Los Human Gates de piso se atienden en Decisiones y en cada expediente."/>}
        </Panel>
        <Panel title="Pendientes">
          <Cases rows={pending} open={openCase} emptyTitle="Sin pendientes de Human Gate" emptyText="No hay consolidado profesional listo para decisión humana."/>
        </Panel>
        <Panel title="Decisiones recientes">
          <Cases rows={decisions.slice(0, 8)} open={openCase} emptyTitle="Sin decisiones humanas registradas" emptyText="Las aprobaciones y rechazos de expediente aparecerán aquí."/>
        </Panel>
        <Panel title="Documentos">
          <Empty title="Sin repositorio de Directorio" text="Los documentos permanecen en cada expediente. No hay un archivo separado del Directorio."/>
        </Panel>
      </div>
    </>
  );
}

export function CorporateOffice() {
  return (
    <AreaView
      code="CO"
      title="Corporate Office"
      summary="Oficina corporativa del Holding. Un agente IA por función cuando se habilite. Fase 1: estructura visual."
    />
  );
}

export function Areas({navigate}) {
  return (
    <>
      <Hero e="HOLDING" t="Áreas corporativas" p="Cada área operará con un agente IA de función. Ningún agente está habilitado en esta fase."/>
      <div className="area-grid">
        {CORPORATE_AREAS.map(area => (
          <AreaCard key={area.id} area={area} open={item => navigate(item.route || 'Area', item.route ? undefined : item.id)}/>
        ))}
      </div>
    </>
  );
}

export function AreaView({code, title, summary, list = [], openCase}) {
  const [tab, setTab] = useState('Resumen');
  return (
    <>
      <Hero e="ÁREA CORPORATIVA" t={code ? `${code} | ${title}` : title} p={summary}/>
      <nav className="tabs" role="tablist">
        {['Resumen', 'Actividad', 'Expedientes', 'Documentos'].map(name => (
          <button type="button" role="tab" key={name} aria-selected={tab === name} onClick={() => setTab(name)}>{name}</button>
        ))}
      </nav>
      {tab === 'Resumen' && (
        <div className="kpis">
          <Metric label="Agente IA" value="—" note="Pendiente de habilitación"/>
          <Metric label="Indicadores propios" value="—" note="Sin backend de área"/>
          <Metric label="Expedientes" value={list.length} note={list.length ? 'Filtrados si aplica' : 'Sin vínculo de área en el backend'}/>
        </div>
      )}
      {tab === 'Actividad' && <Empty title="Sin actividad de área" text="No hay un registro de actividad corporativa distinto de los expedientes de piso."/>}
      {tab === 'Expedientes' && <Cases rows={list} open={openCase} emptyTitle="Sin expedientes de área" emptyText="El backend actual asocia expedientes a empresa/piso, no a áreas LNH."/>}
      {tab === 'Documentos' && <Empty title="Sin documentos de área" text="Los documentos se conservan en el expediente correspondiente."/>}
      <Panel title="Accesos funcionales">
        <Pending/>
        <p className="muted">Funciones operativas del área se habilitarán con el agente de función. No se simula ejecución.</p>
      </Panel>
    </>
  );
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
          <article className="connector"><small>EMAIL</small><b>Correo</b><span>No conectado</span></article>
          <article className="connector"><small>MENSAJERÍA</small><b>WhatsApp</b><span>No conectado</span></article>
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

const COMMUNICATIONS = [];

export function Communications({list, openCase}) {
  const [channel, setChannel] = useState('Sistema');
  const systemItems = list.filter(x => x.requires_decision || ['PLATFORM_EXECUTION_ERROR', 'PLATFORM_CONNECTION_ERROR'].includes(x.status)).map(row => ({
    id: row.case_id,
    channel: 'Sistema',
    subject: row.requires_decision ? 'Human Gate pendiente' : row.status,
    case: row,
  }));
  const items = channel === 'Sistema' ? systemItems : [];
  return (
    <>
      <Hero e="MI OFICINA" t="Comunicaciones" p="Canales reales en esta fase: notificaciones internas derivadas de expedientes. Email y WhatsApp no están conectados."/>
      <div className="connector-row four">
        <article className="connector on"><small>CANAL</small><b>Sistema</b><span>Notificaciones de expedientes</span></article>
        <article className="connector"><small>CANAL</small><b>Email</b><span>No conectado</span></article>
        <article className="connector"><small>CANAL</small><b>WhatsApp</b><span>No conectado</span></article>
        <article className="connector"><small>CANAL</small><b>Notificaciones internas</b><span>Human Gate y errores de Platform</span></article>
      </div>
      <div className="inbox-toolbar">
        {['Sistema', 'Email', 'WhatsApp', 'Notificaciones internas'].map(id => (
          <button type="button" key={id} className={channel === id ? 'active' : ''} onClick={() => setChannel(id)}>{id}</button>
        ))}
      </div>
      {['Email', 'WhatsApp'].includes(channel) ? (
        <Empty title="No conectado" text={`El canal ${channel} no tiene integración en esta fase.`}/>
      ) : items.length ? (
        <section className="panel">
          {items.map(item => (
            <article className="comm-row" key={item.id}>
              <div>
                <b>{item.subject}</b>
                <small>{item.case.floor_id} · {item.case.case_id}</small>
              </div>
              <button type="button" onClick={() => openCase(item.case)}>Ver expediente</button>
            </article>
          ))}
        </section>
      ) : <Empty title="Bandeja vacía" text="No hay notificaciones internas materializadas."/>}
    </>
  );
}

export function CalendarAgenda() {
  const [view, setView] = useState('mes');
  const now = new Date();
  return (
    <>
      <Hero e="MI OFICINA" t="Calendario" p="Agenda de Presidencia. Sin reuniones ficticias. Calendarios externos se integrarán en una fase posterior."/>
      <div className="inbox-toolbar">
        {[['dia', 'Día'], ['semana', 'Semana'], ['mes', 'Mes'], ['agenda', 'Agenda']].map(([id, label]) => (
          <button type="button" key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}>{label}</button>
        ))}
      </div>
      <div className="kpis">
        <Metric label="Vista" value={view} note={now.toLocaleDateString('es-CL', {month: 'long', year: 'numeric'})}/>
        <Metric label="Próximos eventos" value="0" note="Sin eventos materializados"/>
      </div>
      <section className="panel cal-panel">
        {view === 'mes' ? <MonthGrid date={now}/> : <Empty title="Sin eventos" text="No hay citas registradas para esta vista. No se inventan reuniones."/>}
      </section>
    </>
  );
}

function MonthGrid({date}) {
  const year = date.getFullYear();
  const month = date.getMonth();
  const first = new Date(year, month, 1).getDay();
  const days = new Date(year, month + 1, 0).getDate();
  const offset = (first + 6) % 7;
  const cells = [...Array(offset).fill(null), ...Array.from({length: days}, (_, i) => i + 1)];
  return (
    <div className="month-grid">
      {['L', 'M', 'X', 'J', 'V', 'S', 'D'].map(d => <span className="dow" key={d}>{d}</span>)}
      {cells.map((day, i) => (
        <span className={`day ${day === date.getDate() ? 'today' : ''}`} key={i}>{day || ''}</span>
      ))}
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
