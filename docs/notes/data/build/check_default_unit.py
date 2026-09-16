#!/usr/bin/env python3
"""Lane default_unit validator (T18). Stdlib only (pandas is not installed in this repo).

The brief's four checks:
  1. default_share sums to 1.00 +/- 0.015 per (activity, set, process, duty_family)
  2. every unit_id resolves to unit.csv
  3. every (activity, set, process) resolves to activity_process_register.csv
  4. every (unit_id, activity, process_id) has a unit_eligibility row
     -- REPORTED as a count, never failed, as the brief directs

plus schema checks: column order, enums, no placeholders, every duty in
activity_process_duty_profile.csv is served, every [REF_ID] resolves, and a
REPORTED count of rows whose unit breaks C10 (grade_out < the duty's grade_rank).

Exit status 0 = clean, 1 = at least one failure.
"""
import csv, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, os.pardir))
ADU  = os.path.join(DATA, 'activity_default_unit.csv')
DP   = os.path.join(DATA, 'activity_process_duty_profile.csv')
REG  = os.path.join(DATA, 'activity_process_register.csv')
UNIT = os.path.join(DATA, 'unit.csv')
ELIG = os.path.join(DATA, 'unit_eligibility.csv')
REFS = os.path.join(DATA, 'references.csv')
LANE = os.path.join(HERE, 'references_default_unit.csv')

COLS = ['carb3_activity','process_set_id','process_id','duty_family','unit_id',
        'default_share','sizing_basis','evidence_tier','provenance','confidence']
BASES = {'duty_annual','duty_peak','throughput'}
TIERS = {'sector_statistic','derived','assumed'}
CONF  = {'high','medium','low'}
PLACEHOLDERS = {'NA','n/a','N/A','-','?','none','NULL','null'}

fails, reported = [], []
def fail(m): fails.append(m)

def read(p):
    with open(p, newline='') as f:
        r = csv.DictReader(f); return r.fieldnames, list(r)

_, adu  = read(ADU)
_, dp   = read(DP)
_, reg  = read(REG)
_, unit = read(UNIT)
_, elig = read(ELIG)
_, refs = read(REFS)

units    = {u['unit_id']: u for u in unit}
register = {(r['carb3_activity'], r['process_set_id'], r['process_id']) for r in reg}
duties   = {(r['carb3_activity'], r['process_set_id'], r['process_id'], r['duty_family']): r
            for r in dp}
eligible = {(r['unit_id'], r['carb3_activity'], r['process_id']) for r in elig}
elig_act = {(r['unit_id'], r['carb3_activity']) for r in elig if not r['process_id']}
ref_ids  = {r['ref_id'] for r in refs}
if os.path.exists(LANE):
    lc, lr = read(LANE)
    if lc != ['ref_id','title','publisher','year','url','accessed','note']:
        fail('references_default_unit.csv columns differ from references.csv: %s' % lc)
    for r in lr:
        if r['ref_id'] in ref_ids:
            fail('references_default_unit.csv re-declares existing ref_id %s' % r['ref_id'])
        if not re.fullmatch(r'[A-Z0-9_]{1,24}', r['ref_id']):
            fail('ref_id %r is not UPPER_SNAKE <= 24 chars' % r['ref_id'])
        ref_ids.add(r['ref_id'])
else:
    # The coordinator merges each lane's staging reference file into references.csv and
    # deletes it, so its absence is the merged state, not an error. What must still hold
    # is that this lane's three new ids are present in references.csv.
    missing = {'DUKES_7_4', 'ECUK_2025_U4', 'CARB3_EP'} - ref_ids
    if missing:
        fail('references_default_unit.csv is gone (merged) but references.csv is missing '
             "this lane's ids: %s" % ', '.join(sorted(missing)))
    else:
        reported.append('references_default_unit.csv has been merged into references.csv; '
                        'DUKES_7_4, ECUK_2025_U4 and CARB3_EP all resolve there')

cols, _ = read(ADU)
if cols != COLS:
    fail('column order is %s, spec section 3.16 wants %s' % (cols, COLS))

def gi(s):
    try: return int(s)
    except: return None

