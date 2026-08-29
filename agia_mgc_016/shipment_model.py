from dataclasses import dataclass, field


@dataclass
class Alert:
    level: str
    message: str


@dataclass
class Shipment:
    fields: dict[str, str] = field(default_factory=dict)
    documents: dict[str, str] = field(default_factory=dict)
    incidents: list[str] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
