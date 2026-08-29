from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .operations_analyzer import analyze
from .operations_report import build_report
from .reader import read_document
from .reviewer import review
from .shipment_parser import parse


@dataclass
class RunResult:
    report_path: Path
    review_issues: list[str]
    shipment: object


def run_with_result(mission: str, paths: list[Path], output_dir: Path) -> RunResult:
    documents = {path.name: read_document(path) for path in paths}
    shipment = analyze(parse(mission, documents))
    report = build_report(mission, shipment)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f'AGIA-MGC-016_{datetime.now().strftime("%Y%m%d%H%M%S")}.md'
    target.write_text(report, encoding='utf-8')
    return RunResult(target, review(report), shipment)


def run(mission: str, paths: list[Path], output_dir: Path):
    result = run_with_result(mission, paths, output_dir)
    return result.report_path, result.review_issues
