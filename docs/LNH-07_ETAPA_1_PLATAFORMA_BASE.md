# LNH-07 — Etapa 1: Plataforma Base

La plataforma base es local y reutilizable. Mantiene Holding → Company → Department, agentes por capacidades, misiones, estados de caso, evidencia, gate humano, observabilidad y un gateway de inferencia desacoplado.

MGC-05 es el primer departamento registrado. AGIA-MGC-014, 015 y 016 se registran sólo como capacidades operacionales: no se reconstruyen ni se invocan durante los tests de plataforma.

`MockInferenceGateway` es el único gateway usado por las pruebas. No utiliza GPU, Vast, APIs, servicios pagados ni dependencias de Codex en runtime. `CorporateAPI` es una fachada Python local sin exposición de red; el transporte queda fuera de Etapa 1.
