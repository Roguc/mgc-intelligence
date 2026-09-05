# LNH-07 Etapa 5 — ciclo de vida de Mission Control

El acceso directo existente conserva su destino: `scripts/start_mission_control.ps1`.

Antes de reutilizar Streamlit, el lanzador calcula una huella de `app.py`,
`mission_control.py` y `mgc_05/backend.py`. La huella y el PID se guardan en
`outputs/mission_control_runtime.json`, que es estado local ignorado por Git.

Si una instancia escucha en el puerto 8501 pero su huella no coincide (o el
estado no permite asociarla de forma segura), el lanzador sólo detiene el
proceso Streamlit validado de Mission Control y lo inicia de nuevo. Un proceso
ajeno que use el puerto no se termina: el lanzador informa el bloqueo.

Con una huella y PID coincidentes reutiliza la única instancia existente.
