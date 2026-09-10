"""多臂老虎机自适应算子选择器 (Multi-Armed Bandit ALNS) 单元测试 — 方案二。

验证契约: UCB1Selector 在冷启动阶段对每个算子臂至少严格轮转探索一次;
热阶段按 UCB1 得分 Q̄ + c·√(ln N / n) 择臂, 高收益算子 (如
spatial_cluster_destroy) 经多轮奖励强化后抽取频次显著高于其他算子;
边界与异常输入 (空臂池 / 重复臂 / 非法 c / 未知臂 / 非有限奖励) 一律拒绝。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algos.mab_selector import UCB1Selector

# 模拟 ALNS 算子池: 高收益空间算子 + 三个普通算子
ARMS = [
    "spatial_cluster_destroy",
    "worst_removal",
    "random_removal",
    "regret_insert",
]


# ---------------------------------------------------------------------------
# 冷启动: 每个臂至少被探索一次
# ---------------------------------------------------------------------------


def test_cold_start_explores_every_arm_at_least_once():
    """前 |arms| 轮 select→update 必须覆盖全部算子臂, 无一遗漏。"""
    sel = UCB1Selector(ARMS)
    explored = []
    for _ in range(len(ARMS)):
        arm = sel.select_arm()
        explored.append(arm)
        sel.update(arm, 0.0)
    assert set(explored) == set(ARMS)
    assert len(explored) == len(set(explored))


def test_cold_start_round_robin_follows_declaration_order():
    """冷启动轮转确定性: 首轮严格按臂声明序各拉一次。"""
    sel = UCB1Selector(ARMS)
    first_cycle = []
    for _ in range(len(ARMS)):
        arm = sel.select_arm()
        first_cycle.append(arm)
        sel.update(arm, 0.0)
    assert first_cycle == ARMS
    # 冷启动结束后所有臂拉动次数均为 1
    assert all(count == 1 for count in sel.pulls.values())


def test_select_is_pure_without_update():
    """select_arm 为纯读操作: 不调用 update 时冷启动游标不推进、计数不变。"""
    sel = UCB1Selector(ARMS)
    assert sel.select_arm() == sel.select_arm() == ARMS[0]
    assert sel.pulls == {arm: 0 for arm in ARMS}
    assert sel.total_rewards == {arm: 0.0 for arm in ARMS}


# ---------------------------------------------------------------------------
# 强化学习收敛: 高收益算子频次显著占优
# ---------------------------------------------------------------------------


def test_high_reward_operator_dominates_after_reinforcement():
    """多轮奖励强化后, 高收益算子抽取频次 > 90% 且 ≥ 其他任一算子 10 倍。"""
    sel = UCB1Selector(ARMS)
    high = "spatial_cluster_destroy"
    n_rounds = 2000
    for _ in range(n_rounds):
        arm = sel.select_arm()
        sel.update(arm, 1.0 if arm == high else 0.1)
    assert sel.pulls[high] > 0.9 * n_rounds
    for other in ARMS:
        if other != high:
            assert sel.pulls[high] > 10 * sel.pulls[other], (
                f"{high} ({sel.pulls[high]}) 应显著高于 {other} ({sel.pulls[other]})"
            )


def test_negative_rewards_still_prefer_best_arm():
    """全负奖励环境下 UCB1 仍收敛到最不差 (损失最小) 的臂。"""
    sel = UCB1Selector(ARMS)
    best = "spatial_cluster_destroy"
    for _ in range(1000):
        arm = sel.select_arm()
        sel.update(arm, -0.1 if arm == best else -1.0)
    assert sel.pulls[best] > 0.8 * 1000
    assert sel.mean_rewards[best] == pytest.approx(-0.1, abs=1e-9)


def test_exploration_constant_controls_exploitation_strength():
    """c 极小 → 几乎纯利用; c 极大 → 探索项主导, 拉动次数趋近均衡。"""
    greedy = UCB1Selector(["good", "bad"], c=1e-3)
    for _ in range(500):
        arm = greedy.select_arm()
        greedy.update(arm, 1.0 if arm == "good" else 0.0)
    assert greedy.pulls["good"] >= 490

    explorer = UCB1Selector(["good", "bad"], c=100.0)
    for _ in range(500):
        arm = explorer.select_arm()
        explorer.update(arm, 1.0 if arm == "good" else 0.0)
    assert min(explorer.pulls.values()) >= 100


# ---------------------------------------------------------------------------
# 状态记账: 拉动次数与累积奖励
# ---------------------------------------------------------------------------


def test_update_accumulates_pulls_and_rewards():
    sel = UCB1Selector(ARMS)
    sel.update("worst_removal", 0.5)
    sel.update("worst_removal", 0.3)
    assert sel.pulls["worst_removal"] == 2
    assert sel.total_rewards["worst_removal"] == pytest.approx(0.8)
    assert sel.mean_rewards["worst_removal"] == pytest.approx(0.4)
    # 未拉动臂保持零值
    assert sel.pulls["random_removal"] == 0
    assert sel.total_rewards["random_removal"] == 0.0


def test_tie_breaks_deterministically_toward_earlier_arm():
    """对称奖励下 UCB 得分并列, 稳定选择声明序靠前的臂。"""
    sel = UCB1Selector(["left", "right"])
    sel.update("left", 0.5)
    sel.update("right", 0.5)
    assert sel.select_arm() == "left"


def test_single_arm_pool_always_selected():
    sel = UCB1Selector(["only_destroy"])
    for _ in range(5):
        assert sel.select_arm() == "only_destroy"
        sel.update("only_destroy", 0.42)
    assert sel.pulls["only_destroy"] == 5
    assert sel.total_rewards["only_destroy"] == pytest.approx(2.1)


# ---------------------------------------------------------------------------
# 边界与异常
# ---------------------------------------------------------------------------


def test_init_rejects_empty_arm_pool():
    with pytest.raises(ValueError, match="臂"):
        UCB1Selector([])


def test_init_rejects_duplicate_arms():
    with pytest.raises(ValueError, match="重复"):
        UCB1Selector(["a", "b", "a"])


def test_init_rejects_nonpositive_exploration_constant():
    for bad_c in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="c"):
            UCB1Selector(ARMS, c=bad_c)


def test_update_unknown_arm_rejected():
    sel = UCB1Selector(ARMS)
    with pytest.raises(ValueError, match="未知"):
        sel.update("ghost_destroy", 1.0)


def test_update_rejects_non_finite_reward():
    sel = UCB1Selector(ARMS)
    for bad_reward in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="有限"):
            sel.update("worst_removal", bad_reward)
    # 拒绝后状态未被污染
    assert sel.pulls["worst_removal"] == 0
    assert sel.total_rewards["worst_removal"] == 0.0
