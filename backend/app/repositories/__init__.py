"""All SQL lives here, and this is the only place the tenant filter lives (D1, ADR-0001).

Callers import from the submodules; nothing is re-exported so parallel work never shares this file.
"""
