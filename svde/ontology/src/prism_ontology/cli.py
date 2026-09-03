"""CLI for prism-ontology (Phase 0)."""
import sys
import click
from pathlib import Path


@click.group()
def main():
    """prism-ontology — independent ontology engineering CLI."""
    pass


@main.command()
@click.option("--out", default="./ontology-bundles", help="Bundle output path")
def init(out: str):
    """Create empty bundle skeleton."""
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    click.echo(f"Bundle skeleton created at {out_path}")
    return 0


@main.command()
@click.option("--file", required=True, help="Evidence source YAML/JSON")
@click.option("--bundle", default="./ontology-bundles", help="Bundle path")
def ingest_source(file: str, bundle: str):
    """Register an evidence source from YAML/JSON."""
    from prism_ontology.evidence import EvidenceRegistry
    from pathlib import Path
    import yaml, json

    bundle_path = Path(bundle)
    bundle_path.mkdir(parents=True, exist_ok=True)
    src_path = Path(file)

    if src_path.suffix in (".yaml", ".yml"):
        with open(src_path) as f:
            data = yaml.safe_load(f)
    else:
        with open(src_path) as f:
            data = json.load(f)

    if "source_id" not in data:
        click.echo(f"Error: source file must contain 'source_id'", err=True)
        return 4

    reg = EvidenceRegistry(bundle_path)
    try:
        reg.add_source(data)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return 4

    out_file = bundle_path / f"source_{data['source_id']}{src_path.suffix}"
    with open(out_file, "w") as f:
        if src_path.suffix in (".yaml", ".yml"):
            yaml.dump(data, f, default_flow_style=False)
        else:
            json.dump(data, f, indent=2)

    click.echo(f"Source '{data['source_id']}' ingested into {out_file}")
    return 0


@main.command()
@click.option("--file", required=True, help="Claim YAML/JSON")
@click.option("--bundle", default="./ontology-bundles", help="Bundle path")
def add_claim(file: str, bundle: str):
    """Register a business claim from YAML/JSON."""
    from prism_ontology.evidence import EvidenceRegistry
    from pathlib import Path
    import yaml, json

    bundle_path = Path(bundle)
    reg = EvidenceRegistry(bundle_path)
    src_path = Path(file)

    if src_path.suffix in (".yaml", ".yml"):
        with open(src_path) as f:
            data = yaml.safe_load(f)
    else:
        with open(src_path) as f:
            data = json.load(f)

    if "claim_id" not in data:
        click.echo("Error: claim must contain 'claim_id'", err=True)
        return 4

    try:
        reg.add_claim(data)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return 4

    out_file = bundle_path / f"claim_{data['claim_id']}{src_path.suffix}"
    with open(out_file, "w") as f:
        if src_path.suffix in (".yaml", ".yml"):
            yaml.dump(data, f, default_flow_style=False)
        else:
            json.dump(data, f, indent=2)

    click.echo(f"Claim '{data['claim_id']}' added to {out_file}")
    return 0


@main.command()
@click.option("--bundle", default="./ontology-bundles", help="Bundle path")
def validate(bundle: str):
    """Run SHACL validation on bundle (Phase 0 stub)."""
    from prism_ontology.validator import SHACLRunner
    from pathlib import Path
    runner = SHACLRunner()
    report = runner.validate(Path(bundle))
    click.echo(f"Validation: conforms={report['conforms']} note={report['note']}")
    return 0 if report["conforms"] else 2


@main.command()
@click.option("--question", required=True, help="User question to diagnose")
def diagnose(question: str):
    """Route user question to 5 decision levels."""
    from prism_ontology.diagnostics import IntentRouter
    router = IntentRouter()
    diag = router.route(question)
    click.echo(f"Primary: {diag.primary_decision_level}")
    if diag.secondary_decision_levels:
        click.echo(f"Secondary: {', '.join(diag.secondary_decision_levels)}")
    click.echo(f"Confidence: {diag.confidence:.2f}")
    if diag.needs_clarification:
        click.echo(f"Refusal: {diag.refusal_reason}")
    return 0 if not diag.needs_clarification else 5


@main.command()
@click.option("--strict", is_flag=True, help="Strict gate enforcement")
def gate(strict: bool):
    """Verify frozen state and GAP approval (Phase 0 stub)."""
    from prism_ontology.governance import LifecycleState
    click.echo(f"Gate check: strict={strict} (Phase 0 stub — no claims yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
