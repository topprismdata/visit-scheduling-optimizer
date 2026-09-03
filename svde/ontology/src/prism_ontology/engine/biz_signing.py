"""BIZ 业务签署注册表与校验框架 (EXPERIMENTAL DRAFT, NOT SIGNED, NOT EFFECTIVE)

WARNING: 本模块是实验性草案. MVP 正式基线不加载此模块.
业务方签署前不得启用. 待业务方签署 BIZ-01~09 后, 解除 EXPERIMENTAL 标记并激活.
"""BIZ 业务签署注册表与校验框架 (MVP 范围)

设计原则:
- 仅做"接收 + 加载 + 校验"框架, 不实现 BIZ 规则的**实际业务执行**
- BIZ 规则内容由业务方签署后填充 (BIZ_01~09_*.md)
- MVP 在 audit 阶段叠加 BIZ 校验到 constraint_violations
- 不修改 MVP 主流程主链路
- 4 项 MVP 运行不变量保持 (external_dispatch / baseline_writeback / canonical_api_status / scenario_effect_applied)
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class BIZRule:
    """单条 BIZ 业务规则"""
    biz_id: str                    # 如 "BIZ-01"
    version: str                  # 如 "v1.0-DRAFT"
    scope: str                    # 适用范围
    predicate_name: str           # 校验函数名 (用于 BIZSigningRegistry 查找)
    severity_on_violation: str    # "WARNING" | "CRITICAL_INCIDENT" | "IGNORE"


@dataclass(frozen=True)
class ConstraintViolation:
    """BIZ 校验违反记录"""
    biz_id: str
    severity: str                # "WARNING" | "CRITICAL_INCIDENT" | "IGNORE"
    message: str
    target: str = ""             # 违反影响的实体 (如 store_code, rep_id)


class BIZSigningRegistry:
    """BIZ 业务签署注册表 (MVP 进程内, 不持久化)

    用法:
        registry = BIZSigningRegistry()
        registry.register(BIZ-01, cadence_rule, check_cadence_violation)
        violations = registry.apply_all(plan, world_state)
    """
    def __init__(self):
        self._rules: Dict[str, BIZRule] = {}
        self._predicates: Dict[str, Callable] = {}

    def register(self, rule: BIZRule, predicate: Callable) -> None:
        """注册一条 BIZ 规则及其校验函数

        Args:
            rule: BIZRule 数据类
            predicate: 校验函数, 签名 (plan, world_state) -> List[ConstraintViolation]
        """
        self._rules[rule.biz_id] = rule
        self._predicates[rule.predicate_name] = predicate

    def has(self, biz_id: str) -> bool:
        return biz_id in self._rules

    def apply_all(self, plan, world_state) -> List[ConstraintViolation]:
        """应用所有已注册 BIZ 规则, 返回违反清单 (空 list = 全通过)"""
        violations: List[ConstraintViolation] = []
        for biz_id, rule in self._rules.items():
            predicate = self._predicates.get(rule.predicate_name)
            if predicate is None:
                continue
            try:
                result = predicate(plan, world_state, rule)
                violations.extend(result)
            except Exception as e:
                violations.append(ConstraintViolation(
                    biz_id=biz_id,
                    severity="WARNING",
                    message=f"BIZ 校验函数 {rule.predicate_name} 执行失败: {e!r}",
                    target="",
                ))
        return violations


# ===== Mock BIZ 校验函数 (BIZ-01~09 占位) =====

def check_cadence_violation(plan, world_state, rule) -> List[ConstraintViolation]:
    """BIZ-01 占位: CADENCE 频次校验 — 业务方签署时填充实际逻辑"""
    # 当前 DRAFT: 默认返回空 (无违反)
    return []


def check_three_per_month_violation(plan, world_state, rule) -> List[ConstraintViolation]:
    """BIZ-02 占位: 3次/月语义校验"""
    return []


def check_deferral_violation(plan, world_state, rule) -> List[ConstraintViolation]:
    """BIZ-03 占位: Deferral 校验"""
    return []


def check_key_store_violation(plan, world_state, rule) -> List[ConstraintViolation]:
    """BIZ-04 占位: Key 店零脱访校验"""
    return []


def check_gps_violation(plan, world_state, rule) -> List[ConstraintViolation]:
    """BIZ-05 占位: GPS 偏差校验"""
    return []


def check_workload_violation(plan, world_state, rule) -> List[ConstraintViolation]:
    """BIZ-06 占位: 工时双重红线校验"""
    return []


def check_ownership_violation(plan, world_state, rule) -> List[ConstraintViolation]:
    """BIZ-07 占位: 归属冲突校验"""
    return []


def check_multi_product_violation(plan, world_state, rule) -> List[ConstraintViolation]:
    """BIZ-08 占位: 多产品线策略校验"""
    return []


def check_approval_violation(plan, world_state, rule) -> List[ConstraintViolation]:
    """BIZ-09 占位: 决策审批层级校验"""
    return []


def build_default_registry() -> BIZSigningRegistry:
    """构建默认 BIZ 注册表 (BIZ-01~09 占位)"""
    registry = BIZSigningRegistry()
    for biz_id, predicate_name, scope, severity in [
        ("BIZ-01", "check_cadence_violation", "All stores, all tiers", "WARNING"),
        ("BIZ-02", "check_three_per_month_violation", "Tier A/B stores", "WARNING"),
        ("BIZ-03", "check_deferral_violation", "All visits, deferral scenarios", "WARNING"),
        ("BIZ-04", "check_key_store_violation", "Tier=Key stores", "CRITICAL_INCIDENT"),
        ("BIZ-05", "check_gps_violation", "All SFA/CRM events", "WARNING"),
        ("BIZ-06", "check_workload_violation", "All field reps", "WARNING"),
        ("BIZ-07", "check_ownership_violation", "All visit conflicts", "WARNING"),
        ("BIZ-08", "check_multi_product_violation", "Multi-brand stores", "WARNING"),
        ("BIZ-09", "check_approval_violation", "All candidate plans", "WARNING"),
    ]:
        rule = BIZRule(
            biz_id=biz_id,
            version="v1.0-DRAFT",
            scope=scope,
            predicate_name=predicate_name,
            severity_on_violation=severity,
        )
        # 通过 globals 查 predicate 函数
        predicate = globals()[predicate_name]
        registry.register(rule, predicate)
    return registry
