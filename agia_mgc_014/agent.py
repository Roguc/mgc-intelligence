"""AGIA-MGC-014 local orchestration."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .critical_path import calculate_critical_path
from .dependency_analyzer import analyze_dependencies
from .deviation_analyzer import analyze_deviations
from .milestone_analyzer import analyze_milestones
from .pmo_report import build_report
from .project_model import ProjectAnalysis
from .project_parser import parse_tasks
from .reader import read_document
from .recovery_planner import propose_recovery
from .reviewer import review
from .risk_analyzer import analyze_risks_and_issues


@dataclass
class RunResult:
    report_path: Path
    review_issues: list[str]
    analysis: ProjectAnalysis


def analyze(mission: str, paths: list[Path]) -> ProjectAnalysis:
    documents = {path.name: read_document(path) for path in paths}
    tasks = parse_tasks(mission, documents)
    analysis = ProjectAnalysis(tasks=tasks, sources=list(documents))
    analysis.alerts.extend(analyze_milestones(tasks))
    analysis.alerts.extend(analyze_dependencies(tasks))
    analysis.critical_path, analysis.critical_path_reason = calculate_critical_path(tasks)
    analysis.deviations = analyze_deviations(tasks)
    analysis.risks, analysis.issues, analysis.declared = analyze_risks_and_issues(mission, documents)
    if not tasks:
        analysis.assumptions.append('No se informaron tareas o hitos en formato estructurado; no se infirieron fechas, responsables ni duraciones.')
    if any(not task.owner for task in tasks):
        analysis.assumptions.append('Los responsables faltantes requieren confirmación humana.')
    if any(not task.target_date for task in tasks):
        analysis.assumptions.append('Las fechas objetivo faltantes requieren confirmación humana.')
    analysis.recovery_actions = propose_recovery(analysis.deviations, analysis.alerts)
    return analysis


def run_with_result(mission: str, paths: list[Path], output_dir: Path) -> RunResult:
    analysis = analyze(mission, paths)
    report = build_report(mission, analysis)
    issues = review(report)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f'AGIA-MGC-014_{datetime.now().strftime("%Y%m%d%H%M%S")}.md'
    target.write_text(report, encoding='utf-8')
    return RunResult(target, issues, analysis)


def run(mission: str, paths: list[Path], output_dir: Path) -> tuple[Path, list[str]]:
    result = run_with_result(mission, paths, output_dir)
    return result.report_path, result.review_issues
