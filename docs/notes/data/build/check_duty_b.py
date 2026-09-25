#!/usr/bin/env python3
"""Validator for lane duty_b (stdlib only; pandas is not installed in this repo).

Checks, per docs/notes/data/build/brief_duty_common.md:
  (a) every register row in the lane's activity list has >= 1 duty row
  (b) duty_share sums to 1.00 +/- 0.015 per (carb3_activity, process_set_id, process_id)
  (c) every heat row carries a grade_rank, and it matches carrier.csv
  (d) all keys and every [REF_ID] resolve
plus the schema rules of spec section 3.3 and the crosswalk rules of the brief.

Run:  python3 docs/notes/data/build/check_duty_b.py
Exit: 0 clean, 1 if any check fails.
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(HERE)
LANE = 'duty_b'

DUTY_FAMILIES = {'DRY','HRS','HTH','LTH','MOT','NEUOTH','OTH','PHEAT','REF','SPC','STM'}  # EN is a unit family only (spec 3.4, note 22 Task 1)
HEAT_FAMILIES = {'DRY','HTH','LTH','PHEAT','SPC','STM'}
TIERS = {'measured','engineering','published_sec','fallback'}
CONFS = {'high','medium','low'}
MATCH_KINDS = {'direct','analogue','none'}
SECTOR_ROOTS = {'ICH','ICM','ICR','ICN','IEE','IFD','IGL','IIS','ILM','IME','INF','IOI','IPP','IPR','ITX','IVH'}
DUTY_COLS = ['carb3_activity','process_set_id','process_id','duty_family','carrier_id','grade_rank',
             'duty_share','share_low','share_high','evidence_tier','provenance','confidence']
X_COLS = ['carb3_activity','process_set_id','process_id','comit_process_code','match_kind','notes']
BAD_BLANKS = {'NA','N/A','n/a','na','-','?','none','None','null','NULL'}

errors, warnings = [], []
def err(m): errors.append(m)
def warn(m): warnings.append(m)

def load(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f)), csv.DictReader(open(path, newline='')).fieldnames

acts = [l[2:] for l in open(os.path.join(HERE,'brief_%s.md'%LANE)).read()
        .split("180 register rows):\n\n")[1].strip().split("\n")]

reg, _      = load(os.path.join(DATA,'activity_process_register.csv'))
carriers, _ = load(os.path.join(DATA,'carrier.csv'))
duty, dcols = load(os.path.join(HERE,'activity_process_duty_profile_%s.csv'%LANE))
xw, xcols   = load(os.path.join(HERE,'carb3_comit_process_crosswalk_%s.csv'%LANE))
comit, _    = load(os.path.join(DATA,'comit_sector_processes.csv'))

refs = {r['ref_id'] for r in csv.DictReader(open(os.path.join(DATA,'references.csv')))}
refs |= {r['ref_id'] for r in csv.DictReader(open(os.path.join(HERE,'references_%s.csv'%LANE)))}

mine = {(r['carb3_activity'], r['process_set_id'], r['process_id']) for r in reg if r['carb3_activity'] in acts}
if len(mine) != 180:
    err('register: expected 180 rows for this lane, found %d' % len(mine))

CARRIER = {c['carrier_id']: c for c in carriers}
CODES = {c['process_commodity'] for c in comit}

# ---- schema ---------------------------------------------------------------
if dcols != DUTY_COLS: err('duty file columns are %r, expected %r' % (dcols, DUTY_COLS))
if xcols != X_COLS:    err('crosswalk columns are %r, expected %r' % (xcols, X_COLS))

# ---- (a) coverage ---------------------------------------------------------
seen = {}
for i, r in enumerate(duty, 2):
    k = (r['carb3_activity'], r['process_set_id'], r['process_id'])
    if k not in mine: err('duty row %d: key not in this lane\'s register rows: %r' % (i, k))
    seen.setdefault(k, []).append((i, r))
for k in sorted(mine - set(seen)):
    err('coverage: no duty row for register row %r' % (k,))
xseen = {}
for i, r in enumerate(xw, 2):
    k = (r['carb3_activity'], r['process_set_id'], r['process_id'])
    if k not in mine: err('crosswalk row %d: key not in this lane\'s register rows: %r' % (i, k))
    if k in xseen:    err('crosswalk row %d: duplicate register row %r' % (i, k))
    xseen[k] = r
for k in sorted(mine - set(xseen)):
    err('crosswalk: no row for register row %r' % (k,))

# ---- per-row rules --------------------------------------------------------
pk = set()
for i, r in enumerate(duty, 2):
    fam, car, gr = r['duty_family'], r['carrier_id'], r['grade_rank']
    for c in DUTY_COLS:
        if r[c].strip() in BAD_BLANKS and r[c] != '':
            err('duty row %d: %s is a placeholder blank %r; use an empty string' % (i, c, r[c]))
    if fam not in DUTY_FAMILIES: err('duty row %d: duty_family %r not in the 12 families' % (i, fam))
    if r['evidence_tier'] not in TIERS: err('duty row %d: evidence_tier %r' % (i, r['evidence_tier']))
    if r['confidence'] not in CONFS:    err('duty row %d: confidence %r' % (i, r['confidence']))
    key = (r['carb3_activity'], r['process_set_id'], r['process_id'], fam, gr)
    if key in pk: err('duty row %d: duplicate primary key %r' % (i, key))
    pk.add(key)

    if fam == 'NEUOTH':
        if car: err('duty row %d: NEUOTH is feedstock and must carry a blank carrier_id' % i)
    else:
        if not car: err('duty row %d: carrier_id is required' % i)
        elif car not in CARRIER: err('duty row %d: carrier_id %r not in carrier.csv' % (i, car))
    if fam == 'HRS': err('duty row %d: HRS is the steel hot-rolling chemistry node and is out of this lane' % i)
    if fam == 'MOT' and car != 'motive_power': err('duty row %d: MOT must bind motive_power, found %r' % (i, car))
    if fam == 'REF' and car not in ('cooling_lt0', 'cooling_0_15', 'cooling_gt15'):
        err('duty row %d: REF must bind a cooling band (note 22 Task 3), found %r' % (i, car))
    if fam in HEAT_FAMILIES and car and not car.startswith('heat_'):
        err('duty row %d: %s must bind a heat_* band, found %r' % (i, fam, car))

    # (c) gradeable carriers must carry a matching grade_rank
    c = CARRIER.get(car)
    if c and c['is_gradeable'] == 'TRUE':
        if not gr: err('duty row %d: grade_rank is non-nullable on a gradeable carrier (%s)' % (i, car))
        elif gr != c['grade_rank']:
            err('duty row %d: grade_rank %r does not match carrier.csv rank %r for %s' % (i, gr, c['grade_rank'], car))
    elif c and gr:
        err('duty row %d: grade_rank set on non-gradeable carrier %s' % (i, car))

    try: s = float(r['duty_share'])
    except ValueError: err('duty row %d: duty_share %r is not a number' % (i, r['duty_share'])); s = None
    if s is not None and not (0.0 <= s <= 1.0):
        err('duty row %d: duty_share %r outside [0,1]' % (i, s))
    for lo_hi, cmp_ok in (('share_low', lambda a, b: a <= b), ('share_high', lambda a, b: a >= b)):
        if r[lo_hi]:
            try: v = float(r[lo_hi])
            except ValueError: err('duty row %d: %s %r is not a number' % (i, lo_hi, r[lo_hi])); continue
            if s is not None and not cmp_ok(v, s):
                err('duty row %d: %s %r is on the wrong side of duty_share %r' % (i, lo_hi, v, s))

    if not r['provenance'].strip(): err('duty row %d: provenance is required' % i)
    ids = re.findall(r'\[([A-Za-z0-9_]{1,40})\]', r['provenance'])
    if not ids and r['evidence_tier'] != 'fallback':
        err('duty row %d: no [REF_ID] in provenance on a non-fallback row' % i)
    for rid in ids:
        if rid not in refs: err('duty row %d: [%s] does not resolve to references.csv or references_%s.csv' % (i, rid, LANE))

# ---- (b) shares sum to one ------------------------------------------------
for k, rows in sorted(seen.items()):
    tot = sum(float(r['duty_share']) for _i, r in rows)
    if abs(tot - 1.0) > 0.015:
        err('shares: %r sums to %.4f, outside 1.00 +/- 0.015' % (k, tot))

# ---- crosswalk ------------------------------------------------------------
for i, r in enumerate(xw, 2):
    code, kind = r['comit_process_code'], r['match_kind']
    if kind not in MATCH_KINDS: err('crosswalk row %d: match_kind %r' % (i, kind))
    if code:
        if code in SECTOR_ROOTS:
            err('crosswalk row %d: %s is a sector-root demand commodity, never a process' % (i, code))
        elif code not in CODES:
            err('crosswalk row %d: %r is not one of the 94 COMIT process codes' % (i, code))
        if kind == 'none': err('crosswalk row %d: match_kind=none must carry a blank code' % i)
    elif kind != 'none':
        err('crosswalk row %d: blank code requires match_kind=none' % i)
    if not r['notes'].strip(): err('crosswalk row %d: notes is required' % i)

# ---- report ---------------------------------------------------------------
print('lane %s: %d register rows, %d duty rows, %d crosswalk rows, %d references (%d new)'
      % (LANE, len(mine), len(duty), len(xw), len(refs),
         sum(1 for _ in csv.DictReader(open(os.path.join(HERE,'references_%s.csv'%LANE))))))
for w in warnings: print('WARN  ' + w)
for e in errors:   print('FAIL  ' + e)
print('%d error(s), %d warning(s)' % (len(errors), len(warnings)))
sys.exit(1 if errors else 0)
