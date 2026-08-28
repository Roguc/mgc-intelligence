from dataclasses import dataclass

@dataclass
class Analysis:
    documented:list[str]; declared:list[str]; pending:list[str]; risks:list[str]; actions:list[str]; sources:list[str]

def analyze(instruction:str, documents:dict[str,str]) -> Analysis:
    text=(instruction+'\n'+'\n'.join(documents.values())).lower()
    documented=['Se recibió la misión y los documentos indicados por el usuario.']
    declared=[]; pending=[]; risks=[]; actions=[]
    for marker,label in [('declara','Información aportada por una parte'),('afirma','Información aportada por una parte'),('no existe','No existe evidencia documental suficiente'),('no ha sido verificada','No ha sido verificada independientemente')]:
        if marker in text: (declared if label.startswith('Información') else pending).append(label+'.')
    if pending:
        risks.append('Avanzar sin validación puede generar decisiones inconsistentes o compromisos sin respaldo documental.')
        actions.append('Solicitar y verificar la documentación pendiente antes de formalizar el proceso u operación.')
    return Analysis(documented,declared or ['No informado en los documentos.'],pending or ['No informado en los documentos.'],risks or ['No se identificó un riesgo específico con la información disponible.'],actions or ['Revisión humana de los hallazgos antes de actuar.'],list(documents))
