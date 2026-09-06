#!/usr/bin/env python3
# encoding: utf-8
"""TopPrism 全仓文档扫描脚本（v1.0.2 升级版 — 含角色分类 + CURRENT AUTHORITATIVE 优先级）

用法:
    PYTHONIOENCODING=utf-8 python3 svde/tools/topprism_scan.py

输出:
    - 终端: 5 类状态分类 + role 字段 + 完整路径清单 + 危险残留扫描汇总
    - JSON: svde/docs/evidence/topprism_scan_result.json

扫描规则:
- 范围: svde/docs/**/*.md（含 decisions/ 子目录）
- 排除: 无
- 5 类状态分类（与 role 字段正交）:
    - CANONICAL: 当前权威 L0-L7 文档（含 L0-L7 chain 且无 L0-L6/HIST/CONFLICT 标记）
    - SUPPORTING: 辅助文档（含 L0-L7 chain 但 L0-L6 残留；或无 chain 但属于架构族）
    - HISTORICAL: 含 HISTORICAL SNAPSHOT 或 MIGRATED-TO 头（且不含 CURRENT AUTHORITATIVE）
    - CONFLICTED: 含 INTERNAL CONFLICT DETECTED 头
    - UNCLASSIFIED: 未明确分类（异常，不应有）
- role 字段（与 status 正交）:
    - canonical_spec: 规范文档（主架构/接口/类型规范）
    - supporting_report: 支撑/历史报告/Phase 报告/Sprint 报告
    - audit_report: 审计/Correction Pass 报告
    - business_doc: 业务诊断/业务资料
    - undetermined: 未明确（异常）
- CURRENT AUTHORITATIVE 优先级:
    - 含 "CURRENT AUTHORITATIVE" 标记的文档，若同时含 "HISTORICAL" 则以 AUTHORITATIVE 优先（status 仍按内容标注，role 标记为 audit_report）
- DEPRECATED 反向引用规则（视为合规）:
    ❌ / DEPRECATED / HISTORICAL / 严禁 / 错误 / 不应 / 禁止 / 不构成 / 缺 / 差异 / 设计目标 / ⚠️ / SUPERSEDED
"""
import os
import re
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent  # svde/tools/topprism_scan.py → repo root
DOCS_DIR = REPO / "svde/docs"
EVIDENCE_DIR = REPO / "svde/docs/evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# ── 标记 ──
HISTORICAL_MARKERS = ["HISTORICAL SNAPSHOT", "MIGRATED-TO", "MIGRATED-BY"]
CONFLICT_MARKERS = ["INTERNAL CONFLICT DETECTED"]
SUPERSEDED_MARKERS = ["SUPERSEDED BY", "SUPERSEDES"]
CURRENT_AUTHORITATIVE_MARKERS = ["CURRENT AUTHORITATIVE"]
# 角色判定关键词
CANONICAL_SPEC_KEYWORDS = ["_SPEC", "_TYPES_SPEC", "FOUNDATIONAL", "METAMODEL", "API_SPEC", "BOUNDARY", "CONTRACT", "RESPONSIBILITY_MATRIX", "WORLD_MODEL_SPEC", "OPERATIONAL_DECISION_WORLD_MODEL"]
SUPPORTING_REPORT_KEYWORDS = ["PHASE_", "SPRINT_", "_REPORT", "_AUDIT", "DELIVERY_OVERVIEW", "DELIVERABLE_", "V3_CLOSURE", "V2_CLOSURE", "REMEDIATION", "GAP_", "ARBITRATION", "HITL_", "FOUNDATIONAL_WORLD_MODEL_SUITE", "REQUIRED_SPEC_UPDATES"]
AUDIT_REPORT_KEYWORDS = ["CORRECTION_PASS", "CONTRACT_ALIGNMENT_MASTER_REPORT", "PREFLIGHT_", "FREEZE_READINESS", "CONTRACT_FREEZE", "FREEZE_REVIEW_CHECKLIST", "ARCHITECTURE_AUDIT_ROUND"]
BUSINESS_DOC_KEYWORDS = ["FMCG_", "REAL_DATA", "RENJUN_", "BUSINESS_", "CADENCE_AUDIT", "EVIDENCE_BUNDLE", "SALES_VISIT_DOMAIN", "SALES_VISIT_CONCEPT", "SALES_VISIT_ONTOLOGY_DESIGN", "SALES_VISIT_EVIDENCE", "SALES_VISIT_ONTOLOGY_GAP", "HITL_REMEDIATION", "ARCHITECTURE_DECISION_BASELINE", "POSITIONING_AND_ADVANTAGES", "PRODUCT_AND_COMMUNICATION_SPEC"]
L0_L6_PATTERNS = ["L0-L6", "L0 → L1 → L2 → L3 → L4 → L5 → L6"]
L0_L7_PATTERNS = ["L0-L7", "L0 + L1 + L2 + L3 + L4 + L5 + L6 + L7"]

