"""AGIA-MGC-007 — Investigador IA de Mercado y Competencia Minera."""

from .agent import run
from .profile import AGENT_ID, OFFICIAL_PROFILE, register

__all__ = ("AGENT_ID", "OFFICIAL_PROFILE", "register", "run")
