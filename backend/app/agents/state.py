"""Shared LangGraph state. Node names never collide with these keys."""
from typing import Any, TypedDict


class CaseState(TypedDict, total=False):
    project: dict
    files: list
    output_dir: str
    engine: str
    evidence: list          # every citable sentence / table row with its source
    warnings: list
    documents: list
    timeline: list
    undated: list
    scope_changes: list
    span: Any
    kpis: list
    privacy: dict
    versions: list
    quotes: list
    assets: list
    approval_pack: dict
    approval_items: list
    validation: dict