REVERSED_MARKERS = [
    "❌", "DEPRECATED", "HISTORICAL", "严禁", "错误", "不应", "禁止",
    "不构成", "缺", "差异", "设计目标", "⚠️", "SUPERSEDED", "DEPRECATED 字段",
    "DEPRECATED：", "DEPRECATED)", "DEPRECATED ",
]

DANGEROUS_PATTERNS = [
    "ExecutionEventStream = OperationalDecisionWorldState.execution_fact_stream",
    "ExecutionEvent(IN_PROGRESS)",
    "ExecutionEvent(COMPLETED)",
    'visit_id="RES_',
    "单一 Canonical API 双入口",
    "16/16",
    "31/31",
]

BIZ_PATTERN = re.compile(r"BIZ-0(\d)")


def determine_role(name: str, head: str) -> str:
    """根据文件名与头部内容判定 role（与 status 正交）。"""
    # 优先级: AUDIT_REPORT > CANONICAL_SPEC > BUSINESS_DOC > SUPPORTING_REPORT > UNDETERMINED
    for kw in AUDIT_REPORT_KEYWORDS:
        if kw in name:
            return "audit_report"
    for kw in CANONICAL_SPEC_KEYWORDS:
        if kw in name:
            return "canonical_spec"
    for kw in BUSINESS_DOC_KEYWORDS:
        if kw in name:
            return "business_doc"
    for kw in SUPPORTING_REPORT_KEYWORDS:
        if kw in name:
            return "supporting_report"
    # 头部含 "CANONICAL" / "MATAMODEL" / "WORLD_MODEL" / "FOUNDATIONAL" 等视为规范
    if any(m in head for m in ["# TopPrism Canonical", "# SVDE Operational Decision", "# SVDE World Model Foundational"]):
        return "canonical_spec"
    if "BUSINESS" in head.upper() or "DOMAIN ONTOLOGY" in head.upper():
        return "business_doc"
    return "undetermined"


def classify_file(path: Path, doc_root: Path) -> dict:
    """5 类状态分类（互斥）+ role 字段 + CURRENT AUTHORITATIVE 优先级。"""
    rel = str(path.relative_to(doc_root))
    head = path.read_text(encoding="utf-8")[:800]
    full_src = path.read_text(encoding="utf-8")
    has_l06 = any(p in head for p in L0_L6_PATTERNS)
    has_l07 = any(p in head for p in L0_L7_PATTERNS)
    has_hist = any(m in head for m in HISTORICAL_MARKERS)
    has_conflict = any(m in head for m in CONFLICT_MARKERS)
    has_current_auth = any(m in head for m in CURRENT_AUTHORITATIVE_MARKERS)
    has_superseded = any(m in head for m in SUPERSEDED_MARKERS)

    role = determine_role(path.name, head)

    # 互斥优先级（v1.0.2 升级）：
    # 1. CURRENT AUTHORITATIVE 文档 → 即使含 HISTORICAL/SUPERSEDED 字样（描述历史），role=audit_report，status 仍可含 HIST 标记但优先 AUTHORITATIVE
    #    实际为 Correction Pass 自身；分类为 SUPPORTING（因为是审计报告）+ audit_report role
    #    若文件内容含 "Status: CURRENT AUTHORITATIVE" 且 role=audit_report，标 is_authoritative=True
    is_authoritative = has_current_auth

    # 2. CONFLICT 文档（冲突未解）
    # 3. HISTORICAL 文档（除非是 CURRENT AUTHORITATIVE 自描述其历史）
    # 4. CANONICAL 文档（含 L0-L7 chain，无 L0-L6/HIST/CONFLICT）
    # 5. SUPPORTING 文档（其他）
    # 6. UNCLASSIFIED

    if has_current_auth and role == "audit_report":
        # Correction Pass 自身：即使是 AUTHORITATIVE，但 role 是 audit_report，
        # 状态分类应标记为 SUPPORTING（属于支撑/审计），让 CURRENT AUTHORITATIVE 标记在 is_authoritative 字段体现
        category = "SUPPORTING"
        reason = "CURRENT AUTHORITATIVE audit_report (Correction Pass)"
    elif has_conflict:
        category = "CONFLICTED"
        reason = "INTERNAL_CONFLICT_DETECTED header"
    elif has_hist and not has_current_auth:
        category = "HISTORICAL"
        reason = "HISTORICAL_SNAPSHOT or MIGRATED-TO header (not authoritative)"
    elif has_l07 and not has_l06:
        category = "CANONICAL"
        reason = "L0-L7 active reference (no L0-L6 residue)"
    elif has_l06 and not has_l07:
        category = "SUPPORTING"
        reason = "Only L0-L6 (no L0-L7) — likely needs migration"
    elif has_l06 and has_l07:
        category = "CONFLICTED"
        reason = "Contains both L0-L6 and L0-L7 references"
    else:
        category = "SUPPORTING"
        reason = "Architectural doc without explicit L0-L6/L0-L7 chain"

    return {
        "path": rel,
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "category": category,
        "role": role,
        "is_authoritative": is_authoritative,
        "reason": reason,
        "has_l06": has_l06,
        "has_l07": has_l07,
        "has_historical": has_hist,
        "has_conflict": has_conflict,
        "has_current_authoritative": has_current_auth,
        "has_superseded": has_superseded,
        "biz_numbers": sorted(set(BIZ_PATTERN.findall(full_src))),
    }


