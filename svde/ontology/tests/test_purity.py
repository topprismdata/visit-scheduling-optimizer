"""Phase 0 Architecture Purity Test — Independence Verification."""
import sys
from pathlib import Path

ONTOLOGY_SRC = Path(__file__).resolve().parents[1] / "src" / "prism_ontology"


def test_prism_ontology_has_zero_forbidden_imports():
    """Verify that src/prism_ontology/ has ZERO imports of svde, svde_bench, ortools, or network libs."""
    forbidden = ["from svde", "import svde", "svdebench", "svde_bench", "ortools", "requests", "urllib.request"]
    
    py_files = list(ONTOLOGY_SRC.rglob("*.py"))
    assert len(py_files) > 0, "No source files found in src/prism_ontology/"
    
    for f in py_files:
        content = f.read_text(encoding="utf-8")
        for bad in forbidden:
            assert bad not in content, f"Forbidden import '{bad}' found in {f}"
