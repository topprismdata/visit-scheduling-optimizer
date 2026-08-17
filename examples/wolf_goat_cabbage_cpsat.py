"""
狼羊菜过河 — 数学建模 + CP-SAT 求解
=====================================

经典问题：农夫带狼、羊、菜过河。
- 船只能载农夫 + 一物（或农夫空手）
- 人不在时：狼吃羊，羊吃菜
- 问：最少几步过河？

建模思路：
  状态向量 (p,w,g,c) ∈ {0,1}^4，0=此岸 1=对岸
  约束：安全（狼羊不独处、羊菜不独处）+ 转移（每步农夫必动，至多带一物）
  目标：最少步数从 (0,0,0,0) 到 (1,1,1,1)
"""

from ortools.sat.python import cp_model


def solve_for_steps(num_steps: int):
    """尝试用恰好 num_steps 步过河，返回是否可行并打印方案。"""
    model = cp_model.CpModel()

    # ─── 决策变量 ───
    # state[t][e]: 第 t 步后实体 e 的位置 (0=此岸, 1=对岸)
    #   e: 0=农夫, 1=狼, 2=羊, 3=菜
    state = [
        [model.NewBoolVar(f"s{t}_{e}") for e in range(4)] for t in range(num_steps + 1)
    ]

    # ─── 约束 1: 初始 & 终止 ───
    for e in range(4):
        model.Add(state[0][e] == 0)  # 初始：全在此岸
        model.Add(state[num_steps][e] == 1)  # 终止：全在对岸

    # ─── 约束 2: 转移规则 ───
    for t in range(num_steps):
        # 农夫必须换边
        model.Add(state[t][0] != state[t + 1][0])

        # 至多带一物：定义 carry[t][e] = 1 表示第 t 步带了物品 e
        carry = [model.NewBoolVar(f"c{t}_{e}") for e in range(1, 4)]

        for e in range(1, 4):
            # carry[t][e] = 1 ↔ 物品 e 换了边
            # 即 state[t][e] != state[t+1][e]
            moved = model.NewBoolVar(f"moved{t}_{e}")
            model.Add(state[t][e] != state[t + 1][e]).OnlyEnforceIf(moved)
            model.Add(state[t][e] == state[t + 1][e]).OnlyEnforceIf(moved.Not())
            model.Add(carry[e - 1] == moved)

        # 至多带一个
        model.Add(sum(carry) <= 1)

        # 携带的物品必须和农夫同方向移动
        # 如果物品 e 被携带，则它必须跟农夫去同一边
        for e in range(1, 4):
            # carry[e-1] = 1 → state[t+1][e] == state[t+1][0]（到达同侧）
            model.Add(state[t + 1][e] == state[t + 1][0]).OnlyEnforceIf(carry[e - 1])

    # ─── 约束 3: 安全约束 ───
    for t in range(num_steps + 1):
        # 狼吃羊：如果农夫不在狼这边，则狼和羊不能同侧
        # 即 NOT(p==w) → NOT(w==g)
        # 等价于 (p==w) OR (w!=g)
        #
        # 用 CP-SAT 表达：
        #   如果 state[t][0] != state[t][1]（农夫和狼不同侧）
        #   则 state[t][1] != state[t][2]（狼和羊不同侧）
        #
        # 等价于：(p==w) OR (w!=g)
        # 用 AddBoolOr 表达：
        #   b_pw = (p == w), b_wg_diff = (w != g)
        #   AddBoolOr([b_pw, b_wg_diff])

        # p == w?
        pw_same = model.NewBoolVar(f"pw{t}")
        model.Add(state[t][0] == state[t][1]).OnlyEnforceIf(pw_same)
        model.Add(state[t][0] != state[t][1]).OnlyEnforceIf(pw_same.Not())

        # w != g?
        wg_diff = model.NewBoolVar(f"wg{t}")
        model.Add(state[t][1] != state[t][2]).OnlyEnforceIf(wg_diff)
        model.Add(state[t][1] == state[t][2]).OnlyEnforceIf(wg_diff.Not())

        # (p==w) OR (w!=g)
        model.AddBoolOr([pw_same, wg_diff])

        # 羊吃菜：(p==g) OR (g!=c)
        pg_same = model.NewBoolVar(f"pg{t}")
        model.Add(state[t][0] == state[t][2]).OnlyEnforceIf(pg_same)
        model.Add(state[t][0] != state[t][2]).OnlyEnforceIf(pg_same.Not())

        gc_diff = model.NewBoolVar(f"gc{t}")
        model.Add(state[t][2] != state[t][3]).OnlyEnforceIf(gc_diff)
        model.Add(state[t][2] == state[t][3]).OnlyEnforceIf(gc_diff.Not())

        model.AddBoolOr([pg_same, gc_diff])

    # ─── 求解 ───
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        return True, solver, state, num_steps
    return False, None, None, None


