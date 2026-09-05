# -*- coding: utf-8 -*-
"""Load SRP plan data, filter by line, return LineData."""
import pandas as pd
import os, warnings
from core.base import LineData

SRP_PATH = os.environ.get("SRP_PATH", "/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
ALL_LINE_IDS = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]


def load_plan():
    """Read SRP plan, returns filtered DataFrame with 客户编码, 拜访日期, 经度, 纬度, 拜访顺序, 销售名称."""
    warnings.filterwarnings("ignore")
    plan = pd.read_excel(SRP_PATH)
    pv = plan[plan["计划是否有效标识"] == "有效"].copy()
    pv["客户编码"] = pv["客户编码"].astype(str)
    pv["拜访日期"] = pd.to_datetime(pv["拜访日期"])
    pv["date"] = pv["拜访日期"].dt.date
    return pv


def load_line(pv, line_id: str) -> LineData:
    """Filter plan for one line, return LineData.
    
    line_id: "02".."11", matches "海珠荔湾XX" in 销售名称.
    """
    g = pv[pv["销售名称"].str.contains(f"海珠荔湾{line_id}")]
    if g.empty:
        raise ValueError(f"线路 海珠荔湾{line_id} 无数据")

    line_name = g["销售名称"].iloc[0]
    pts = g.dropna(subset=["经度", "纬度"]).drop_duplicates("客户编码", keep="first").set_index("客户编码")
    codes = pts.index.tolist()
    idx = {c: i for i, c in enumerate(codes)}
    lon = pts["经度"].astype(float).tolist()
    lat = pts["纬度"].astype(float).tolist()
    dates = sorted(g["date"].unique())

    days_orig = {}
    for dd in dates:
        rows = g[g["date"] == dd].sort_values("拜访顺序")
        days_orig[dd] = [idx[c] for c in rows["客户编码"] if c in idx]

    freq = g.groupby("客户编码").size().to_dict()

    return LineData(
        line_id=line_id,
        line_name=line_name,
        codes=codes,
        lon=lon,
        lat=lat,
        dates=dates,
        days_orig=days_orig,
        freq=freq,
        stores=len(codes),
        visits=len(g),
    )