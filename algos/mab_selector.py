"""多臂老虎机自适应算子选择器 (Multi-Armed Bandit ALNS) — 方案二。

以 UCB1 (Upper Confidence Bound) 置信上界替代 ALNS 传统的自适应权重分段:
- 冷启动阶段: 对每个算子臂按声明序严格轮转探索一次, 消除零先验偏差;
- 热阶段: 按 UCB1 得分 Q̄_i + c·√(ln N / n_i) 择臂 — 利用项 (均值奖励)
  与探索项 (置信半径) 平衡, 高收益算子 (如 spatial_cluster_destroy)
  在多轮奖励强化后自然占据主导抽取频次, 低收益算子仍保有对数级探索。

参考: Auer, Cesa-Bianchi & Fischer (2002), "Finite-time Analysis of the
Multiarmed Bandit Problem", Machine Learning 47(2-3):235-256.
"""

import math
from typing import Dict, List

__all__ = ["UCB1Selector"]


class UCB1Selector:
    """UCB1 多臂老虎机算子选择器。

    select_arm() 为纯读操作 (不改变内部状态); 冷启动游标由拉动计数驱动 —
    仅当 update() 记录拉动后才推进轮转。 Attributes:
        arms: 算子臂名列表 (声明序, 用于冷启动轮转与并列裁决)。
        c: 探索常数, 默认 √2 ≈ 1.414; 越大越偏探索, 越小越偏利用。
        pulls: 各臂累计拉动次数。
        total_rewards: 各臂累计奖励。
        mean_rewards: 各臂平均奖励 (热阶段利用项)。
    """

    def __init__(self, arms: List[str], c: float = 1.414) -> None:
        if not arms:
            raise ValueError("算子臂池不能为空: 至少需要一个臂")
        if len(set(arms)) != len(arms):
            raise ValueError(f"算子臂必须唯一, 发现重复: {arms}")
        if not (isinstance(c, (int, float)) and math.isfinite(c) and c > 0.0):
            raise ValueError(f"探索常数 c 必须为正有限值, 收到 {c!r}")
        self.arms: List[str] = list(arms)
        self.c = float(c)
        self.pulls: Dict[str, int] = {arm: 0 for arm in self.arms}
        self.total_rewards: Dict[str, float] = {arm: 0.0 for arm in self.arms}

    @property
    def mean_rewards(self) -> Dict[str, float]:
        """各臂平均奖励; 未拉动的臂为 0.0。"""
        return {
            arm: (self.total_rewards[arm] / n if n > 0 else 0.0)
            for arm, n in self.pulls.items()
        }

    def select_arm(self) -> str:
        """返回本轮应使用的算子臂; 纯读操作, 不改变任何内部状态。

        冷启动 (存在零拉动臂): 按声明序返回首个未探索臂, 保证每臂至少
        探索一次; 热阶段: 返回 UCB1 得分最高的臂, 得分并列时取声明序
        靠前者 (确定性裁决)。
        """
        if min(self.pulls.values()) == 0:
            for arm in self.arms:
                if self.pulls[arm] == 0:
                    return arm

        total_pulls = sum(self.pulls.values())
        log_total = math.log(total_pulls)
        best_arm, best_score = self.arms[0], -math.inf
        for arm in self.arms:
            mean = self.total_rewards[arm] / self.pulls[arm]
            explore = self.c * math.sqrt(log_total / self.pulls[arm])
            score = mean + explore
            if score > best_score:
                best_arm, best_score = arm, score
        return best_arm

    def update(self, arm: str, reward: float) -> None:
        """记录一次拉动: 累加该臂拉动次数与奖励。

        Args:
            arm: 本轮实际使用的算子臂 (必须已注册)。
            reward: 本轮奖励 (必须为有限浮点值, 正负皆可)。
        """
        if arm not in self.pulls:
            raise ValueError(f"未知算子臂 {arm!r}, 已注册: {self.arms}")
        if not math.isfinite(reward):
            raise ValueError(f"奖励必须为有限值, 收到 {reward!r}")
        self.pulls[arm] += 1
        self.total_rewards[arm] += float(reward)
