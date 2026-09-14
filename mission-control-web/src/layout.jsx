import React, {useEffect, useMemo, useState} from 'react';
import {Logo, Icon} from './icons';
import {Notice} from './components';

const NAV = [
  ['MI OFICINA', [
    ['Inicio', 'home'],
    ['Decisiones', 'decisions'],
    ['NuevaInstruccion', 'instruction', 'Nueva Instrucción'],
    ['Calendario', 'calendar'],
    ['Comunicaciones', 'communications'],
  ]],
  ['HOLDING', [
    ['Holding', 'holding', 'Visión General'],
    ['Directorio', 'users'],
    ['CorporateOffice', 'office', 'Corporate Office'],
    ['Areas', 'floors', 'Áreas Corporativas'],
  ]],
  ['EMPRESAS', 'companies'],
  ['SISTEMA', [
    ['Configuracion', 'settings', 'Configuración'],
  ]],
];

const aliases = {
  'Inicio CEO': 'Inicio',
  'Holding corporativo': 'Holding',
  Correo: 'Comunicaciones',
  'Calendario y agenda': 'Calendario',
  Configuración: 'Configuracion',
  Empresas: 'Holding',
  Pisos: 'Holding',
  Misiones: 'Inicio',
  Evidencia: 'Inicio',
  Conocimiento: 'Configuracion',
  Reportes: 'Inicio',
};

function activeItem(page) {
  const raw = aliases[page] || page;
  if (raw === 'Empresa' || raw === 'Piso' || raw === 'Instrucción') return 'companies';
  if (raw === 'case') return 'Decisiones';
  if (raw === 'Area') return 'Areas';
  return raw;
}

export function Shell({page, navigate, refresh, crumbs, error, children, companies = [], query, setQuery, noticeCount = 0, routeTarget = ''}) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(t);
  }, []);
  const current = activeItem(page);
  const groups = useMemo(() => NAV.map(entry => {
    if (entry[1] === 'companies') {
      return ['EMPRESAS', companies.map(c => [c.id, 'company', c.name, () => navigate('Empresa', c.id)])];
    }
    return entry;
  }), [companies]);

  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <Logo/>
          <div>
            <b>LNH</b>
            <small>Latitud Norte Holding</small>
          </div>
        </div>
        {groups.map(([group, items]) => (
          <div className="nav" key={group}>
            <label>{group}</label>
            {items.map(([name, icon, label, go]) => {
              const isCompany = typeof go === 'function';
              const active = isCompany ? page === 'Empresa' && routeTarget === name : current === name;
              return (
                <button
                  type="button"
                  className={active ? 'active' : ''}
                  aria-current={active ? 'page' : undefined}
                  key={name}
                  onClick={() => { (go || (() => navigate(name)))(); refresh(); }}
                >
                  <Icon name={icon}/>
                  <span>{label || name}</span>
                </button>
              );
            })}
          </div>
        ))}
        <footer>Presidencia · Gobierno LNH. Las misiones empresariales se crean dentro de cada empresa y piso.</footer>
      </aside>
      <div className="workspace-frame">
        <header>
          <nav className="crumb header-crumb" aria-label="Ubicación">{crumbs}</nav>
          <label className="global-search">
            <Icon name="search"/>
            <input
              type="search"
              placeholder="Buscar en todo el sistema…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              aria-label="Buscar en Mission Control"
            />
          </label>
          <button type="button" className="icon-btn" aria-label="Notificaciones" onClick={() => navigate('Decisiones')}>
            <Icon name="bell"/>
            {noticeCount > 0 && <em>{noticeCount}</em>}
          </button>
          <time dateTime={now.toISOString()}>{now.toLocaleString('es-CL', {day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit'})}</time>
          <div className="profile" title="Sesión local de Presidencia">
            <span className="avatar">VP</span>
            <span>
              <b>Presidencia LNH</b>
              <small>Sesión local</small>
            </span>
          </div>
        </header>
        <main>
          <Notice error>{error}</Notice>
          {children}
        </main>
      </div>
    </div>
  );
}
