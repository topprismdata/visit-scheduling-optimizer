# -*- coding: utf-8 -*-
"""Road distance matrix: fetch from OSM FOSSGIS or load from cache."""
import numpy as np
import json
import time
import urllib.request

URL = "https://routing.openstreetmap.de/routed-bike/table/v1/driving/"
BATCH = 40


def fetch_matrix(codes: list[str], lon: list[float], lat: list[float]) -> np.ndarray:
    """Fetch full n×n road distance matrix via FOSSGIS routed-bike.
    
    Splits sources into batches of BATCH to stay within 50-point limit.
    Returns km matrix (numpy, NaN → D.max() * 0.5).
    """
    n = len(codes)
    D = np.full((n, n), np.nan)
    coord = ";".join(f"{lo:.6f},{la:.6f}" for lo, la in zip(lon, lat))

    for s0 in range(0, n, BATCH):
        s1 = min(s0 + BATCH, n)
        srcs = ";".join(str(i) for i in range(s0, s1))
        url = f"{URL}{coord}?sources={srcs}&annotations=distance"
        for attempt in range(6):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "gz-eval/1.0"})
                r = json.loads(urllib.request.urlopen(req, timeout=90).read())
                if r.get("code") == "Ok":
                    for li, row in enumerate(r["distances"]):
                        for j in range(n):
                            if row[j] is not None:
                                D[s0 + li][j] = row[j] / 1000.0
                    break
            except Exception:
                time.sleep(2 + attempt)

    D = np.nan_to_num(D, nan=float(np.nanmax(D)) * 0.5)
    return D


def load_cached(line_id: str, expected_codes: list[str] | None = None) -> np.ndarray | None:
    """Load cached road matrix for line_id.
    
    若传入 expected_codes, 严格校验 sidecar road_codes_{line_id}.json 中的门店编码序与矩阵尺寸,
    防止因输入顺序变更导致错误的矩阵索引对齐 (Review P1-4 修复).
    """
    mat_path = f"output/road_dist_{line_id}.npy"
    meta_path = f"output/road_codes_{line_id}.json"
    if not os.path.exists(mat_path):
        return None
    try:
        D = np.load(mat_path)
        if expected_codes is not None:
            n_exp = len(expected_codes)
            if D.shape != (n_exp, n_exp):
                print(f"  [WARN] 缓存矩阵尺寸 {D.shape} 与期望店数 ({n_exp}, {n_exp}) 不符, 缓存失效", flush=True)
                return None
            if os.path.exists(meta_path):
                meta = json.load(open(meta_path))
                cached_codes = meta.get("codes", [])
                if cached_codes != list(expected_codes):
                    print(f"  [WARN] 缓存门店编码顺序与期望输入不一致, 缓存失效 (防止距离对齐错乱)", flush=True)
                    return None
            else:
                print(f"  [WARN] 缺少编码序元数据 {meta_path}, 为保证绝对正确性视同失效", flush=True)
                return None
        return D
    except Exception as e:
        print(f"  [WARN] 读取缓存失败 ({e}), 重新获取", flush=True)
        return None


def save_cached(line_id: str, D: np.ndarray, codes: list[str]):
    """Save road matrix to cache."""
    np.save(f"output/road_dist_{line_id}.npy", D)
    json.dump({"codes": codes}, open(f"output/road_codes_{line_id}.json", "w"))