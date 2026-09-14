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