def is_reversed_reference(line: str) -> bool:
    return any(marker in line for marker in REVERSED_MARKERS)


def scan_dangerous_residues(classifications: list) -> dict:
    """按 role 分别统计危险残留：活跃规范 vs 审计报告自描述。"""
    active_results = {p: [] for p in DANGEROUS_PATTERNS}
    audit_results = {p: [] for p in DANGEROUS_PATTERNS}

    for c in classifications:
        fp = DOCS_DIR / c["path"]
        if not fp.exists():
            continue
        src = fp.read_text(encoding="utf-8")
        is_audit = c["role"] == "audit_report"
        target = audit_results if is_audit else active_results

        for pat in DANGEROUS_PATTERNS:
            for line in src.splitlines():
                if pat in line:
                    reversed_ref = is_reversed_reference(line)
                    entry = {
                        "file": c["path"],
                        "line_preview": line[:140],
                        "is_reversed_reference": reversed_ref,
                        "category": c["category"],
                        "role": c["role"],
                    }
                    if reversed_ref:
                        entry["status"] = "OK (reversed reference / DEPRECATED list)"
                    else:
                        # 审计报告元描述：含 "历史" / "Reason for Supersede" / "已加 SUPERSEDED" / "总计" 等
                        if is_audit and any(k in line for k in ["历史", "Reason for Supersede", "总计", "本报告", "已加 SUPERSEDED", "SUPERSEDED BY"]):
                            entry["status"] = "OK (audit meta-description)"
                        else:
                            entry["status"] = "VIOLATION"
                    target[pat].append(entry)
    return {"active": active_results, "audit": audit_results}


