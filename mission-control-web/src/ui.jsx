import React from 'react';
import {Icon} from './icons';
import {Badge, Empty} from './components';

export const CORPORATE_AREAS = [
  {id: 'directorio', name: 'Directorio', route: 'Directorio'},
  {id: 'corporate-office', name: 'Corporate Office', route: 'CorporateOffice'},
  {id: 'finanzas', name: 'Finanzas Corporativas', code: 'LNH-04'},
  {id: 'desarrollo', name: 'Desarrollo Corporativo'},
  {id: 'pmo', name: 'PMO'},
  {id: 'ia', name: 'IA y Automatización'},
  {id: 'marketing', name: 'Marketing Corporativo'},
  {id: 'bi', name: 'Business Intelligence'},
  {id: 'juridico', name: 'Jurídico y Compliance'},
  {id: 'auditoria', name: 'Auditoría y Riesgos'},
];

export const DIRECTORS = [
  {id: 'D01', name: 'Director 01', mandate: 'Estrategia y Crecimiento'},
  {id: 'D02', name: 'Director 02', mandate: 'Finanzas, Caja y Capital'},
  {id: 'D03', name: 'Director 03', mandate: 'Riesgo, Compliance y Patrimonio'},
  {id: 'D04', name: 'Director 04', mandate: 'Operaciones, Sistemas y Tecnología'},
  {id: 'D05', name: 'Director 05', mandate: 'Empresas, Mercado e Inversiones'},
];

export function Pending({label = 'Pendiente de integración'}) {
  return <span className="status-pending">{label}</span>;
}

export function Panel({title, action, children, className = ''}) {
  return (
    <section className={`panel ds-panel ${className}`}>
      {(title || action) && (
        <div className="panel-head">
          {title && <h2>{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Shortcut({icon, title, text, gold, onClick}) {
  return (
    <button type="button" className={`shortcut ${gold ? 'gold' : ''}`} onClick={onClick}>
      <span className="shortcut-icon"><Icon name={icon}/></span>
      <span>
        <b>{title}</b>
        <small>{text}</small>
      </span>
    </button>
  );
}

export function CompanyBlock({company, floors, cases, enter}) {
  const units = floors.filter(f => f.company === company.id);
  const agents = units.flatMap(f => f.agents);
  const work = cases.filter(c => units.some(f => f.id === c.floor_id));
  const alerts = work.filter(c => c.requires_decision || ['PLATFORM_EXECUTION_ERROR', 'PLATFORM_CONNECTION_ERROR', 'RECOVERY_PENDING'].includes(c.status));
  const theme = company.id.toLowerCase();
  return (
    <article className={`company-block theme-${theme}`}>
      <div className="company-visual" role="img" aria-label={company.name}/>
      <div className="company-body">
        <div className="company-meta">
          <div>
            <h3>{company.name}</h3>
            <p>{company.id === 'MGC' ? 'Inteligencia de mercados e investigación minera.' : 'Desarrollo inmobiliario del Holding. Pisos de agentes aún no habilitados.'}</p>
          </div>
          <Badge>{company.status}</Badge>
        </div>
        <dl className="facts compact">
          <div><small>Pisos</small><b>{units.length}</b></div>
          <div><small>Agentes</small><b>{agents.length}</b></div>
          <div><small>Expedientes</small><b>{work.length}</b></div>
          <div><small>Alertas</small><b>{alerts.length}</b></div>
        </dl>
        {alerts.length > 0
          ? <p className="alert-line">{alerts.length} expediente(s) requieren atención.</p>
          : <p className="muted">Sin alertas materializadas.</p>}
        <button type="button" onClick={() => enter(company.id)}>Ingresar</button>
      </div>
    </article>
  );
}

export function AreaCard({area, open}) {
  return (
    <button type="button" className="area-card" onClick={() => open(area)}>
      <span className="area-mark"><Icon name={area.id === 'directorio' ? 'users' : area.id === 'finanzas' ? 'finance' : 'holding'}/></span>
      <span>
        <b>{area.code ? `${area.code} · ${area.name}` : area.name}</b>
        <small>Pendiente de habilitación</small>
      </span>
      <Pending/>
    </button>
  );
}

export function ClockWeather() {
  const [now, setNow] = React.useState(() => new Date());
  React.useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const dateLabel = now.toLocaleDateString('es-CL', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'});
  const timeLabel = now.toLocaleTimeString('es-CL', {hour: '2-digit', minute: '2-digit'});
  return (
    <aside className="clock-card">
      <p className="clock-date">{dateLabel}</p>
      <p className="clock-time">{timeLabel}</p>
      <p className="clock-place">Santiago, Chile</p>
      <p className="status-pending">Clima: No conectado</p>
    </aside>
  );
}

export function EmptyState({title, text}) {
  return <Empty title={title} text={text}/>;
}
