def review(report:str)->list[str]:
    required=('Resultado','Qué se analizó','Qué está demostrado','Información declarada','Pendiente de verificar','Riesgos','Acciones recomendadas','Decisión recomendada')
    return [f'Sección ausente: {name}' for name in required if name not in report]
