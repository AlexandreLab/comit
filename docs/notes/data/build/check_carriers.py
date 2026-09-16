#!/usr/bin/env python3
"""Checks for the `carriers` lane. Stdlib only (pandas is not installed here).

Run from anywhere:  python3 docs/notes/data/build/check_carriers.py

Blocking checks
  1. every carrier_id in the three outputs resolves to docs/notes/data/carrier.csv
  2. carrier_factors.csv has exactly one row per primary carrier, and no others
  3. every [REF_ID] cited in a provenance resolves to references_carriers.csv
     or the existing references.csv
  4. every populated row carries a provenance
  5. enums and booleans are spelled as the spec spells them; blanks are empty
  6. biogenic_fraction in [0, 1]
  7. V21: export_price strictly below import_price for the same carrier and period
  8. infrastructure_scenario carrier enum and a complete cluster x carrier x period grid
"""
import csv, os, re, sys

_HERE = os.path.dirname(os.path.abspath(__file__))          # docs/notes/data/build
ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))  # repo root
DATA = os.path.join(ROOT, 'docs', 'notes', 'data')
STAGING = os.path.join(DATA, 'build')

errors, notes, warnings = [], [], []
def bad(msg): errors.append(msg)

def read(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

carrier = read(os.path.join(DATA, 'carrier.csv'))
CARRIER_IDS = {r['carrier_id'] for r in carrier}
PRIMARY = {r['carrier_id'] for r in carrier if r['carrier_kind'] == 'primary'}

factors = read(os.path.join(STAGING, 'carrier_factors.csv'))
params  = read(os.path.join(DATA, 'scenario_parameters.csv'))
infra   = read(os.path.join(DATA, 'infrastructure_scenario.csv'))

ref_ids = {r['ref_id'] for r in read(os.path.join(STAGING, 'references_carriers.csv'))}
ref_ids |= {r['ref_id'] for r in read(os.path.join(DATA, 'references.csv'))}

# 1 + 2 -- carrier_id resolution
for r in factors:
    if r['carrier_id'] not in CARRIER_IDS:
        bad(f"carrier_factors: unknown carrier_id {r['carrier_id']!r}")
got = {r['carrier_id'] for r in factors}
if got != PRIMARY:
    for c in sorted(PRIMARY - got): bad(f'carrier_factors: missing primary carrier {c!r}')
    for c in sorted(got - PRIMARY): bad(f'carrier_factors: {c!r} is not a primary carrier')
if len(got) != len(factors):
    bad('carrier_factors: duplicate carrier_id')

for r in params:
    if r['carrier_id'] and r['carrier_id'] not in CARRIER_IDS:
        bad(f"scenario_parameters: unknown carrier_id {r['carrier_id']!r}")

# 3 -- every [REF_ID] resolves
CITE = re.compile(r'\[([A-Z0-9_]{2,24})\]')
for name, rows in (('carrier_factors', factors), ('scenario_parameters', params),
                   ('infrastructure_scenario', infra)):
    for r in rows:
        for rid in CITE.findall(r.get('provenance', '')):
            if rid not in ref_ids:
                bad(f'{name}: [{rid}] does not resolve to references_carriers.csv or references.csv')

# 4 -- populated rows carry provenance
for r in factors:
    if r['ef_gross_kt_per_pj'] and not r['provenance']:
        bad(f"carrier_factors: {r['carrier_id']} has a factor and no provenance")
for r in params:
    if r['value'] and not r['provenance']:
        bad(f"scenario_parameters: {r['parameter_id']}/{r['period']} has a value and no provenance")
for r in infra:
    if not r['provenance']:
        bad(f"infrastructure_scenario: {r['cluster_id']}/{r['carrier']}/{r['period']} has no provenance")

# 5 -- enums, booleans, blanks
BLANK_IMPOSTORS = {'NA', 'N/A', 'n/a', '-', '?', 'null', 'NULL', 'None'}
for name, rows in (('carrier_factors', factors), ('scenario_parameters', params),
                   ('infrastructure_scenario', infra)):
    for r in rows:
        for k, v in r.items():
            if v in BLANK_IMPOSTORS:
                bad(f'{name}: {k}={v!r} - blanks must be empty strings')
for r in factors:
    if r['gcv_ncv_basis'] not in ('', 'gross_cv', 'net_cv', 'not_applicable'):
        bad(f"carrier_factors: gcv_ncv_basis {r['gcv_ncv_basis']!r} not in the allowed set")
    if r['confidence'] not in ('', 'high', 'medium', 'low'):
        bad(f"carrier_factors: confidence {r['confidence']!r} not in the allowed set")
    if r['emission_factor_source'] and r['emission_factor_source'] != 'ef_' + r['carrier_id']:
        bad(f"carrier_factors: emission_factor_source {r['emission_factor_source']!r} is not ef_<carrier_id>")
for r in infra:
    if r['available'] not in ('TRUE', 'FALSE'):
        bad(f"infrastructure_scenario: available {r['available']!r} must be TRUE or FALSE")

# 6 -- biogenic_fraction range
for r in factors:
    if r['biogenic_fraction']:
        v = float(r['biogenic_fraction'])
        if not 0.0 <= v <= 1.0:
            bad(f"carrier_factors: biogenic_fraction {v} for {r['carrier_id']} outside [0, 1]")

# 6b -- emission_factor_source points at a series that exists (warning: an
# unsourced carrier keeps its pointer, because spec 3.4 requires the field)
series = {r['parameter_id'] for r in params}
for r in factors:
    s = r['emission_factor_source']
    if s and s not in series:
        warnings.append(f"{s!r} has no rows in scenario_parameters.csv "
                        f"(no published factor for {r['carrier_id']} - a recorded gap)")

# 7 -- V21 (the export price is strictly below the import price)
imp = {(r['carrier_id'], r['period']): float(r['value'])
       for r in params if r['parameter_id'] == 'import_price' and r['value']}
exp = {(r['carrier_id'], r['period']): float(r['value'])
       for r in params if r['parameter_id'] == 'export_price' and r['value']}
for k, v in exp.items():
    if k not in imp:
        bad(f'V21 (export price strictly below import price): export_price for {k} has no import_price to compare')
    elif not v < imp[k]:
        bad(f'V21 (export price strictly below import price): {k} export {v} >= import {imp[k]}')

# 8 -- infrastructure grid
INFRA_CARRIERS = {'hydrogen', 'co2_transport', 'grid_headroom'}
clusters = sorted({r['cluster_id'] for r in infra})
periods  = sorted({r['period'] for r in infra})
for r in infra:
    if r['carrier'] not in INFRA_CARRIERS:
        bad(f"infrastructure_scenario: carrier {r['carrier']!r} not in {sorted(INFRA_CARRIERS)}")
seen = {(r['cluster_id'], r['carrier'], r['period']) for r in infra}
if len(seen) != len(infra):
    bad('infrastructure_scenario: duplicate (cluster_id, carrier, period)')
for c in clusters:
    for k in sorted(INFRA_CARRIERS):
        for p in periods:
            if (c, k, p) not in seen:
                bad(f'infrastructure_scenario: no row for {c}/{k}/{p}')

notes.append(f'carrier.csv: {len(carrier)} carriers, {len(PRIMARY)} primary')
notes.append(f'carrier_factors.csv: {len(factors)} rows, '
             f"{sum(1 for r in factors if r['ef_gross_kt_per_pj'])} with a factor")
notes.append(f'scenario_parameters.csv: {len(params)} rows, {len(series)} series, periods {periods}')
notes.append(f'infrastructure_scenario.csv: {len(infra)} rows, {len(clusters)} clusters')

for n in notes: print('  ' + n)
if warnings:
    print(f'\n{len(warnings)} warning(s):')
    for w in warnings: print('  ! ' + w)
if errors:
    print(f'\n{len(errors)} FAILURE(S):')
    for e in errors: print('  x ' + e)
    sys.exit(1)
print('\nall checks pass')
