"""Shadow Mode 公共模块 (BIZ 无关 — 不加载 BIZ 规则)

本包为 ShadowReplayRunner 的子模块基础之一, 当前只包含 InputSnapshot.
DataPrechecker / ReadOnlyGuard / ReplayMetrics / BaselineComparator 待后续按需加入.

严格红线:
- 不修改 MVP 主流程 (vertical_slice_mvp.py)
- 不加载 BIZ 业务规则
- 不写回 WorldState
- 不下发到 SFA/CRM
- 不创建新状态报告版本
"""