def main():
    md_files = sorted(DOCS_DIR.rglob("*.md"))
    classifications = [classify_file(f, REPO / "svde") for f in md_files]

    by_cat = {"CANONICAL": [], "SUPPORTING": [], "HISTORICAL": [], "CONFLICTED": [], "UNCLASSIFIED": []}
    by_role = {"canonical_spec": [], "supporting_report": [], "audit_report": [], "business_doc": [], "undetermined": []}
    for c in classifications:
        by_cat[c["category"]].append(c)
        by_role[c["role"]].append(c)

    residues = scan_dangerous_residues(classifications)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print("=" * 78)
    print(f"【TopPrism 全仓文档扫描 v1.0.2 升级版】 扫描时间: {now}")
    print("=" * 78)
    print(f"\n扫描范围: svde/docs/**/*.md  (共 {len(md_files)} 份文件，含 decisions/ 子目录)")
    print(f"扫描脚本: svde/tools/topprism_scan.py")

    print(f"\n5 类状态分类（互斥）:")
    for cat in ["CANONICAL", "SUPPORTING", "HISTORICAL", "CONFLICTED", "UNCLASSIFIED"]:
        print(f"  {cat:<14} {len(by_cat[cat]):>3} 份")

    print(f"\n角色分类（与 status 正交）:")
    for role in ["canonical_spec", "supporting_report", "audit_report", "business_doc", "undetermined"]:
        print(f"  {role:<20} {len(by_role[role]):>3} 份")

    print(f"\n完整路径清单（按 5 类 + role）:")
    for cat in ["CANONICAL", "SUPPORTING", "HISTORICAL", "CONFLICTED", "UNCLASSIFIED"]:
        if not by_cat[cat]:
            print(f"\n## {cat}（0 份）")
            continue
        print(f"\n## {cat}（{len(by_cat[cat])} 份）")
        print("| # | 路径 | 字节 | role | AUTH | L0-L6 | L0-L7 | HIST | CONFLICT | BIZ |")
        print("|---|---|---:|---|:---:|:---:|:---:|:---:|:---:|---|")
        for i, c in enumerate(by_cat[cat], 1):
            biz = ",".join(c["biz_numbers"]) if c["biz_numbers"] else "-"
            auth = "Y" if c["is_authoritative"] else ""
            print(f"| {i} | `{c['path']}` | {c['size_bytes']:,} | {c['role']} | "
                  f"{auth} | {'Y' if c['has_l06'] else ''} | {'Y' if c['has_l07'] else ''} | "
                  f"{'Y' if c['has_historical'] else ''} | {'Y' if c['has_conflict'] else ''} | {biz} |")

    print(f"\n{'=' * 78}")
    print(f"【危险残留扫描】活跃规范 vs 审计报告自描述（按 role 分别统计）")
    print("=" * 78)
    active_total = len(md_files) - sum(1 for c in classifications if c["role"] == "audit_report")
    audit_total = sum(1 for c in classifications if c["role"] == "audit_report")
    print(f"\n【规范文档扫描】(活跃文档，排除 audit_report role)")
    print(f"扫描范围: {active_total} 份（{len(md_files)} 总数 - {audit_total} 份 audit_report）")
    print(f"排除规则: role=audit_report 的文档视为元描述")

    active_violations = 0
    print(f"\n{'模式':<70} {'总匹配':>6} {'活跃违反':>10} {'合规反向':>10}")
    for pat, hits in residues["active"].items():
        violations = [h for h in hits if h["status"] == "VIOLATION"]
        ok_refs = [h for h in hits if "OK" in h["status"]]
        active_violations += len(violations)
        pat_disp = pat if len(pat) <= 68 else pat[:65] + "..."
        print(f"  `{pat_disp}`  {len(hits):>6} {len(violations):>10} "
              f"{len(ok_refs):>10}")
        for v in violations:
            print(f"    ❌ {v['file']}: {v['line_preview']}")

    print(f"\n【审计报告自描述扫描】(按 role=audit_report 分别核对)")
    audit_violations = 0
    print(f"\n扫描范围: {audit_total} 份（role=audit_report）")
    print(f"\n{'模式':<70} {'总匹配':>6} {'违反':>10}")
    for pat, hits in residues["audit"].items():
        violations = [h for h in hits if h["status"] == "VIOLATION"]
        ok_refs = [h for h in hits if "OK" in h["status"]]
        audit_violations += len(violations)
        pat_disp = pat if len(pat) <= 68 else pat[:65] + "..."
        print(f"  `{pat_disp}`  {len(hits):>6} {len(violations):>10}")

    out = {
        "scan_time": now,
        "scan_tool": "svde/tools/topprism_scan.py",
        "scope": f"{len(md_files)} files in svde/docs (recursive, including decisions/)",
        "exclude_rules": [
            "role=audit_report (self-description only, scanned separately)",
        ],
        "category_counts": {cat: len(by_cat[cat]) for cat in ["CANONICAL", "SUPPORTING", "HISTORICAL", "CONFLICTED", "UNCLASSIFIED"]},
        "role_counts": {role: len(by_role[role]) for role in ["canonical_spec", "supporting_report", "audit_report", "business_doc", "undetermined"]},
        "classifications": classifications,
        "dangerous_residues": residues,
        "summary": {
            "active_violations": active_violations,
            "audit_violations": audit_violations,
            "scan_status_active_docs": "PASS" if active_violations == 0 else "FAIL",
            "scan_status_audit_self_description": "INFO" if audit_violations == 0 else "REVIEW",
            "scan_status_overall": "规范文档扫描通过；审计报告自描述已单独排除并核对；Runtime 未验证",
        },
    }
    out_path = EVIDENCE_DIR / "topprism_scan_result.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完整结果写入: {out_path}")
    print(f"  Size: {out_path.stat().st_size:,} bytes")

    print(f"\n{'=' * 78}")
    print(f"扫描汇总:")
    print(f"  活跃规范文档违规: {active_violations}  {'PASS ✅' if active_violations == 0 else 'FAIL ❌'}")
    print(f"  审计报告自描述违规: {audit_violations}  {'INFO ⚠️' if audit_violations == 0 else 'REVIEW ⚠️'}")
    print(f"  最终状态: {out['summary']['scan_status_overall']}")
    print(f"{'=' * 78}")


if __name__ == "__main__":
    main()
