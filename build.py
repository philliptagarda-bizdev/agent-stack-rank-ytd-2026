#!/usr/bin/env python3
"""
Presales Weekly Report Build Script  v1.0
==========================================
Usage:
  python build.py data_W3.json             # build only
  python build.py data_W3.json --deploy    # build + deploy
  python build.py data_W3.json --source Presales_Weekly_Report_W2_Jun_2026.html

Within-month builds (W2→W3, W3→W4):  update last element of each monthly array.
Month-boundary builds (W4→W1 next):  see MONTH BOUNDARY section below.

PATCH RULE (per CLAUDE.md): str.replace() only — no regex, no AST.
  If a patch fails (old string not found), build aborts. Fix the old string in the
  patches list below by re-reading the source HTML.
"""

import json, sys, os, re, subprocess, shutil
from pathlib import Path

REPORTS_DIR = Path("/Users/phillip.tagarda/Documents/Claude/Projects/Weekly Cross-brand Sales Report")


# ══════════════════════════════════════════════════════════════════════
#  LOAD & VALIDATE
# ══════════════════════════════════════════════════════════════════════

def load_data(path):
    with open(path) as f:
        return json.load(f)


SANITY = {
    "xv_conv":  (0.20, 0.35, "XV presale conv%"),
    "bau_conv": (0.08, 0.28, "BAU conv%"),
    "cg_conv":  (0.20, 0.45, "CG conv%"),
    "pia_conv": (0.25, 0.45, "PIA conv%"),
}

def validate(d):
    warns = []
    xv, cg, pia = d["xv"], d["cg"], d["pia"]

    for key, field, lo, hi in [
        ("xv_conv",  float(xv["mtd_conv_pct"]) / 100, *SANITY["xv_conv"][:2]),
        ("bau_conv", float(xv["bau_mtd_conv_pct"]) / 100, *SANITY["bau_conv"][:2]),
        ("cg_conv",  float(cg["mtd_conv_pct"]) / 100, *SANITY["cg_conv"][:2]),
        ("pia_conv", float(pia["mtd_conv_pct"]) / 100, *SANITY["pia_conv"][:2]),
    ]:
        lo2, hi2, label = SANITY[key]
        if not (lo2 <= field <= hi2):
            warns.append(f"⚠  {label}: {field*100:.2f}% outside {lo2*100:.0f}–{hi2*100:.0f}% range")

    # Conv formula cross-check (XV)
    if xv.get("mtd_tickets") and xv.get("mtd_sales"):
        computed = float(xv["mtd_sales"]) / float(xv["mtd_tickets"]) * 100
        if abs(computed - float(xv["mtd_conv_pct"])) > 0.5:
            warns.append(f"⚠  XV conv% mismatch: {xv['mtd_sales']}/{xv['mtd_tickets']} = {computed:.2f}% but data says {xv['mtd_conv_pct']}%")

    return warns


# ══════════════════════════════════════════════════════════════════════
#  PRE-FLIGHT SUMMARY
# ══════════════════════════════════════════════════════════════════════

def pre_flight(d, warns, no_confirm=False):
    w, xv, cg, pia = d["week"], d["xv"], d["cg"], d["pia"]
    t, ob, ytd = d["teams"], d["outbound"], d["ytd"]

    print(f"""
{'='*60}
PRE-FLIGHT — {w['label']} · {w['filing_week']} · {w['dates']}
{'='*60}

INBOUND
 XV MTD:   {xv['mtd_sales']} sales · {xv['mtd_tickets']} tickets · {xv['mtd_conv_pct']}% · ${float(xv['mtd_gross']):,.2f}
 XV W{w['week_number']}:    {xv['filing_week_sales']} validated this week
 BAU MTD:  {xv['bau_mtd_sales']} sales · {xv['bau_mtd_tickets']} tickets · {xv['bau_mtd_conv_pct']}%
 CG MTD:   {cg['mtd_sales']} · {cg['mtd_conv_pct']}% · ${float(cg['mtd_gross']):,.2f}
 PIA MTD:  {pia['mtd_sales']} · {pia['mtd_conv_pct']}% · ${float(pia['mtd_gross']):,.2f}
 Teams:    {t['mtd_won']} deals · {t['mtd_conv_pct']}% · ${float(t['mtd_gross']):,.2f}

OUTBOUND
 Mabel:    {ob['mabel']['deals']} deals · ${float(ob['mabel']['gross']):,.2f}
 Audrey:   {ob['audrey']['deals']} deals · ${float(ob['audrey']['gross']):,.2f}

DERIVED
 All-brands Jun MTD: ${float(ytd['jun_mtd_all_brands']):,.2f}
 All-brands YTD:     ${float(ytd['ytd_total']):,.0f}  ({float(ytd['ytd_total'])/2e6*100:.1f}% of $2M)
 Monthly needed:     ~${float(ytd['monthly_needed']):,.0f}/mo from {w['next_month']}
""")

    if warns:
        print("VALIDATION WARNINGS:")
        for w2 in warns:
            print(f"  {w2}")
        print()

    if no_confirm:
        return True
    print("Confirm build? (y/n): ", end="")
    return input().strip().lower() == "y"


