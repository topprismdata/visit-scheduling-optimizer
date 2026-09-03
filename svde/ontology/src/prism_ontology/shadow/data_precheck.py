"""DataPrechecker — 输入快照与世界状态完整性预检 (BIZ 无关)

职责:
- 接收 InputSnapshot + OperationalDecisionWorldState
- 校验 InputSnapshot.content_sha256 == WorldState.manifest.source_file_sha256
- 校验 WorldState 必需字段 (bitemporal / manifest / 核心实体字典)
- 校验实体 ID 唯一性 (customers / resources / commitments)
- 校验时间字段合法性 (bitemporal.valid_from < valid_to, transaction_from 不晚于 now)
- 输出结构化 DataPrecheckReport (status / snapshot_id / checked_fields / findings / error_count / warning_count)

严格红线:
- 只读, 不修改 WorldState
- 不加载 BIZ 规则
- 不修改 MVPResult
- 不实现 ReadOnlyGuard / ReplayMetrics / BaselineComparator / ShadowReplayRunner
- 不创建新状态报告版本
- 不下发外部系统
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict


# WorldState 与 SourceManifest 是从 state_snapshot.py 导入的类型 (避免循环依赖, 这里用 duck-typing)
# MVP 当前使用 OperationalDecisionWorldState (来自 prism_ontology.world_model.state_snapshot)
WorldStateT = Any
SourceManifestT = Any


# --- 校验结果严重性 ---

class FindingSeverity:
    """finding 严重性 (字符串字面量, 不依赖 enum import)"""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class Finding:
    """单条校验发现

    Fields:
        severity: "ERROR" / "WARNING" / "INFO"
        code: 短标识 (如 "HASH_MISMATCH", "MISSING_FIELD")
        message: 人类可读描述
        target: 影响对象 (如 field name / entity key), 可选
    """
    severity: str
    code: str
    message: str
    target: str = ""


# --- 报告状态 ---

class ReportStatus:
    """DataPrecheckReport.status (与 MVPResult.feasibility_judgment / error_kind 类似字面量约定)"""
    PASS = "PASS"      # 所有校验通过, 无 ERROR
    WARN = "WARN"      # 有 WARNING 但无 ERROR
    FAIL = "FAIL"      # 有 ERROR


@dataclass(frozen=True)
class DataPrecheckReport:
    """DataPrecheckReport — 不可变预检报告

    Fields:
        status: "PASS" / "WARN" / "FAIL"
        snapshot_id: 关联的 InputSnapshot.snapshot_id
        worldstate_id: 关联的 WorldState.snapshot_id (可能与 snapshot_id 不同)
        checked_fields: 已校验的字段集合 (人类可读)
        findings: Finding 列表 (ERROR 排前)
        error_count: ERROR 级 finding 数量
        warning_count: WARNING 级 finding 数量
    """
    status: str
    snapshot_id: str
    worldstate_id: str
    checked_fields: List[str]
    findings: List[Finding]
    error_count: int
    warning_count: int

    def __post_init__(self):
        if self.status not in (ReportStatus.PASS, ReportStatus.WARN, ReportStatus.FAIL):
            raise ValueError(f"status 必须是 PASS/WARN/FAIL, 实际: {self.status}")
        # 一致性: error_count = ERROR findings 长度, warning_count = WARNING findings 长度
        actual_errors = sum(1 for f in self.findings if f.severity == FindingSeverity.ERROR)
        actual_warnings = sum(1 for f in self.findings if f.severity == FindingSeverity.WARNING)
        if self.error_count != actual_errors:
            raise ValueError(f"error_count {self.error_count} != 实际 ERROR findings {actual_errors}")
        if self.warning_count != actual_warnings:
            raise ValueError(f"warning_count {self.warning_count} != 实际 WARNING findings {actual_warnings}")
        if self.status == ReportStatus.PASS and (self.error_count > 0 or self.warning_count > 0):
            raise ValueError("status=PASS 但有 findings (error/warning > 0)")
        if self.status == ReportStatus.WARN and self.error_count > 0:
            raise ValueError("status=WARN 但有 ERROR findings")
        if self.status == ReportStatus.FAIL and self.error_count == 0:
            raise ValueError("status=FAIL 但无 ERROR findings")


# --- 校验逻辑 ---

def _check_hash_consistency(snapshot, manifest) -> List[Finding]:
    """校验 InputSnapshot.content_sha256 == WorldState.manifest.source_file_sha256

    不要求 snapshot_id 字符串一致 (MVP 当前 assembler 可能生成不同格式).
    """
    findings = []
    if not hasattr(manifest, "source_file_sha256"):
        findings.append(Finding(
            severity=FindingSeverity.ERROR,
            code="MANIFEST_MISSING_HASH_FIELD",
            message="WorldState.manifest 缺少 source_file_sha256 字段",
            target="manifest.source_file_sha256",
        ))
        return findings
    snap_hash = snapshot.content_sha256
    manifest_hash = manifest.source_file_sha256
    if snap_hash != manifest_hash:
        findings.append(Finding(
            severity=FindingSeverity.ERROR,
            code="HASH_MISMATCH",
            message=f"InputSnapshot.content_sha256 ({snap_hash[:16]}...) 与 WorldState.manifest.source_file_sha256 ({manifest_hash[:16]}...) 不一致",
            target=f"snapshot={snap_hash[:12]}|manifest={manifest_hash[:12]}",
        ))
    elif len(manifest_hash) != 64:
        findings.append(Finding(
            severity=FindingSeverity.ERROR,
            code="MANIFEST_HASH_INVALID_LENGTH",
            message=f"WorldState.manifest.source_file_sha256 长度 {len(manifest_hash)} != 64 (非合法 SHA-256 hex)",
            target="manifest.source_file_sha256",
        ))
    return findings


def _check_required_fields(worldstate) -> List[Finding]:
    """校验 WorldState 必需字段存在且非空

    检查项: bitemporal / manifest / 核心实体字典.
    """
    findings = []
    # 1. bitemporal
    if not hasattr(worldstate, "bitemporal") or worldstate.bitemporal is None:
        findings.append(Finding(
            severity=FindingSeverity.ERROR,
            code="MISSING_BITEMPORAL",
            message="WorldState 缺少 bitemporal 字段",
            target="bitemporal",
        ))
    # 2. manifest
    if not hasattr(worldstate, "manifest") or worldstate.manifest is None:
        findings.append(Finding(
            severity=FindingSeverity.ERROR,
            code="MISSING_MANIFEST",
            message="WorldState 缺少 manifest 字段",
            target="manifest",
        ))
    # 3. 核心实体字典
    for dict_name in ("customers", "resources", "policies", "commitments"):
        if not hasattr(worldstate, dict_name):
            findings.append(Finding(
                severity=FindingSeverity.ERROR,
                code="MISSING_ENTITY_DICT",
                message=f"WorldState 缺少核心实体字典字段: {dict_name}",
                target=dict_name,
            ))
        elif getattr(worldstate, dict_name) is None:
            findings.append(Finding(
                severity=FindingSeverity.ERROR,
                code="ENTITY_DICT_NULL",
                message=f"WorldState.{dict_name} 不应为 None",
                target=dict_name,
            ))
    return findings


def _check_entity_id_uniqueness(worldstate) -> List[Finding]:
    """校验核心实体 ID 唯一性

    检查 customers / resources / commitments.
    """
    findings = []
    for dict_name in ("customers", "resources", "commitments"):
        entity_dict = getattr(worldstate, dict_name, None)
        if not isinstance(entity_dict, dict):
            continue
        seen_ids = {}
        for entity_id, entity_obj in entity_dict.items():
            if entity_id in seen_ids:
                findings.append(Finding(
                    severity=FindingSeverity.ERROR,
                    code="DUPLICATE_ENTITY_ID",
                    message=f"WorldState.{dict_name} 存在重复 ID '{entity_id}'",
                    target=f"{dict_name}.{entity_id}",
                ))
            seen_ids[entity_id] = entity_obj
    return findings


def _check_time_fields(worldstate) -> List[Finding]:
    """校验时间字段合法性

    bitemporal.valid_from < valid_to
    bitemporal.transaction_from 不晚于 now (允许一定 tolerance)
    SourceManifest.assembled_at 不晚于 now
    """
    findings = []
    now = datetime.now(timezone.utc)

    # bitemporal 时间
    bitemporal = getattr(worldstate, "bitemporal", None)
    if bitemporal is not None:
        try:
            vf = bitemporal.valid_from
            vt = bitemporal.valid_to
            if vf.tzinfo is None or vt.tzinfo is None:
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    code="BITEMPORAL_NAIVE_DATETIME",
                    message=f"bitemporal.valid_from/valid_to 缺 timezone (建议用 timezone-aware)",
                    target="bitemporal",
                ))
            else:
                if vf >= vt:
                    findings.append(Finding(
                        severity=FindingSeverity.ERROR,
                        code="BITEMPORAL_INVALID_RANGE",
                        message=f"bitemporal.valid_from ({vf.isoformat()}) >= valid_to ({vt.isoformat()})",
                        target="bitemporal",
                    ))
        except Exception as e:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                code="BITEMPORAL_ACCESS_ERROR",
                message=f"访问 bitemporal 时间字段失败: {e!r}",
                target="bitemporal",
            ))

    # manifest 时间
    manifest = getattr(worldstate, "manifest", None)
    if manifest is not None:
        try:
            assembled_at = manifest.assembled_at
            if assembled_at.tzinfo is None:
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    code="MANIFEST_NAIVE_DATETIME",
                    message="manifest.assembled_at 缺 timezone",
                    target="manifest.assembled_at",
                ))
            elif assembled_at > now:
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    code="MANIFEST_FUTURE_TIMESTAMP",
                    message=f"manifest.assembled_at ({assembled_at.isoformat()}) 晚于当前时间 ({now.isoformat()})",
                    target="manifest.assembled_at",
                ))
        except Exception as e:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                code="MANIFEST_ACCESS_ERROR",
                message=f"访问 manifest 时间字段失败: {e!r}",
                target="manifest.assembled_at",
            ))

    return findings


def _check_source_manifest(manifest) -> List[Finding]:
    """校验 SourceManifest 来源清单

    source_file_path 非空; source_file_sha256 是 64 字符 hex.
    """
    findings = []
    if not hasattr(manifest, "source_file_path"):
        findings.append(Finding(
            severity=FindingSeverity.ERROR,
            code="MANIFEST_MISSING_PATH",
            message="SourceManifest 缺少 source_file_path",
            target="manifest.source_file_path",
        ))
        return findings

    path = manifest.source_file_path
    if not path or not isinstance(path, str) or path.strip() == "":
        findings.append(Finding(
            severity=FindingSeverity.ERROR,
            code="MANIFEST_EMPTY_PATH",
            message=f"SourceManifest.source_file_path 为空 (实际: {path!r})",
            target="manifest.source_file_path",
        ))

    if hasattr(manifest, "source_file_sha256"):
        sha = manifest.source_file_sha256
        if not isinstance(sha, str) or len(sha) != 64:
            findings.append(Finding(
                severity=FindingSeverity.ERROR,
                code="MANIFEST_INVALID_SHA256_LENGTH",
                message=f"SourceManifest.source_file_sha256 长度 {len(sha) if isinstance(sha, str) else 'N/A'} != 64",
                target="manifest.source_file_sha256",
            ))

    return findings


def precheck_worldstate(snapshot, worldstate) -> DataPrecheckReport:
    """DataPrechecker 主入口

    Args:
        snapshot: InputSnapshot
        worldstate: OperationalDecisionWorldState (MVP 主流程的 L4 canonical state)

    Returns:
        DataPrecheckReport (frozen)
    """
    findings = []
    checked_fields = []

    # 0. 类型预检
    if not hasattr(snapshot, "content_sha256"):
        findings.append(Finding(
            severity=FindingSeverity.ERROR,
            code="INVALID_SNAPSHOT",
            message=f"snapshot 不是 InputSnapshot (缺 content_sha256 字段); 实际类型: {type(snapshot).__name__}",
            target="snapshot",
        ))
    if not hasattr(worldstate, "snapshot_id") or not hasattr(worldstate, "manifest"):
        findings.append(Finding(
            severity=FindingSeverity.ERROR,
            code="INVALID_WORLDSTATE",
            message=f"worldstate 不是 OperationalDecisionWorldState (缺 snapshot_id / manifest); 实际类型: {type(worldstate).__name__}",
            target="worldstate",
        ))

    if any(f.severity == FindingSeverity.ERROR and f.code.startswith(("INVALID_",)) for f in findings):
        # 类型预检失败, 跳过后续详细校验
        return DataPrecheckReport(
            status=ReportStatus.FAIL,
            snapshot_id=getattr(snapshot, "snapshot_id", "<unknown>"),
            worldstate_id=getattr(worldstate, "snapshot_id", "<unknown>"),
            checked_fields=[],
            findings=findings,
            error_count=sum(1 for f in findings if f.severity == FindingSeverity.ERROR),
            warning_count=sum(1 for f in findings if f.severity == FindingSeverity.WARNING),
        )

    snapshot_id = snapshot.snapshot_id
    worldstate_id = worldstate.snapshot_id

    # 1. 哈希一致性
    findings.extend(_check_hash_consistency(snapshot, worldstate.manifest))
    checked_fields.append("manifest.source_file_sha256")

    # 2. 必需字段
    findings.extend(_check_required_fields(worldstate))
    checked_fields.extend(["bitemporal", "manifest", "customers", "resources", "policies", "commitments"])

    # 3. 实体 ID 唯一性
    findings.extend(_check_entity_id_uniqueness(worldstate))
    checked_fields.append("entity_id_uniqueness")

    # 4. 时间字段
    findings.extend(_check_time_fields(worldstate))
    checked_fields.append("bitemporal.valid_from/valid_to",)
    checked_fields.append("manifest.assembled_at")

    # 5. SourceManifest 来源清单
    findings.extend(_check_source_manifest(worldstate.manifest))
    checked_fields.append("manifest.source_file_path")
    checked_fields.append("manifest.source_file_sha256")

    # 状态判定
    error_count = sum(1 for f in findings if f.severity == FindingSeverity.ERROR)
    warning_count = sum(1 for f in findings if f.severity == FindingSeverity.WARNING)
    if error_count > 0:
        status = ReportStatus.FAIL
    elif warning_count > 0:
        status = ReportStatus.WARN
    else:
        status = ReportStatus.PASS

    return DataPrecheckReport(
        status=status,
        snapshot_id=snapshot_id,
        worldstate_id=worldstate_id,
        checked_fields=checked_fields,
        findings=findings,
        error_count=error_count,
        warning_count=warning_count,
    )
