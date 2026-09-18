# Inventario del motor operativo MGC-03 — LNH gobierno + OpenAI Platform

## Flujo productivo
Mission Control → web_api → facade → governance/case → PlatformGateway → GER en OpenAI Platform → especialistas/tools en Platform → gateway → ingest → expediente → documentos/versiones → Human Gate → UI

## A. GOVERNANCE
- `facade.py`, `presentation.py` (authorize), `catalog.py`, `floor.py` (IDs de configuración)

## B. CASE / DATA
- `mission.py`, `store.py`, `persist.py`, `progress.py`, `archive.py`, `contracts.py`

## C. PLATFORM GATEWAY
- `platform.py` (`PlatformGateway`)

## D. RESULT INGESTION
- `ingest.py`, `classify.py`, `artifacts.py`, `evidence.py`

## E. HUMAN GATE
- `gate.py`

## F. DOCUMENT / VERSIONING
- `publish.py`, `pack.py`

## G. AUDIT / ECONOMY
- `audit.py`

## H. PRESENTATION CONTRACTS
- `presentation.py` `case_view`, `catalog.py`, adapters UI/HTTP

## ELIMINADO DEL RUNTIME
- `workstream.py`, `jsonutil.py`
- orquestación LNH de especialistas (`execute_specialist`, `ThreadPoolExecutor`, `PLAN_CONTRACT`)
- Alibaba/Ollama como motor (stubs retirados que no generan)

## ADAPTERS
- `corporate/web_api.py`, `corporate_api_server.py`, `corporate_mission_control.py`, `app.py`
