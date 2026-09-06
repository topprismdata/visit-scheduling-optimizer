# prism-ontology — Phase 0 Independent Skeleton

**Status:** Phase 0 DESIGN (per v1.1 §9 — CLI + EAC skeleton only, no business objects)

## Independence Requirement (v1.1 §1.3 / §9)

This package **MUST NOT** import:
- `svde` or `svde_bench`
- `ortools` or any solver library
- `requests` or `urllib.request`

The package operates **offline only** in Phase 0.

## Quick Start

```bash
pip install -e ".[dev]"

# Create empty bundle
prism-ontology init

# Register an evidence source
prism-ontology ingest-source --file examples/source.yaml

# Register a business claim
prism-ontology add-claim --file examples/claim.yaml

# Validate bundle
prism-ontology validate

# Check frozen state
prism-ontology gate --strict
```

## Architecture

See `PHASE0_DESIGN_CHECKLIST_v1.1.md` for full design specification.

## Test

```bash
pytest tests/ -v --disable-network
```
