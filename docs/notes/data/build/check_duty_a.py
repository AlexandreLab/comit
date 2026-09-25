#!/usr/bin/env python3
"""Lane duty_a validator. Stdlib only (pandas is not installed in this repo).

Checks, per brief_duty_common.md:
  (a) every register row in the lane's activity list has >= 1 duty row
  (b) duty_share sums to 1.00 +/- 0.015 per (activity, set, process)
  (c) every heat row carries a grade_rank, and it matches carrier.csv
  (d) all keys and every [REF_ID] resolve
plus schema checks: column order, enums, booleans, no NA/-/? placeholders,
band ordering, crosswalk completeness and the sector-root prohibition.

Exit status 0 = clean, 1 = at least one failure.
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, os.pardir))

DUTY = os.path.join(HERE, 'activity_process_duty_profile_duty_a.csv')
XW   = os.path.join(HERE, 'carb3_comit_process_crosswalk_duty_a.csv')
REFS_LANE = os.path.join(HERE, 'references_duty_a.csv')
REG  = os.path.join(DATA, 'activity_process_register.csv')
CARR = os.path.join(DATA, 'carrier.csv')
REFS = os.path.join(DATA, 'references.csv')
COMIT = os.path.join(DATA, 'comit_sector_processes.csv')

ACTIVITIES = [
 'Abattoir / Slaughter House','Aggregate/Mineral Processing Plant / Depot','Aircraft works',
 'Aluminium Smelting Works','Artificial Fibre Works','Asphalt Plant','Beet Sugar Factory',
 'Brewery','Brickworks / clay tile/pipe works','Cement Tile Works','Cement Works',
 'Chemical Works','Coking and Carbonising Plant','Concrete Block Works',
 'Concrete Product Works','Concrete batching plant','Creamery','Distillery',
 'Effluent Minewater Treatment Plant','Exhaust and tyre centre','Factory','Flour Mill',
 'Food Processing Centre','Foundry','Industrial Minerals NEC','Industrial NEC',
 'Iron and/or Steel Works']

DUTY_COLS = ['carb3_activity','process_set_id','process_id','duty_family','carrier_id',
             'grade_rank','duty_share','share_low','share_high','evidence_tier',
             'provenance','confidence']
XW_COLS = ['carb3_activity','process_set_id','process_id','comit_process_code',
           'match_kind','notes']

FAMILIES = {'DRY','HRS','HTH','LTH','MOT','NEUOTH','OTH','PHEAT','REF','SPC','STM'}  # EN is a unit family only (spec 3.4, note 22 Task 1)
TIERS = {'measured','engineering','published_sec','fallback'}
CONF = {'high','medium','low'}
KINDS = {'direct','analogue','none'}
HEAT_FAMILIES = {'DRY','HTH','LTH','PHEAT','SPC','STM'}
PLACEHOLDERS = {'NA','n/a','N/A','-','?','none','NULL','null'}
# the 16 COMIT sector-root codes: sector totals, never a process
SECTOR_ROOTS = {'ICH','ICM','ICN','ICR','IEE','IFD','IGL','IIS','ILM','IME','INF','IOI',
                'IPP','IPR','ITX','IVH'}

fails, warns = [], []
def fail(msg): fails.append(msg)
def warn(msg): warns.append(msg)

def read(path):
    with open(path, newline='') as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)

# ------------------------------------------------------------------ load keys
_, reg_rows = read(REG)
register = {(r['carb3_activity'], r['process_set_id'], r['process_id'])
            for r in reg_rows if r['carb3_activity'] in ACTIVITIES}
_, carr_rows = read(CARR)
carriers = {r['carrier_id']: r for r in carr_rows}
gradeable = {cid for cid, r in carriers.items() if r['is_gradeable'].strip().upper() == 'TRUE'}
_, ref_rows = read(REFS)
ref_ids = {r['ref_id'] for r in ref_rows}
if os.path.exists(REFS_LANE):
    lane_cols, lane_refs = read(REFS_LANE)
    if lane_cols != ['ref_id','title','publisher','year','url','accessed','note']:
        fail('references_duty_a.csv columns differ from references.csv: %s' % lane_cols)
    for r in lane_refs:
        if r['ref_id'] in ref_ids:
            fail('references_duty_a.csv re-declares existing ref_id %s' % r['ref_id'])
        if not re.fullmatch(r'[A-Z0-9_]{1,24}', r['ref_id']):
            fail('ref_id %r is not UPPER_SNAKE <= 24 chars' % r['ref_id'])
        ref_ids.add(r['ref_id'])
else:
    fail('references_duty_a.csv is missing')
_, comit_rows = read(COMIT)
comit_codes = {r['process_commodity'] for r in comit_rows}

print('register rows in lane: %d (%d activities)' %
      (len(register), len({a for a, _, _ in register})))
if len(register) != 196:
    fail('expected 196 register rows in this lane, found %d' % len(register))

# ------------------------------------------------------------------ duty file
cols, duty = read(DUTY)
if cols != DUTY_COLS:
    fail('duty column order is %s, spec section 3.3 wants %s' % (cols, DUTY_COLS))

seen_pk = set()
covered = set()
for i, r in enumerate(duty, start=2):
    where = 'duty row %d (%s / %s / %s / %s)' % (
        i, r['carb3_activity'], r['process_set_id'], r['process_id'], r['duty_family'])
    key = (r['carb3_activity'], r['process_set_id'], r['process_id'])

    # (d) keys resolve
    if key not in register:
        fail('%s: key not in activity_process_register.csv' % where)
    covered.add(key)

    if r['duty_family'] not in FAMILIES:
        fail('%s: duty_family not in the 12 families' % where)
    if r['evidence_tier'] not in TIERS:
        fail('%s: evidence_tier %r' % (where, r['evidence_tier']))
    if r['confidence'] not in CONF:
        fail('%s: confidence %r' % (where, r['confidence']))

    # (d) carrier resolves
    if r['duty_family'] == 'NEUOTH':
        if r['carrier_id']:
            fail('%s: NEUOTH must carry a blank carrier' % where)
    elif r['carrier_id'] not in carriers:
        fail('%s: carrier_id %r not in carrier.csv' % (where, r['carrier_id']))

    # (c) heat rows carry a grade, and it is the carrier's own grade
    rank = r['grade_rank'].strip()
    if r['carrier_id'] in gradeable:
        if not rank:
            fail('%s: gradeable carrier %s with no grade_rank' % (where, r['carrier_id']))
        elif rank != carriers[r['carrier_id']]['grade_rank']:
            fail('%s: grade_rank %s != carrier.csv grade_rank %s for %s' %
                 (where, rank, carriers[r['carrier_id']]['grade_rank'], r['carrier_id']))
    else:
        if rank:
            fail('%s: grade_rank set on non-gradeable carrier %s' % (where, r['carrier_id']))
    if r['duty_family'] in HEAT_FAMILIES and r['carrier_id'] not in gradeable:
        fail('%s: heat family with non-heat carrier %s' % (where, r['carrier_id']))
    if r['duty_family'] == 'MOT' and r['carrier_id'] != 'motive_power':
        fail('%s: MOT must use motive_power' % where)
    if r['duty_family'] == 'REF' and r['carrier_id'] not in ('cooling_lt0', 'cooling_0_15', 'cooling_gt15'):
        fail('%s: REF must use a cooling band (note 22 Task 3)' % where)

    # PK uniqueness: (activity, set, process, family, grade_rank)
    pk = key + (r['duty_family'], rank)
    if pk in seen_pk:
        fail('%s: duplicate primary key' % where)
    seen_pk.add(pk)

    # share range and banding
    try:
        share = float(r['duty_share'])
    except ValueError:
        fail('%s: duty_share %r is not a number' % (where, r['duty_share'])); continue
    if not (0.0 <= share <= 1.0):
        fail('%s: duty_share %s outside [0, 1]' % (where, share))
    for band, cmpf in (('share_low', lambda v: v <= share), ('share_high', lambda v: v >= share)):
        if r[band].strip():
            try:
                v = float(r[band])
            except ValueError:
                fail('%s: %s %r is not a number' % (where, band, r[band])); continue
            if not cmpf(v):
                fail('%s: %s %s does not bracket duty_share %s' % (where, band, v, share))

    # provenance and placeholders
    if not r['provenance'].strip():
        fail('%s: empty provenance' % where)
    for m in re.findall(r'\[([A-Za-z0-9_]+)\]', r['provenance']):
        if m not in ref_ids:
            fail('%s: [%s] does not resolve to references.csv or references_duty_a.csv'
                 % (where, m))
    if not re.search(r'\[[A-Za-z0-9_]+\]', r['provenance']):
        fail('%s: provenance carries no [REF_ID]' % where)
    for c in DUTY_COLS:
        if r[c].strip() in PLACEHOLDERS:
            fail('%s: column %s holds placeholder %r (blanks must be empty)' % (where, c, r[c]))

# (a) coverage
missing = register - covered
for k in sorted(missing):
    fail('register row with no duty row: %s' % (k,))

# (b) shares sum to 1.00 +/- 0.015
sums = {}
for r in duty:
    k = (r['carb3_activity'], r['process_set_id'], r['process_id'])
    try:
        sums[k] = sums.get(k, 0.0) + float(r['duty_share'])
    except ValueError:
        pass
for k, v in sorted(sums.items()):
    if abs(v - 1.0) > 0.015:
        fail('duty_share for %s sums to %.5f, not 1.00 +/- 0.015' % (k, v))

# ------------------------------------------------------------- crosswalk file
cols, xrows = read(XW)
if cols != XW_COLS:
    fail('crosswalk column order is %s, brief wants %s' % (cols, XW_COLS))
xw_keys = set()
for i, r in enumerate(xrows, start=2):
    where = 'crosswalk row %d (%s / %s / %s)' % (
        i, r['carb3_activity'], r['process_set_id'], r['process_id'])
    k = (r['carb3_activity'], r['process_set_id'], r['process_id'])
    if k not in register:
        fail('%s: key not in activity_process_register.csv' % where)
    if k in xw_keys:
        fail('%s: duplicate register key' % where)
    xw_keys.add(k)
    if r['match_kind'] not in KINDS:
        fail('%s: match_kind %r' % (where, r['match_kind']))
    code = r['comit_process_code'].strip()
    if code:
        if code not in comit_codes:
            fail('%s: %s is not one of the 94 COMIT process codes' % (where, code))
        if code in SECTOR_ROOTS:
            fail('%s: %s is a sector-root code and must never be mapped to' % (where, code))
        if r['match_kind'] == 'none':
            fail('%s: match_kind none with a non-blank code' % where)
    else:
        if r['match_kind'] != 'none':
            fail('%s: blank code must carry match_kind none' % where)
    if not r['notes'].strip():
        fail('%s: empty notes' % where)
for k in sorted(register - xw_keys):
    fail('register row with no crosswalk row: %s' % (k,))

# ----------------------------------------------------------------- report
print('duty rows: %d' % len(duty))
print('crosswalk rows: %d' % len(xrows))
print('processes covered: %d of %d' % (len(covered), len(register)))
for w in warns:
    print('WARN  ' + w)
if fails:
    print('\n%d FAILURE(S):' % len(fails))
    for f in fails:
        print('  FAIL  ' + f)
    sys.exit(1)
print('\nAll checks pass.')
