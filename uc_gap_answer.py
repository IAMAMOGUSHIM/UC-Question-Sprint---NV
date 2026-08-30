"""
How did the admission-rate gap between California and international freshman
applicants change at each UC campus from 2018 to 2024?

Run:
    python uc_gap_answer.py uc_admissions.csv

Input CSV, one row per campus x year x residency group:
    campus,year,residency,applicants,admits
    Berkeley,2018,California Resident,66000,11000
    Berkeley,2018,International,20000,2900
    ...
A raw UC Information Center crosstab export (with "Measure Names" /
"Measure Values" columns) is reshaped automatically.

Prints: the per-campus answer, significance tests, a decomposition of what
drove each change, and a written summary. Writes uc_gap_results.csv.
"""

import sys

import numpy as np
import pandas as pd

CA, INTL = "California Resident", "International"
Y0, Y1 = 2018, 2024


# ---------------------------------------------------------------- load
def normalize_residency(v: str) -> str:
    s = str(v).strip().lower()
    if "international" in s:
        return INTL
    if "california" in s or s in {"ca", "resident", "ca resident"}:
        return CA
    return str(v).strip()


def reshape_raw(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower().strip(): c for c in df.columns}
    pick = lambda *cs: next((cols[c] for c in cs if c in cols), None)  # noqa: E731
    c_campus = pick("campus", "campus name", "location")
    c_year = pick("year", "academic yr", "academic year", "term")
    c_res = pick("residency", "category", "resident status")
    c_meas = pick("measure names", "measure", "count type")
    c_val = pick("measure values", "value", "count")
    if None in (c_campus, c_year, c_res, c_meas, c_val):
        raise ValueError("Raw export is missing one of: campus, year, residency, "
                         "measure name, measure value")
    d = df[[c_campus, c_year, c_res, c_meas, c_val]].copy()
    d.columns = ["campus", "year", "residency", "measure", "value"]
    d["measure"] = d["measure"].astype(str).str.strip().str.lower()
    d = d[d["measure"].str.startswith(("app", "adm"))]
    d["measure"] = np.where(d["measure"].str.startswith("app"), "applicants", "admits")
    d["value"] = pd.to_numeric(
        d["value"].astype(str).str.replace(",", "", regex=False), errors="coerce")
    return (d.pivot_table(index=["campus", "year", "residency"], columns="measure",
                          values="value", aggfunc="sum")
            .reset_index().rename_axis(None, axis=1))


def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "measure names" in df.columns or "measure values" in df.columns:
        df = reshape_raw(df)
        df.columns = [c.lower() for c in df.columns]
    need = {"campus", "year", "residency", "applicants", "admits"}
    if not need.issubset(df.columns):
        raise ValueError(f"CSV must contain {sorted(need)}; found {sorted(df.columns)}")
    df["campus"] = df["campus"].astype(str).str.strip()
    df["year"] = pd.to_numeric(
        df["year"].astype(str).str.extract(r"(\d{4})")[0], errors="coerce").astype("Int64")
    df["residency"] = df["residency"].map(normalize_residency)
    for c in ("applicants", "admits"):
        df[c] = pd.to_numeric(
            df[c].astype(str).str.replace(",", "", regex=False), errors="coerce")
    df = df.dropna(subset=["year", "applicants", "admits"])
    df = df[(df["applicants"] > 0) & df["residency"].isin([CA, INTL])]
    bad = df[df["admits"] > df["applicants"]]
    if len(bad):
        raise ValueError(f"{len(bad)} rows have more admits than applicants")
    return df


# ---------------------------------------------------------------- stats
def norm_cdf(z):
    """Standard normal CDF via erf, so scipy is not required."""
    from math import erf, sqrt
    return 0.5 * (1 + erf(z / sqrt(2)))


def two_sided_p(z):
    return 2 * (1 - norm_cdf(abs(z)))


