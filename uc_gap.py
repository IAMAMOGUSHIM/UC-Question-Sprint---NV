import pandas as pd

df = pd.read_csv("/mnt/user-data/uploads/uc_admissions_summary_by_ethnicity.csv")

# Freshman applicants and admits, 2018-2024, campuses only
df = df[(df.entrant_level == "freshman")
        & (df.count_type.isin(["App", "Adm"]))
        & (df.fall_term.between(2018, 2024))
        & (df.campus != "Systemwide")]

# Everything that is not "International" is a domestic student
df["group"] = df.ethnicity.where(df.ethnicity == "International", "Domestic")

t = df.pivot_table(index=["campus", "fall_term"],
                   columns=["group", "count_type"], values="n", aggfunc="sum")

t["rate_dom"] = t[("Domestic", "Adm")] / t[("Domestic", "App")]
t["rate_int"] = t[("International", "Adm")] / t[("International", "App")]
t["gap_pp"] = (t["rate_dom"] - t["rate_int"]) * 100

g = t["gap_pp"].unstack("fall_term")
out = pd.DataFrame({"gap_2018": g[2018], "gap_2024": g[2024]})
out["change"] = out.gap_2024 - out.gap_2018
out = out.sort_values("change", ascending=False)

print("Domestic minus international admit rate, percentage points\n")
print(out.round(1).to_string())
print(f"\nWidened at {(out.change > 0).sum()} campuses, narrowed at {(out.change < 0).sum()}.")
print(f"Median change: {out.change.median():+.1f} pp")
print("\nFull series by year:\n")
print((g.round(1)).to_string())
print("\nUnderlying rates (%):\n")
r = (t[["rate_dom", "rate_int"]] * 100).round(1)
print(r.loc[(slice(None), [2018, 2024]), :].to_string())
