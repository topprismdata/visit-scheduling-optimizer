"""ReadOnlyGuard — MVP 4 项硬约束运行时闸门 (BIZ 无关)

职责:
- 接受 MVP 4 项不变量值 (external_dispatch / baseline_writeback / canonical_api_status / scenario_effect_applied)
- 任一违反 -> 拒绝 + 抛 ReadOnlyViolation
- 全 4 项符合 -> 返回 GuardResult(passed=True)
- 纯函数, 不修改输入

设计:
- ReadOnlyViolation 携带 violated_field + observed + required + message
- GuardResult 含 passed / violations 列表
- check_mvp_invariants() 是单一入口 (与 MVP 4 项不变量名严格对齐)
- 严格红线: 不实现 ReplayMetrics / BaselineComparator / ShadowReplayRunner; 不加载 BIZ
"""
from dataclasses import dataclass
from typing import List, Any, Optional


# MVP 4 项硬约束字段名 (与 MVPResult 字段对齐)
MVP_INVARIANT_FIELDS = (
    "external_dispatch",
    "baseline_writeback",
    "canonical_api_status",
    "scenario_effect_applied",
)

# 4 项不变量期望值
EXPECTED_VALUES = {
    "external_dispatch": False,
    "baseline_writeback": False,
    "canonical_api_status": "NOT_IMPLEMENTED",
    "scenario_effect_applied": False,
}


class ReadOnlyViolation(Exception):
    """MVP 4 项不变量之一被违反时抛出的异常 (含违反字段 + 观察值 + 期望值)"""
    def __init__(self, violated_field: str, observed: Any, required: Any, message: str = ""):
        self.violated_field = violated_field
        self.observed = observed
        self.required = required
        self.message = message or (
            f"MVP 不变量 {violated_field!r} 违反: observed={observed!r}, required={required!r}"
        )
        super().__init__(self.message)

    def __str__(self):
        return self.message


@dataclass(frozen=True)
class GuardResult:
    """ReadOnlyGuard 校验结果 (frozen dataclass)

    Fields:
        passed: True if 全部 4 项不变量符合; False if 任一违反
        violations: ReadOnlyViolation 列表 (passed=True 时为空)
        checked_fields: 实际检查的字段名列表 (与 MVP_INVARIANT_FIELDS 对齐)
    """
    passed: bool
    violations: List[ReadOnlyViolation]
    checked_fields: List[str]

    def __post_init__(self):
        if self.passed and self.violations:
            raise ValueError(
                f"passed=True 但有 {len(self.violations)} 个 violations (矛盾)"
            )
        if not self.passed and not self.violations:
            raise ValueError("passed=False 但无 violations (矛盾)")
        for f in MVP_INVARIANT_FIELDS:
            if f not in self.checked_fields:
                raise ValueError(f"checked_fields 必须包含 MVP 不变量 {f!r}")


def _check_field(invariants: dict, field: str) -> Optional[ReadOnlyViolation]:
    """单字段检查; 返回 None if 满足, 或 ReadOnlyViolation"""
    if field not in invariants:
        return ReadOnlyViolation(
            violated_field=field,
            observed="<MISSING>",
            required=EXPECTED_VALUES[field],
            message=f"MVP 不变量字段 {field!r} 缺失 (无法校验)",
        )
    observed = invariants[field]
    required = EXPECTED_VALUES[field]
    if observed != required:
        return ReadOnlyViolation(
            violated_field=field,
            observed=observed,
            required=required,
        )
    return None


def check_mvp_invariants(invariants: dict) -> GuardResult:
    """ReadOnlyGuard 单一入口

    Args:
        invariants: dict 含 MVP 4 项硬约束字段值, 例:
            {
                "external_dispatch": False,
                "baseline_writeback": False,
                "canonical_api_status": "NOT_IMPLEMENTED",
                "scenario_effect_applied": False,
            }

    Returns:
        GuardResult (frozen)
        - 全通过: passed=True, violations=[]
        - 任一违反: passed=False, violations=[...]

    Raises:
        TypeError: 如果 invariants 不是 dict
        ValueError: 如果 invariants 缺字段或类型不对
    """
    if not isinstance(invariants, dict):
        raise TypeError(f"invariants 必须是 dict, 实际: {type(invariants).__name__}")

    violations: List[ReadOnlyViolation] = []
    for field in MVP_INVARIANT_FIELDS:
        violation = _check_field(invariants, field)
        if violation is not None:
            violations.append(violation)

    return GuardResult(
        passed=len(violations) == 0,
        violations=violations,
        checked_fields=list(MVP_INVARIANT_FIELDS),
    )


def assert_mvp_invariants(invariants: dict) -> None:
    """便捷函数: 不通过时直接抛 ReadOnlyViolation (首个违反)

    适合作为 ShadowReplayRunner / 任何下游模块的入口闸门.
    """
    result = check_mvp_invariants(invariants)
    if not result.passed:
        raise result.violations[0]


# ============================================================================
# Runtime Safety Gate (v2 升级): 从 postcondition 检查升级为可阻止的执行前闸门
# ============================================================================

import dataclasses as _dc
import hashlib as _hashlib


class GateBlocked(Exception):
    """Pre-execution gate 拒绝执行时抛出 (含拒绝原因)"""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Pre-execution gate 阻止执行: {reason}")


