"""Hierarchy metric Phi of the mobility network of each city, from raw call detail records.

    python mobility_hierarchy.py --cdr-dir /data/CDR/CDRs_Municipios --out-dir Data/Mobility_hierarchy

A trip is a pair of consecutive calls of the same user placed from two different
antennas. Antennas are grouped into activity levels by the iterated LouBar procedure
applied to their number of outgoing trips, and Phi is the share of all trips between
antennas in the same or in adjacent levels (Eq. 5; Bassolas et al., Nat. Commun. 10, 4817,
2019). Trips are directed, so every trip is counted once, in the cell (origin level,
destination level).

Input:  <cdr-dir>/cdr_<City>.txt, semicolon-separated, without header (columns below).
Output: <out-dir>/hierarchical_flow_<City>.txt holding the value of Phi, read by
        reproduce_figures.ipynb for Fig. 5.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

CITIES = [
    "Belem", "Campinas", "Fortaleza", "Guarulhos", "Maceio", "Manaus", "Recife",
    "Salvador", "Sao_Luis", "Sao_Paulo", "Belo_Horizonte", "Goiania", "Brasilia",
]  # fmt: skip
CDR_COLUMNS = [
    "date", "time", "duration", "ddd_from", "user_from", "ddd_to", "user_to", "antenna",
    "cell_id_to", "nu_trafego", "tp_trafego", "hold_from", "hold_to", "tp_line", "unk_number",
]  # fmt: skip
CHUNK_SIZE = 500_000


def count_trips(cdr_file: Path) -> pd.Series:
    """Number of trips between every ordered pair of antennas, indexed by (origin, destination)."""
    calls = defaultdict(list)  # user -> [(time of call, antenna), ...]
    chunks = pd.read_csv(
        cdr_file,
        sep=";",
        header=None,
        names=CDR_COLUMNS,
        dtype={"user_from": str, "antenna": str},
        chunksize=CHUNK_SIZE,
    )
    for chunk in chunks:
        chunk["datetime"] = pd.to_datetime(chunk["date"] + " " + chunk["time"], errors="coerce")
        chunk = chunk.dropna(subset=["datetime", "antenna"])
        for user, time, antenna in zip(chunk["user_from"], chunk["datetime"], chunk["antenna"]):
            calls[user].append((time, antenna))

    trips = Counter()
    for history in calls.values():
        history.sort(key=lambda call: call[0])
        antennas = [antenna for _, antenna in history]
        trips.update(pair for pair in zip(antennas, antennas[1:]) if pair[0] != pair[1])

    index = pd.MultiIndex.from_tuples(list(trips), names=["origin", "destination"])
    return pd.Series(list(trips.values()), index=index, name="trips", dtype="int64")


def loubar_cut(ascending: np.ndarray) -> int:
    """Index of the LouBar cut in an ascending array of positive values."""
    n = len(ascending)
    slope = ascending[-1] / np.mean(ascending)
    return min(int((1.0 - 1.0 / slope) * n), n - 1)


def loubar_levels(values: pd.Series, min_size: int = 5) -> pd.Series:
    """Iterated LouBar: activity level of every entry with a positive value (1 = most active)."""
    values = values[values > 0].sort_values(kind="stable")
    ascending = values.to_numpy()
    levels = np.zeros(len(ascending), dtype=int)
    remaining, level = len(ascending), 1
    while remaining > 0:
        cut = loubar_cut(ascending[:remaining]) if remaining >= min_size else 0
        levels[cut:remaining] = level
        remaining, level = cut, level + 1
    return pd.Series(levels, index=values.index, name="level")


def mobility_hierarchy(trips: pd.Series) -> float:
    """Phi of a table of trips; 0 if there are none."""
    if trips.empty:
        return 0.0
    levels = loubar_levels(trips.groupby(level="origin").sum())  # levels from outgoing trips
    origin = trips.index.get_level_values("origin").map(levels).to_numpy(dtype=float)
    destination = trips.index.get_level_values("destination").map(levels).to_numpy(dtype=float)
    known = ~(
        np.isnan(origin) | np.isnan(destination)
    )  # antennas with no outgoing trip have no level
    i, j = origin[known].astype(int) - 1, destination[known].astype(int) - 1

    n = int(levels.max())
    matrix = np.bincount(i * n + j, weights=trips.to_numpy()[known], minlength=n * n).reshape(n, n)
    band = np.trace(matrix) + np.trace(matrix, offset=1) + np.trace(matrix, offset=-1)
    return float(band / matrix.sum()) if matrix.sum() else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--cdr-dir", type=Path, default=Path("/data/CDR/CDRs_Municipios"))
    parser.add_argument("--out-dir", type=Path, default=Path("Data/Mobility_hierarchy"))
    parser.add_argument("--cities", nargs="+", default=CITIES)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for city in args.cities:
        phi = mobility_hierarchy(count_trips(args.cdr_dir / f"cdr_{city}.txt"))
        (args.out_dir / f"hierarchical_flow_{city}.txt").write_text(str(phi))
        print(f"{city}: Phi = {phi:.4f}")


if __name__ == "__main__":
    main()
