from .analyzer import Analysis

def bullet(items): return '\n'.join(f'- {x}' for x in items)
def build_report(mission:str, analysis:Analysis)->str:
    recommendation='AVANZAR CONDICIONADO' if analysis.pending[0]!='No informado en los documentos.' else 'INFORMACIÓN INSUFICIENTE'
    return f'''# Informe profesional — AGIA-MGC-015

## Resultado

**{recommendation}**

## Qué se analizó

{mission}

## Qué está demostrado

{bullet(analysis.documented)}

## Información declarada

{bullet(analysis.declared)}

## Pendiente de verificar

{bullet(analysis.pending)}

## Riesgos

{bullet(analysis.risks)}

## Acciones recomendadas

{bullet(analysis.actions)}

## Trazabilidad documental

{bullet(analysis.sources or ['No se adjuntaron documentos.'])}

## Decisión recomendada

**{recommendation}**. La aprobación final requiere revisión humana; este informe no autoriza producción.
'''
