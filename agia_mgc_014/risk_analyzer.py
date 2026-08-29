"""Classify explicit risks and issues from supplied text."""

import re


def analyze_risks_and_issues(mission: str, documents: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    risks, issues, declared = [], [], []
    for source, text in {'Instrucción humana': mission, **documents}.items():
        for line in text.splitlines():
            clean = line.strip(' -•\t')
            if not clean:
                continue
            lower = clean.casefold()
            if re.search(r'\b(riesgo|risk)\b', lower):
                risks.append(f'{source}: {clean}')
            if re.search(r'\b(issue|incidente|problema|bloqueo|vencid[oa])\b', lower):
                issues.append(f'{source}: {clean}')
            if re.search(r'\b(declara|afirma|reporta|indica|según)\b', lower):
                declared.append(f'{source}: {clean}')
    return risks, issues, declared
