# -*- coding: utf-8 -*-
"""Sales Visit Dispatch Agent (销售拜访动态调度副驾智能体).

Agentic 核心架构:
- World Model (业务世界状态): 维护业代当前位置、已完成打卡前缀、剩余计划路线、路网模型.
- Event Stream (事件驱动): 接收 AdHocVisitRequest(新增加盟店/临时巡检店/突发补录单).
- Tool Calling (工具编排): 调用 CorridorDynamicInsertionTool 进行毫秒级走廊投影与顺路插单.
- Reasoning & Copilot (可解释决策生成): 输出结构化调度指令与人性化的自然语言业代指引.
"""
import time
from algos.agentic.corridor_insertion import CorridorDynamicInsertionTool


class SalesVisitDispatchAgent:
    """销售拜访动态调度副驾智能体."""

    def __init__(self, rep_name: str, date_str: str, planned_route: list[int],
                 D, store_info: dict):
        """
        参数:
          rep_name: 业代姓名 (如 '梁健满')
          date_str: 日期 (如 '2026-07-01')
          planned_route: 今日早晨初始计划路线 [store_idx_0, store_idx_1, ...]
          D: 骑行路网矩阵 (公里)
          store_info: 门店元数据字典 {idx: {"code": ..., "name": ..., "address": ...}}
        """
        self.rep_name = rep_name
        self.date_str = date_str
        self.D = D
        self.store_info = store_info

        # Agent 维护的内部世界状态 (World State)
        self.active_route = list(planned_route)
        self.visited_indices = []       # 已打卡前缀 (冻结)
        self.current_idx = planned_route[0] if planned_route else None
        self.tool = CorridorDynamicInsertionTool()

    def record_checkin(self, store_idx: int):
        """事件驱动: 业代完成一家门店打卡, 推进世界状态."""
        if store_idx in self.active_route:
            self.visited_indices.append(store_idx)
            self.current_idx = store_idx

    def handle_adhoc_request(self, adhoc_store_indices: list[int]) -> dict:
        """事件驱动: 收到当日大批量临时加店请求, 触发 Agent 决策闭环."""
        t0 = time.time()
        num_adhoc = len(adhoc_store_indices)
        current_loc_name = self.store_info.get(self.current_idx, {}).get("name", "当前位置")

        # 1. 工具调用: 沿街走廊动态插单 (冻结已完成前缀)
        res = self.tool.insert_adhoc_batch(
            active_route=self.active_route,
            adhoc_stores=adhoc_store_indices,
            D=self.D,
            visited_prefix_len=len(self.visited_indices)
        )

        old_km = res["old_km"]
        new_km = res["new_km"]
        detour_km = res["detour_km"]
        elapsed_ms = res["elapsed_ms"]

        # 更新 Agent 世界状态
        self.active_route = res["new_route"]

        # 2. 业务评估 (工时与骑行耗时)
        # 按城市电单车/自行车平均时速 15 km/h 计算通行耗时
        extra_cycling_min = round(detour_km / 15.0 * 60, 1)
        # 每家门店在店服务时长基准 7 分钟
        extra_service_min = num_adhoc * 7
        total_extra_min = round(extra_cycling_min + extra_service_min)

        # 3. 提取关键插入片段, 构建自然语言可解释性建议
        key_instructions = []
        for item in res["insertions"][:3]:  # 举前 3 家为例
            s_idx = item["store"]
            s_meta = self.store_info.get(s_idx, {})
            pos = self.active_route.index(s_idx)
            prev_name = self.store_info.get(self.active_route[pos - 1], {}).get("name", "起点") if pos > 0 else "首站"
            next_name = self.store_info.get(self.active_route[pos + 1], {}).get("name", "终点") if pos < len(self.active_route) - 1 else "末站"
            d_km = item.get("detour_km", 0.0)
            key_instructions.append(
                f"在拜访完【{prev_name}】后，顺路前往新增的【{s_meta.get('name', '临时店')}】(预计绕行仅 {d_km*1000:.0f} 米)，随后前往【{next_name}】"
            )

        explanation_text = (
            f"【{self.rep_name} 师傅调度指引 · {self.date_str}】\n"
            f"收到今日临时新增 {num_adhoc} 家拜访门店需求。\n"
            f"智能体已完成沿街走廊顺路分析（耗时 {elapsed_ms} 毫秒）：\n"
            f"- 路线调整：今日总行程从 {old_km} km 微调至 {new_km} km，仅净增绕行 {detour_km} km；\n"
            f"- 耗时预估：增加骑行时间约 {extra_cycling_min} 分钟，在店操作约 {extra_service_min} 分钟，预计多耗时 {total_extra_min} 分钟；\n"
            f"- 关键调度建议：\n" + "\n".join(f"  • {inst}" for inst in key_instructions)
        )

        return {
            "status": "SUCCESS",
            "rep_name": self.rep_name,
            "date": self.date_str,
            "adhoc_count": num_adhoc,
            "old_km": old_km,
            "new_km": new_km,
            "detour_km": detour_km,
            "extra_cycling_min": extra_cycling_min,
            "extra_service_min": extra_service_min,
            "total_extra_min": total_extra_min,
            "elapsed_ms": elapsed_ms,
            "full_route": self.active_route,
            "explanation": explanation_text
        }