no_elig, c10, seen_pk, served = [], [], set(), set()
for i, r in enumerate(adu, start=2):
    key3 = (r['carb3_activity'], r['process_set_id'], r['process_id'])
    key4 = key3 + (r['duty_family'],)
    where = 'row %d (%s / %s / %s / %s / %s)' % (i, *key4, r['unit_id'])

    # 3. register
    if key3 not in register:
        fail('%s: key not in activity_process_register.csv' % where)
    # duty_family resolves to the duty profile
    if key4 not in duties:
        fail('%s: no such duty in activity_process_duty_profile.csv' % where)
    served.add(key4)
    # 2. unit resolves
    if r['unit_id'] not in units:
        fail('%s: unit_id not in unit.csv' % where); continue
    u = units[r['unit_id']]

    pk = key4 + (r['unit_id'],)
    if pk in seen_pk: fail('%s: duplicate primary key' % where)
    seen_pk.add(pk)

    if r['sizing_basis'] not in BASES: fail('%s: sizing_basis %r' % (where, r['sizing_basis']))
    if r['evidence_tier'] not in TIERS: fail('%s: evidence_tier %r' % (where, r['evidence_tier']))
    if r['confidence'] not in CONF: fail('%s: confidence %r' % (where, r['confidence']))
    try:
        sh = float(r['default_share'])
        if not (0.0 <= sh <= 1.0): fail('%s: default_share %s outside [0, 1]' % (where, sh))
    except ValueError:
        fail('%s: default_share %r is not a number' % (where, r['default_share']))

    for c in COLS:
        if not r[c].strip(): fail('%s: column %s is blank (section 3.16 allows none)' % (where, c))
        elif r[c].strip() in PLACEHOLDERS: fail('%s: column %s holds placeholder %r' % (where, c, r[c]))
    for m in re.findall(r'\[([A-Za-z0-9_]+)\]', r['provenance']):
        if m not in ref_ids:
            fail('%s: [%s] does not resolve to references.csv or references_default_unit.csv' % (where, m))

    # 4. eligibility -- REPORTED, not failed
    if (r['unit_id'], r['carb3_activity'], r['process_id']) not in eligible \
       and (r['unit_id'], r['carb3_activity']) not in elig_act:
        no_elig.append((r['carb3_activity'], r['process_id'], r['duty_family'], r['unit_id']))
    # C10 -- REPORTED, not failed
    dg, go = gi(duties.get(key4, {}).get('grade_rank', '')), gi(u['grade_out'])
    if dg is not None and go is not None and go < dg:
        c10.append((r['carb3_activity'], r['process_id'], r['duty_family'], r['unit_id'], go, dg))

# 1. shares sum
sums = collections.defaultdict(float)
for r in adu:
    try: sums[(r['carb3_activity'], r['process_set_id'], r['process_id'], r['duty_family'])] += float(r['default_share'])
    except ValueError: pass
for k, v in sorted(sums.items()):
    if abs(v - 1.0) > 0.015:
        fail('default_share for %s sums to %.5f, not 1.00 +/- 0.015' % (k, v))

# every duty served
for k in sorted(set(duties) - served):
    fail('duty with no default unit: %s' % (k,))

print('duties in activity_process_duty_profile.csv: %d' % len(duties))
print('default-unit rows:                          %d' % len(adu))
print('duties served:                              %d of %d' % (len(served), len(duties)))
print('distinct units used:                        %d of %d in unit.csv'
      % (len({r['unit_id'] for r in adu}), len(units)))
print()
print('REPORTED (not failures), as the brief directs:')
for _r in reported: print('  ' + _r)
print('  rows with no unit_eligibility entry: %d (%d distinct activity/process)'
      % (len(no_elig), len({(a, p) for a, p, _, _ in no_elig})))
for x in sorted({(a, p, f) for a, p, f, _ in no_elig}):
    print('      %-44s %-30s %s' % x)
print('  rows whose unit breaks C10 (grade_out < duty grade_rank): %d' % len(c10))
for x in sorted({(a, p, f, u, go, dg) for a, p, f, u, go, dg in c10}):
    print('      %-40s %-28s %-6s %-26s grade_out %s < duty %s' % x)

if fails:
    print('\n%d FAILURE(S):' % len(fails))
    for f in fails[:60]: print('  FAIL  ' + f)
    sys.exit(1)
print('\nAll checks pass.')