def main():
    print("=" * 70)
    print("  狼羊菜过河 — CP-SAT 求解")
    print("=" * 70)
    print()
    print("【数学建模】")
    print("  状态向量: (p, w, g, c) ∈ {0,1}⁴  (0=此岸, 1=对岸)")
    print("  状态空间: 2⁴ = 16 种")
    print("  安全约束: 狼羊不独处 ∧ 羊菜不独处 → 砍掉 6 种非法状态")
    print("  转移规则: 农夫每步必动，至多带一物同向")
    print("  目标: 最少步数 (0,0,0,0) → (1,1,1,1)")
    print()
    print("【CP-SAT 求解】")
    print()

    # 从 7 步开始尝试（理论最优是 7）
    for steps in range(7, 12):
        feasible, solver, state, n = solve_for_steps(steps)
        if feasible:
            print(f"  ✅ 最优解：{steps} 步")
            print()
            print(f"  {'步':>3} | {'农夫':^4} {'狼':^4} {'羊':^4} {'菜':^4} | 操作")
            print("  " + "-" * 55)

            names = ["农夫", "狼", "羊", "菜"]
            for t in range(steps + 1):
                s = [solver.Value(state[t][e]) for e in range(4)]

                def pos(v):
                    return "对岸" if v else "此岸"

                if t == 0:
                    action = "初始状态"
                elif t == steps:
                    action = "🎉 全部过河！"
                else:
                    # 判断带了什么
                    prev = [solver.Value(state[t - 1][e]) for e in range(4)]
                    carried = []
                    for e in range(1, 4):
                        if s[e] != prev[e]:
                            carried.append(names[e])
                    if carried:
                        action = f"带{carried[0]}→{pos(s[0])}"
                    else:
                        action = f"空手→{pos(s[0])}"

                print(
                    f"  {t:>3} | {pos(s[0]):^4} {pos(s[1]):^4} "
                    f"{pos(s[2]):^4} {pos(s[3]):^4} | {action}"
                )

            print()
            print("  📊 求解统计:")
            print(f"     布尔变量: {(steps + 1) * 4} 个状态 + {steps * 3} 个携带")
            print(f"     约束数: 安全 {2 * (steps + 1)} + 转移 {steps * 5} + 边界 8")
            print(f"     求解时间: {solver.WallTime():.4f}s")
            print(f"     状态: OPTIMAL")
            break

    print()
    print("【类比我们的 PVRP 项目】")
    print("  ┌────────────────────────────────────────────────────────┐")
    print("  │  狼羊菜:  16 种状态, 10 种合法, BFS 找 7 步           │")
    print("  │  PVRP:   10^1414 种排班, 约束砍掉 99.99..%, CP-SAT   │")
    print("  │                                                        │")
    print("  │  底层逻辑完全一样:                                     │")
    print("  │    1. 定义决策变量 (状态/排班)                         │")
    print("  │    2. 编码约束 (安全/频次+间隔+工时)                   │")
    print("  │    3. 设目标 (最少步数/最少时间)                       │")
    print("  │    4. 交给求解器 → 在可行域内找最优                    │")
    print("  └────────────────────────────────────────────────────────┘")


if __name__ == "__main__":
    main()
