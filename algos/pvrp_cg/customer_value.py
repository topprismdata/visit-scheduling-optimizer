"""CustomerValueModel — 从执行结果中学习客户价值评分 (Phase 2)。

输入 ActualVisit 列表，输出每个客户的动态 value_score + confidence。
不硬编码，而是从 Plan vs Actual 偏差中提炼可解释信号。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Sequence

from .planning import ActualVisit, BusinessSignal


class CustomerValueModel:
    """从执行结果中学习客户价值评分。

    当前实现: 规则引擎（可解释、无训练依赖），适合 Phase 2 初期。
    Phase 3 深化方向: 接入贝叶斯模型 / 强化学习。
    """

    def __init__(
        self,
        completion_weight: float = 0.3,
        service_quality_weight: float = 0.25,
        frequency_adherence_weight: float = 0.25,
        recency_weight: float = 0.2,
    ):
        total = sum([completion_weight, service_quality_weight,
                     frequency_adherence_weight, recency_weight])
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"权重之和必须 = 1.0, 实际 {total}")
        self.w_completion = completion_weight
        self.w_service = service_quality_weight
        self.w_freq = frequency_adherence_weight
        self.w_recency = recency_weight

    def compute_scores(
        self,
        actual_visits: Sequence[ActualVisit],
        required_freq: dict[str, int] | None = None,
    ) -> tuple[dict[str, float], dict[str, float], list[BusinessSignal]]:
        """从实际拜访列表计算每个客户的价值评分和置信度。

        Args:
            actual_visits: 执行结果列表。
            required_freq: customer_id → 目标月频次 (None = 用实际值作为参考基线)。

        Returns:
            (scores, confidences, signals)
            scores: customer_id → value_score [0,1]
            confidences: customer_id → confidence [0,1]
            signals: 生成的 BusinessSignal 列表
        """
        by_customer: dict[str, list[ActualVisit]] = defaultdict(list)
        for av in actual_visits:
            by_customer[av.customer_id].append(av)

        if not by_customer:
            return {}, {}, []

        # 群体统计
        all_completion_rates = []
        for c, visits in by_customer.items():
            comp = sum(1 for v in visits if v.outcome_code == "COMPLETED")
            all_completion_rates.append(comp / len(visits))
        baseline_completion = (
            sum(all_completion_rates) / len(all_completion_rates) if all_completion_rates else 0.5
        )

        scores: dict[str, float] = {}
        confidences: dict[str, float] = {}
        signals: list[BusinessSignal] = []

        now = datetime.now(timezone.utc)

        for cust, visits in sorted(by_customer.items()):
            n_visits = len(visits)

            # 维度 1: 完成率
            completed = sum(1 for v in visits if v.outcome_code == "COMPLETED")
            completion_rate = completed / n_visits
            completion_score = min(1.0, completion_rate)

            # 维度 2: 服务质量 (在店时间是否达到 ~45min 期望)
            svc_times = [v.service_minutes for v in visits if v.service_minutes > 0]
            expected_svc = 45.0
            if svc_times:
                avg_svc = sum(svc_times) / len(svc_times)
                service_score = min(1.0, avg_svc / expected_svc)
            else:
                service_score = 0.5

            # 维度 3: 频次遵守
            if required_freq and cust in required_freq:
                target = required_freq[cust]
                freq_score = min(1.0, n_visits / max(target, 1))
            else:
                freq_score = min(1.0, n_visits / 2.0)  # 无目标时假设 2 次/月为满

            # 维度 4: 时近性 (最近拜访距今越近得分越高)
            dates_sorted = sorted((v.actual_date for v in visits), reverse=True)
            if dates_sorted and hasattr(dates_sorted[0], 'toordinal'):
                ordinal_now = date.today().toordinal() if False else datetime.now(timezone.utc).toordinal()
                last_ord = dates_sorted[0].toordinal()
                days_since = max(0, ordinal_now - last_ord)
                recency_score = max(0.0, 1.0 - days_since / 30.0)
            else:
                recency_score = 0.5

            score = (
                completion_rate * self.w_completion
                + service_score * self.w_service
                + freq_score * self.w_freq
                + recency_score * self.w_recency
            )
            score = round(max(0.0, min(1.0, score)), 4)

            # 置信度 = log(n_visits+1) / log(max_n+1) 归一化
            max_n = max(len(v_list) for v_list in by_customer.values())
            confidence = round(
                min(1.0, __import__('math').log(n_visits + 1) /
                    __import__('math').log(max_n + 1)),
                4,
            )

            scores[cust] = score
            confidences[cust] = confidence

            signals.append(BusinessSignal(
                id=f"SIG-VALUE-{cust}",
                subject_type="customer",
                subject_id=cust,
                signal_type="strategic_priority",
                value=str(score),
                numeric_value=score,
                kind="inferred",
                source=f"CustomerValueModel(w_c={self.w_completion},w_s={self.w_service})",
                model_version="rule-engine-v1",
                confidence=confidence,
                observed_at=now,
                valid_from=now,
            ))

        return scores, confidences, signals