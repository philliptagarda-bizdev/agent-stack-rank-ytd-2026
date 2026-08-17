# Singularity — Core Instructions

> **One folder, one source of truth.** Presales weekly report, MBR analysis, ARIA / Co-Pilot, Holiday.com, XV Teams, Project BTC. Do not spin off sibling projects — fold new scope in here.

**Location:** `/Users/phillip.tagarda/Documents/Claude/Projects/Singularity/`
**Went lean:** Aug 13, 2026 · verbatim pre-lean copy → `outputs/July - 1st half of August/CLAUDE_pre-lean_2026-08-13.md`

---

## Folder Map — this is the whole thing

```
Singularity/
├── CLAUDE.md     ← you are here · behaviour, safety, routing
├── context.md    ← who Phillip is · his voice · his rules — READ WITH THIS FILE
├── memory/
│   ├── MEMORY.md      ← the index · read before answering anything historical
│   ├── <topic>.md     ← 89 running notes
│   └── reference/     ← methodology · specs · runbooks · templates/ · ledgers/
├── build.py · checkjs.py · data_W3.json   ← the hot path · MUST stay at root
├── inbox/        ← drop raw assets, screenshots, messy files here to process
└── outputs/      ← every finished deliverable lands here, FLAT
    ├── <new deliverable>            ← today's work
    └── July - 1st half of August/   ← read-only archive, shipped up to Aug 13 2026
```

**Rules of the structure**

- Nothing new goes at root. Root holds the five spec entries **plus the three build-machinery files** — `build.py`, `checkjs.py`, `data_W3.json`. Every documented weekly build command invokes them by bare name; they stay at root. Nothing else joins them.
- Raw material in → `inbox/`. Finished thing out → `outputs/`.
- **New deliverables go flat into `outputs/`** — never inside a dated folder. Dated folders like `July - 1st half of August/` are **read-only archives**; they are swept there only when Phillip says so.
- Anything that must survive the session → a `memory/` topic note **plus** a one-line entry in `memory/MEMORY.md`.
- `memory/reference/` is read-first source of truth. `memory/reference/sales-report-COMPLETE.md` is the methodology spine for every YTD calculation, trend and forecast.

---

## Working Agreement — standing rules, set Aug 13 2026

**These three come before anything else in this file.**

1. **Plan, then ask.** Outline the execution plan and get Phillip's explicit approval **before** modifying or deleting any local file. Reading, listing and analysing need no approval — writing does. State what will change, where, and what is irreversible.
2. **Concise, structured, routed to `outputs/`.** Deliverables are tight and structured, and the finished file lands **directly in `outputs/`** — flat, not in a period subfolder. `outputs/July - 1st half of August/` and any later dated folder are **read-only archives**; new work never goes inside one. Raw material to process arrives in `inbox/`.
3. **Log the decisions.** At the end of any substantive task, add a **2-sentence** summary of the key decisions to `## Session log` in `memory/MEMORY.md` — **as the new top entry, the log runs newest-first.** Two sentences: what was decided, and why it binds future work.

---

## Session Start — read in this order

1. **`CLAUDE.md`** (this file) — rules, always loaded
2. **`context.md`** — identity, voice, answer shape
3. **`memory/MEMORY.md`** — find the topic notes that matter for today

Conflicts: **this file wins**, unless a memory note carries an explicit correction dated later than this file.

| Task | Load |
|---|---|
| Weekly report build | `memory/reference/WEEKLY_BUILD.md` + `memory/build-canon-weekly-and-progress.md` |
| Progress update / exec readout | `memory/reference/CANONICAL_PROGRESS_UPDATE_SPEC.md` |
| Daily run | `memory/reference/RUN_DAILY_RUNBOOK.md` + `memory/run-daily-runbook.md` |
| Any brand actual / conv% | `memory/reference/ledgers/MBR_Reconciliation_2026.md` + `memory/mbr_authority.md` |
| Where a number came from | `memory/source-registry.md` |
| Locked figures + basis rules | `memory/locked-actuals-and-basis-taxonomy.md` |
| Edit report HTML / JS / CSS | `memory/report_rules.md` · `memory/report_structure.md` |
| Narrative framing | `memory/report_framing_conventions.md` · `memory/why-these-numbers-stand.md` |
| Strategy / CEO context | `memory/strategic-context-btc-copilot-fifa.md` · `memory/yossi_requirements.md` |

---

## Safety & Truth-Telling — non-negotiable

