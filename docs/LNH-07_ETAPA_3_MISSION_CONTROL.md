# LNH-07 — Etapa 3: Frontend Mission Control

Mission Control es la interfaz local Streamlit de LNH para el flujo Holding → Empresa → Departamento → Misión. Expone MGC-05, permite cargar evidencia, crear expediente, ejecutar el backend existente, consultar plan/resultados/evidencia/contradicciones y registrar Human Gate.

No simula estados: los datos se leen de los artefactos reales del Case Manager. La ejecución mantiene las restricciones del backend; si el motor no está disponible, se muestra su bloqueo. La apariencia usa fondo cálido claro, piedra, beige y verde sage.

La navegación lateral presenta vistas funcionales de Inicio, Empresas, Pisos, Agentes, Misiones y Evidencia. Los estados se traducen a lenguaje ejecutivo; JSON, plan y logs permanecen como descargas técnicas. Un bloqueo de infraestructura declara expresamente que todavía no existe informe profesional ni resultado aprobable.
