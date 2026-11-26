"""College Bridges: which colleges move low-income students up, does campus cross-class
friendship matter, and which affordable high-mobility colleges are near Atlas priority counties?

Data
  Mobility Report Cards (Chetty et al.): students born 1980-82; "success rate" = share of
    students from bottom-quintile families who reach the top income quintile (kq5_cond_parq1);
    "access" = share of students from bottom-quintile families (par_q1); "mobility rate" =
    access x success (mr_kq5_pq1).
  College Scorecard (most recent): today's net price for families earning $0-30k, Pell share,
    completion, earnings 10 years after entry for low-income students.
  Social Capital Atlas, colleges: economic connectedness, exposure, friending bias.

Run: python3 -I scripts/01_college_bridges.py  ->  output/
Associations across colleges, not causal effects.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

# ---------------- Load ----------------
SC_COLS = ["UNITID", "OPEID", "OPEID6", "INSTNM", "CITY", "STABBR", "LATITUDE", "LONGITUDE", "CONTROL",
           "PREDDEG", "CURROPER", "ADM_RATE", "UGDS", "PCTPELL", "NPT41_PUB", "NPT41_PRIV", "NPT4_PUB",
           "NPT4_PRIV", "C150_4", "C150_L4", "C150_4_PELL", "MD_EARN_WNE_P10", "MD_EARN_WNE_INC1_P10"]
sc = pd.read_csv(RAW / "scorecard" / "Most-Recent-Cohorts-Institution.csv", usecols=SC_COLS, dtype=str)
for c in SC_COLS[5:]:
    if c not in ("STABBR", "CITY"):
        sc[c] = pd.to_numeric(sc[c], errors="coerce")  # "PrivacySuppressed" -> NaN
sc["opeid8"] = pd.to_numeric(sc.OPEID, errors="coerce")
sc["opeid6"] = pd.to_numeric(sc.OPEID6, errors="coerce")
sc["main_campus"] = sc.OPEID.str[-2:] == "00"
sc["net_price_low_income"] = np.where(sc.CONTROL == 1, sc.NPT41_PUB, sc.NPT41_PRIV)
sc["completion"] = np.where(sc.PREDDEG == 3, sc.C150_4, sc.C150_L4)
sc["control"] = sc.CONTROL.map({1: "Public", 2: "Private nonprofit", 3: "Private for-profit"})
main = sc[sc.main_campus].sort_values("UGDS", ascending=False).drop_duplicates("opeid6")

mrc = pd.read_csv(RAW / "mrc_table2.csv")
mrc = mrc[mrc.super_opeid > 0]
soc = pd.read_csv(RAW / "social_capital_college.csv")

d = (mrc[["super_opeid", "name", "tier_name", "type", "state", "count", "par_q1", "kq5_cond_parq1",
          "mr_kq5_pq1", "k_rank_cond_parq1", "cfips"]]
     .merge(main, left_on="super_opeid", right_on="opeid6", how="left")
     .merge(soc[["college", "ec_parent_ses_college", "exposure_parent_ses_college", "bias_parent_ses_college",
                 "ec_own_ses_college", "mean_students_per_cohort"]],
            left_on="opeid8", right_on="college", how="left"))
for c in ["par_q1", "kq5_cond_parq1", "mr_kq5_pq1"]:
    d[c] = d[c] * 100

# Guard against wrong joins: an OPEID can pass to a different institution after a merger or
# acquisition (e.g. a beauty school ID now belonging to another chain). Keep a Scorecard match
# only if the names are similar or share a distinctive word; otherwise blank today's fields.
import difflib
import re
GENERIC = {"college", "university", "of", "the", "school", "institute", "state", "community", "technical",
           "at", "and", "in", "for", "academy", "center", "campus", "suny", "cuny", "main", "new", "north",
           "south", "east", "west", "saint", "st", "beauty", "career", "colleges", "technology", "inc"}
norm = lambda s: re.sub(r"[^a-z ]", " ", str(s).lower().replace("&", " and "))
toks = lambda s: {t for t in norm(s).split() if t not in GENERIC and len(t) > 2}
sim = [difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() if isinstance(b, str) else np.nan
       for a, b in zip(d.name, d.INSTNM)]
share = [bool(toks(a) & toks(b)) if isinstance(b, str) else False for a, b in zip(d.name, d.INSTNM)]
d["name_match_ok"] = (pd.Series(sim, index=d.index) >= 0.45) | pd.Series(share, index=d.index)
bad = d.INSTNM.notna() & ~d.name_match_ok
match_rejected = d.loc[bad, ["super_opeid", "name", "INSTNM"]]
match_rejected.to_csv(OUT / "rejected_name_matches.csv", index=False)
d.loc[bad, [c for c in main.columns]] = np.nan
match = {"mrc_colleges": len(mrc), "matched_scorecard": int(d.UNITID.notna().sum()), "rejected_name_mismatch": len(match_rejected),
         "matched_social_capital": int(d.ec_parent_ses_college.notna().sum())}

# ---------------- A. Do 1980s-cohort mobility rates still track today's outcomes? ----------------
stab = []
for old, olab in [("kq5_cond_parq1", "Success rate (1980-82 cohorts)"), ("mr_kq5_pq1", "Mobility rate (1980-82 cohorts)"),
                  ("par_q1", "Access: % from bottom quintile (1980-82)")]:
    for new, nlab in [("MD_EARN_WNE_INC1_P10", "Earnings 10 yrs after entry, low-income students (today)"),
                      ("PCTPELL", "Pell share (today)"), ("C150_4_PELL", "Pell completion rate, 4-yr (today)")]:
        s = d[[old, new]].dropna()
        stab.append({"then": olab, "now": nlab, "n": len(s), "spearman": s.corr(method="spearman").iloc[0, 1]})
stab = pd.DataFrame(stab)
stab.to_csv(OUT / "stability_then_vs_now.csv", index=False, float_format="%.3f")

# ---------------- B. Campus cross-class friendship and low-income students' success ----------------
def zw(s, w):
    m = np.average(s, weights=w)
    return (s - m) / np.sqrt(np.average((s - m) ** 2, weights=w))


b = d.dropna(subset=["kq5_cond_parq1", "ec_parent_ses_college", "exposure_parent_ses_college",
                     "bias_parent_ses_college", "count", "tier_name"]).copy()
for c in ["ec_parent_ses_college", "exposure_parent_ses_college", "bias_parent_ses_college"]:
    b[c + "_z"] = zw(b[c], b["count"])
tiers = pd.get_dummies(b.tier_name, prefix="tier", drop_first=True, dtype=float)
rows = []
for y, ylab in [("kq5_cond_parq1", "Success rate: % of bottom-quintile students reaching top quintile"),
                ("k_rank_cond_parq1", "Mean adult income rank of bottom-quintile students")]:
    yy = b[y] * (100 if y == "k_rank_cond_parq1" else 1)
    for name, xs, ctrl in [("Economic connectedness, no controls", ["ec_parent_ses_college_z"], False),
                           ("Economic connectedness + selectivity tier", ["ec_parent_ses_college_z"], True),
                           ("Exposure + friending bias + selectivity tier", ["exposure_parent_ses_college_z", "bias_parent_ses_college_z"], True)]:
        X = b[xs] if not ctrl else pd.concat([b[xs], tiers], axis=1)
        r = sm.WLS(yy, sm.add_constant(X), weights=b["count"]).fit(cov_type="cluster", cov_kwds={"groups": b.state})
        for x in xs:
            rows.append({"outcome": ylab, "model": name, "term": x.replace("_parent_ses_college_z", ""),
                         "coef_per_sd": r.params[x], "ci_low": r.conf_int().loc[x, 0], "ci_high": r.conf_int().loc[x, 1],
                         "n_colleges": int(r.nobs), "r2": r.rsquared})
assoc = pd.DataFrame(rows)
assoc.to_csv(OUT / "social_capital_vs_success.csv", index=False, float_format="%.4f")

# ---------------- C. Bridge colleges near Atlas priority counties ----------------
cur = d[(d.CURROPER == 1) & d.net_price_low_income.notna() & d.kq5_cond_parq1.notna() & d.LATITUDE.notna()].copy()
price_cut = cur.net_price_low_income.median()
succ_cut = cur.kq5_cond_parq1.quantile(0.6)
cur["bridge"] = (cur.net_price_low_income <= price_cut) & (cur.kq5_cond_parq1 >= succ_cut) & \
                ((cur.completion >= 0.4) | cur.completion.isna())
# Many affordable high-success colleges are selective (generous aid, hard to get into).
# "Accessible" bridges also admit at least half of applicants (or have open admission).
cur["accessible"] = cur.bridge & ((cur.ADM_RATE >= 0.5) | cur.ADM_RATE.isna())
bridges = cur[cur.bridge].copy()
access_br = cur[cur.accessible].copy()
bridges.sort_values("kq5_cond_parq1", ascending=False)[
    ["INSTNM", "CITY", "STABBR", "control", "tier_name", "accessible", "ADM_RATE", "net_price_low_income", "kq5_cond_parq1", "par_q1",
     "mr_kq5_pq1", "completion", "MD_EARN_WNE_INC1_P10", "PCTPELL", "ec_parent_ses_college"]
].to_csv(OUT / "bridge_colleges.csv", index=False, float_format="%.3f")

gaz = pd.read_csv(RAW / "gazetteer" / "2022_Gaz_counties_national.txt", sep="\t", dtype={"GEOID": str})
gaz.columns = gaz.columns.str.strip()
pri = pd.read_csv(ROOT / "data" / "from_projects" / "priority_counties.csv", dtype={"fips": str})
pri = pri[~pri.flag_small_child_pop].merge(gaz[["GEOID", "INTPTLAT", "INTPTLONG"]], left_on="fips", right_on="GEOID", how="left")


def miles(lat1, lon1, lat2, lon2):
    p = np.radians
    a = np.sin(p(lat2 - lat1) / 2) ** 2 + np.cos(p(lat1)) * np.cos(p(lat2)) * np.sin(p(lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * np.arcsin(np.sqrt(a))


near_rows = []
for _, c in pri.iterrows():
    dist = miles(c.INTPTLAT, c.INTPTLONG, bridges.LATITUDE.values, bridges.LONGITUDE.values)
    any_dist = miles(c.INTPTLAT, c.INTPTLONG, cur.LATITUDE.values, cur.LONGITUDE.values)
    order = np.argsort(dist)[:3]
    rec = {"fips": c.fips, "county": f"{c.county_name}, {c.state}", "children": c.children_0_17_acs2022,
           "nearest_any_college_mi": round(float(any_dist.min()), 1),
           "bridge_colleges_within_60mi": int((dist <= 60).sum()),
           "nearest_bridge_mi": round(float(dist[order[0]]), 1)}
    adist = miles(c.INTPTLAT, c.INTPTLONG, access_br.LATITUDE.values, access_br.LONGITUDE.values)
    ai = int(np.argmin(adist))
    rec["accessible_bridges_within_60mi"] = int((adist <= 60).sum())
    rec["nearest_accessible_bridge_mi"] = round(float(adist[ai]), 1)
    rec["nearest_accessible_bridge"] = f"{access_br.iloc[ai].INSTNM} ({access_br.iloc[ai].CITY}, {access_br.iloc[ai].STABBR})"
    for k, i in enumerate(order, 1):
        bb = bridges.iloc[i]
        rec[f"bridge_{k}"] = f"{bb.INSTNM} ({bb.CITY}, {bb.STABBR}): {dist[i]:.0f} mi, net price ${bb.net_price_low_income:,.0f}, success {bb.kq5_cond_parq1:.0f}%"
    near_rows.append(rec)
near = pd.DataFrame(near_rows).sort_values("nearest_bridge_mi")
near.to_csv(OUT / "priority_counties_nearest_bridges.csv", index=False)

# ---------------- Figures ----------------
SURFACE, TEXT, TEXT2, GRID, C1, C2 = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6", "#eb6834"
fig, ax = plt.subplots(figsize=(9.5, 6.4), dpi=100)
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
oth = cur[~cur.bridge]
ax.scatter(oth.par_q1, oth.kq5_cond_parq1, s=np.clip(oth["count"] / 60, 4, 90), color=TEXT2, alpha=0.25, lw=0, label="Other colleges")
ax.scatter(bridges.par_q1, bridges.kq5_cond_parq1, s=np.clip(bridges["count"] / 60, 6, 90), color=C2, alpha=0.8,
           lw=0.5, edgecolor=SURFACE, label=f"Bridge colleges ({len(bridges)}): affordable for $0-30k families, high success")
ax.set_xscale("log")
ax.set_xticks([1, 2, 5, 10, 20, 40], ["1%", "2%", "5%", "10%", "20%", "40%"])
ax.set_xlabel("Access: share of students from bottom-quintile families (log scale)", color=TEXT2)
ax.set_ylabel("Success: % of those students reaching the top quintile", color=TEXT2)
ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
for s_ in ["top", "right"]:
    ax.spines[s_].set_visible(False)
ax.tick_params(colors=TEXT2)
ax.legend(frameon=False, labelcolor=TEXT, loc="upper right")
fig.text(0.02, 0.955, "Bridge colleges: affordable for low-income families and good at moving them up", fontsize=13.5, weight="bold", color=TEXT)
fig.text(0.02, 0.918, "Each dot is a college, sized by cohort. Success and access from students born 1980-82; net price from today's College Scorecard.", color=TEXT2, fontsize=9.5)
fig.text(0.02, 0.012, "Sources: Opportunity Insights Mobility Report Cards; U.S. Dept. of Education College Scorecard. Exploratory - verify before external use.", fontsize=8.5, color=TEXT2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.88, bottom=0.12)
fig.savefig(OUT / "access_success_bridges.png", dpi=150, facecolor=SURFACE)
plt.close(fig)

# Binned: share of high-income classmates (exposure) vs success, adjusted for tier and friending bias
Xc = sm.add_constant(pd.concat([b[["bias_parent_ses_college_z"]], tiers], axis=1))
ry = b.kq5_cond_parq1 - sm.WLS(b.kq5_cond_parq1, Xc, weights=b["count"]).fit().fittedvalues
rx = b.exposure_parent_ses_college - sm.WLS(b.exposure_parent_ses_college, Xc, weights=b["count"]).fit().fittedvalues
bins = pd.qcut(rx, 15, labels=False)
bx = rx.groupby(bins).mean() + np.average(b.exposure_parent_ses_college, weights=b["count"])
by = ry.groupby(bins).apply(lambda s: np.average(s, weights=b["count"][s.index])) + np.average(b.kq5_cond_parq1, weights=b["count"])
slope = sm.WLS(ry, sm.add_constant(rx), weights=b["count"]).fit().params.iloc[1]
fig, ax = plt.subplots(figsize=(9, 5.8), dpi=100)
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.scatter(bx, by, s=60, color=C1, zorder=3)
xx = np.linspace(bx.min(), bx.max(), 20)
ax.plot(xx, by.mean() + slope * (xx - bx.mean()), color=TEXT, lw=2)
ax.set_xlabel("Exposure: how many high-income classmates a low-income student has (x2; 1 = even mix)", color=TEXT2)
ax.set_ylabel("Success rate of bottom-quintile students (%)", color=TEXT2)
ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
for s_ in ["top", "right"]:
    ax.spines[s_].set_visible(False)
ax.tick_params(colors=TEXT2)
fig.text(0.02, 0.955, "Low-income students rise further at colleges with more high-income classmates", fontsize=13, weight="bold", color=TEXT)
fig.text(0.02, 0.918, f"{len(b):,} colleges in 15 equal-size groups, comparing colleges in the same selectivity tier. Friending bias showed no link.", color=TEXT2, fontsize=9.5)
fig.text(0.02, 0.012, "Sources: Social Capital Atlas (colleges); Mobility Report Cards. Association only: exposure also tracks resources. Verify before use.", fontsize=8.5, color=TEXT2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.88, bottom=0.12)
fig.savefig(OUT / "exposure_success.png", dpi=150, facecolor=SURFACE)

pd.set_option("display.width", 200)
print(match)
print(stab.round(2).to_string(index=False))
print(assoc[["outcome", "model", "term", "coef_per_sd", "ci_low", "ci_high", "n_colleges", "r2"]].round(3).to_string(index=False))
print(f"\nBridge colleges: {len(bridges)} of {len(cur)} operating colleges "
      f"(net price <= ${price_cut:,.0f}, success >= {succ_cut:.1f}%)")
print(bridges.control.value_counts().to_dict(), bridges.tier_name.value_counts().head(6).to_dict())
print(f"Priority counties: {len(near)}; median distance to nearest bridge college {near.nearest_bridge_mi.median():.0f} mi; "
      f"with none within 60 mi: {(near.bridge_colleges_within_60mi == 0).sum()}")
print(f"Accessible bridges: {len(access_br)}; priority counties with none within 60 mi: "
      f"{(near.accessible_bridges_within_60mi == 0).sum()}; median distance {near.nearest_accessible_bridge_mi.median():.0f} mi")
print(near[["county", "nearest_any_college_mi", "nearest_bridge_mi", "bridge_colleges_within_60mi", "bridge_1"]].head(8).to_string(index=False))
