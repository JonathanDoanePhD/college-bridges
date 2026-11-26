# 04 - College Bridges

**Question:** After high school, which colleges actually move low-income students up? Does
campus social capital matter? Which affordable, high-mobility colleges are within reach of
the Atlas priority counties (Project 01)?

**Status:** complete (2026-11-14). Before going public: confirm Opportunity Insights terms for
the Mobility Report Cards (no license published), and have counselors or college-access
staff review the bridge-college list.

> **Exploratory.** Associations across colleges, not causal effects. Verify figures against
> the original sources before external use. The lists are a starting point for people who
> advise students, not recommendations for any individual student.

## Key findings

1. **The old mobility data still points the right way.** Mobility Report Cards follow
   students born 1980-82, but a college's success rate for low-income students then tracks
   **today's earnings for low-income students** closely (rank correlation **0.85**, 1,814
   colleges) and today's Pell completion rate (0.66). So the 1980s rankings are still a
   useful guide.
2. **Low-income students rise further at colleges with more high-income classmates,** even
   comparing colleges in the same selectivity tier. Success rate is **+5.6 percentage points
   per SD** of exposure (CI 4.8 to 6.5; 1,727 colleges; tier fixed effects; SEs clustered by
   state). Without tier controls the overall cross-class friendship measure is +10.6.
3. **Unlike in high schools, friending bias shows no link at college** (+0.3, CI -0.1 to
   +0.7). In Project 02, high schools where low-income students befriended higher-income
   peers graduated more of them. In college, what matters is *who is on campus* (which also
   tracks resources and networks), not whether friendships cross class lines. For a
   mentoring program, the bridging job may matter most *before* college, along with getting
   students into well-resourced, mixed campuses.
4. **221 "bridge colleges"** combine a net price at or below $12,417 for families earning
   $0-30k (the median) with a top-40% success rate. **148 of them are accessible** (admit at
   least half of applicants, or open admission). Most are selective publics and private
   colleges with strong aid. Only 12 are two-year colleges, partly because the success
   measure (reaching the top income quintile) favors four-year degrees.
5. **Bridge-college deserts:** of the 64 Atlas priority counties with at least 2,000
   children, **52 have no bridge college within 60 miles** (median distance **89 miles**).
   For accessible bridges it's **55 of 64** (median **96 miles**). Most have *some* college
   nearby (median 22 miles to the nearest one), it's rarely one that is both affordable and
   strong on mobility. That makes the case for mentoring that includes college navigation,
   campus visits and support for students who move away for college.

## Outputs

| File | What |
|---|---|
| `output/stability_then_vs_now.csv` | 1980s mobility measures vs. today's Scorecard outcomes (Spearman) |
| `output/social_capital_vs_success.csv` | Campus economic connectedness, exposure, friending bias vs. low-income success |
| `output/bridge_colleges.csv` | 221 bridge colleges, with accessibility, net price, success, completion, earnings |
| `output/priority_counties_nearest_bridges.csv` | For each priority county: distance to nearest college, nearest three bridges, nearest accessible bridge |
| `output/access_success_bridges.png` | Access vs. success, bridge colleges highlighted |
| `output/exposure_success.png` | Exposure vs. success, adjusted for tier and friending bias |
| `output/rejected_name_matches.csv` | ID matches rejected because the names disagree (see Method) |

## Rebuild

From the repository root:

```bash
python3 -I scripts/fetch_data.py .
python3 -I scripts/01_college_bridges.py
```

If `opportunityinsights.org` refuses the scripted download, download `mrc_table2.csv` with a
browser or plain `curl` into `data/raw/`. The fetch script records hand-placed files in the
lock. `data/from_projects/priority_counties.csv` comes from Project 01.

## Method

- **Joins:** Mobility Report Card `super_opeid` → Scorecard `OPEID6` (main campus, OPEID ending
  `00`); Social Capital Atlas `college` → Scorecard 8-digit `OPEID`. Because IDs can pass to a
  different institution after mergers, a Scorecard match is kept only if the names are
  similar (ratio ≥ 0.45) or share a distinctive word. 14 matches were rejected. Most were
  real mismatches (acquired career schools); a few were legitimate renames (e.g. MCPHS, SUNY
  Poly), dropped conservatively.
- **Success model:** weighted by cohort size; selectivity-tier fixed effects (Mobility Report
  Card tiers); standardized social capital measures (parental-SES versions); SEs clustered
  by state.
- **Bridge colleges:** currently operating; net price for $0-30k families at or below the
  median of matched colleges; success rate in the top 40%; completion ≥ 40% where reported.
  Distances are straight-line miles from county population-weighted centers (Census 2022
  Gazetteer, internal points) to campus coordinates.

## Caveats

- Mobility Report Card cohorts are old; today's net price and outcomes come from a different
  era (finding 1 suggests rankings are stable, but levels may differ).
- Exposure at college also reflects selectivity within tiers, resources and alumni networks,
  so it is not purely a "peer" effect.
- The success measure (top income quintile) undervalues colleges that move students into
  the middle class, especially two-year colleges.
- Straight-line distance understates travel time in rural areas.

## License, citation and data terms

- **Code:** MIT (proposed; see `LICENSE`). **Outputs:** CC BY 4.0 (proposed), subject to the source terms below.
- **Cite this project as:** JonathanDoanePhD (2026). *College Bridges*. https://github.com/JonathanDoanePhD/college-bridges
- **Data sources and terms** (from `data/sources.csv`; recorded versions and checksums in `data/sources.lock.csv`):

| Source | Terms |
|---|---|
| U.S. Dept. of Education College Scorecard (most recent institution-level) | U.S. government work (public domain) |
| Opportunity Insights College Mobility Report Cards (preferred access & mobility estimates) | No license published on opportunityinsights.org/data (site notice: all rights reserved); cite Chetty et al. 2017/2020 and link rather than re-host |
| Social Capital Atlas - US Colleges (Chetty et al. 2022) via HDX | Meta data license: use/redistribute incl. license; no endorsement; no re-identification |
| Census 2022 Gazetteer county file (county centroids) | U.S. government work (public domain) |

Built with AI assistance (Claude). Exploratory research: every statistic needs checking against its original source
before it appears in funder reports, grant applications or public material.

## Before public release

- [ ] Every statistic in this README and in `output/` is checked against its original source.
- [ ] College-access staff review the bridge-college list.
- [ ] Mobility Report Cards have no published license: link rather than re-host.
- [ ] The owner confirms the license choice above.