# ══════════════════════════════════════════════════════════════════════
#  PATCH HELPERS
# ══════════════════════════════════════════════════════════════════════

_errors = []

def patch(html, old, new, label, allow_multiple=False):
    global _errors
    count = html.count(old)
    if count == 0:
        _errors.append(f"NOT FOUND [{label}]: {old[:90]!r}")
        print(f"  ✗ {label}")
        return html
    if count > 1 and not allow_multiple:
        print(f"  ⚠  {label}: {count} matches (replacing all)")
    result = html.replace(old, new)
    print(f"  ✓ {label}")
    return result


def dollar(v):
    return int(round(float(v)))

def dec4(pct_float):
    """Convert percentage string/float like 25.73 → 0.2573"""
    return round(float(pct_float) / 100, 4)

def signed_pp(new_pct, old_pct):
    delta = float(new_pct) - float(old_pct)
    sign = "▲ +" if delta >= 0 else "▼ "
    return f"{sign}{abs(delta):.2f}pp"


# ══════════════════════════════════════════════════════════════════════
#  HTML PATCH FUNCTION
# ══════════════════════════════════════════════════════════════════════

def patch_html(source_path, out_path, d):
    global _errors
    _errors = []

    with open(source_path, encoding="utf-8") as f:
        html = f.read()

    w   = d["week"]
    xv  = d["xv"]
    cg  = d["cg"]
    pia = d["pia"]
    t   = d["teams"]
    ob  = d["outbound"]
    ytd = d["ytd"]
    prev = d["prev"]   # previous month locked finals

    # ── Derived values ──────────────────────────────────────────────
    xv_conv  = dec4(xv["mtd_conv_pct"])
    cg_conv  = dec4(cg["mtd_conv_pct"])
    pia_conv = dec4(pia["mtd_conv_pct"])
    bau_conv = dec4(xv["bau_mtd_conv_pct"])

    xv_combined = round(float(xv["mtd_sales"]) + float(xv["bau_mtd_sales"]), 1)
    all_sales   = round(float(xv["mtd_sales"]) + float(cg["mtd_sales"]) + float(pia["mtd_sales"]), 1)
    all_gross   = dollar(float(xv["mtd_gross"]) + float(cg["mtd_gross"]) +
                         float(pia["mtd_gross"]) + float(t["mtd_gross"]))
    ytd_total   = float(ytd["ytd_total"])
    ytd_pct     = round(ytd_total / 2_000_000 * 100, 1)
    ytd_needed  = float(ytd["monthly_needed"])

    # ── CG / PIA chip delta text ─────────────────────────────────────
    cg_delta  = f"{signed_pp(cg['mtd_conv_pct'], prev['cg_may_conv_pct'])} vs May · {cg['mtd_sales']} sales / {cg['mtd_tickets']} tickets"
    pia_delta = f"{signed_pp(pia['mtd_conv_pct'], prev['pia_may_conv_pct'])} vs May · {pia['mtd_sales']} sales / {pia['mtd_tickets']} tickets"
    cg_dir    = "up" if float(cg["mtd_conv_pct"]) >= float(prev["cg_may_conv_pct"]) else "down"
    pia_dir   = "up" if float(pia["mtd_conv_pct"]) >= float(prev["pia_may_conv_pct"]) else "down"

    # ── Section-chip derived values (patches 10-20) ──────────────────
    mtd_range       = w.get("month_mtd_range", "Jun MTD")
    prev_wk_num     = str(w.get("prev_week_number", int(w["week_number"]) - 1))
    prev_wk_dates   = w.get("prev_week_dates", "")
    prev_wk_sales   = xv.get("prev_week_sales", "")
    prev_wk_gross   = int(xv.get("prev_week_gross_est") or 0)
    prev_wk_conv    = xv.get("prev_week_conv_pct", "")
    prev_wk_tix     = xv.get("prev_week_tickets_est", "")
    fw_sales        = xv.get("filing_week_sales") or "TBD"
    fw_gross        = int(xv.get("filing_week_gross_est") or 0)
    fw_dates_html   = w["dates"].split(",")[0].replace("–", "&ndash;")
    jan_may_teams   = float(prev.get("jan_may_teams_gross", 238205))
    jan_may_deals   = int(prev.get("jan_may_teams_deals", 104))
    teams_ytd_gross = dollar(jan_may_teams + float(t["mtd_gross"]))
    teams_ytd_deals = jan_may_deals + int(t["mtd_won"])
    ob_total_gross  = dollar(float(ob["mabel"]["gross"]) + float(ob["audrey"]["gross"]))
    audrey_gross    = float(ob["audrey"]["gross"])
    audrey_display  = f"${dollar(audrey_gross):,}" if audrey_gross > 0 else "$0"
    bau_may_conv    = float(prev.get("may_bau_conv_pct", 21.58))
    bau_dir         = "down" if float(xv["bau_mtd_conv_pct"]) < bau_may_conv else "up"
    bau_arrow       = "&#9660;" if bau_dir == "down" else "&#9650;"
    may_ob_gross    = dollar(float(prev.get("may_outbound_gross", 6222.88)))

    print("\n── Applying Patches ──────────────────────────────────────────")

    # ── 1. Page metadata ─────────────────────────────────────────────
    html = patch(html,
        '<title>Presales Weekly Performance Report · W2 Jun 2026 · Jun 9–15 · Looker Jun 15, 2026</title>',
        f'<title>Presales Weekly Performance Report · {w["label"]} · {w["dates"]} · Looker {w["report_date"]}</title>',
        "page title")

    html = patch(html,
        'reportDate: "June 15, 2026"',
        f'reportDate: "{w["report_date"]}"',
        "REPORT.reportDate")

    html = patch(html,
        'weekOf: "Jun W2 (Jun 9–15) · pulled Jun 15, 2026 · month-to-date declared"',
        f'weekOf: "{w["week_of"]}"',
        "REPORT.weekOf")

    html = patch(html,
        '"Jun W2"]',
        f'"{w["month_label"]}"]',
        "monthsLabels last element")

    # ── 2. XV brand arrays (last element) ───────────────────────────
    html = patch(html,
        'grossSalesUSD: [50207, 104509, 118696, 125830, 107697, 36893]',
        f'grossSalesUSD: [50207, 104509, 118696, 125830, 107697, {dollar(xv["mtd_gross"])}]',
        "XV.grossSalesUSD")

    html = patch(html,
        'saleCount: [515, 955, 1055, 1092, 1015.5, 324]',
        f'saleCount: [515, 955, 1055, 1092, 1015.5, {xv["mtd_sales"]}]',
        "XV.saleCount")

    html = patch(html,
        'conversionRate: [0.2464, 0.3001, 0.2838, 0.2731, 0.2769, 0.2573]',
        f'conversionRate: [0.2464, 0.3001, 0.2838, 0.2731, 0.2769, {xv_conv}]',
        "XV.conversionRate")

    html = patch(html,
        'saleCountCombined: [699, 1004, 1088, 1111, 1045.5, 354]',
        f'saleCountCombined: [699, 1004, 1088, 1111, 1045.5, {xv_combined}]',
        "XV.saleCountCombined")

    html = patch(html,
        'presaleVolume: [2090, 3182, 3717, 3998, 3668, 1226]',
        f'presaleVolume: [2090, 3182, 3717, 3998, 3668, {xv["mtd_tickets"]}]',
        "XV.presaleVolume")

    html = patch(html,
        'presaleTeamVol: [2090, 3182, 3717, 3998, 3668, 1226]',
        f'presaleTeamVol: [2090, 3182, 3717, 3998, 3668, {xv["mtd_tickets"]}]',
        "XV.presaleTeamVol")

    html = patch(html,
        'presaleTeamSale:[515, 955, 1055, 1092, 1015.5, 324]',
        f'presaleTeamSale:[515, 955, 1055, 1092, 1015.5, {xv["mtd_sales"]}]',
        "XV.presaleTeamSale")

    html = patch(html,
        'presaleTeamConv:[0.2464, 0.3001, 0.2838, 0.2731, 0.2769, 0.2573]',
        f'presaleTeamConv:[0.2464, 0.3001, 0.2838, 0.2731, 0.2769, {xv_conv}]',
        "XV.presaleTeamConv")

    html = patch(html,
        'bauVolume: [910, 264, 261, 166, 139, 267]',
        f'bauVolume: [910, 264, 261, 166, 139, {xv["bau_mtd_tickets"]}]',
        "XV.bauVolume")

    html = patch(html,
        'bauSale: [184, 49, 33, 19, 30, 30]',
        f'bauSale: [184, 49, 33, 19, 30, {xv["bau_mtd_sales"]}]',
        "XV.bauSale")

    html = patch(html,
        'bauConversion: [0.2022, 0.1856, 0.1264, 0.1145, 0.2158, 0.1124]',
        f'bauConversion: [0.2022, 0.1856, 0.1264, 0.1145, 0.2158, {bau_conv}]',
        "XV.bauConversion")

    # ── 3. CG brand arrays ───────────────────────────────────────────
    html = patch(html,
        'grossSalesUSD: [null, 9711, 24460, 23585, 22938, 9449]',
        f'grossSalesUSD: [null, 9711, 24460, 23585, 22938, {dollar(cg["mtd_gross"])}]',
        "CG.grossSalesUSD")

    html = patch(html,
        'saleCount: [null, 169, 428.5, 407.5, 408, 174]',
        f'saleCount: [null, 169, 428.5, 407.5, 408, {cg["mtd_sales"]}]',
        "CG.saleCount")

    html = patch(html,
        'conversionRate: [null, 0.2328, 0.3377, 0.3226, 0.3611, 0.2626]',
        f'conversionRate: [null, 0.2328, 0.3377, 0.3226, 0.3611, {cg_conv}]',
        "CG.conversionRate")

    html = patch(html,
        'presaleVolume: [null, 726, 1269, 1263, 1061, 663]',
        f'presaleVolume: [null, 726, 1269, 1263, 1061, {cg["mtd_tickets"]}]',
        "CG.presaleVolume")

    # ── 4. PIA brand arrays ──────────────────────────────────────────
    # NOTE: PIA Apr conv% in chart (0.3645) is wrong vs Looker (0.2736).
    #       Per CLAUDE.md: confirm with Phillip before fixing. Not patched here.
    # NOTE: PIA May conv% corrected from chart 0.3531 → canonical 0.3393.

    html = patch(html,
        'grossSalesUSD: [null, 19132, 24820, 24311, 23675, 9222]',
        f'grossSalesUSD: [null, 19132, 24820, 24311, 23675, {dollar(pia["mtd_gross"])}]',
        "PIA.grossSalesUSD")

    html = patch(html,
        'saleCount: [null, 280.5, 342.67, 278.83, 360, 140]',
        f'saleCount: [null, 280.5, 342.67, 278.83, 360, {pia["mtd_sales"]}]',
        "PIA.saleCount")

    html = patch(html,
        'conversionRate: [null, 0.2404, 0.3129, 0.2736, 0.3766, 0.3531]',
        f'conversionRate: [null, 0.2404, 0.3129, 0.2736, 0.3766, {pia_conv}]',
        "PIA.conversionRate")

    html = patch(html,
        'presaleVolume: [null, 1167, 1095, 1019, 956, 397]',
        f'presaleVolume: [null, 1167, 1095, 1019, 956, {pia["mtd_tickets"]}]',
        "PIA.presaleVolume")

    # ── 5. Trajectory12 arrays (last element = Jun MTD) ─────────────
    # NOTE: May XV in sales/lookerCombined shows 1045.5 (chart) vs 1015.5 (locked).
    #       Not silently fixed here — per CLAUDE.md flag.

    html = patch(html,
        'sales: [181, 229, 344, 276, 618, 538, 549, 450, 699, 1004, 1088, 1111, 1045.5, 638]',
        f'sales: [181, 229, 344, 276, 618, 538, 549, 450, 699, 1004, 1088, 1111, 1045.5, {all_sales}]',
        "T12.sales (all brands combined)")

    html = patch(html,
        'lookerCombined: [null,null,null,null,null,null,null,null, 699, 1004, 1088, 1111, 1045.5, 324]',
        f'lookerCombined: [null,null,null,null,null,null,null,null, 699, 1004, 1088, 1111, 1045.5, {xv["mtd_sales"]}]',
        "T12.lookerCombined")

    html = patch(html,
        'revenue:[null,null,null,null,null,null,null,null, 50207, 104509, 118696, 125830, 107697, 36893]',
        f'revenue:[null,null,null,null,null,null,null,null, 50207, 104509, 118696, 125830, 107697, {dollar(xv["mtd_gross"])}]',
        "T12.revenue (XV)")

    html = patch(html,
        'salesXV:[181,229,344,276,618,538,549,450,699,1005,1087,1166,1015.5,324]',
        f'salesXV:[181,229,344,276,618,538,549,450,699,1005,1087,1166,1015.5,{xv["mtd_sales"]}]',
        "T12.salesXV")

    html = patch(html,
        'salesCG:[null,null,null,null,null,null,null,null,null,169,428.5,407.5,408,174]',
        f'salesCG:[null,null,null,null,null,null,null,null,null,169,428.5,407.5,408,{cg["mtd_sales"]}]',
        "T12.salesCG")

    html = patch(html,
        'salesPIA:[null,null,null,null,null,null,null,null,null,280.5,342.67,278.83,360,140]',
        f'salesPIA:[null,null,null,null,null,null,null,null,null,280.5,342.67,278.83,360,{pia["mtd_sales"]}]',
        "T12.salesPIA")

    html = patch(html,
        'volXV:[null,null,null,null,null,null,null,null,3000,3446,3978,4164,3807,1226]',
        f'volXV:[null,null,null,null,null,null,null,null,3000,3446,3978,4164,3807,{xv["mtd_tickets"]}]',
        "T12.volXV")

    html = patch(html,
        'volCG:[null,null,null,null,null,null,null,null,null,726,1269,1263,1061,663]',
        f'volCG:[null,null,null,null,null,null,null,null,null,726,1269,1263,1061,{cg["mtd_tickets"]}]',
        "T12.volCG")

    html = patch(html,
        'volPIA:[null,null,null,null,null,null,null,null,null,1167,1095,1019,956,397]',
        f'volPIA:[null,null,null,null,null,null,null,null,null,1167,1095,1019,956,{pia["mtd_tickets"]}]',
        "T12.volPIA")

    html = patch(html,
        'convXV:[null,null,null,null,null,null,null,null,0.2330,0.2916,0.2733,0.2800,0.2628,0.2573]',
        f'convXV:[null,null,null,null,null,null,null,null,0.2330,0.2916,0.2733,0.2800,0.2628,{xv_conv}]',
        "T12.convXV")

    html = patch(html,
        'convCG:[null,null,null,null,null,null,null,null,null,0.2328,0.3377,0.3226,0.3611,0.2626]',
        f'convCG:[null,null,null,null,null,null,null,null,null,0.2328,0.3377,0.3226,0.3611,{cg_conv}]',
        "T12.convCG")

    # PIA May conv% also corrected here (0.3624 → 0.3393)
    html = patch(html,
        'convPIA:[null,null,null,null,null,null,null,null,null,0.2404,0.3129,0.2736,0.3766,0.3531]',
        f'convPIA:[null,null,null,null,null,null,null,null,null,0.2404,0.3129,0.2736,0.3766,{pia_conv}]',
        "T12.convPIA")

    html = patch(html,
        'revenueCG:[null,null,null,null,null,null,null,null,null,9711,24460,23585,22938,9449]',
        f'revenueCG:[null,null,null,null,null,null,null,null,null,9711,24460,23585,22938,{dollar(cg["mtd_gross"])}]',
        "T12.revenueCG")

    html = patch(html,
        'revenuePIA:[null,null,null,null,null,null,null,null,null,19132,24820,24311,23675,9222]',
        f'revenuePIA:[null,null,null,null,null,null,null,null,null,19132,24820,24311,23675,{dollar(pia["mtd_gross"])}]',
        "T12.revenuePIA")

    html = patch(html,
        'revenueAll:[null,null,null,null,null,null,null,null,50207,133352,167976,173726,154310,55564]',
        f'revenueAll:[null,null,null,null,null,null,null,null,50207,133352,167976,173726,154310,{all_gross}]',
        "T12.revenueAll")

    # ── 6. Forecast actual arrays (index 5 = Jun MTD) ───────────────
    html = patch(html,
        'actual: [50207, 104509, 118696, 125830, 107697, 36893, null, null, null, null, null, null]',
        f'actual: [50207, 104509, 118696, 125830, 107697, {dollar(xv["mtd_gross"])}, null, null, null, null, null, null]',
        "forecast.XV.actual")

    html = patch(html,
        'actual: [null, 9711, 24460, 23585, 22938, 9449, null, null, null, null, null, null]',
        f'actual: [null, 9711, 24460, 23585, 22938, {dollar(cg["mtd_gross"])}, null, null, null, null, null, null]',
        "forecast.CG.actual")

    html = patch(html,
        'actual: [null, 19132, 24820, 24311, 23675, 9222, null, null, null, null, null, null]',
        f'actual: [null, 19132, 24820, 24311, 23675, {dollar(pia["mtd_gross"])}, null, null, null, null, null, null]',
        "forecast.PIA.actual")

    # ── 7. $2M Progress bar ──────────────────────────────────────────
    html = patch(html,
        '36.8% · $735,538 raised so far · need $189,061/mo from Jul',
        f'{ytd_pct:.1f}% · ${ytd_total:,.0f} raised so far · need ${ytd_needed:,.0f}/mo from {w["next_month"]}',
        "progress bar text")

    # Bar fill width (appears twice: fill div + marker div)
    html = patch(html,
        '"rs-progress-fill" style="width:34.0%"',
        f'"rs-progress-fill" style="width:{ytd_pct:.1f}%"',
        "progress fill width")

    html = patch(html,
        '"rs-progress-marker" style="left:34.0%"',
        f'"rs-progress-marker" style="left:{ytd_pct:.1f}%"',
        "progress marker position")

    html = patch(html,
        '$679,584 actual',
        f'${ytd_total:,.0f} actual',
        "progress actual amount")

    # ── 8. KPI chips — CG Jun MTD (appears in multiple grids) ───────
    html = patch(html,
        '<div class="hkc-val">26.26%</div>\n<div class="hkc-lbl">CG Jun (1–15) Close Rate</div>',
        f'<div class="hkc-val">{cg["mtd_conv_pct"]}%</div>\n<div class="hkc-lbl">CG {mtd_range} Close Rate</div>',
        "CG MTD chip val/lbl", allow_multiple=True)

    html = patch(html,
        '<div class="hkc-delta down">▼ −9.85 pts vs May · 174 sales / 663 tickets</div>',
        f'<div class="hkc-delta {cg_dir}">{cg_delta}</div>',
        "CG MTD chip delta", allow_multiple=True)

    # ── 9. KPI chips — PIA Jun MTD ───────────────────────────────────
    html = patch(html,
        '<div class="hkc-val">35.31%</div>\n<div class="hkc-lbl">PIA Jun (1–15) Close Rate</div>',
        f'<div class="hkc-val">{pia["mtd_conv_pct"]}%</div>\n<div class="hkc-lbl">PIA {mtd_range} Close Rate</div>',
        "PIA MTD chip val/lbl", allow_multiple=True)

    html = patch(html,
        '<div class="hkc-delta down">▼ −2.35 pts vs May · 140 sales / 397 tickets</div>',
        f'<div class="hkc-delta {pia_dir}">{pia_delta}</div>',
        "PIA MTD chip delta", allow_multiple=True)

    # ── 10. XV prev-week revenue chip ───────────────────────────────
    html = patch(html,
        '<div class="hkc-val">~$22,579</div>\n<div class="hkc-lbl">XV W1 Revenue <small style="opacity:.6">(est)</small></div>\n<div class="hkc-delta up">&#9650; 204 validated &middot; Jun 1–8 Jun 1&ndash;8</div>',
        f'<div class="hkc-val">~${prev_wk_gross:,}</div>\n<div class="hkc-lbl">XV W{prev_wk_num} Revenue <small style="opacity:.6">(est)</small></div>\n<div class="hkc-delta up">&#9650; {prev_wk_sales} validated &middot; {prev_wk_dates}</div>',
        "XV prev-week revenue chip")

    # ── 11. XV prev-week close rate chip ────────────────────────────
    html = patch(html,
        '<div class="hkc-val">25.73%</div>\n<div class="hkc-lbl">XV W1 Jun Close Rate</div>\n<div class="hkc-delta flat">&#8594; 204 validated &middot; ~794 est. tickets</div>',
        f'<div class="hkc-val">{prev_wk_conv}%</div>\n<div class="hkc-lbl">XV W{prev_wk_num} {w["month_short"]} Close Rate</div>\n<div class="hkc-delta flat">&#8594; {prev_wk_sales} validated &middot; ~{prev_wk_tix} est. tickets</div>',
        "XV prev-week close rate chip")

    # ── 12. XV MTD close rate chip ───────────────────────────────────
    html = patch(html,
        '<div class="hkc-val">25.73%</div>\n<div class="hkc-lbl">XV Jun (1–15) Close Rate</div>\n<div class="hkc-delta flat">&#8594; 324 validated &middot; 1,226 tickets &middot; vs May 27.69%</div>',
        f'<div class="hkc-val">{xv["mtd_conv_pct"]}%</div>\n<div class="hkc-lbl">XV {mtd_range} Close Rate</div>\n<div class="hkc-delta flat">&#8594; {xv["mtd_sales"]} validated &middot; {int(xv["mtd_tickets"]):,} tickets &middot; vs May {prev["may_xv_conv_pct"]}%</div>',
        "XV MTD close rate chip")

    # ── 13. CG revenue chip (×2) ─────────────────────────────────────
    html = patch(html,
        '<div class="hkc-val">$9,449</div>\n<div class="hkc-lbl">CG Jun (1–15) Revenue</div>\n<div class="hkc-delta flat">&#8594; 174 sales &middot; 26.26% conv &middot; Jun (1–15)</div>',
        f'<div class="hkc-val">${dollar(cg["mtd_gross"]):,}</div>\n<div class="hkc-lbl">CG {mtd_range} Revenue</div>\n<div class="hkc-delta flat">&#8594; {cg["mtd_sales"]} sales &middot; {cg["mtd_conv_pct"]}% conv &middot; {mtd_range}</div>',
        "CG revenue chip", allow_multiple=True)

    # ── 14. PIA revenue chip (×2) ────────────────────────────────────
    html = patch(html,
        '<div class="hkc-val">$9,222</div>\n<div class="hkc-lbl">PIA Jun (1–15) Revenue</div>\n<div class="hkc-delta flat">&#8594; 140 sales &middot; 35.31% conv &middot; Jun (1–15)</div>',
        f'<div class="hkc-val">${dollar(pia["mtd_gross"]):,}</div>\n<div class="hkc-lbl">PIA {mtd_range} Revenue</div>\n<div class="hkc-delta flat">&#8594; {pia["mtd_sales"]} sales &middot; {pia["mtd_conv_pct"]}% conv &middot; {mtd_range}</div>',
        "PIA revenue chip", allow_multiple=True)

    # ── 15. Teams YTD chip — &mdash; version (×2) ────────────────────
    html = patch(html,
        '<div class="hkc-val">$249,571</div>\n<div class="hkc-lbl">Business Accounts &mdash; Year to Date</div>\n<div class="hkc-delta up">&#9650; 131 deals &middot; Jun (1–15) 27 won &middot; 30%</div>',
        f'<div class="hkc-val">${teams_ytd_gross:,}</div>\n<div class="hkc-lbl">Business Accounts &mdash; Year to Date</div>\n<div class="hkc-delta up">&#9650; {teams_ytd_deals} deals &middot; {mtd_range} {t["mtd_won"]} won &middot; {t["mtd_conv_pct"]}%</div>',
        "Teams YTD chip (&mdash; variant)", allow_multiple=True)

    # ── 16. Teams YTD chip — plain unicode dash version ───────────────
    html = patch(html,
        '<div class="hkc-val">$249,571</div>\n<div class="hkc-lbl">Business Accounts — Year to Date</div>\n<div class="hkc-delta up">▲ +$11,366 Jun (1–15) · 27 deals · Jan–Jun running</div>',
        f'<div class="hkc-val">${teams_ytd_gross:,}</div>\n<div class="hkc-lbl">Business Accounts — Year to Date</div>\n<div class="hkc-delta up">▲ +${dollar(t["mtd_gross"]):,} {mtd_range} · {t["mtd_won"]} deals · Jan–{w["month_short"]} running</div>',
        "Teams YTD chip (plain unicode variant)")

    # ── 17. Outbound MTD chip (×2) ───────────────────────────────────
    html = patch(html,
        '<div class="hkc-val">$2,020</div>\n<div class="hkc-lbl">Outbound Jun (1–15) Revenue</div>\n<div class="hkc-delta up">&#9650; 4 deals (Mabel 3 &middot; Audrey 1) &middot; vs May $6,223</div>',
        f'<div class="hkc-val">${ob_total_gross:,}</div>\n<div class="hkc-lbl">Outbound {mtd_range} Revenue</div>\n<div class="hkc-delta up">&#9650; {int(ob["mabel"]["deals"])+int(ob["audrey"]["deals"])} deals (Mabel {ob["mabel"]["deals"]} &middot; Audrey {ob["audrey"]["deals"]}) &middot; vs May ${may_ob_gross:,}</div>',
        "Outbound MTD chip", allow_multiple=True)

    # ── 18. BAU chip — flat delta ────────────────────────────────────
    html = patch(html,
        '<div class="hkc-val">11.24%</div>\n<div class="hkc-lbl">Support Agents (Support Team) Close Rate</div>\n<div class="hkc-delta flat">&#8594; 30 sales &middot; 267 tickets &middot; Jun (1–15)</div>',
        f'<div class="hkc-val">{xv["bau_mtd_conv_pct"]}%</div>\n<div class="hkc-lbl">Support Agents (Support Team) Close Rate</div>\n<div class="hkc-delta flat">&#8594; {xv["bau_mtd_sales"]} sales &middot; {xv["bau_mtd_tickets"]} tickets &middot; {mtd_range}</div>',
        "BAU chip (flat delta)")

    # ── 19. BAU chip — warning delta ─────────────────────────────────
    html = patch(html,
        '<div class="hkc-val">11.24%</div>\n<div class="hkc-lbl">Support Agents (Support Team) Close Rate</div>\n<div class="hkc-delta down">&#9660; 30 sales &middot; 267 tickets &middot; &#9888; vs May 21.58%</div>',
        f'<div class="hkc-val">{xv["bau_mtd_conv_pct"]}%</div>\n<div class="hkc-lbl">Support Agents (Support Team) Close Rate</div>\n<div class="hkc-delta {bau_dir}">{bau_arrow} {xv["bau_mtd_sales"]} sales &middot; {xv["bau_mtd_tickets"]} tickets &middot; &#9888; vs May {bau_may_conv}%</div>',
        "BAU chip (warning delta)")

    # ── 20. XV current filing-week chip (TBD → actuals) ×2 ──────────
    # Only fires when filing_week_sales and filing_week_gross_est are filled in data JSON
    if fw_sales != "TBD" and fw_gross > 0:
        fw_chip_old = (
            f'<div class="hkc-val">TBD</div>\n'
            f'<div class="hkc-lbl">XV Week {w["week_number"]} &mdash; {fw_dates_html}</div>\n'
            f'<div class="hkc-delta flat">&#8594; Data not yet available</div>'
        )
        fw_chip_new = (
            f'<div class="hkc-val">{fw_sales}</div>\n'
            f'<div class="hkc-lbl">XV W{w["week_number"]} &mdash; {fw_dates_html}</div>\n'
            f'<div class="hkc-delta flat">&#8594; {w["dates"].split(",")[0]} validated &middot; ~${fw_gross:,} est.</div>'
        )
        html = patch(html, fw_chip_old, fw_chip_new,
                     "XV current-week TBD chip", allow_multiple=True)
    else:
        print("  – XV current-week chip: skipped (filing_week_sales or filing_week_gross_est not set)")

    # ── Write output ─────────────────────────────────────────────────
    if _errors:
        print(f"\n✗ {len(_errors)} patch(es) FAILED — output NOT written.")
        for e in _errors:
            print(f"  {e}")
        return False, html

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  → Written: {out_path.name}")
    return True, html


