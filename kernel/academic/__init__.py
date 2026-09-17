"""Catálogo académico estrutural — CATÁLOGO ENCONTRA, RAG EXPLICA."""

from kernel.academic.bootstrap import AcademicState, bootstrap_academic_state
from kernel.academic.catalog import AcademicCatalog
from kernel.academic.resolver import resolve_academic_query

__all__ = [
    "AcademicCatalog",
    "AcademicState",
    "bootstrap_academic_state",
    "resolve_academic_query",
]