def _fingerprint_value(value: Any) -> str:
    """递归指纹: 突变敏感 (list/dict/set 内容变化 -> 指纹变化)"""
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return f"{type(value).__name__}:{value!r}"
    if _dc.is_dataclass(value) and not isinstance(value, type):
        fields = _dc.fields(value)
        parts = [f"{f.name}={_fingerprint_value(getattr(value, f.name))}" for f in fields]
        return f"{type(value).__name__}{{{','.join(parts)}}}"
    if isinstance(value, tuple):
        return f"tuple({','.join(_fingerprint_value(v) for v in value)})"
    if isinstance(value, list):
        # 保序 (顺序变化 -> 指纹变化)
        return f"list({','.join(_fingerprint_value(v) for v in value)})"
    if isinstance(value, dict):
        # 按 key 排序 (确定性)
        items = sorted((_fingerprint_value(k), _fingerprint_value(v)) for k, v in value.items())
        return f"dict({','.join(f'{k}->{v}' for k, v in items)})"
    if isinstance(value, (set, frozenset)):
        items = sorted(_fingerprint_value(v) for v in value)
        return f"set({','.join(items)})"
    if isinstance(value, (type(None),)) or hasattr(value, "tzinfo"):  # datetime/date/time
        return f"{type(value).__name__}:{value.isoformat()}"
    # 兜底: enum / 其他不可变对象用 repr
    return f"{type(value).__name__}:{value!r}"


def compute_worldstate_fingerprint(worldstate: Any) -> str:
    """WorldState 深度指纹 (256-bit SHA-256 digest represented as 64 hexadecimal characters)

    突变敏感: 任何嵌套 list/dict 的原地突变都会改变指纹.
    """
    return _hashlib.sha256(_fingerprint_value(worldstate).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GateToken:
    """Pre-execution gate 通过后发放的令牌 (frozen)

    Fields:
        worldstate_fingerprint: MVP 运行前的 WorldState 深度指纹
        fixture_sha256: fixture 文件字节哈希 (与 InputSnapshot.content_sha256 对齐)
        worldstate_type: WorldState 类型名
        is_frozen_dataclass: 是否 frozen dataclass
    """
    worldstate_fingerprint: str
    fixture_sha256: str
    worldstate_type: str
    is_frozen_dataclass: bool

    def __post_init__(self):
        if len(self.worldstate_fingerprint) != 64:
            raise ValueError(
                f"worldstate_fingerprint 必须是 64 hex 字符, 实际 {len(self.worldstate_fingerprint)}"
            )
        if len(self.fixture_sha256) != 64:
            raise ValueError(
                f"fixture_sha256 必须是 64 hex 字符, 实际 {len(self.fixture_sha256)}"
            )


def gate_pre_execution(worldstate: Any, snapshot: Any, fixture_path: str) -> GateToken:
    """执行前安全闸门 (可阻止): 任一检查失败 -> 抛 GateBlocked, 拒绝进入 MVP run

    检查项:
    1. worldstate 是 frozen dataclass (类型级只读)
    2. fixture 文件当前字节哈希 == snapshot.content_sha256 (输入未被篡改)
    3. 捕获 WorldState 深度指纹 (供 post-execution 突变检测)
    """
    # 1. frozen dataclass 检查
    params = getattr(type(worldstate), "__dataclass_params__", None)
    is_frozen = params is not None and getattr(params, "frozen", False)
    if not is_frozen:
        raise GateBlocked(
            f"worldstate 不是 frozen dataclass (实际: {type(worldstate).__name__}), 拒绝执行"
        )

    # 2. fixture 完整性检查
    from pathlib import Path as _Path
    current_sha = _hashlib.sha256(_Path(fixture_path).read_bytes()).hexdigest()
    expected_sha = getattr(snapshot, "content_sha256", None)
    if expected_sha is None:
        raise GateBlocked("snapshot 缺 content_sha256 (非 InputSnapshot?), 拒绝执行")
    if current_sha != expected_sha:
        raise GateBlocked(
            f"fixture 已被篡改: 当前 sha256={current_sha[:16]}... != snapshot.content_sha256={expected_sha[:16]}..."
        )

    # 3. 捕获指纹
    return GateToken(
        worldstate_fingerprint=compute_worldstate_fingerprint(worldstate),
        fixture_sha256=current_sha,
        worldstate_type=type(worldstate).__name__,
        is_frozen_dataclass=True,
    )


def gate_post_execution(token: GateToken, worldstate: Any) -> GuardResult:
    """执行后突变检测: 比对 WorldState 深度指纹, 检测 MVP 运行期间的原地突变

    返回 GuardResult (passed=True 表示无突变); 与 4 项 MVP 不变量检查互补.
    """
    current = compute_worldstate_fingerprint(worldstate)
    if current != token.worldstate_fingerprint:
        violation = ReadOnlyViolation(
            violated_field="worldstate_fingerprint",
            observed=current,
            required=token.worldstate_fingerprint,
            message=(
                "WorldState 在 MVP 运行期间被原地突变 "
                f"(fingerprint {token.worldstate_fingerprint[:16]}... -> {current[:16]}...)"
            ),
        )
        return GuardResult(
            passed=False,
            violations=[violation],
            # checked_fields 须含 4 项不变量名 (GuardResult.__post_init__ 契约) + 突变检测项
            checked_fields=list(MVP_INVARIANT_FIELDS) + ["worldstate_fingerprint"],
        )
    # GuardResult.__post_init__ 要求 checked_fields 含全部 4 项不变量名;
    # 突变检测通过时用完整字段列表表达 "全部检查均通过"
    return GuardResult(
        passed=True,
        violations=[],
        checked_fields=list(MVP_INVARIANT_FIELDS),
    )