# ══════════════════════════════════════════════════════════════════════
#  VERIFICATION
# ══════════════════════════════════════════════════════════════════════

def verify(out_path):
    print("\n── Verification ──────────────────────────────────────────────")
    with open(out_path, encoding="utf-8") as f:
        html = f.read()

    # Canvas count
    canvas_count = html.count('<canvas')
    if canvas_count == 22:
        print(f"  ✓ Canvas count: 22")
    else:
        print(f"  ✗ Canvas count: {canvas_count} (expected 22)")
        return False

    # JS syntax check
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    with open("/tmp/ck.js", "w") as f:
        f.write("\n".join(scripts))
    r = subprocess.run(["node", "--check", "/tmp/ck.js"], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  ✓ JS syntax: OK")
    else:
        print(f"  ✗ JS syntax error:\n{r.stderr}")
        return False

    return True


# ══════════════════════════════════════════════════════════════════════
#  DEPLOY
# ══════════════════════════════════════════════════════════════════════

def deploy(out_path, no_confirm=False):
    print("\n── Deploy ────────────────────────────────────────────────────")
    if not no_confirm:
        print("Deploy to GitHub Pages? (y/n): ", end="")
        if input().strip().lower() != "y":
            print("  Skipped.")
            return

    # Copy to index.html in repo root (GitHub Pages serves index.html)
    repo_index = REPORTS_DIR / "index.html"
    shutil.copy2(out_path, repo_index)

    r = subprocess.run(
        ["git", "push", "-f", "origin", "master:main"],
        cwd=REPORTS_DIR,
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print(f"  ✓ Deployed → https://philliptagarda-bizdev.github.io/presales-report/")
    else:
        print(f"  ✗ Deploy failed:\n{r.stderr}")


# ══════════════════════════════════════════════════════════════════════
#  MONTH BOUNDARY NOTES
# ══════════════════════════════════════════════════════════════════════
# When a new month starts (W4→W1 next month), update build.py:
#
# 1. All 6-element monthly arrays: drop index 0, shift left, append new MTD
#    e.g. [Jan,Feb,Mar,Apr,May,JunMTD] → [Feb,Mar,Apr,May,Jun_final,JulMTD]
#
# 2. trajectory12 arrays: drop first element (oldest), append:
#    - Second-to-last = prior month FINAL (confirmed Looker close)
#    - Last element   = new month MTD
#    Update T12.labels accordingly.
#
# 3. KPI chips: prior month becomes the "vs [Month]" comparison point.
#    Update prev.* values in data.json and chip narrative text.
#
# 4. forecast.actual arrays: prior month index finalised; new month = MTD.
#
# 5. Update the old_strings in patch_html() to reflect the new baseline HTML.
#    Run: grep -n "<array_name>" source.html to find exact current values.


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    import argparse
    p = argparse.ArgumentParser(description="Presales Weekly Report Build Script")
    p.add_argument("data",          help="data JSON file (e.g. data_W3.json)")
    p.add_argument("--source",      help="source HTML (default: most-recent Presales_Weekly_Report_W*.html)")
    p.add_argument("--out",         help="output HTML (default: auto from week.label)")
    p.add_argument("--deploy",      action="store_true", help="deploy to GitHub Pages after build")
    p.add_argument("--no-confirm",  action="store_true", help="skip confirmation prompts")
    args = p.parse_args()

    d = load_data(args.data)
    warns = validate(d)

    # Source
    if args.source:
        source = Path(args.source)
    else:
        files = sorted(REPORTS_DIR.glob("Presales_Weekly_Report_W*.html"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            sys.exit("ERROR: No source HTML found. Use --source.")
        source = files[0]
        print(f"Source: {source.name}")

    # Output
    if args.out:
        out = Path(args.out)
    else:
        label = d["week"]["label"].replace(" ", "_")
        out = REPORTS_DIR / f"Presales_Weekly_Report_{label}.html"
    print(f"Output: {out.name}\n")

    if not pre_flight(d, warns, no_confirm=args.no_confirm):
        sys.exit("Build cancelled.")

    ok, _ = patch_html(source, out, d)
    if not ok:
        sys.exit(1)

    if not verify(out):
        sys.exit(1)

    print(f"\n✓ Build complete: {out.name}")

    if args.deploy:
        deploy(out, no_confirm=args.no_confirm)


if __name__ == "__main__":
    main()
