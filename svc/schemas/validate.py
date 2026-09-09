"""jsonschema 包装 —— 阶段输出的唯一守门员."""
import json
from pathlib import Path

import jsonschema

_DIR = Path(__file__).parent
_SCHEMA_FILES = {
    "problem": "problem.v2.schema.json",
    "calendar_map": "calendar_map.v1.schema.json",
    "model": "model.v1.schema.json",
    "solution": "solution.v1.schema.json",
}


class SchemaError(ValueError):
    pass


def validate_obj(obj: dict, name: str) -> None:
    if name not in _SCHEMA_FILES:
        raise SchemaError(f"unknown schema: {name}")
    schema = json.loads((_DIR / _SCHEMA_FILES[name]).read_text(encoding="utf-8"))
    try:
        jsonschema.validate(obj, schema)
    except jsonschema.ValidationError as e:
        raise SchemaError(f"{name}: {e.message} at {list(e.absolute_path)}") from e
