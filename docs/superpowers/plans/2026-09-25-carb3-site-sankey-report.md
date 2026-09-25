# carb3 site report — a Sankey per premise, with a year slider

*Plan written 2026-09-25. Nothing built yet.*

## What it is

For every premise `python -m carb3 --out-dir …` solves, write one more file beside the seven
parquet tables: `site_report.html`. It opens offline in any browser and shows:

- **Top — a Sankey of the site in one period.** Imports on the left, units in the middle,
  and on the right the four ways a stream ends that D16 (an internal product is a carrier,
  the site boundary is a property of the carrier) names: a duty delivered to a process, an
  export, a disposal, or a loss inside a unit.
- **Bottom — a year slider** over the seven periods (2021 … 2050) with a play button. Moving
  it redraws the Sankey for that year, animated, so a switch from a gas boiler to a heat pump
  reads as one ribbon thinning while another grows.
- **Under the slider — the site's evolution across all years**, four small charts that share
  the slider's year as a highlighted column: imports by carrier, available capacity by unit,
  cost by term, and CO₂ vented versus exported. Clicking a year on any of them moves the
  slider.

## What the output has today, and the gap

The ledger writes `dispatch` (unit activity per duty and period), `carrier_mix` (per carrier:
imported, produced, consumed, disposed, exported), `build`, `cost_by_term` and `disposal`.

**It has no table saying how much of which carrier each unit drew or made.** `dispatch` gives
`z` (a unit's activity) and `carrier_mix` gives carrier totals, but the edge *natural gas →
boiler_lt_gas* exists only inside the solver, as activity × the `unit_input_output`
coefficient. A Sankey needs exactly those edges. Recomputing them in the report would break
the ledger's own rule — "every number here is read back from the solution, never recomputed"
— so the first task adds them to the ledger, where `_balance_coefficients` already has them.

## Design decisions (defaults — flag any you want changed)

1. **Three tabs, one unit each — settled 2026-09-25.** The site's flows are in PJ (energy), Mt (clinker,
   cement) and kt (CO₂). One ribbon width cannot mean all three. The report carries a tab
   per layer — **Energy (PJ)** by default, **CO₂ (kt)**, **Materials (Mt)** — and a unit
   appears in every layer it touches (the cement kiln is in all three). A layer with no
   flow at a premise is not shown.
2. **Width scale fixed across years.** Scaled to the largest year of that layer, so a
   shrinking site looks smaller. Per-year autoscaling would make 2021 and 2050 look the same
   size.
3. **Node positions stable across years.** The layout is computed once over the union of
   nodes in all periods; a node with no flow in a year collapses to zero height rather than
   disappearing, so ribbons do not jump when the slider moves.
4. **Losses are explicit.** In the Energy layer, a unit's energy in minus energy out is drawn
   to a `losses` node. Reject heat is not a loss: it is a carrier (`heat_lt60`) and ends at
   disposal or feeds a heat pump.
5. **One self-contained HTML file, no network.** JSON data embedded, `d3` and `d3-sankey`
   vendored and inlined (≈100 kB after trimming to the modules used). Generated from stdlib
   Python plus the parquet tables; no plotting dependency added to `pyproject.toml`.
6. **Regenerable without re-solving.** `python -m carb3.report outputs/carb3/mvp-dairy`
   rebuilds the HTML from the parquet alone, so changing the page never costs a solve.
7. **It is not model code.** `carb3`'s docstring fixes the model at five modules. The report
   lives in `carb3/src/carb3/report/`, reads only the ledger's parquet, and imports nothing
   from `build` or `sets`; like `__main__.py`, it is wiring, not a sixth module.

## Tasks

Each task has the same four fields.

### Task 1 — `unit_flow` ledger table

- **Goal.** A sixth ledger table, one row per `(unit_id, carrier_id, role, period)`:
  `flow`, signed (+ produced, − consumed), in the carrier's own unit. Written as
  `unit_flow.parquet`.
- **Files.** `carb3/src/carb3/ledger.py` (new `_unit_flow_table`, reusing
  `_balance_coefficients` plus the `primary_output` rows; add to `LEDGER_TABLES`);
  `carb3/tests/test_ledger.py`.