def panel(df: pd.DataFrame) -> pd.DataFrame:
    """One row per campus-year: both rates, the gap, and its standard error."""
    w = df.pivot_table(index=["campus", "year"], columns="residency",
                       values=["applicants", "admits"], aggfunc="sum")
    w.columns = [f"{m}_{'ca' if r == CA else 'intl'}" for m, r in w.columns]
    w = w.reset_index().dropna()
    w["p_ca"] = w["admits_ca"] / w["applicants_ca"]
    w["p_intl"] = w["admits_intl"] / w["applicants_intl"]
    w["gap_pp"] = (w["p_ca"] - w["p_intl"]) * 100
    w["var_ca"] = w["p_ca"] * (1 - w["p_ca"]) / w["applicants_ca"]
    w["var_intl"] = w["p_intl"] * (1 - w["p_intl"]) / w["applicants_intl"]
    w["se_gap_pp"] = np.sqrt(w["var_ca"] + w["var_intl"]) * 100
    w["log_odds_gap"] = (np.log(w["p_ca"] / (1 - w["p_ca"]))
                         - np.log(w["p_intl"] / (1 - w["p_intl"])))
    w["se_log_odds"] = np.sqrt(
        1 / w["admits_ca"] + 1 / (w["applicants_ca"] - w["admits_ca"])
        + 1 / w["admits_intl"] + 1 / (w["applicants_intl"] - w["admits_intl"]))
    w["odds_ratio"] = np.exp(w["log_odds_gap"])
    return w.sort_values(["campus", "year"]).reset_index(drop=True)


def wls_trend(g: pd.DataFrame) -> float:
    """Precision-weighted slope of the gap in pp per year across all years."""
    x = g["year"].astype(float).to_numpy()
    y = g["gap_pp"].to_numpy()
    wt = 1 / np.clip(g["se_gap_pp"].to_numpy(), 1e-9, None) ** 2
    xb = np.average(x, weights=wt)
    yb = np.average(y, weights=wt)
    denom = np.sum(wt * (x - xb) ** 2)
    return float(np.sum(wt * (x - xb) * (y - yb)) / denom) if denom else np.nan


def answer_table(p: pd.DataFrame, y0: int, y1: int) -> pd.DataFrame:
    rows = []
    for campus, g in p.groupby("campus"):
        g = g.set_index("year")
        if y0 not in g.index or y1 not in g.index:
            continue
        a, b = g.loc[y0], g.loc[y1]
        d_pp = b["gap_pp"] - a["gap_pp"]
        se_d = np.sqrt(a["se_gap_pp"] ** 2 + b["se_gap_pp"] ** 2)
        z = d_pp / se_d
        d_lo = b["log_odds_gap"] - a["log_odds_gap"]
        se_lo = np.sqrt(a["se_log_odds"] ** 2 + b["se_log_odds"] ** 2)
        rows.append({
            "campus": campus,
            f"gap_{y0}_pp": a["gap_pp"],
            f"gap_{y1}_pp": b["gap_pp"],
            "change_pp": d_pp,
            "ci_lo": d_pp - 1.96 * se_d,
            "ci_hi": d_pp + 1.96 * se_d,
            "z": z,
            "p_value": two_sided_p(z),
            "d_ca_rate_pp": (b["p_ca"] - a["p_ca"]) * 100,
            "d_intl_rate_pp": (b["p_intl"] - a["p_intl"]) * 100,
            f"odds_ratio_{y0}": a["odds_ratio"],
            f"odds_ratio_{y1}": b["odds_ratio"],
            "or_of_ors": np.exp(d_lo),
            "or_change_p": two_sided_p(d_lo / se_lo),
            "trend_pp_per_yr": wls_trend(
                p[(p.campus == campus) & p.year.between(y0, y1)]),
        })
    return (pd.DataFrame(rows)
            .sort_values("change_pp", ascending=False)
            .reset_index(drop=True))


def driver(r) -> str:
    """Which side of the comparison moved the gap."""
    ca, intl = r["d_ca_rate_pp"], r["d_intl_rate_pp"]
    if abs(ca) >= 2 * abs(intl):
        return "CA rate moved"
    if abs(intl) >= 2 * abs(ca):
        return "intl rate moved"
    return "both moved"


