"""CLI Entrypoint for SVDE-Bench v0.2.

Usage:
  svde-bench generate --domain delivery --count 1
  svde-bench validate --case <path_to_case_dir>
  svde-bench oracle-run --case <path_to_case_dir>
  svde-bench full-pipeline --case <path_to_case_dir> [--output <profile.json>]
"""
import sys
import json
from pathlib import Path

# Ensure svde-bench root is in sys.path
BENCH_ROOT = Path(__file__).resolve().parents[2]
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))

import click

from tools.case_generator.case_synthesizer import DecisionScenarioSynthesizer
from tools.case_generator.schema_validator import validate_case
from tools.case_generator.oracle_runner import OracleRunner
from tools.case_generator.pipeline_runner import FullPipelineRunner


@click.group()
def cli():
    """SVDE-Bench v0.2 CLI Tools."""
    pass


@cli.command()
@click.option("--domain", default="delivery", type=click.Choice(["delivery", "warehouse", "channel", "visit"]))
@click.option("--output-dir", required=True, type=click.Path())
@click.option("--case-id", default="SYNTH-CASE-001")
def generate(domain, output_dir, case_id):
    """Synthesize a decision scenario skeleton conforming to Layer 1 Schema."""
    synth = DecisionScenarioSynthesizer()
    out = synth.synthesize_minimal_delivery_case(Path(output_dir), case_id=case_id)
    click.echo(f"Synthesized case at: {out}")


@cli.command()
@click.option("--case", required=True, type=click.Path(exists=True))
def validate(case):
    """Validate a multi-file case directory against Schema and Decision-Completeness rules."""
    res = validate_case(Path(case))
    click.echo(json.dumps(res.to_dict(), indent=2))
    if not res.ok():
        sys.exit(1)


@cli.command()
@click.option("--case", required=True, type=click.Path(exists=True))
@click.option("--timeout", default=300, type=int)
def oracle_run(case, timeout):
    """Solve case with CPSATExactOracle and print OracleResult."""
    runner = OracleRunner(timeout_sec=timeout)
    res = runner.run_directory(Path(case))
    click.echo(json.dumps(res.to_dict(), indent=2))


@cli.command()
@click.option("--case", required=True, type=click.Path(exists=True))
@click.option("--output", default=None, type=click.Path())
@click.option("--timeout", default=300, type=int)
def full_pipeline(case, output, timeout):
    """Run full benchmark pipeline (Validate -> Oracle -> Agent -> Evaluate -> Profile)."""
    runner = FullPipelineRunner(oracle_timeout_sec=timeout)
    res = runner.run_case_dir(Path(case))
    if not res.get("ok"):
        click.echo(f"Pipeline failed: {res}", err=True)
        sys.exit(1)
    
    prof = res["profile"]
    if output:
        out_p = Path(output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(prof, f, indent=2)
        click.echo(f"DecisionProfile written to: {out_p}")
    else:
        click.echo(json.dumps(prof, indent=2))


if __name__ == "__main__":
    cli()