- **Evidence rule.** Built from the solved `z` and the same coefficient set C8 (carrier
  balance) used, never from `dispatch` re-joined to the CSV.
- **Verification.** New test: for every carrier and period, the positive `unit_flow` sum
  equals `carrier_mix.produced` and the negative sum equals `carrier_mix.consumed`, to
  1e-9, on all three premises.

### Task 2 — Sankey data builder

- **Goal.** A pure function, parquet directory → one JSON document: per layer, the node
  list (fixed order) and per period the link list `{source, target, value}`.
- **Files.** `carb3/src/carb3/report/sankey_data.py`; `carb3/tests/test_report.py`.
- **Evidence rule.** Nodes and edges: import → carrier (`carrier_mix.imported`), carrier →
  unit and unit → carrier (`unit_flow`), carrier → process (`dispatch`, `kind = duty`),
  carrier → export (`carrier_mix.exported`), carrier → disposal (`disposal`), unit →
  losses (Energy layer only). The layer a carrier belongs to comes from `carrier.csv`'s
  `carrier_kind` (`emission` → CO₂, `product` → Materials, the rest → Energy), not from
  its name.
- **Verification.** Tests: every link value ≥ 0; no NaN; every period present; the graph
  is acyclic (d3-sankey cannot draw a cycle — a failure names the loop); each carrier
  node's inflow equals its outflow to 1e-9 per period.

### Task 3 — the HTML page

- **Goal.** The Sankey, the layer tabs, the year slider with play, hover tooltips (value,
  unit, share of the node; on a unit, its available capacity and utilisation that year),
  light and dark themes.
- **Files.** `carb3/src/carb3/report/template.html`,
  `carb3/src/carb3/report/vendor/{d3,d3-sankey}.min.js` (with their licences),
  `carb3/src/carb3/report/render.py` (inlines JSON and JS into the template).
- **Evidence rule.** No `fetch`, no CDN: the file must render with networking off.
- **Verification.** Open `mvp-cement`'s report with the network disabled; move the slider
  through all seven periods; check the kiln switch (coal → gas by 2025) and the CCS train
  appearing in 2035 are visible in the Energy and CO₂ layers.

### Task 4 — the evolution panel

- **Goal.** Four small multiples under the slider: stacked area of imports by carrier;
  available capacity by unit (`build`); cost by term as stacked bars (`cost_by_term`,
  discounted and undiscounted toggle); CO₂ vented versus exported. The slider's year is a
  highlighted column on each; clicking a column moves the slider.
- **Files.** `template.html`, `sankey_data.py` (adds the four series to the JSON).
- **Evidence rule.** Cost totals must equal `run_report`'s objective; the panel shows the
  residual if they do not, rather than hiding it.
- **Verification.** On `mvp-dairy`, the cost bars sum to the printed objective; the
  capacity chart shows `boiler_lt_gas`'s original capacity retiring in 2045 and
  0.072 PJ/yr rebuilt the same year, as `build.parquet` says.

### Task 5 — CLI and Makefile wiring

- **Goal.** `python -m carb3 --out-dir …` writes `site_report.html` per solved premise;
  `--no-report` skips it; `python -m carb3.report <dir>` regenerates one;
  `make carb3-report OUT_DIR=…` regenerates all.
- **Files.** `carb3/src/carb3/__main__.py`, `carb3/src/carb3/report/__main__.py`,
  `Makefile`, `carb3/README.md`.
- **Evidence rule.** A blocked or non-optimal premise writes no report — there is nothing
  solved to draw.
- **Verification.** `make carb3-run OUT_DIR=outputs/carb3` leaves three HTML files; `make
  check` still green.

## Order

Task 1 blocks Task 2, which blocks 3 and 4. Tasks 3 and 4 share `template.html`, so one
agent owns both. Task 5 last.

## Out of scope

Comparing premises side by side; comparing scenarios (e.g. two `--co2-tariff` runs);
emissions attribution (MF-52, MF-53, MF-79 — out of the slice per note 21); any hosted
dashboard.
