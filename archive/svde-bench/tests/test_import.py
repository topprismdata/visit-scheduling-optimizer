"""
test_import.py — Package Import Smoke Test
"""
def test_import_svdebench():
    import svdebench
    assert svdebench.__version__ == "0.1.0"

def test_import_submodules():
    import svdebench.core
    import svdebench.evaluator
    import svdebench.oracle
    import svdebench.agents
    import svdebench.runner
    assert hasattr(svdebench.core, "DecisionCase")
    assert hasattr(svdebench.core, "DecisionArtifact")
