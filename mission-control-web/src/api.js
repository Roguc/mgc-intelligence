const base = (floor, id) => `/cases/${encodeURIComponent(floor)}/${encodeURIComponent(id)}`;
async function request(path, payload, signal) {
  let response;
  try {
    response = await fetch(`/api${path}`, payload === undefined ? {signal} : {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload), signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('No se pudo conectar con Corporate API. Puede actualizar para consultar el estado antes de reintentar.');
  }
  const data = await response.json().catch(() => ({error: 'Corporate API devolvió una respuesta no válida.'}));
  if (!response.ok || data.error) throw new Error(data.error || `Error ${response.status}`);
  return data;
}
export const get = (path, signal) => request(path, undefined, signal);
export const hierarchy = () => get('/corporate/hierarchy');
export const cases = () => get('/cases');
export const health = () => get('/health');
export const createCase = (mission, floor_id, documents = []) => request('/cases', {mission, floor_id, documents});
export const createCorporateExpediente = payload => request('/corporate/expedientes', payload);
export const corporateExpedientes = () => get('/corporate/expedientes');
export const corporateExpediente = (id, signal) => get(`/corporate/expedientes/${encodeURIComponent(id)}`, signal);
export const corporateExpedienteEvents = (id, signal) => get(`/corporate/expedientes/${encodeURIComponent(id)}/events`, signal);
export const corporateAgents = () => get('/corporate/agents');
export const corporateAreas = () => get('/corporate/areas');
export const boardSessions = () => get('/corporate/board-sessions');
export const boardSession = (id, signal) => get(`/corporate/board-sessions/${encodeURIComponent(id)}`, signal);
export const createBoardSession = payload => request('/corporate/board-sessions', payload);
export const updateBoardSession = (id, payload) => request(`/corporate/board-sessions/${encodeURIComponent(id)}`, payload);
export const prepareBoardSession = (id, payload = {}) => request(`/corporate/board-sessions/${encodeURIComponent(id)}/prepare`, payload);
export const freezeBoardSession = (id, payload = {}) => request(`/corporate/board-sessions/${encodeURIComponent(id)}/freeze`, payload);
export const deliberateBoardSession = (id, payload = {}) => request(`/corporate/board-sessions/${encodeURIComponent(id)}/deliberate`, payload);
export const consolidateBoardSession = (id, payload = {}) => request(`/corporate/board-sessions/${encodeURIComponent(id)}/consolidate`, payload);
export const boardHumanGate = (id, payload) => request(`/corporate/board-sessions/${encodeURIComponent(id)}/human-gate`, payload);
export const reopenCorporateExpediente = (id, payload) => request(`/corporate/expedientes/${encodeURIComponent(id)}/reopen`, payload);
export const executeCorporateTask = (expedienteId, taskId, payload = {}) =>
  request(`/corporate/expedientes/${encodeURIComponent(expedienteId)}/tasks/${encodeURIComponent(taskId)}/execute`, payload);
export const corporateResults = (id, signal) => get(`/corporate/expedientes/${encodeURIComponent(id)}/results`, signal);
export const corporateSessions = (id, signal) => get(`/corporate/expedientes/${encodeURIComponent(id)}/sessions`, signal);

function qs(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    if (Array.isArray(value)) value.forEach(v => search.append(key, v));
    else search.set(key, value);
  });
  const s = search.toString();
  return s ? `?${s}` : '';
}

export const calendarEvents = (params = {}, signal) => get(`/corporate/calendar/events${qs(params)}`, signal);
export const calendarEvent = (id, signal) => get(`/corporate/calendar/events/${encodeURIComponent(id)}`, signal);
export const createCalendarEvent = payload => request('/corporate/calendar/events', payload);
export const updateCalendarEventStatus = (id, payload) =>
  request(`/corporate/calendar/events/${encodeURIComponent(id)}/status`, payload);

export const communications = (params = {}, signal) => get(`/corporate/communications${qs(params)}`, signal);
export const communication = (id, signal) => get(`/corporate/communications/${encodeURIComponent(id)}`, signal);
export const createCommunication = payload => request('/corporate/communications', payload);
export const syncEmailPull = (payload = {}) => request('/corporate/communications/sync/pull', payload);
export const linkCommunicationExpediente = (id, payload) =>
  request(`/corporate/communications/${encodeURIComponent(id)}/link-expediente`, payload);
export const markCommunicationRead = (id, payload = {}) =>
  request(`/corporate/communications/${encodeURIComponent(id)}/read`, payload);

export const notificationsBoard = (params = {}, signal) => get(`/corporate/notifications${qs(params)}`, signal);
export const markNotificationRead = (id, payload = {}) =>
  request(`/corporate/notifications/${encodeURIComponent(id)}/read`, payload);
export const archiveNotification = (id, payload = {}) =>
  request(`/corporate/notifications/${encodeURIComponent(id)}/archive`, payload);
export const createNotification = payload => request('/corporate/notifications', payload);

export const expedienteCalendarEvents = (id, signal) =>
  get(`/corporate/expedientes/${encodeURIComponent(id)}/calendar-events`, signal);
export const expedienteCommunications = (id, signal) =>
  get(`/corporate/expedientes/${encodeURIComponent(id)}/communications`, signal);
export const expedienteNotifications = (id, signal) =>
  get(`/corporate/expedientes/${encodeURIComponent(id)}/notifications`, signal);

export const providersStatus = (signal) => get('/corporate/providers', signal);
export const runF2bSync = (payload = {}) => request('/corporate/f2b-sync', payload);
export const executiveBoard = (params = {}, signal) => get(`/corporate/executive/board${qs(params)}`, signal);
export const executiveNews = (params = {}, signal) => get(`/corporate/executive/news${qs(params)}`, signal);
export const executiveAlerts = (params = {}, signal) => get(`/corporate/executive/alerts${qs(params)}`, signal);
export const scanExecutiveAlerts = (payload = {}) => request('/corporate/executive/alerts/scan', payload);
export const setExecutiveAlertState = (id, payload) =>
  request(`/corporate/executive/alerts/${encodeURIComponent(id)}/state`, payload);
export const refreshExecutiveBoard = (payload = {}) => request('/corporate/executive/refresh', payload);
export const syncCalendarEvent = (id, payload = {}) =>
  request(`/corporate/calendar/events/${encodeURIComponent(id)}/sync`, payload);
export const submitCommunicationApproval = (id, payload = {}) =>
  request(`/corporate/communications/${encodeURIComponent(id)}/submit-approval`, payload);
export const communicationHumanGate = (id, payload) =>
  request(`/corporate/communications/${encodeURIComponent(id)}/human-gate`, payload);
export const sendCommunication = (id, payload = {}) =>
  request(`/corporate/communications/${encodeURIComponent(id)}/send`, payload);

export const caseDetail = (floor, id, version, signal) => get(`${base(floor,id)}${version ? `?version=${encodeURIComponent(version)}` : ''}`, signal);
export const executeCase = (floor, id, expected_version) => request(`${base(floor,id)}/execute`, {expected_version});
export const humanGate = (floor, id, decision, rationale, expected_version) => request(`${base(floor,id)}/human-gate`, {decision, rationale, expected_version});
export const artifactUrl = (floor,id,path) => `/api${base(floor,id)}/artifact?path=${encodeURIComponent(path)}`;
export const encodeFile = file => new Promise((resolve,reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve({name:file.name,content:reader.result.split(',')[1]});
  reader.onerror = () => reject(new Error(`No se pudo leer ${file.name}.`));
  reader.readAsDataURL(file);
});
