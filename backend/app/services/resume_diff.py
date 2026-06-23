"""
Resume Diff — Feature 2.
Compares original vs optimized resume and categorises changes.
"""
from __future__ import annotations


def generate_diff(resume_data: dict, optimized: dict) -> dict:
    """
    Generate a structured diff with ADDED / REMOVED / REORDERED / REWRITTEN categories.
    Reads the changes list already computed by the optimizer.
    """
    changes = list(optimized.get("changes", []))

    added = [c for c in changes if c.get("type") == "ADDED"]
    removed = [c for c in changes if c.get("type") == "REMOVED"]
    reordered = [c for c in changes if c.get("type") == "REORDERED"]
    rewritten = [c for c in changes if c.get("type") == "REWRITTEN"]

    return {
        "added": added,
        "removed": removed,
        "reordered": reordered,
        "rewritten": rewritten,
        "total_changes": len(changes),
        "has_changes": bool(changes),
        "summary": _build_summary(added, removed, reordered, rewritten),
    }


def _build_summary(added, removed, reordered, rewritten) -> str:
    parts = []
    if reordered:
        parts.append(f"{len(reordered)} section(s) reordered")
    if rewritten:
        parts.append(f"{len(rewritten)} bullet(s) rewritten")
    if added:
        parts.append(f"{len(added)} item(s) added")
    if removed:
        parts.append(f"{len(removed)} item(s) removed")
    return "; ".join(parts) if parts else "No changes"
