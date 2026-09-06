# SVDE-Bench: A Benchmark for Decision Compiler & Enterprise Decision Systems

SVDE-Bench is the first standardized benchmark suite designed to evaluate enterprise decision systems, decision compilers, and decision-oriented AI agents.

## Core Benchmark Philosophy

- **Decision Artifact > Solver Solution**: Evaluates the complete decision lifecycle (Intent → Contract → Type → Validation → Model → Solution → Trace → Memory), not just raw solver objective values.
- **Protocol not Runtime**: Standardized evaluation protocol decoupled from specific kernel implementations.
- **Oracle & Gold Label Isolation**: Strict structural isolation preventing benchmark leakage.

## Architecture

- `svdebench/core`: Core data models (`DecisionCase`, `DecisionArtifact`, `Trace`, `Memory`).
- `svdebench/evaluator`: Multi-dimensional evaluation engines (Semantic, Feasibility, Runtime, Memory).
- `svdebench/oracle`: Independent mathematical reference oracles.
- `svdebench/datasets`: Public input cases and private hidden gold labels.
- `svdebench/agents`: Standardized baseline agents.
- `svdebench/runner`: Benchmark runner and report generators.

## Quickstart

```bash
pip install -e ".[dev]"
pytest
```
