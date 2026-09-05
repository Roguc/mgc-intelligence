# LNH-07 Etapa 5 — transporte privado Tailscale

Mission Control consume exclusivamente la identidad privada `lnh-mgc-qwen` de
la tailnet. No contiene API de Vast, IP pública, endpoint dinámico, SSH ni
túneles. El appliance remoto se instala una vez con Tailscale, Ollama y
Qwen3 14B; al encender Vast recupera esos servicios automáticamente.

La ACL de la tailnet permite sólo PC LNH → appliance:11434. Ollama no tiene
puerto público. Mission Control muestra únicamente red privada no disponible,
preparando motor de inteligencia o motor listo.
