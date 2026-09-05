# LNH-07 Etapa 5 — cómputo remoto autónomo

Mission Control usa una única ruta: `remote_compute.RemoteComputeLifecycle`.
Al abrirse o al despachar una misión, consulta la API autenticada de Vast para
descubrir el endpoint SSH vigente; no conserva IP ni puerto de una instancia
anterior. El token se lee únicamente desde `LNH_VAST_API_KEY` y el identificador
opcional desde `LNH_VAST_INSTANCE_ID`; ninguno se guarda en el repositorio.

La clave SSH dedicada ya existente se usa con un archivo de hosts conocido
exclusivo de LNH. `StrictHostKeyChecking=accept-new` acepta solamente un host
nuevo y conserva su huella; un cambio posterior se rechaza. Ollama permanece
ligado al loopback remoto y el único transporte es el túnel privado local.

La interfaz muestra sólo estados ejecutivos: motor listo, preparando motor o
cómputo remoto no disponible/inicie Vast. Los detalles se conservan para
diagnóstico interno. El ciclo tiene timeout y reintentos acotados; no realiza
inferencia durante verificaciones ni instala software en este equipo.
