"""Colocation and co-connectedness of every antenna of a city, from raw call detail records.

    python colocation_coconnectedness.py --cdr-dir /data/CDR/CDRs_Municipios \
        --antenna-dir /data/CDR/Antennas_Municipios --out-dir Data

A call record holds the antenna of the caller only. The receiver is located at the antenna
of the last call he or she placed in the 30 minutes before the call; if that antenna is the
antenna of the caller, the two individuals are co-present there (Fig. 1).

Colocation C_A (Eq. 2): number of co-present pairs at antenna A, a pair being counted once
per day.
Co-connectedness O_AB (Eq. 4): number of individuals who were co-present at both antenna A
and antenna B during the observation period.

Input:  <cdr-dir>/cdr_<City>.txt, semicolon-separated, with the columns
        date, time, user_from, user_to, antenna;
        <antenna-dir>/antennas_<City>.txt, semicolon-separated, with the columns
        CELLID, LAT, LONG.
Output: <out-dir>/3_unified_social_metrics_<City>.csv, read by reproduce_figures.ipynb.
        Rows with metric_type = colocation hold C_A of antenna1 in value; rows with
        metric_type = co-connectedness hold O_AB of the pair (antenna1, antenna2).
"""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

CITIES = [
    "Belem", "Campinas", "Fortaleza", "Guarulhos", "Maceio", "Manaus", "Recife",
    "Salvador", "Sao_Luis", "Sao_Paulo", "Belo_Horizonte", "Goiania", "Brasilia",
]  # fmt: skip
OUTPUT_COLUMNS = ["metric_type", "antenna1", "lat1", "long1", "antenna2", "lat2", "long2", "value"]


def read_calls(cdr_file: Path) -> pd.DataFrame:
    """Calls with a valid time stamp: user_from, user_to, antenna (of the caller), datetime."""
    calls = pd.read_csv(cdr_file, sep=";")
    calls["datetime"] = pd.to_datetime(
        calls["date"].astype(str) + " " + calls["time"].astype(str), errors="coerce"
    )
    calls = calls[["user_from", "user_to", "antenna", "datetime"]]
    return calls.dropna(subset=["datetime"]).sort_values("datetime", kind="stable")


def co_present_calls(calls: pd.DataFrame, window_minutes: float = 30) -> pd.DataFrame:
    """Calls whose receiver last called from the antenna of the caller within the time window."""
    last_seen = calls[["user_from", "datetime", "antenna"]].rename(
        columns={"user_from": "user", "antenna": "receiver_antenna"}
    )
    located = pd.merge_asof(
        calls,
        last_seen,
        on="datetime",
        left_by="user_to",
        right_by="user",
        direction="backward",
        tolerance=pd.Timedelta(minutes=window_minutes),
    )
    return located[located["antenna"] == located["receiver_antenna"]]


def colocation(co_present: pd.DataFrame) -> pd.Series:
    """C_A: number of co-present pairs at every antenna, each pair counted once per day."""
    first, second = co_present["user_from"], co_present["user_to"]
    events = pd.DataFrame(
        {
            "day": co_present["datetime"].dt.date,
            "antenna": co_present["antenna"],
            "user_low": first.where(first <= second, second),
            "user_high": second.where(first <= second, first),
        }
    ).drop_duplicates()
    return events.groupby("antenna").size().rename("value")


def co_connectedness(co_present: pd.DataFrame) -> pd.Series:
    """O_AB: number of individuals co-present at both antennas, indexed by (antenna1, antenna2)."""
    visits = pd.concat(
        [
            co_present[["user_from", "antenna"]].rename(columns={"user_from": "user"}),
            co_present[["user_to", "antenna"]].rename(columns={"user_to": "user"}),
        ]
    ).drop_duplicates()

    shared = Counter()
    for antennas in visits.groupby("user")["antenna"].apply(sorted):
        shared.update(combinations(antennas, 2))

    index = pd.MultiIndex.from_tuples(list(shared), names=["antenna1", "antenna2"])
    return pd.Series(list(shared.values()), index=index, name="value", dtype="int64")


def unified_social_metrics(cdr_file: Path, antenna_file: Path, window_minutes: float = 30):
    """Table of the colocation and the co-connectedness of one city, with antenna coordinates."""
    co_present = co_present_calls(read_calls(cdr_file), window_minutes)
    sites = pd.read_csv(antenna_file, sep=";").drop_duplicates("CELLID").set_index("CELLID")
    lat, lon = sites["LAT"], sites["LONG"]

    nodes = colocation(co_present).rename_axis("antenna1").reset_index()
    nodes = nodes.assign(metric_type="colocation", antenna2=np.nan, lat2=np.nan, long2=np.nan)
    edges = co_connectedness(co_present).reset_index().assign(metric_type="co-connectedness")
    edges["lat2"], edges["long2"] = edges["antenna2"].map(lat), edges["antenna2"].map(lon)

    table = pd.concat([nodes, edges], ignore_index=True)
    table["lat1"], table["long1"] = table["antenna1"].map(lat), table["antenna1"].map(lon)
    return table[OUTPUT_COLUMNS]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--cdr-dir", type=Path, default=Path("/data/CDR/CDRs_Municipios"))
    parser.add_argument("--antenna-dir", type=Path, default=Path("/data/CDR/Antennas_Municipios"))
    parser.add_argument("--out-dir", type=Path, default=Path("Data"))
    parser.add_argument("--cities", nargs="+", default=CITIES)
    parser.add_argument(
        "--window", type=float, default=30, help="co-presence time window in minutes"
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for city in args.cities:
        table = unified_social_metrics(
            args.cdr_dir / f"cdr_{city}.txt", args.antenna_dir / f"antennas_{city}.txt", args.window
        )
        table.to_csv(args.out_dir / f"3_unified_social_metrics_{city}.csv", index=False)
        counts = table["metric_type"].value_counts()
        print(
            f"{city}: {counts.get('colocation', 0)} antennas, "
            f"{counts.get('co-connectedness', 0)} antenna pairs"
        )


if __name__ == "__main__":
    main()