- **Anti-hallucination.** Never invent a source, figure, date or citation. Unknown input = `[NEEDS DATA]`. Halt rather than guess.
- **Precedence:** safety / untrusted data **>** data integrity **>** clarity **>** brevity **>** format.
- **Dissent.** If the data contradicts a stakeholder's premise, say so first, with the number. Deference to hierarchy never overrides data integrity. Lead bad news with the figure and the fix.
- **Never soften a metric** to make a slide read better. Positive scripting governs *framing*, never the number.
- **Source data is never silently changed** — flag discrepancies, do not quietly fix them.
- **Escalation gate.** Revenue-at-risk, compliance / security exposure, or logo-loss → tag `[ESCALATION-THRESHOLD: TBD]` and **wait for Phillip's confirmation** before anything reaches Yossi Tal.
- **Memory approval gate.** Before writing a new rule to memory, ask: *"I have noted a strategic pivot regarding [Topic]. Do you approve adding this to core memory?"* Append or surgically update — never rewrite an established rule.
- **No browser storage** (localStorage / sessionStorage) in any HTML artifact.

---

## Data Rules — the ones that break reports

**Authority chain:** 1 CS MBR deck (slides 62–64) → 2 daily SR / MBR PPTX → 3 Looker Conversion tab *(secondary — must be labeled)* → 4 Sales Opportunity dashboard *(cross-check only; never overwrites a locked value without Phillip's confirmation)*.
MBR does not outrank SR — authority splits by purpose → `memory/mbr_authority.md`

**Three ticket denominators — keep them apart**

1. **MBR "Sales Tickets"** (slide 63) — the authoritative presales denominator
2. **Looker Conversion volume** — narrower, weighted-credit basis (source of the `.5` / `.67` / `.17` fractions)
3. **Zendesk category volume** — category counts; **never** a conversion denominator

**Four basis axes — two figures compare only if all four match:** date attribution (filed vs sub) · validation state · numerator (raw closed vs weighted split credit) · denominator. **Trend series use filed date** — the only basis present in every month.

- Label every published figure `[value · basis · confidence]`; state cadence and as-of date.
- Never publish a conv% whose sales are mostly unvalidated. 🔴 **Never publish CG June 58.43% / PIA June 66.07%.**
- 🔴 **Never quote live-feed Jan–Jun** from the SR feed — migrated months read 17–28% low → `memory/sr-feed-migration-deficit-aug12.md`
- Assert every rate = its own numerator ÷ denominator — and sweep hero copy, not just tables → `memory/derived-rate-assertion.md`
- No series labelled XV or All may include support volume → `memory/presale-only-graph-rule.md`
- Never publish an unmeasured per-agent rate → `memory/agent-heatmap-modeled-retired.md`
- **Month-1 figures are a floor.** Restatements land later — always pair validated with pending upside.
- Round counts **up** at display; conv% stays precise where a ceiling would distort.
- Sanity ranges (flag outside): XV conv 24–30% · BAU 15–22% · CG 26–38% · PIA 30–40%.
- Kianna Sison → excluded from agent rankings. Agent `#N/A` → always render as **"Jhem"**.

---

## Brand Routing — `R = Devices ÷ Licensed Users`

| Condition | Route to | Why |
|---|---|---|
| R > 3.0 · SOC2 / HIPAA | **PIA** | unlimited simultaneous devices · Deloitte no-logs audit · RAM-only NextGen servers |
| R ≤ 2.0 · ISO 27001 · dev / API / MCP | **ExpressVPN for Teams** | per-user volume tiers · 10-Gbps · Lightway |
| Localized scale / CAPTCHA avoidance | **CyberGhost** | 11,500+ servers, 100+ countries |
| Mac endpoint security | **Intego** | — |
| Global eSIM | **Holiday.com** | — |

Never cannibalize internal brands — route on constraints, not preference.

---

## No Internal Codenames Externally

| Internal | Say instead |
|---|---|
| CERBERUS | "client-side PII scrubber" / "output guardrails" |
| ATHENA | "knowledge-base retrieval and framework detection" |
| HERMES | "the Claude integration" |
| Hades Hub | never mention |

---

## Build Constraints — full detail in `memory/build-canon-weekly-and-progress.md`

- **Two visual canons exist and never merge.** Weekly report (slate `#020617`) vs progress update (obsidian `#050505` + royal-blue→cyan). If a deliverable is ambiguous, ask which canon applies.
- **Copy the canonical file, change the numbers, do not redesign.** Restyling needs explicit instruction.
- Edit report JS via Python `str.replace()` with **anchored** strings — never the Edit tool.
- `node --check` after every JS patch · `safeChart()` on every chart · one `DOMContentLoaded` block.
- CDN pinned: Chart.js 4.4.0 · html2canvas 1.4.1 · jsPDF 2.5.1.
- **Ten verification gates** before delivery — including the numeric sweep of every visible token and an independent subagent fact-check. Neither is optional: the sweep caught a fabricated "88% of the volume"; the fact-check returned 22 findings on a first build.
- **Light mode is the default** for slides and docs (`#F7F8FA` / `#1F2933`). The dark canons govern those two HTML artifact classes only.
