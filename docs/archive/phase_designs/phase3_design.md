# Phase 3 设计：Adaptive Digital Manager / Continuous Learning

> 计划不再是月初一次性产物，而是在业务变化中持续更新
> 日期：2026-08-27
> 证据源：Palantir Scenarios + 优化建议 §5 + 世界模型综述 arXiv:2411.14499

## 一、核心设计原则

### 1.1 Rolling-horizon Re-planning

支持每日或每周滚动求解，每次重排生成新的 PlanVersion：

```text
Week 1 ──→ 执行 ──→ ActualVisit ──→ 增量重算 ──→ PlanVersion@v2
                                    ↑
                             新事件: 客户取消 / 新机会 / 销售请假
```

**冻结规则：**
- 已完成拜访：固定（不可修改）
- 未来 3 天内的拜访：frozen（不可移动，但可取消）
- 已确认拜访（经理 locked）：不可移动
- 未受影响的客户：尽量保持原日期（稳定性优先）

### 1.2 稳定性预算

每次重算的变化幅度受预算约束：

| 维度 | 预算 | 说明 |
|---|---|---|
| 最大变更客户数 | configurable | 每轮最多改变多少客户的拜访日期 |
| 最大变更拜访数 | configurable | 每轮最多改变多少条拜访记录 |
| 临近惩罚 | 指数衰减 | 离执行日期越近的变更惩罚越大 |
| 已确认客户冻结 | 硬约束 | 经理 locked 的客户不可移动 |

### 1.3 三类学习模型

#### 旅行与驻留时间模型（回归 → 校准）

```python
class TravelTimeModel:
    """预测 travel/service residual，按区域、时段和客户类型校准。"""
    def predict(self, origin, dest, county, time_of_day, customer_type) -> float:
        """返回预测的分钟/公里。"""
    
    def monitor_drift(self, actuals: list[ActualVisit]) -> dict:
        """监控 fallback 比例、漂移和异常值。"""
        return {"drift_detected": bool, "fallback_ratio": float, "anomalies": [...]}
```

#### 计划接受与执行模型（分类 → 调整）

```python
class PlanAcceptanceModel:
    """预测推荐被经理接受的概率。"""
    def predict_acceptance(self, change: dict) -> float:
        """返回 0-1 概率。"""
    
    def identify_frequent_overrides(self, overrides: list[ManualOverride]) -> list[str]:
        """识别频繁被人工覆盖的规则。"""
        # 不把人工覆盖自动视为"错误"，必须记录原因
```

#### 业务响应模型（因果推断 → 策略）

```python
class BusinessResponseModel:
    """学习拜访后的业务响应（区分相关性与增量效果）。"""
    def estimate_effect(self, visit_frequency: int, customer_id: str) -> dict:
        """返回增量效果估计，含置信区间。"""
    
    def evaluate_strategy_change(self, old_policy, new_policy, historical_data) -> dict:
        """离线评估策略变更的预期影响。"""
        # 不允许未经评估直接改变客户覆盖策略
```

### 1.4 安全上线顺序

```text
离线回放 → 影子推荐 → 经理审阅 → 小范围受控上线 → 扩大覆盖
```

每阶段必须保留：
- 模型版本
- 特征版本
- 策略版本
- 回放指标
- 数据漂移指标
- 人工审批记录
- 回滚能力

---

## 二、与现有架构的关系

### 2.1 PlanVersion 生命周期扩展

```python
@dataclass(frozen=True)
class PlanVersion:
    ...
    # Phase 3 增加
    parent_plan_id: str | None = None   # 被替代的计划
    triggered_by: str = "scheduled"      # "scheduled" / "event" / "manual"
    triggering_event_ref: str | None = None  # 触发事件引用
    stability_metrics: dict | None = None    # 相对父计划的变更统计
    model_versions: dict | None = None       # 使用的学习模型版本
```

### 2.2 增量重算接口

```python
def incremental_replan(
    existing_plan: PlanVersion,
    actual_visits: list[ActualVisit],
    new_events: list[PlanningEvent],    # 客户取消 / 新机会 / 请假
    models: LearningModels,              # 三类学习模型
    policy: DynamicPlanningPolicy,
    change_budget: ChangeBudget,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """滚动重算 → 新版本 (v+1)，受稳定性预算约束。"""
```

### 2.3 影子运行管道

```python
def shadow_run(
    plan: PlanVersion,
    actual: list[ActualVisit],
    proposed_policy: DynamicPlanningPolicy,
    overrides: list[ManualOverride],
) -> ShadowReport:
    """离线回放：新策略 vs 旧策略 vs 实际执行，三路对比。"""
```

---

## 三、验收标准

- [ ] 新业务事件（客户取消/新机会）可触发增量重排，产生新 PlanVersion
- [ ] 增量重排后，未受影响的客户 ≥ 80% 保持原日期
- [ ] 三类学习模型可离线回放和版本比较
- [ ] 自动策略更新前必须经过审批（影子运行 → 经理审阅 → 上线）
- [ ] 可以证明新策略相对基线改善了哪些指标（价值覆盖、效率、合规）