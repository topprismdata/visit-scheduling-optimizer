#!/usr/bin/env python3
"""validate_registry_anchors.py — Registry 锚点引用完整性校验 (评审报告建议 9)

扫描 CANONICAL_TYPE_REGISTRY.md 中所有 `<文档别名|文件名> §x.x` 引用,
解析目标文档章节锚点, 验证存在且非空。

用法: /usr/bin/python3 svde/tools/validate_registry_anchors.py
退出码: 0 = 全部通过; 1 = 存在悬空引用
"""
import re
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
REGISTRY = DOCS_DIR / "CANONICAL_TYPE_REGISTRY.md"

# 别名 -> 目标文件
DOC_ALIASES = {
    "主 API 规范": "TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md",
    "Canonical Types Spec": "TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md",
    "本规范": "TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md",
    "L3 动力学规范": "TOPPRISM_L3_DYNAMICS_TRANSITION_ENGINE_DETAILED_SPEC_v1_0.md",
    "L5 场景规范": "TOPPRISM_L5_SCENARIO_SIMULATION_ENGINE_DETAILED_SPEC_v1_0.md",
    "L7 规范": "TOPPRISM_L7_ENTERPRISE_DECISION_ENGINE_SPEC_v1_0.md",
}

# 通用引用模式: `<别名或完整文件名> §N`
REF_RE = re.compile(
    r"([A-Za-z0-9_\.\-]+\.md|主 API 规范|本规范|Canonical Types Spec|"
    r"L3 动力学规范|L5 场景规范|L7 规范)\s*§(\d+(?:\.\d+)*)"
)


def resolve_doc(ref_name: str):
    """引用名 -> 目标文件 Path (不存在则 None)"""
    fname = DOC_ALIASES.get(ref_name, ref_name if ref_name.endswith(".md") else None)
    if fname is None:
        return None
    p = DOCS_DIR / fname
    return p if p.exists() else None


def load_section_index(path: Path) -> dict:
    """返回 {章节号: 是否非空} — 依据标题行: `### §N` / `#### N.M` / `## N、`"""
    sections = {}
    lines = path.read_text(encoding="utf-8").split("\n")
    for i, ln in enumerate(lines):
        m = re.match(r"^#{2,4}\s+.*?§(\d+(?:\.\d+)*)", ln)
        if not m:
            m2 = re.match(r"^#{2,4}\s+(\d+(?:\.\d+)*)[、.\s]", ln)
            if m2:
                m = m2
        if m:
            sec = m.group(1).rstrip(".")
            body = "\n".join(lines[i + 1: i + 6]).strip()
            sections[sec] = bool(body)
    return sections


def main() -> int:
    if not REGISTRY.exists():
        print(f"[FAIL] Registry 不存在: {REGISTRY}")
        return 1
    src = REGISTRY.read_text(encoding="utf-8")

    indexes = {}   # doc filename -> section index
    missing_docs = set()
    violations = []
    checked = 0

    for line_no, line in enumerate(src.split("\n"), 1):
        for m in REF_RE.finditer(line):
            ref_name, sec = m.group(1), m.group(2).rstrip(".")
            doc = resolve_doc(ref_name)
            if doc is None:
                missing_docs.add(ref_name)
                violations.append((line_no, ref_name, sec, "目标文档不存在"))
                continue
            fname = doc.name
            if fname not in indexes:
                indexes[fname] = load_section_index(doc)
            checked += 1
            idx = indexes[fname]
            if sec not in idx:
                violations.append((line_no, ref_name, sec, "锚点不存在"))
            elif not idx[sec]:
                violations.append((line_no, ref_name, sec, "章节为空"))

    print(f"检查引用数: {checked}")
    if missing_docs:
        print(f"[WARN] 未识别的引用目标: {sorted(missing_docs)}")
    if violations:
        print(f"\n[FAIL] 悬空/空锚点引用 {len(violations)} 处:")
        for line_no, ref_name, sec, reason in violations:
            print(f"  L{line_no}: {ref_name} §{sec} — {reason}")
        return 1
    print("[OK] Registry 全部锚点引用有效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
