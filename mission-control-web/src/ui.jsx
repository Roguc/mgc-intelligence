import React from 'react';
import {Icon} from './icons';
import {Badge, Empty} from './components';
import {AREA_FUNCTIONS, ASSETS, areaPhoto, availabilityTone} from './assets';

/** Navigation + functional LNH areas (8 agents). No false “pending” areas. */
export const CORPORATE_AREAS = [
  {id: 'directorio', name: 'Directorio', route: 'Directorio', icon: 'users'},
  {id: 'corporate-office', name: 'Corporate Office', code: 'LNH-03', areaId: 'LNH-03', route: 'CorporateOffice', icon: 'office'},
  {id: 'finanzas', name: 'Finanzas Corporativas', code: 'LNH-04', areaId: 'LNH-04', icon: 'finance'},
  {id: 'desarrollo', name: 'Desarrollo Corporativo', code: 'LNH-05', areaId: 'LNH-05', icon: 'holding'},
  {id: 'pmo', name: 'PMO', code: 'LNH-06', areaId: 'LNH-06', icon: 'reports'},
  {id: 'ia', name: 'IA y Automatización', code: 'LNH-07', areaId: 'LNH-07', icon: 'agents'},
  {id: 'marketing', name: 'Marketing Corporativo', code: 'LNH-08', areaId: 'LNH-08', icon: 'news'},
  {id: 'bi', name: 'Business Intelligence', code: 'LNH-09', areaId: 'LNH-09', icon: 'reports'},
  {id: 'juridico', name: 'Jurídico y Compliance', code: 'LNH-10', areaId: 'LNH-10', icon: 'decisions'},
];

export const DIRECTORS = [
  {id: 'DIR-01', name: 'DIR-01', mandate: 'Estrategia y Crecimiento'},
  {id: 'DIR-02', name: 'DIR-02', mandate: 'Finanzas, Caja y Capital'},
  {id: 'DIR-03', name: 'DIR-03', mandate: 'Riesgo, Compliance y Patrimonio'},
  {id: 'DIR-04', name: 'DIR-04', mandate: 'Operaciones, Sistemas y Tecnología'},
  {id: 'DIR-05', name: 'DIR-05', mandate: 'Empresas, Mercado e Inversiones'},
];

export const LNH_FUNCTIONAL_AREAS = CORPORATE_AREAS.filter(a => a.areaId);

export function Pending({label = 'Pendiente de integración'}) {
  return <span className="status-pending">{label}</span>;
}

/** Technical status — keep for Config / tooltips; avoid on executive cards. */
export function StatusLabel({label}) {
  if (!label) return null;
  return <span className="status-pending">{label}</span>;
}

