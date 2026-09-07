# LNH-07 — Alibaba Cloud Model Studio

Mission Control usa el Gateway de inferencia existente. Para seleccionar Alibaba
Model Studio, configure sólo variables de entorno del proceso que inicia Mission
Control; no cree archivos `.env` versionados ni ingrese secretos en la interfaz.

| Variable | Uso |
| --- | --- |
| `MGC_INFERENCE_PROVIDER` | `alibaba` |
| `MGC_ALIBABA_API_KEY` | API key regional de Model Studio |
| `MGC_ALIBABA_BASE_URL` | API host de Singapore, con terminación `/compatible-mode/v1` |
| `MGC_ALIBABA_MODEL` | Modelo habilitado en el workspace; por defecto `qwen-plus` |

Para Singapore (`ap-southeast-1`), use el host OpenAI-compatible informado por
Model Studio para el workspace: `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`.
El health check sólo consulta `GET /models`; no genera tokens ni ejecuta una
misión. Las credenciales nunca se registran en trazas, Git, logs ni frontend.
