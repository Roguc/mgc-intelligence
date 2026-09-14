import React, {useCallback, useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {hierarchy, cases, health} from './api';
import {Workspace} from './Workspace';
import {Shell} from './layout';
import {Cases, Empty} from './components';
import {
  Home, Holding, Companies, CompanyPage, FloorPage, Instruction, CorporateInstruction,
  Directorio, CorporateOffice, Areas, AreaView, Configuracion, Communications,
  CalendarAgenda, EvidenceCatalog, SearchResults,
} from './pages';
import {CORPORATE_AREAS} from './ui';
import './styles.css';

function readRoute() {
  try { return location.hash.replace(/^#\/?/, '').replace(/\/+$/, '').split('/').map(decodeURIComponent); }
  catch { return ['Inicio']; }
}
export function navigate(...parts) {
  location.hash = '/' + parts.filter(x => x !== undefined && x !== null && x !== '').map(x => encodeURIComponent(x)).join('/');
}

const HOME = new Set(['', 'Inicio', 'Inicio CEO']);
const HOLDING = new Set(['Holding', 'Holding corporativo']);

function App() {
  const [route, setRoute] = useState(readRoute);
  const [data, setData] = useState();
  const [list, setList] = useState([]);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [page = 'Inicio', target, id, tab, version] = route;

  useEffect(() => {
    const update = () => setRoute(readRoute());
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);

  const refresh = useCallback(() => cases().then(rows => { setList(rows); setError(''); }).catch(e => setError(e.message)), []);
  const load = useCallback(() => {
    setError('');
    Promise.all([hierarchy(), cases(), health()]).then(([a, b, h]) => {
      if (!h.workspace_api) throw new Error('La Corporate API activa requiere reiniciarse para cargar el workspace actualizado.');
      setData(a);
      setList(b);
    }).catch(e => setError(e.message));
  }, []);
  useEffect(load, [load]);

  const floor = data?.floors.find(f => f.id === target);
  const company = data?.companies.find(c => c.id === target);
  const openCase = c => navigate('case', c.floor_id, c.case_id, 'Resumen');
  const openFloor = floorId => navigate('Piso', floorId);
  const work = list.filter(c => c.floor_id === target);
  const reviewCount = list.filter(x => x.requires_decision).length;

  let content;
  if (!data) {
    content = (
      <>
        <Empty title={error ? 'Corporate API no disponible' : 'Cargando Mission Control'} text={error || 'Consultando datos corporativos materializados.'}/>
        <button type="button" className="primary" onClick={load}>Reintentar conexión</button>
      </>
    );
  } else if (HOME.has(page)) {
    content = (
      <>
        <Home data={data} list={list} openCase={openCase} navigate={navigate}/>
        <SearchResults query={query} list={list} floors={data.floors} companies={data.companies} openCase={openCase} navigate={navigate}/>
      </>
    );
  } else if (page === 'Comunicaciones' || page === 'Correo') {
    content = <Communications list={list} openCase={openCase}/>;
  } else if (page === 'Calendario' || page === 'Calendario y agenda') {
    content = <CalendarAgenda/>;
  } else if (page === 'Decisiones') {
    content = (
      <>
        <section className="page-head">
          <small>MI OFICINA</small>
          <h1>Decisiones</h1>
          <p>Human Gate y pendientes reales. La decisión se registra dentro del expediente del piso.</p>
        </section>
        <Cases rows={list.filter(x => x.requires_decision)} emptyTitle="Sin decisiones humanas pendientes" emptyText="No hay un consolidado profesional listo para APROBAR en este momento." open={openCase}/>
      </>
    );
  } else if (page === 'NuevaInstruccion') {
    content = <CorporateInstruction cancel={() => navigate('Inicio')}/>;
  } else if (HOLDING.has(page)) {
    content = <Holding companies={data.companies} floors={data.floors} list={list} enter={cid => navigate('Empresa', cid)} navigate={navigate}/>;
  } else if (page === 'Directorio') {
    content = <Directorio list={list} openCase={openCase}/>;
  } else if (page === 'CorporateOffice') {
    content = <CorporateOffice/>;
  } else if (page === 'Areas') {
    content = <Areas navigate={navigate}/>;
  } else if (page === 'Area') {
    const area = CORPORATE_AREAS.find(a => a.id === target) || CORPORATE_AREAS[2];
    content = <AreaView code={area.code} title={area.name} summary={`Área corporativa ${area.name}. Agente IA pendiente de habilitación.`} list={[]} openCase={openCase}/>;
  } else if (page === 'Empresa' && company) {
    content = (
      <CompanyPage
        company={company}
        floors={data.floors}
        work={list.filter(c => data.floors.some(f => f.company === company.id && f.id === c.floor_id))}
        openFloor={openFloor}
        instruct={floorId => navigate('Instrucción', floorId)}
      />
    );
  } else if (page === 'Piso' && floor) {
    content = <FloorPage floor={floor} work={work} openCase={openCase} instruct={() => navigate('Instrucción', floor.id)}/>;
  } else if (page === 'Instrucción' && floor) {
    content = (
      <Instruction
        key={floor.id}
        floor={floor}
        company={data.companies.find(c => c.id === floor.company)}
        cancel={() => navigate('Piso', floor.id)}
        created={c => { openCase(c); refresh(); }}
      />
    );
  } else if (page === 'Configuracion' || page === 'Configuración') {
    content = <Configuracion data={data}/>;
  } else if (page === 'Misiones') {
    content = (
      <>
        <section className="page-head"><small>EXPEDIENTES</small><h1>Misiones empresariales</h1><p>Supervisión transversal. La creación se realiza en Empresa → Piso.</p></section>
        <Cases rows={list} open={openCase}/>
      </>
    );
  } else if (page === 'Evidencia') {
    content = <EvidenceCatalog list={list} openCase={openCase}/>;
  } else if (page === 'case' && floor && id) {
    content = <Workspace key={`${floor.id}/${id}`} floor={floor} id={id} tab={tab} version={version} navigate={navigate} onChange={refresh}/>;
  } else {
    content = <Empty title="Página no encontrada" text="Seleccione una sección desde la navegación."/>;
  }

  const crumbs = (
    <>
      <button type="button" onClick={() => navigate('Inicio')}>LNH</button>
      {HOLDING.has(page) && <> › Holding</>}
      {page === 'Directorio' && <> › Directorio</>}
      {page === 'Areas' && <> › Áreas Corporativas</>}
      {page === 'NuevaInstruccion' && <> › Nueva Instrucción</>}
      {page === 'Configuracion' && <> › Configuración</>}
      {company && page === 'Empresa' && <> › <button type="button" onClick={() => navigate('Empresa', company.id)}>{company.name}</button></>}
      {floor && <> › <button type="button" onClick={() => navigate('Empresa', floor.company)}>{floor.company}</button> › <button type="button" onClick={() => navigate('Piso', floor.id)}>{floor.id}</button></>}
      {page === 'case' && <> › Expediente</>}
      {page === 'Instrucción' && <> › Nueva misión</>}
      {['Decisiones', 'Comunicaciones', 'Calendario'].includes(page) && !floor && <> › {page}</>}
    </>
  );

  return (
    <Shell page={page} navigate={navigate} refresh={refresh} crumbs={crumbs} error={data ? error : ''} companies={data?.companies || []} query={query} setQuery={setQuery} noticeCount={reviewCount} routeTarget={target || ''}>
      {content}
    </Shell>
  );
}

createRoot(document.getElementById('root')).render(<App/>);
