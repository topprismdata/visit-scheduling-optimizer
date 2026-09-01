# -*- coding: utf-8 -*-
"""Algorithm registry: add new algorithms here."""
from core.base import Algorithm

# Global registry: name -> class
_ALGORITHMS: dict[str, type[Algorithm]] = {}


def register(cls):
    """Decorator: register an Algorithm subclass."""
    name = getattr(cls, "name", None)
    if not name:
        name = cls.__name__
    cls.name = name
    _ALGORITHMS[name] = cls
    return cls


def get(name: str) -> type[Algorithm]:
    if name not in _ALGORITHMS:
        raise KeyError(f"Unknown algorithm: {name}. Available: {list(_ALGORITHMS)}")
    return _ALGORITHMS[name]


def list_all() -> list[str]:
    return list(_ALGORITHMS)


def solve_all(data, D, names: list[str] = None):
    """Run all (or selected) algorithms on one line, return results."""
    from core.metric import check_freq
    import time
    
    algos = names if names else list_all()
    results = []
    for name in algos:
        cls = get(name)
        algo = cls()
        t0 = time.time()
        result = algo.solve(data, D)
        result.elapsed = time.time() - t0
        result.count_ok = check_freq(result.days, data.codes, data.freq)
        results.append(result)
    return results