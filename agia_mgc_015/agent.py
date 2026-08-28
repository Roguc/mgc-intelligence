from pathlib import Path
from datetime import datetime
from .reader import read_document
from .analyzer import analyze
from .report import build_report
from .reviewer import review

def run(mission:str, paths:list[Path], output_dir:Path)->tuple[Path,list[str]]:
    docs={p.name:read_document(p) for p in paths}; report=build_report(mission,analyze(mission,docs)); issues=review(report)
    output_dir.mkdir(parents=True,exist_ok=True); target=output_dir/f'AGIA-MGC-015_{datetime.now().strftime("%Y%m%d%H%M%S")}.md'; target.write_text(report,encoding='utf-8'); return target,issues
