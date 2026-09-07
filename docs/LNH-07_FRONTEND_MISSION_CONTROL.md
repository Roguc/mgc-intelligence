# LNH Mission Control — frontend corporativo

Mission Control conserva los expedientes, Human Gate, gerentes de piso e
Inference Gateway existentes. La capa de presentación se organiza en Mi
Oficina, Holding, Empresas y Operación, con navegaciones separadas para
empresa, piso, misión, evidencia y reportes.

La interfaz presenta exclusivamente datos materializados por los pisos. Las
integraciones de correo y calendario se identifican como `No conectado`; las
capacidades que aún no tienen backend se presentan como `No disponible` o
`Pendiente de implementación`.

El sistema visual se compone de sidebar corporativo, cabecera ejecutiva,
breadcrumbs, tarjetas de estado, tablas de evidencia, tabs de expediente y
paneles de Human Gate. No sustituye el criterio de los gerentes ni crea datos,
resultados, actividad, herramientas o decisiones inexistentes.
