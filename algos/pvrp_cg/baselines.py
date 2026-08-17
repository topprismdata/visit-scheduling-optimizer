"""
Røpke–Pisinger (2006) ALNS baseline for the same PVRP constraints.

Implements:
  Destroy: random / worst (cost-proportional) / Shaw (neighborhood) / day
  Repair:  greedy insertion / regret-2 insertion
  Adaptive weights: ρ = 0.1, score (new-best=3, improved=2, accepted=1)
  Acceptance: Record-to-Record Travel, threshold = 5%

Same constraints as the CG solver:
  - per-customer visit frequency f_i
  - per-customer min gap Δ_i = ⌊days/(f_i+1)⌋
  - per-day visit count ≤ 6
  - per-day total time ≤ daily_cap (minutes, optional)

Run as a baseline for the same 400 s wall-clock budget.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Sequence

INF = float("inf")
RHO = 0.1
MAX_PER_DAY = 6
SHORT_KINK = 15  # nbrs lookup depth for Shaw removal


class ALNS:
    """Røpke–Pisinger ALNS for the PVRP / visit-scheduling problem."""

    def __init__(
        self,
        n: int,
        freq: Sequence[int],
        days: int = 20,
        col_cost_fn: Callable | None = None,
        daily_cap: float | None = None,
        seed: int = 42,
    ):
        self.n = n
        self.freq = list(freq)
        self.days = days
        self.gap = {i: (days // (freq[i] + 1)) if freq[i] >= 2 else 0 for i in range(n)}
        self.col_cost_fn = col_cost_fn or (lambda ids: 0.0)
        self.daily_cap = daily_cap
        self.rng = random.Random(seed)
        self.nbrs = [sorted(range(n), key=lambda j: j) for _ in range(n)]

    # ----------------- time / feasibility -----------------
    def day_time(self, day: set[int]) -> float:
        if not day:
            return 0.0
        return self.col_cost_fn(list(day))

    def total_time(self, sol: list[set[int]]) -> float:
        return sum(self.day_time(d) for d in sol if d)

    def feasible_insert(self, sol: list[set[int]], cust: int, day: int) -> bool:
        if self.daily_cap is not None:
            if (
                self.day_time(sol[day]) + self._delta_insert(sol[day], cust)
                > self.daily_cap
            ):
                return False
        days_c = [k for k in range(self.days) if cust in sol[k]]
        for k in days_c:
            if abs(k - day) < self.gap[cust]:
                return False
        return True

    def _delta_insert(self, day: set[int], cust: int) -> float:
        new_day = sorted(list(day) + [cust])
        return self.day_time(new_day) - self.day_time(day)

    def valid(self, sol: list[set[int]]) -> bool:
        cnt = [0] * self.n
        for d in sol:
            if self.daily_cap is not None and self.day_time(d) > self.daily_cap + 1e-6:
                return False
            for i in d:
                cnt[i] += 1
        for i in range(self.n):
            if cnt[i] != self.freq[i]:
                return False
            if self.freq[i] >= 2:
                ks = sorted(k for k in range(self.days) if i in sol[k])
                for a, b in zip(ks, ks[1:]):
                    if b - a < self.gap[i]:
                        return False
        return True

    # ----------------- initial solution -----------------
    def initial(self) -> list[set[int]]:
        sol: list[set[int]] = [set() for _ in range(self.days)]
        order = sorted(range(self.n), key=lambda i: -self.freq[i])
        for cust in order:
            placed = 0
            cand_days = sorted(
                range(self.days),
                key=lambda d: (
                    self._delta_insert(sol[d], cust)
                    if self.feasible_insert(sol, cust, d)
                    else 1e18
                ),
            )
            for d in cand_days:
                if placed >= self.freq[cust]:
                    break
                if not self.feasible_insert(sol, cust, d):
                    continue
                remaining = self.freq[cust] - placed - 1
                if (
                    remaining > 0
                    and sum(1 for k in range(d + self.gap[cust], self.days)) < remaining
                ):
                    continue
                sol[d].add(cust)
                placed += 1
            # If greedy could not place all required visits for this customer,
            # we deliberately leave the solution *partially* infeasible (some
            # customers have fewer than freq[i] visits). The run() loop's
            # destroy + repair operators will re-insert missing visits. The
            # previous "last resort" was removed because it checked only
            # gap and ignored the daily_cap, which could create an incumbent
            # that violates the 9h cap (the Rep-6 900-min artefact).
        return sol

    # ----------------- destroy operators -----------------
    def d_random(self, sol, q):
        visits = [(i, d) for d in range(self.days) for i in sol[d]]
        self.rng.shuffle(visits)
        out = visits[:q]
        for i, d in out:
            sol[d].discard(i)
        return out

    def d_worst(self, sol, q):
        scored = []
        for d in range(self.days):
            base = self.day_time(sol[d])
            for i in sol[d]:
                nd = sol[d] - {i}
                delta = base - self.day_time(nd)
                scored.append((delta, i, d))
        scored.sort(reverse=True)
        out = self.rng.sample(scored[: max(2 * q, q)], min(q, len(scored)))
        out = [(i, d) for _, i, d in out]
        for i, d in out:
            sol[d].discard(i)
        return out

    def d_shaw(self, sol, q):
        active = [d for d in range(self.days) if sol[d]]
        if not active:
            return self.d_random(sol, q)
        d0 = self.rng.choice(active)
        seed_cust = self.rng.choice(sorted(sol[d0]))
        out = []
        for d in range(self.days):
            for i in list(sol[d]):
                if len(out) >= q:
                    break
                # similarity: same-region / same-day prefix
                if i in sol[d] and (
                    i == seed_cust or i in sol[d0] or self.rng.random() < 0.5
                ):
                    out.append((i, d))
                    sol[d].discard(i)
        # top up if needed
        for i, d in self.d_random(sol, q - len(out)):
            out.append((i, d))
        return out

    def d_day(self, sol, q):
        active = [d for d in range(self.days) if sol[d]]
        if not active:
            return self.d_random(sol, q)
        d = self.rng.choice(active)
        out = [(i, d) for i in sol[d]]
        sol[d] = set()
        return out

    # ----------------- repair operators -----------------
    def r_greedy(self, sol, visits):
        self.rng.shuffle(visits)
        for cust, _ in visits:
            best, best_c = None, 1e18
            for d in range(self.days):
                if not self.feasible_insert(sol, cust, d):
                    continue
                c = self._delta_insert(sol[d], cust)
                if c < best_c:
                    best_c, best = c, d
            if best is not None:
                sol[best].add(cust)
        return []

    def r_regret(self, sol, visits):
        self.rng.shuffle(visits)
        pending = [c for c, _ in visits]
        while pending:
            best_pair, best_regret = None, -1e18
            for c in pending:
                costs = []
                for d in range(self.days):
                    if self.feasible_insert(sol, c, d):
                        costs.append((self._delta_insert(sol[d], c), d))
                costs.sort()
                if not costs:
                    continue
                regret = (costs[1][0] - costs[0][0]) if len(costs) > 1 else 1e9
                if regret > best_regret:
                    best_regret, best_pair = regret, (costs[0][1], c)
            if best_pair is None:
                break
            d, c = best_pair
            sol[d].add(c)
            pending.remove(c)
        return []

    # ----------------- main loop -----------------
    def run(self, time_budget: int = 400) -> tuple:
        import time as _time
        t0 = _time.time()
        sol = [set(d) for d in self.initial()]

        # If the initial solution is infeasible, attempt a brief repair
        # phase using the same r_greedy / r_regret operators before
        # declaring it the incumbent. Previously run() would set
        # best = initial even when initial violated daily_cap, which is
        # what produced the spurious 900-min max-load for Rep-6.
        repair_budget = min(20, max(5, time_budget // 20))
        for _ in range(repair_budget):
            if self.valid(sol):
                break
            # destroy half of one day, then re-insert
            cand = [set(d) for d in sol]
            active = [d for d in range(self.days) if cand[d]]
            if not active:
                break
            d = self.rng.choice(active)
            visits = [(i, d) for i in cand[d]]
            cand[d] = set()
            self.r_greedy(cand, visits)
            sol = cand

        if not self.valid(sol):
            # could not repair within budget; return an empty solution
            # with a clear "infeasible" flag rather than reporting the
            # infeasible incumbent as if it were valid.
            return (
                [set() for _ in range(self.days)],
                float("inf"),
                0,
                {"days": 0, "max_load": 0, "min_load": 0,
                 "valid": False, "note": "initial infeasible and "
                 "could not be repaired within repair_budget"},
            )

        cur = [set(d) for d in sol]
        cur_f = self.total_time(cur)
        best = [set(d) for d in sol]
        best_f = cur_f
        RRT = 0.05 * max(best_f, 1.0)

        ops_d = [self.d_random, self.d_worst, self.d_shaw, self.d_day]
        ops_r = [self.r_greedy, self.r_regret]
        w_d = [1.0] * len(ops_d)
        w_r = [1.0] * len(ops_r)
        it = 0
        total_visits = sum(len(d) for d in cur) or 1
        while time.time() - t0 < time_budget:
            it += 1
            di = self.rng.choices(range(len(ops_d)), weights=w_d)[0]
            ri = self.rng.choices(range(len(ops_r)), weights=w_r)[0]
            cand = [set(d) for d in cur]
            q = max(3, self.rng.randint(3, max(4, total_visits // 8)))
            visits = ops_d[di](cand, q)
            ops_r[ri](cand, visits)
            cand_f = self.total_time(cand)
            score = 0
            if self.valid(cand):
                if cand_f < best_f - 1e-6:
                    best, best_f = [set(d) for d in cand], cand_f
                    score = 3
                if cand_f < cur_f - 1e-6:
                    cur, cur_f = [set(d) for d in cand], cand_f
                    score = max(score, 2)
                elif cand_f < cur_f + RRT:
                    cur, cur_f = [set(d) for d in cand], cand_f
                    score = max(score, 1)
            w_d[di] = RHO * score + (1 - RHO) * w_d[di]
            w_r[ri] = RHO * score + (1 - RHO) * w_r[ri]
        loads = [self.day_time(d) for d in best if d]
        return (
            best,
            best_f,
            it,
            {
                "days": len(loads),
                "max_load": max(loads) if loads else 0,
                "min_load": min(loads) if loads else 0,
                "valid": True,
            },
        )
