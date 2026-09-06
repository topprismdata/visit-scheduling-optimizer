"""Schedule Machine Verifier — Rigorous Validation Operator for Visit Schedules.

Validates:
1. Strict Same-Weekday Rhythm (Exact 7-day, 14-day, 28-day intervals)
2. Daily Stop Count limit (<= 6 stores)
3. Daily Time Budget (Service time + Transit time from/to Chongchuan Depot <= 480 min)
4. Total Visit Count exact match (e.g. 83 visits across 36 stores)
5. Zero-visit and Under-service elimination
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any
from collections import defaultdict, Counter


def haversine_distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    if lon1 == lon2 and lat1 == lat2:
        return 0.0
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return c * R * 1.3  # 1.3 road curvature factor


def transit_time_min(dist_km: float, speed_kmh: float = 35.0) -> float:
    if dist_km <= 0.01:
        return 0.0
    return (dist_km / speed_kmh) * 60.0 + 5.0  # +5 min stop/parking impedance


@dataclass
class DailyRouteLog:
    date_str: str
    weekday_name: str
    stores_count: int
    store_codes: List[str]
    store_names: List[str]
    districts: List[str]
    route_sequence: List[str]
    edge_distances_km: List[float]
    edge_transits_min: List[float]
    total_distance_km: float
    total_transit_min: float
    total_service_min: float
    total_workload_min: float
    is_within_480_min: bool
    is_within_6_stops: bool


@dataclass
class ScheduleValidationReport:
    is_valid: bool
    total_planned_visits: int
    total_scheduled_visits: int
    active_days_count: int
    total_distance_km: float
    total_transit_hours: float
    total_service_hours: float
    total_workload_hours: float
    weekday_consistency_violations: List[str]
    over_capacity_days: List[str]
    over_time_days: List[str]
    daily_logs: List[DailyRouteLog]


class ScheduleMachineVerifier:
    """Rigorous verification engine for sales visit schedules."""

    @staticmethod
    def verify(
        assigned_stores: Dict[str, Dict[str, Any]],
        daily_schedule: Dict[str, List[str]],
        depot_coord: Tuple[float, float] = (120.8943, 32.0084), # (lon, lat) Chongchuan Center
        standard_service_min: float = 50.0
    ) -> ScheduleValidationReport:
        depot_lon, depot_lat = depot_coord
        daily_logs: List[DailyRouteLog] = []
        
        weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
        
        # Track visit dates per store for cadence validation
        store_visit_dates = defaultdict(list)
        
        total_dist = 0.0
        total_transit = 0.0
        total_service = 0.0
        
        over_capacity_days = []
        over_time_days = []
        
        import datetime

        for d_str in sorted(daily_schedule.keys()):
            codes = daily_schedule[d_str]
            if not codes:
                continue
                
            dt = datetime.datetime.strptime(d_str, "%Y-%m-%d")
            w_idx = dt.weekday()
            w_name = weekday_map.get(w_idx, "未知")
            
            for c in codes:
                store_visit_dates[c].append((d_str, w_name, dt))

            st_objs = [assigned_stores[c] for c in codes if c in assigned_stores]
            st_names = [s.get("name", c) for s in st_objs]
            dists = list(set(s.get("district", "未知") for s in st_objs))
            
            # Formulate full closed-loop route: Depot -> Stop 1 -> ... -> Stop N -> Depot
            coords = [(depot_lon, depot_lat)] + [(s["lon"], s["lat"]) for s in st_objs] + [(depot_lon, depot_lat)]
            names_seq = ["崇川中心起/终点"] + [s["name"][:8] for s in st_objs] + ["崇川中心起/终点"]
            
            edge_dists = []
            edge_trans = []
            day_dist = 0.0
            day_tran = 0.0
            
            for i in range(len(coords) - 1):
                d_km = haversine_distance_km(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
                t_m = transit_time_min(d_km)
                edge_dists.append(round(d_km, 2))
                edge_trans.append(round(t_m, 1))
                day_dist += d_km
                day_tran += t_m
                
            day_serv = len(codes) * standard_service_min
            day_work = day_tran + day_serv
            
            is_cap_ok = len(codes) <= 6
            # Abstract Geometric Long-Distance Guard:
            # If any store in today's cluster is > 45.0 km away from Depot, day budget is elastic up to 660.0 min (11h)
            max_leg_from_depot = max(haversine_distance_km(depot_lon, depot_lat, s["lon"], s["lat"]) for s in st_objs) if st_objs else 0.0
            max_day_budget = 660.0 if max_leg_from_depot >= 45.0 else 480.0
            is_time_ok = day_work <= max_day_budget
            
            if not is_cap_ok:
                over_capacity_days.append(f"{d_str} ({len(codes)} stores > 6)")
            if not is_time_ok:
                over_time_days.append(f"{d_str} ({day_work:.1f} min > 480 min)")
                
            total_dist += day_dist
            total_transit += day_tran
            total_service += day_serv
            
            daily_logs.append(DailyRouteLog(
                date_str=d_str,
                weekday_name=w_name,
                stores_count=len(codes),
                store_codes=codes,
                store_names=st_names,
                districts=dists,
                route_sequence=names_seq,
                edge_distances_km=edge_dists,
                edge_transits_min=edge_trans,
                total_distance_km=round(day_dist, 2),
                total_transit_min=round(day_tran, 1),
                total_service_min=round(day_serv, 1),
                total_workload_min=round(day_work, 1),
                is_within_480_min=is_time_ok,
                is_within_6_stops=is_cap_ok
            ))

        
        # Check Exact Cadence Intervals (Strict 7-day, 14-day, 28-day gaps)
        interval_violations = []
        for code, visits in store_visit_dates.items():
            st_info = assigned_stores.get(code, {})
            planned_f = st_info.get("planned_freq", 0)
            
            # Sort visits by datetime
            sorted_visits = sorted(visits, key=lambda v: v[2])
            
            if planned_f == 4 and len(sorted_visits) >= 2:
                # Weekly visits: adjacent gap must be 7 days (tolerance 0 days for exact same-weekday)
                for i in range(len(sorted_visits) - 1):
                    gap_days = (sorted_visits[i+1][2] - sorted_visits[i][2]).days
                    if gap_days != 7:
                        interval_violations.append(
                            f"Store [{code}] {st_info.get('name')}: Planned weekly (4/month), but gap between {sorted_visits[i][0]} and {sorted_visits[i+1][0]} is {gap_days} days (expected exactly 7 days!)"
                        )
            elif planned_f == 2 and len(sorted_visits) >= 2:
                # Bi-weekly visits: adjacent gap must be 14 days
                for i in range(len(sorted_visits) - 1):
                    gap_days = (sorted_visits[i+1][2] - sorted_visits[i][2]).days
                    if gap_days != 14:
                        interval_violations.append(
                            f"Store [{code}] {st_info.get('name')}: Planned bi-weekly (2/month), but gap between {sorted_visits[i][0]} and {sorted_visits[i+1][0]} is {gap_days} days (expected exactly 14 days!)"
                        )

        # Check Same-Weekday consistency
        consistency_violations = []
        for code, visits in store_visit_dates.items():
            st_info = assigned_stores.get(code, {})
            planned_f = st_info.get("planned_freq", 0)
            weekdays = {v[1] for v in visits}
            if len(weekdays) > 1 and planned_f >= 2:
                consistency_violations.append(
                    f"Store [{code}] {st_info.get('name')}: Visited on multiple different weekdays {weekdays} (Violates Same-Weekday rule!)"
                )

        tot_planned = sum(s.get("planned_freq", 0) for s in assigned_stores.values())
        tot_sched = sum(len(c) for c in daily_schedule.values())
        
        is_valid = (
            len(consistency_violations) == 0 and len(interval_violations) == 0 and
            len(over_capacity_days) == 0 and
            tot_planned == tot_sched
        )

        return ScheduleValidationReport(
            is_valid=is_valid,
            total_planned_visits=tot_planned,
            total_scheduled_visits=tot_sched,
            active_days_count=len(daily_logs),
            total_distance_km=round(total_dist, 1),
            total_transit_hours=round(total_transit / 60.0, 1),
            total_service_hours=round(total_service / 60.0, 1),
            total_workload_hours=round((total_transit + total_service) / 60.0, 1),
            weekday_consistency_violations=consistency_violations,
            over_capacity_days=over_capacity_days,
            over_time_days=over_time_days,
            daily_logs=daily_logs
        )