export function AvailabilityDot({agent, className = ''}) {
  const tone = availabilityTone(agent);
  return (
    <span className={`avail-dot avail-${tone.dot} ${className}`.trim()} title={tone.label}>
      <i aria-hidden="true"/>
      <em>{tone.label}</em>
    </span>
  );
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

export function Shortcut({icon, title, text, gold, badge, onClick}) {
  return (
    <button type="button" className={`shortcut ${gold ? 'gold' : ''}`} onClick={onClick}>
      <span className="shortcut-icon"><Icon name={icon}/>{badge ? <em>{badge}</em> : null}</span>
      <span>
        <b>{title}</b>
        {text && <small>{text}</small>}
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
  const hero = company.id === 'MGC' ? ASSETS.mgc.hero : ASSETS.lnre.hero;
  const logo = company.id === 'MGC' ? ASSETS.mgc.logo : ASSETS.lnre.logo;
  return (
    <article className={`company-block theme-${theme}`}>
      <div className="company-visual" role="img" aria-label={company.name} style={{backgroundImage: `url(${hero})`}}>
        <img className="company-logo-mark" src={logo} alt="" />
      </div>
      <div className="company-body">
        <div className="company-meta">
          <div>
            <h3>{company.name}</h3>
            <p>{company.id === 'MGC' ? 'Empresa minera y comercial del Holding.' : 'Desarrollo e inversión inmobiliaria del Holding.'}</p>
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
        <button type="button" onClick={() => enter(company.id)}>Ingresar →</button>
      </div>
    </article>
  );
}

export function AreaCard({area, open, agent}) {
  if (!area.areaId) return null;
  const fn = AREA_FUNCTIONS[area.areaId] || area.name;
  const photo = areaPhoto(area.areaId);
  return (
    <button type="button" className="area-card exec-area-card" onClick={() => open(area)}>
      <span className="area-card-media" style={{backgroundImage: `url(${photo})`}} aria-hidden="true"/>
      <span className="area-card-shade"/>
      <span className="area-card-body">
        <small>{area.code}</small>
        <b>{area.name}</b>
        <em>{fn}</em>
        <AvailabilityDot agent={agent}/>
      </span>
    </button>
  );
}

export function ClockWeather({weather}) {
  const [now, setNow] = React.useState(() => new Date());
  React.useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const dateLabel = now.toLocaleDateString('es-CL', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'});
  const timeLabel = now.toLocaleTimeString('es-CL', {hour: '2-digit', minute: '2-digit', hour12: false});
  const current = weather?.current;
  const today = (weather?.forecast || [])[0];
  const hasTemp = current && current.temperature_c != null;
  const tempLabel = hasTemp ? `${Math.round(Number(current.temperature_c))}°C` : '—';
  const maxLabel = today?.temp_max_c != null ? Math.round(Number(today.temp_max_c)) : null;
  const minLabel = today?.temp_min_c != null ? Math.round(Number(today.temp_min_c)) : null;
  const condition = current?.condition || '—';
  const code = Number(current?.weather_code);

  return (
    <div className="clock-card" aria-label="Clima y hora Santiago">
      <p className="clock-date">{dateLabel}</p>
      <div className="clock-main-row">
        <div className="clock-main-left">
          <p className="clock-time">{timeLabel}</p>
          <p className="clock-place">
            <svg className="clock-pin-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="currentColor" d="M12 2.5c-3.6 0-6.5 2.8-6.5 6.3 0 4.7 5.4 11.2 6.1 12 .2.3.6.3.8 0 .7-.8 6.1-7.3 6.1-12 0-3.5-2.9-6.3-6.5-6.3zm0 8.6a2.4 2.4 0 1 1 0-4.8 2.4 2.4 0 0 1 0 4.8z"/>
            </svg>
            Santiago, Chile
          </p>
        </div>
        <div className="clock-main-right">
          <div className="clock-weather-main">
            <WeatherGlyph code={code}/>
            <span className="clock-temp">{tempLabel}</span>
          </div>
          <p className="clock-condition">{condition}</p>
          <p className="clock-range">
            {maxLabel != null && minLabel != null
              ? `Máx. ${maxLabel}° | Mín. ${minLabel}°`
              : 'Máx. — | Mín. —'}
          </p>
        </div>
      </div>
    </div>
  );
}

function WeatherGlyph({code}) {
  const n = Number(code);
  if (n === 0 || n === 1) {
    return (
      <svg className="clock-weather-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="4.2" fill="#d4b46a"/>
        {[0, 45, 90, 135, 180, 225, 270, 315].map(deg => (
          <line
            key={deg}
            x1="12" y1="2.5" x2="12" y2="5"
            stroke="#d4b46a" strokeWidth="1.6" strokeLinecap="round"
            transform={`rotate(${deg} 12 12)`}
          />
        ))}
      </svg>
    );
  }
  if (n === 2 || n === 3 || n === 45 || n === 48) {
    return (
      <svg className="clock-weather-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M7.5 16a4 4 0 0 1 .3-8 5 5 0 0 1 9.6 1.5A3.5 3.5 0 0 1 17 16H7.5z" fill="#c5d4df"/>
      </svg>
    );
  }
  if ((n >= 51 && n <= 67) || (n >= 80 && n <= 82)) {
    return (
      <svg className="clock-weather-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M7.5 13a4 4 0 0 1 .3-8 5 5 0 0 1 9.6 1.5A3.5 3.5 0 0 1 17 13H7.5z" fill="#c5d4df"/>
        <path d="M9 15.5v3M12 15v4M15 15.5v3" stroke="#7eb6d8" strokeWidth="1.6" strokeLinecap="round"/>
      </svg>
    );
  }
  return (
    <svg className="clock-weather-icon" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4.2" fill="#d4b46a" opacity=".85"/>
    </svg>
  );
}

function fmtIndicatorValue(item) {
  if (item?.value == null) return '—';
  const n = Number(item.value);
  if (Number.isFinite(n)) {
    if (item.key === 'ipc' || item.key === 'tpm') return `${n.toLocaleString('es-CL', {maximumFractionDigits: 2})}${item.unit === '%' || (item.unit || '').toLowerCase().includes('porcent') ? '%' : ''}`;
    if (item.key === 'libra_cobre') return `USD ${n.toLocaleString('es-CL', {minimumFractionDigits: 2, maximumFractionDigits: 2})}/lb`;
    return n.toLocaleString('es-CL', {maximumFractionDigits: 2});
  }
  return String(item.value);
}

export function ExecutiveIndicators({title, boardSection, emptyText}) {
  const indicators = boardSection?.indicators || [];
  const status = boardSection?.status || 'NO_DISPONIBLE';
  const statusClass = status === 'ACTUALIZADO' ? 'status-ok' : (status === 'DESACTUALIZADO' ? 'status-warn' : 'status-pending');
  return (
    <Panel title={title} action={<span className={statusClass}>{status}</span>}>
      {indicators.length ? (
        <div className="finance-kpis exec-intel-kpis">
          {indicators.map(item => (
            <article key={item.key}>
              <small>{item.label}</small>
              <b>{fmtIndicatorValue(item)}</b>
              <span>
                {item.status || '—'}
                {item.unit && item.key !== 'libra_cobre' && item.value != null ? ` · ${item.unit}` : ''}
              </span>
              <span className="exec-intel-meta">
                {item.source || '—'}
                {item.observed_at ? ` · origen ${new Date(item.observed_at).toLocaleDateString('es-CL')}` : ''}
              </span>
              {item.error && <span className="exec-intel-error">{item.error}</span>}
            </article>
          ))}
        </div>
      ) : (
        <Empty title="Sin indicadores" text={emptyText || boardSection?.error || 'Fuente no disponible.'}/>
      )}
      {boardSection?.justification && <p className="muted-note">{boardSection.justification}</p>}
      {boardSection?.source && (
        <p className="muted-note">
          Fuente: {boardSection.source}
          {boardSection.fetched_at ? ` · consulta ${new Date(boardSection.fetched_at).toLocaleString('es-CL')}` : ''}
        </p>
      )}
    </Panel>
  );
}

const NEWS_TABS = [
  {id: 'nacional', label: 'Nacional'},
  {id: 'internacional', label: 'Internacional'},
  {id: 'mineria', label: 'Minería'},
  {id: 'inmobiliario', label: 'Inmobiliario'},
];

function newsTabKey(label) {
  const found = NEWS_TABS.find(t => t.label === label || t.id === label);
  return found ? found.id : 'nacional';
}

function fmtNewsDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('es-CL', {day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'});
}

export function ExecutiveNewsPanel({newsBoard, tab, onTab}) {
  const active = newsTabKey(tab);
  const section = newsBoard?.by_category?.[active];
  const items = section?.items || [];
  const loading = newsBoard === undefined;
  return (
    <>
      <div className="subtabs">
        {NEWS_TABS.map(entry => (
          <button
            type="button"
            key={entry.id}
            className={active === entry.id ? 'on' : ''}
            onClick={() => onTab(entry.label)}
          >
            {entry.label}
          </button>
        ))}
      </div>
      {loading ? (
        <Empty title="Cargando noticias" text="Consultando fuentes verificadas de Presidencia."/>
      ) : items.length ? (
        <div className="news-list">
          {items.map(item => (
            <a
              key={item.id}
              className="news-item"
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              title={item.source}
            >
              <b>{item.title}</b>
              <small>
                {item.source || 'Fuente'}
                {' · '}
                {fmtNewsDate(item.published_at)}
              </small>
            </a>
          ))}
        </div>
      ) : (
        <Empty
          title={`${NEWS_TABS.find(t => t.id === active)?.label || tab}: sin noticias`}
          text={section?.errors?.[0]?.error || (newsBoard === null ? 'No se pudo conectar con Corporate API de noticias.' : 'No hay fuente de noticias conectada o disponible.')}
        />
      )}
      {section?.fetched_at && (
        <p className="muted-note">
          Captura {new Date(section.fetched_at).toLocaleString('es-CL')}
          {section.deduped_dropped ? ` · deduplicadas ${section.deduped_dropped}` : ''}
          {section.status ? ` · ${section.status}` : ''}
        </p>
      )}
    </>
  );
}

function alertRowClass(severidad) {
  if (severidad === 'ALTA') return 'danger';
  if (severidad === 'MEDIA') return 'warn';
  return '';
}

function alertMark(severidad, tipo) {
  if (severidad === 'ALTA') return '!';
  if (tipo && String(tipo).includes('HUMAN_GATE')) return 'A';
  return 'i';
}

export function ExecutiveAlertsPanel({alertsBoard, openCase, navigate}) {
  const loading = alertsBoard === undefined;
  const rows = (alertsBoard?.alerts || []).filter(a => a.estado === 'ACTIVA' || a.estado === 'ATENDIDA');

  const openAlert = (alert) => {
    const accion = alert?.accion || {};
    if (accion.kind === 'case' && openCase) {
      openCase({floor_id: accion.floor_id, case_id: accion.case_id});
      return;
    }
    if (accion.kind === 'expediente' && navigate && accion.expediente_id) {
      navigate('ExpedienteCorporativo', accion.expediente_id);
      return;
    }
    if (accion.kind === 'board' && navigate && accion.board_session_id) {
      navigate('BoardSession', accion.board_session_id);
      return;
    }
    if (accion.kind === 'communication' && navigate) {
      navigate('Comunicaciones', accion.communication_id);
      return;
    }
    if (accion.kind === 'config' && navigate) {
      navigate(accion.route || 'Configuracion');
      return;
    }
    if (accion.kind === 'url' && accion.url) {
      window.open(accion.url, '_blank', 'noopener,noreferrer');
      return;
    }
    if (accion.kind === 'source' && navigate) {
      navigate(accion.route || 'Inicio');
    }
  };

  if (loading) {
    return <Empty title="Cargando alertas" text="Evaluando reglas determinísticas sobre datos reales."/>;
  }
  if (alertsBoard === null) {
    return <Empty title="Alertas no disponibles" text="No se pudo consultar el motor de alertas ejecutivas."/>;
  }
  if (!rows.length) {
    return <Empty title="Sin alertas activas" text="No hay Human Gates, vencimientos ni señales activas materializadas."/>;
  }
  return (
    <div className="alert-list">
      {rows.map(alert => (
        <button
          type="button"
          className={`alert-row ${alertRowClass(alert.severidad)}`.trim()}
          key={alert.alert_id}
          onClick={() => openAlert(alert)}
        >
          <span className="alert-mark">{alertMark(alert.severidad, alert.tipo)}</span>
          <span>
            <b>{alert.titulo}</b>
            <small>
              {alert.severidad}
              {' · '}
              {alert.tipo}
              {alert.entidad ? ` · ${alert.entidad}` : ''}
              {alert.expediente_id ? ` · ${alert.expediente_id}` : ''}
            </small>
          </span>
        </button>
      ))}
    </div>
  );
}

export function EmptyState({title, text}) {
  return <Empty title={title} text={text}/>;
}

/** Shared executive hero for Holding surfaces. */
export function ExecHero({
  breadcrumb = 'LNH',
  title,
  subtitle,
  quote,
  image,
  logo,
  brandLogo,
  aside,
  pillars,
  className = '',
}) {
  return (
    <section className={`exec-hero ${className}`.trim()}>
      <div className="exec-hero-media" style={image ? {backgroundImage: `url(${image})`} : undefined} aria-hidden="true"/>
      <div className="exec-hero-shade"/>
      <div className="exec-hero-copy">
        {breadcrumb && <small>{breadcrumb}</small>}
        {brandLogo
          ? <img src={brandLogo} alt="" className="exec-hero-brand-logo"/>
          : (title ? <h1>{title}</h1> : null)}
        {subtitle && <p className="exec-hero-sub">{subtitle}</p>}
        {aside}
      </div>
      {(quote || logo || pillars) && (
        <div className="exec-hero-aside">
          {logo && <img src={logo} alt="" className="exec-hero-logo"/>}
          {pillars && (
            <ul className="exec-hero-pillars">
              {pillars.map(p => <li key={p}>{p}</li>)}
            </ul>
          )}
          {quote && <blockquote>{quote}</blockquote>}
        </div>
      )}
    </section>
  );
}
