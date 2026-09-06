"""Operational Compiler — generate JSON Schemas + SHACL shapes from Reference Ontology (Phase 2).

Phase 0 stub: simple field reflection.
Phase 2: produces machine-readable operational contracts that DomainAdapters and Capability
implementations can consume.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
from pathlib import Path
import hashlib

from prism_ontology.reference.store import (
    ReferenceOntologyStore, ReferenceObject, ObjectLayer
)


@dataclass
class JSONSchemaField:
    name: str
    type: str           # "string", "number", "boolean", "array", "object", "enum"
    required: bool
    description: str = ""
    enum_values: Optional[List[str]] = None
    item_type: Optional[str] = None  # for array type


@dataclass
class JSONSchema:
    schema_id: str
    title: str
    description: str
    fields: List[JSONSchemaField]
    evidence_sources: List[str] = field(default_factory=list)
    frozen_at: str = "2026-08-24"

    def to_dict(self) -> Dict[str, Any]:
        properties = {}
        required_list = []
        for f in self.fields:
            prop: Dict[str, Any] = {"type": f.type, "description": f.description}
            if f.enum_values:
                prop["enum"] = f.enum_values
            if f.type == "array" and f.item_type:
                prop["items"] = {"type": f.item_type}
            properties[f.name] = prop
            if f.required:
                required_list.append(f.name)
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": self.schema_id,
            "title": self.title,
            "description": self.description,
            "type": "object",
            "properties": properties,
            "required": required_list,
            "evidence_sources": self.evidence_sources,
            "frozen_at": self.frozen_at,
        }

    def compute_hash(self) -> str:
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


@dataclass
class SHACLShape:
    shape_id: str
    target_class: str
    property_constraints: List[Dict[str, Any]]   # each: {path, datatype, minCount, maxCount, etc.}
    closed: bool = True
    evidence_sources: List[str] = field(default_factory=list)

    def to_ttl(self) -> str:
        """Render minimal SHACL shapes in Turtle."""
        lines = [
            f"@prefix sh: <http://www.w3.org/ns/shacl#> .",
            f"@prefix prism: <urn:prism:ontology:> .",
            f"@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "",
            f"prism:{self.shape_id} a sh:NodeShape ;",
            f"  sh:targetClass prism:{self.target_class} ;",
            f"  sh:closed {'true' if self.closed else 'false'} ;",
        ]
        for i, c in enumerate(self.property_constraints):
            prop_uri = f"prism:propertyShape_{self.shape_id}_{i}"
            lines.append(f"  sh:property {prop_uri} .")
            lines.append("")
            lines.append(f"{prop_uri} a sh:PropertyShape ;")
            lines.append(f"  sh:path prism:{c['path']} ;")
            if "datatype" in c:
                lines.append(f"  sh:datatype {c['datatype']} ;")
            if "minCount" in c:
                lines.append(f"  sh:minCount {c['minCount']} ;")
            if "maxCount" in c:
                lines.append(f"  sh:maxCount {c['maxCount']} ;")
            if "class" in c:
                lines.append(f"  sh:class prism:{c['class']} ;")
            lines.append(".")
            lines.append("")
        return "\n".join(lines)


def infer_type(attr_name: str) -> str:
    """Infer JSON Schema type from attribute name."""
    name = attr_name.lower()
    if any(kw in name for kw in ("id", "name", "code", "status", "source", "type", "reason")):
        return "string"
    if any(kw in name for kw in ("is_", "has_", "requires_", "locked", "active")):
        return "boolean"
    if any(kw in name for kw in ("count", "number", "weight", "duration", "minutes", "capacity", "value", "tolerance", "interval", "length", "months", "kg", "mins", "hours", "rate", "score", "depth", "limit", "improvement", "level", "samplings", "iterations", "tolerance", "tolerance")):
        return "number"
    if any(kw in name for kw in ("ids", "items", "list", "array", "rep_ids", "tiers", "nodes")):
        return "array"
    if "window" in name or "time" in name:
        return "array"
    return "string"


class OperationalCompiler:
    """Compiles ReferenceOntologyStore → operational contracts (JSON Schemas + SHACL shapes)."""

    def __init__(self, store: ReferenceOntologyStore):
        self.store = store

    def compile_object_schema(self, obj: ReferenceObject) -> JSONSchema:
        fields = [
            JSONSchemaField(
                name="id",
                type="string",
                required=True,
                description=f"Unique identifier for {obj.object_id}",
            ),
        ]
        for attr in obj.key_attributes:
            fields.append(JSONSchemaField(
                name=attr,
                type=infer_type(attr),
                required=self._is_required(attr, obj),
                description=f"{attr} for {obj.object_id}",
            ))
        return JSONSchema(
            schema_id=f"prism:schema:{obj.object_id}",
            title=f"{obj.object_id} Operational Contract",
            description=f"v0.3 FROZEN operational contract for {obj.object_id}. {obj.definition}",
            fields=fields,
            evidence_sources=obj.evidence_sources,
        )

    def _is_required(self, attr: str, obj: ReferenceObject) -> bool:
        # ID fields are required; core identifiers required; others optional
        if attr.endswith("_id"):
            return True
        if attr in ("date", "rep_id", "customer_id", "lifecycle_state", "status", "time_window"):
            return True
        return False

    def compile_all(self) -> Dict[str, JSONSchema]:
        return {obj.object_id: self.compile_object_schema(obj) for obj in self.store.objects.values()}

    def compile_shacl_shape(self, obj: ReferenceObject) -> SHACLShape:
        constraints = []
        constraints.append({
            "path": "id",
            "datatype": "xsd:string",
            "minCount": 1,
            "maxCount": 1,
        })
        for attr in obj.key_attributes:
            if not attr.endswith("_id"):
                continue
            constraints.append({
                "path": attr,
                "datatype": "xsd:string",
                "minCount": 1,
            })
        return SHACLShape(
            shape_id=f"Shape_{obj.object_id}",
            target_class=obj.object_id,
            property_constraints=constraints,
            evidence_sources=obj.evidence_sources,
        )

    def export_all(self, out_dir: Path) -> None:
        """Write all JSON Schemas + SHACL shapes to out_dir."""
        out_dir.mkdir(parents=True, exist_ok=True)
        for obj in self.store.objects.values():
            schema = self.compile_object_schema(obj)
            (out_dir / f"{obj.object_id}.schema.json").write_text(
                json.dumps(schema.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            shape = self.compile_shacl_shape(obj)
            (out_dir / f"{obj.object_id}.shape.ttl").write_text(shape.to_ttl(), encoding="utf-8")
        manifest = {
            "prism_ontology_version": "0.1.0",
            "compiled_at": "2026-08-24",
            "source_object_count": self.store.total_objects(),
            "schemas": sorted(self.store.all_object_ids()),
        }
        (out_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
