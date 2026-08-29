"""Internal PMO data model. Missing values remain unknown; they are never inferred."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Task:
    name: str
    owner: Optional[str] = None
    start_date: Optional[date] = None
    target_date: Optional[date] = None
    actual_date: Optional[date] = None
    status: Optional[str] = None
    progress: Optional[float] = None
    dependencies: list[str] = field(default_factory=list)
    blocker: Optional[str] = None
    evidence: Optional[str] = None
    source: Optional[str] = None


@dataclass
class Alert:
    level: str
    message: str
    task: Optional[str] = None


@dataclass
class ProjectAnalysis:
    tasks: list[Task] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    declared: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    critical_path: Optional[list[str]] = None
    critical_path_reason: Optional[str] = None
    deviations: list[str] = field(default_factory=list)
    recovery_actions: list[str] = field(default_factory=list)