# ---------------------------------------------------------------- report
def report(t: pd.DataFrame, p: pd.DataFrame, y0: int, y1: int) -> None:
    pd.set_option("display.width", 200, "display.max_columns", 50)

    print(f"\nADMIT-RATE GAP, CALIFORNIA MINUS INTERNATIONAL, {y0} TO {y1}")
    print("=" * 92)
    show = t[["campus", f"gap_{y0}_pp", f"gap_{y1}_pp", "change_pp",
              "ci_lo", "ci_hi", "p_value", "trend_pp_per_yr"]].copy()
    show.columns = ["campus", f"{y0}", f"{y1}", "change", "95% lo", "95% hi",
                    "p", "pp/yr"]
    show["p"] = show["p"].map(lambda v: "  <0.001" if v < 0.001 else f"{v:8.3f}")
    print(show.to_string(index=False, float_format=lambda v: f"{v:8.2f}"))

    print(f"\nWHAT MOVED (percentage-point change in each rate, {y0}->{y1})")
    print("=" * 92)
    d = t[["campus", "d_ca_rate_pp", "d_intl_rate_pp", "change_pp"]].copy()
    d["driver"] = t.apply(driver, axis=1)
    d.columns = ["campus", "d CA rate", "d intl rate", "d gap", "driver"]
    print(d.to_string(index=False, float_format=lambda v: f"{v:8.2f}"))

    print(f"\nON THE ODDS SCALE (odds ratio, CA odds / international odds)")
    print("=" * 92)
    o = t[["campus", f"odds_ratio_{y0}", f"odds_ratio_{y1}", "or_of_ors",
           "or_change_p"]].copy()
    o.columns = ["campus", f"OR {y0}", f"OR {y1}", "OR ratio", "p"]
    print(o.to_string(index=False, float_format=lambda v: f"{v:8.3f}"))

    # ---- written answer
    wid = t[t.change_pp > 0]
    nar = t[t.change_pp < 0]
    sig = t[t.p_value < 0.05]
    top, bot = t.iloc[0], t.iloc[-1]
    med = t["change_pp"].median()
    n_favor_intl_18 = (t[f"gap_{y0}_pp"] < 0).sum()
    n_favor_intl_24 = (t[f"gap_{y1}_pp"] < 0).sum()

    print("\nANSWER")
    print("=" * 92)
    print(
        f"Across {len(t)} campuses, the California-minus-international admit-rate gap "
        f"widened at {len(wid)} and narrowed at {len(nar)} between {y0} and {y1}. "
        f"The median change was {med:+.1f} percentage points. "
        f"{len(sig)} of the {len(t)} changes are larger than sampling noise at the "
        f"5% level.\n"
        f"Widest move: {top['campus']}, from {top[f'gap_{y0}_pp']:+.1f} pp to "
        f"{top[f'gap_{y1}_pp']:+.1f} pp ({top['change_pp']:+.1f} pp, "
        f"95% CI [{top['ci_lo']:.1f}, {top['ci_hi']:.1f}], p={top['p_value']:.3g}); "
        f"{driver(top)}.\n"
        f"Opposite end: {bot['campus']}, {bot['change_pp']:+.1f} pp "
        f"(95% CI [{bot['ci_lo']:.1f}, {bot['ci_hi']:.1f}], p={bot['p_value']:.3g}); "
        f"{driver(bot)}.\n"
        f"Campuses admitting international applicants at the higher rate: "
        f"{n_favor_intl_18} in {y0}, {n_favor_intl_24} in {y1}."
    )
    print(
        "\nRead with care: these are campus-level counts, so a student applying to "
        "several campuses is counted several times and the rows must not be summed "
        "into a systemwide figure. Admit rates are not selectivity; they move with "
        "who applied and how many seats existed. Test-optional began for fall 2021 "
        "entry and test-free for fall 2022, the pandemic disrupted the fall 2021 "
        "cycle, and 2021 state action tightened nonresident enrollment caps at "
        "Berkeley, UCLA and San Diego. The p-values treat one year's applicant pool "
        "as one draw from a process that could have gone otherwise; these are "
        "population counts, not a sample."
    )


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "uc_admissions.csv"
    y0 = int(sys.argv[2]) if len(sys.argv) > 2 else Y0
    y1 = int(sys.argv[3]) if len(sys.argv) > 3 else Y1

    df = load(path)
    p = panel(df)
    p = p[p["year"].between(y0, y1)]
    t = answer_table(p, y0, y1)
    if t.empty:
        raise SystemExit(f"No campus has both {y0} and {y1} rows for both groups.")
    report(t, p, y0, y1)
    t.to_csv("uc_gap_results.csv", index=False)
    p.to_csv("uc_gap_panel.csv", index=False)
    print("\nWrote uc_gap_results.csv and uc_gap_panel.csv")


if __name__ == "__main__":
    main()
