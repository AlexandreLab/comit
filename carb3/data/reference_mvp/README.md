# reference_mvp: the reference data the MVP solves on

**Generated. Do not edit.** Every file here is a row-for-row, byte-for-byte subset of
`docs/notes/data/`, produced by `carb3/data/build_reference_mvp.py`. Change the source tables
or the premises, then regenerate.

```
python3 carb3/data/build_reference_mvp.py           # rewrite this directory
python3 carb3/data/build_reference_mvp.py --check   # exit 1 naming any stale file
```

`make data-check` runs the `--check`. Run the MVP against this copy with

```
uv run --directory carb3 python -m carb3 --reference-root data/reference_mvp
```

`carb3/tests/test_reference_mvp.py` solves the three premises on both roots and asserts the
results agree.

## What it holds

The nine tables `carb3.load.REFERENCE_SCHEMA` reads, same header and column order as the
source, rows in source order, row text untouched (numbers are not reformatted). The three
premises (`mvp-minimal`, `mvp-dairy`, `mvp-cement`) sit at activities
`Cement Works`, `Food Processing Centre` and clusters `humber`, `mersey`.

## Filtering rule per table

- `activity_process_register`: rows whose `carb3_activity` is one of the premises' activities.
- `activity_process_duty_profile`: rows whose `carb3_activity` is one of the premises' activities.
- `unit_eligibility`: rows whose `carb3_activity` is one of the premises' activities, blank `process_id` rows (activity-level supply) included.
- `unit_abatement_host`: rows whose capture train (`unit_id`) is kept; the `host_unit_id` of each such row is then added to the kept units, since V33 leg (b) resolves both keys against `unit`.
- `unit`: units in a kept eligibility row, or named in `premise_process_unit`, or the host of a kept abatement row.
- `unit_input_output`: rows whose `unit_id` is a kept unit.
- `carrier`: every carrier a kept row names: `unit_input_output.carrier_id`, `unit.fuel_carrier_id`, the duty profile's `carrier_id`, the premise connection, energy and throughput carriers, and an `infrastructure_scenario.carrier` that is also a carrier id (`hydrogen`).
- `scenario_parameters`: rows whose `carrier_id` is a kept carrier, plus rows with a blank `carrier_id` (global: `carbon_price`, `discount_rate`).
- `infrastructure_scenario`: every row of the premises' clusters (`cluster_id` of `premise_record`).

## Row counts

| Table | Source rows | Subset rows |
|---|---|---|
| `carrier` | 53 | 35 |
| `unit` | 148 | 67 |
| `unit_input_output` | 477 | 200 |
| `unit_abatement_host` | 37 | 20 |
| `unit_eligibility` | 3773 | 124 |
| `scenario_parameters` | 162 | 141 |
| `activity_process_duty_profile` | 538 | 24 |
| `activity_process_register` | 375 | 15 |
| `infrastructure_scenario` | 189 | 42 |

## What a subset changes

The reference tables as a whole are screened by `carb3.load.screen_units` (the section 3.2
admission screen), and its run report lists every unit it drops. Against this subset the
screen sees only the kept units, so the "admitted N units, dropped M" line and the drop list
cover fewer units than on the full tables. No unit the premises can reach is missing, so the
solves are the same.
