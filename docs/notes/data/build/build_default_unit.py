#!/usr/bin/env python3
"""Lane default_unit (T18): build docs/notes/data/activity_default_unit.csv."""
import csv, collections, os

B = '/Users/alexandrecanet/Documents/01_Code/comit/docs/notes/data/'
OUT = B + 'activity_default_unit.csv'

dp  = list(csv.DictReader(open(B+'activity_process_duty_profile.csv')))
el  = list(csv.DictReader(open(B+'unit_eligibility.csv')))
un  = {u['unit_id']: u for u in csv.DictReader(open(B+'unit.csv'))}
ep  = list(csv.DictReader(open(B+'activity_process_energy_profile.csv')))
xw  = {r['carb3_activity']: r['comit_sector'] for r in csv.DictReader(open(B+'carb3_comit_crosswalk.csv'))}

elig = collections.defaultdict(set)
for r in el:
    if r['process_id']:
        elig[(r['carb3_activity'], r['process_id'])].add(r['unit_id'])

vec = collections.defaultdict(dict)
for r in ep:
    vec[(r['carb3_activity'], r['process_set_id'], r['process_id'])][r['vector']] = float(r['energy_share'])

def gi(s):
    try: return int(s)
    except: return None

# ---------------------------------------------------------------- DUKES / ECUK
# DUKES 7.4.A "Fuel used to generate heat", GWh, 2024 (read from DUKES_7.4.xlsx)
DUKES_HEAT_FUEL_GWH_2024 = {
    'Chemicals': 7358.3, 'Food, beverages and tobacco': 5156.2,
    'Paper, printing, textiles and other industries': 4840.0,
    'Mineral products': 288.7, 'Mechanical engineering': 62.4, 'Vehicles': 71.7,
    'Iron, steel and non-ferrous metals': 839.9,
    'Other industries': 375.2 + 1325.1 + 780.2 + 64.5,
    'Coal extraction and oil refining': 15757.6,
}
# ECUK 2025 Table U4, 2024, ktoe: low-temperature process total + drying/separation total
ECUK_LOWGRADE_KTOE_2024 = {
    'Chemicals': 591.6 + 325.3, 'Food, beverages and tobacco': 1692.8 + 193.6,
    'Paper, printing, textiles and other industries': (246.8+392.0) + (163.5+45.9),
    'Mineral products': 102.5 + 96.8, 'Mechanical engineering': 532.7 + 0.0,
    'Vehicles': 239.9 + 0.0, 'Iron, steel and non-ferrous metals': 0.0 + 0.0,
    'Other industries': 537.1 + 290.8,
}
KTOE_GWH = 11.63   # DUKES 2025 Annex A conversion: 1 ktoe = 11.63 GWh

CHP_SHARE, CHP_CALC = {}, {}
for k, num in DUKES_HEAT_FUEL_GWH_2024.items():
    den = ECUK_LOWGRADE_KTOE_2024.get(k)
    if den:
        CHP_SHARE[k] = round(num / (den * KTOE_GWH), 3)
        CHP_CALC[k] = '%.1f GWh / (%.1f ktoe x %.2f GWh/ktoe = %.1f GWh) = %.3f' % (
            num, den, KTOE_GWH, den*KTOE_GWH, CHP_SHARE[k])

# COMIT sector (carb3_comit_crosswalk.csv) -> DUKES 7.4 sector
COMIT_TO_DUKES = {
    'Chemicals': 'Chemicals', 'Food & drink': 'Food, beverages and tobacco',
    'Paper': 'Paper, printing, textiles and other industries',
    'Textiles': 'Paper, printing, textiles and other industries',
    'Cement': 'Mineral products', 'Lime': 'Mineral products',
    'Ceramics': 'Mineral products', 'Glass': 'Mineral products',
    'Iron & steel': 'Iron, steel and non-ferrous metals',
    'Non-ferrous metals': 'Iron, steel and non-ferrous metals',
    'Iron & steel / Non-ferrous metals': 'Iron, steel and non-ferrous metals',
    'Mechanical engineering': 'Mechanical engineering', 'Vehicles': 'Vehicles',
    'Refineries': 'Coal extraction and oil refining',
    'Other': 'Other industries',
    'Electrical engineering': 'Other industries',
    # COMIT 'Construction' is deliberately absent: DUKES Table 7.4.A publishes no
    # construction row (the workbook's DUKES Sectors sheet defines construction as SIC
    # 41-43 but 7.4.A does not carry it), so no CHP share can be traced to a statistic
    # for a concrete or asphalt works. Mapping it onto 'Other industries' would import
    # the sewerage and waste-management CHP fleet, which is not the same plant.
}
CHP_FLOOR = 0.02      # below this the sector's CHP is not material; no CHP row

REF_DUKES = '[DUKES_7_4]'
REF_ECUK  = '[ECUK_2025_U4]'
REF_EP    = '[CARB3_EP]'
REF_WE_F  = '[CARB3_WE_FOOD]'
REF_WE_C  = '[CARB3_WE_CEMENT]'

# -------------------------------------------------------------- unit selection
VEC_FUEL = {'gas':'natural_gas','oil':'light_fuel_oil','coal':'coal',
            'biomass':'solid_biomass','other':'waste_derived_fuel',
            'electricity':'electricity'}
# novel / future routes: candidates, not base-year incumbents
NOVEL = {'kiln_fluidbed_wdf','kiln_calcium_looping_coal','lime_kiln_fluidbed_wdf',
         'lime_kiln_calcium_looping_coal','grinder_mixer_clinker_sub_elec',
         'cement_lowcarbon_elec','lime_grinder_sub_elec','lime_lowcarbon_elec',
         'steam_cracker_elec','steam_cracker_hydrogen','hisarna_coal',
         'tgr_blast_furnace_coke','refinery_flexible_mix_gas'}
CHP_UNITS = {u for u in un if u.startswith('chp_') and un[u]['unit_class'] == 'generator'}
EXCLUDE_CLASS = {'abatement','storage','hybrid'}
# Not base-year plant. A heat pump, an electrolyser, a CCS reformer or anything burning
# hydrogen or grid biomethane is what the model DECIDES to build; asserting one as the
# incumbent would let A4 back-solve a baseline that does not exist in 2024.
FUTURE_CARRIERS = {'hydrogen', 'biomethane'}
FUTURE_UNITS = ({u for u in un if u.startswith(('heat_pump_', 'heat_exchanger_', 'electrolyser_',
                                                'dryer_heat_pump'))}
                | {'smr_gas_ccs', 'atr_gas_ccs', 'gasifier_biomass_ccs', 'gasifier_coal_ccs',
                   'chiller_electric_hfo', 'pv_rooftop', 'pv_ground_mount', 'solar_thermal_flat',
                   'anaerobic_digester'}
                | {u for u in un if un[u]['fuel_carrier_id'] in FUTURE_CARRIERS})

def candidates(act, proc, grade):
    """Eligible units that C10 admits, minus abatement/storage/hybrid and novel routes."""
    out = set()
    for u in elig.get((act, proc), ()):
        m = un[u]
        if m['unit_class'] in EXCLUDE_CLASS: continue
        if u in NOVEL or u in FUTURE_UNITS: continue
        go = gi(m['grade_out'])
        if grade is not None and go is not None and go < grade: continue
        out.add(u)
    return out

import json
ECUK_U4 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      'ecuk_u4_2024.json')))
# COMIT sector -> ECUK Table U4 row label
COMIT_TO_ECUK = {
    'Chemicals':'Chemicals', 'Food & drink':'Food, beverages etc',
    'Paper':'Paper, printing etc', 'Textiles':'Textiles, leather etc',
    'Cement':'Mineral products', 'Lime':'Mineral products', 'Ceramics':'Mineral products',
    'Glass':'Mineral products', 'Iron & steel':'Non-ferrous metals',
    'Non-ferrous metals':'Non-ferrous metals',
    'Iron & steel / Non-ferrous metals':'Non-ferrous metals',
    'Mechanical engineering':'Mechanical engineering etc',
    'Electrical engineering':'Electrical engineering etc', 'Vehicles':'Vehicles',
    'Refineries':'Other industries', 'Other':'Other industries',
    'Construction':'Other industries',
}
HEAT_FAMS = {'LTH','STM','SPC','HTH','DRY','PHEAT'}
FAM_TO_ENDUSE = {'HTH':'HTH','PHEAT':'HTH','LTH':'LTH','STM':'LTH','DRY':'DRY',
                 'SPC':'SPC','MOT':'MOT','REF':'REF','OTH':'OTH'}
# ECUK resolves four fuels; a vector it does not separate rides on the solid-fuel column
VEC_TO_ECUK_FUEL = {'gas':'gas','oil':'oil','coal':'coal','biomass':'coal',
                    'other':'coal','electricity':'electricity'}

def fuel_mix(key, act, fam, mode):
    """Which fuel vectors the process uses (energy profile) x how that sector's duty
    splits between fuels (ECUK Table U4, 2024). The energy profile's energy_share sums
    to 1.00 down PROCESSES PER VECTOR, so its values are not comparable across vectors
    and must never be renormalised into a fuel split; ECUK supplies the proportions."""
    present = [k for k, s in vec.get(key, {}).items() if s > 0]
    if mode == 'only':
        return ({'electricity': 1.0}, 'electricity-only duty', False)
    fuels = [k for k in present if k != 'electricity'] or [k for k in present]
    if not fuels: return ({}, 'no vector', False)
    if len(fuels) == 1: return ({fuels[0]: 1.0}, 'single vector %s' % fuels[0], True)
    row = ECUK_U4.get(COMIT_TO_ECUK.get(xw.get(act, ''), ''), {})
    split = row.get(FAM_TO_ENDUSE.get(fam, 'OTH')) or row.get('OTH') or {}
    w = {}
    for k in fuels:
        w[k] = w.get(k, 0.0) + split.get(VEC_TO_ECUK_FUEL.get(k, ''), 0.0)
    solids = [k for k in fuels if VEC_TO_ECUK_FUEL.get(k) == 'coal']
    if len(solids) > 1:                       # ECUK does not separate coal, biomass and WDF
        share = w[solids[0]] / len(solids)
        for k in solids: w[k] = share
    tot = sum(w.values())
    if tot <= 0: return ({fuels[0]: 1.0}, 'ECUK gives this sector no fuel split', False)
    return ({k: v/tot for k, v in w.items() if v > 0},
            'ECUK Table U4 2024 %s / %s' % (COMIT_TO_ECUK.get(xw.get(act, ''), '?'),
                                            FAM_TO_ENDUSE.get(fam, 'OTH')),
            len(solids) <= 1)

# The one process whose fuel split is published: the cement kiln, worked example 1.12
WE_CEMENT_KILN = {'kiln_dry_coal': 0.53, 'kiln_dry_wdf': 0.39, 'kiln_dry_gas': 0.08}

rows, notes = [], []
def R(d, unit, share, basis, tier, prov, conf):
    rows.append(dict(carb3_activity=d['carb3_activity'], process_set_id=d['process_set_id'],
                     process_id=d['process_id'], duty_family=d['duty_family'],
                     unit_id=unit, default_share='%.5f' % share, sizing_basis=basis,
                     evidence_tier=tier, provenance=prov, confidence=conf))

# preference order of unit duty_family per duty family, best first; OTH is the
# last resort because generic_process_* has no grade_out and so passes C10 vacuously
FAM_PREF = {'LTH':['LTH','STM','SPC','OTH'], 'SPC':['SPC','LTH','STM','OTH'],
            'STM':['STM','LTH','OTH'], 'HTH':['HTH','PHEAT','DRY','OTH'],
            'DRY':['DRY','HTH','STM','LTH','OTH'], 'MOT':['MOT','HRS','OTH'],
            'REF':['REF','MOT','OTH'], 'OTH':['OTH','MOT'],
            'PHEAT':['PHEAT','HTH','DRY','STM','LTH','OTH']}
# preferred fuel when the energy profile has no row for the process
NO_VEC_FUEL = {'MOT':'electricity','REF':'electricity','OTH':'electricity'}

def pool_for(act, proc, fam, g):
    """Four-rung ladder. Returns (pool, unit-family, flag)."""
    raw = {u for u in elig.get((act, proc), ())
           if un[u]['unit_class'] not in EXCLUDE_CLASS and u not in NOVEL
           and u not in FUTURE_UNITS}
    if not raw:                       # nothing conventional is offered here at all
        raw = {u for u in elig.get((act, proc), ())
               if un[u]['unit_class'] not in EXCLUDE_CLASS and u not in NOVEL}
    ok = {u for u in raw if gi(un[u]['grade_out']) is None or g is None
          or gi(un[u]['grade_out']) >= g}
    # designated unit for this process (rolling mill, refinery heater) wins outright
    des = {u for u in ok if un[u]['process_id'] == proc}
    if des: return des, un[sorted(des)[0]]['duty_family'], ''
    for f in FAM_PREF.get(fam, [fam]):                       # (i) eligible + C10 + family
        p = {u for u in ok if un[u]['duty_family'] == f}
        if p: return p, f, ('' if f == fam else 'FAMILY_FALLBACK')
    des = {u for u in raw if un[u]['process_id'] == proc}
    if des: return des, un[sorted(des)[0]]['duty_family'], 'C10_CONFLICT'
    for f in FAM_PREF.get(fam, [fam]):                       # (ii) eligible, C10 broken, family
        p = {u for u in raw if un[u]['duty_family'] == f}
        if p: return p, f, 'C10_CONFLICT'
    if ok: return ok, None, 'FAMILY_FALLBACK'                # (iii) eligible + C10, any family
    if raw: return raw, None, 'C10_CONFLICT'
    for f in FAM_PREF.get(fam, [fam]):                       # (iv) not eligible at all
        p = {u for u in un if un[u]['duty_family'] == f and un[u]['unit_class'] not in EXCLUDE_CLASS
             and u not in NOVEL and u not in FUTURE_UNITS and not un[u]['process_id']
             and (gi(un[u]['grade_out']) is None or g is None or gi(un[u]['grade_out']) >= g)}
        if p: return p, f, 'NO_ELIGIBILITY'
    for f in FAM_PREF.get(fam, [fam]):
        p = {u for u in un if un[u]['duty_family'] == f and un[u]['unit_class'] not in EXCLUDE_CLASS
             and u not in NOVEL and u not in FUTURE_UNITS and not un[u]['process_id']}
        if p: return p, f, 'NO_ELIGIBILITY+C10_CONFLICT'
    return set(), None, 'NO_UNIT'

FLAG_TEXT = {
 'FAMILY_FALLBACK':
   ' FAMILY FALLBACK: no unit of duty family %(fam)s is both eligible for (%(act)s, %(proc)s) '
   'and admitted by C10 (the heat grade cascade) at grade_rank %(g)s, so the nearest family '
   'that is, %(pf)s, is used. The food and drink worked example does the same thing, putting '
   'boiler_lt_gas (an LTH unit) on the SPC duty.',
 'C10_CONFLICT':
   ' C10 CONFLICT: this unit\'s grade_out is %(go)s and the duty\'s grade_rank is %(g)s, so C10 '
   '(the heat grade cascade) would drop it from U_q at load and the optimiser could not build '
   'it. NO unit in unit.csv satisfies both eligibility and C10 for this duty. Asserted because '
   'spec section 3.16 forbids a blank row (every duty is served today); recorded so the '
   'coordinator can fix one side. See DONE_default_unit.md.',
 'NO_ELIGIBILITY':
   ' NO ELIGIBILITY ROW: unit_eligibility.csv has no entry for (%(act)s, %(proc)s) that this '
   'duty could use, so spec section 3.16\'s eligibility precondition is not met and a strict '
   'validator will reject this row. The unit named is the correct incumbent on the physics; '
   'the gap is in unit_eligibility.csv, not here. See DONE_default_unit.md.',
 'NO_ELIGIBILITY+C10_CONFLICT':
   ' NO ELIGIBILITY ROW, and C10 CONFLICT: unit_eligibility.csv has no usable entry for '
   '(%(act)s, %(proc)s), and no unit in unit.csv reaches grade_rank %(g)s for this duty '
   '(the library\'s highest grade_out is 5). Both gaps are recorded in DONE_default_unit.md.',
}

for d in dp:
    act, ps, proc, fam = d['carb3_activity'], d['process_set_id'], d['process_id'], d['duty_family']
    g = gi(d['grade_rank']); key = (act, ps, proc)
    cand = candidates(act, proc, g)
    chem = sorted(u for u in cand if un[u]['spine'] == 'chemistry' and un[u]['process_id'] == proc)
    dukes = COMIT_TO_DUKES.get(xw.get(act, ''), '')
    share_chp = CHP_SHARE.get(dukes, 0.0)

    # ---- 1. chemistry-spine process units win (the cement worked example's shape)
    if chem:
        if act == 'Cement Works' and proc == 'kiln_pyroprocessing' \
           and set(WE_CEMENT_KILN) <= set(chem):
            for u, sh in sorted(WE_CEMENT_KILN.items()):
                R(d, u, sh, 'throughput', 'derived',
                  '%s section 1.12, verbatim: the activity_default_unit table for Cement Works '
                  'gives kiln_pyroprocessing kiln_dry_coal 0.53, kiln_dry_wdf 0.39 and '
                  'kiln_dry_gas 0.08 at sizing_basis throughput, evidence_tier derived. This is '
                  'the ONLY published per-unit fuel split for a chemistry process in the '
                  'repository, and it is used in preference to any split this lane could '
                  'construct. %s gives this process six vectors each at or near 1.00, which '
                  'says the kiln is the sole consumer of each - it is not a fuel split.'
                  % (REF_WE_C, REF_EP), 'medium')
            continue
        mix, basis, clean = fuel_mix(key, act, fam, 'fuel')
        byfuel = {}
        for u in chem: byfuel.setdefault(un[u]['fuel_carrier_id'], u)
        picks = {}
        for v, sh in mix.items():
            u = byfuel.get(VEC_FUEL.get(v, ''))
            if u: picks[u] = picks.get(u, 0.0) + sh
        if not picks: picks = {chem[0]: 1.0}
        tot = sum(picks.values())
        for u, sh in sorted(picks.items()):
            R(d, u, sh/tot, 'throughput', 'derived' if clean else 'assumed',
              'COMIT chemistry-spine unit for process %s, eligible at this activity in '
              'unit_eligibility.csv. Fuel vectors present from %s for (%s, %s, %s); the split '
              'between them from %s (%s). %s section 1.12 is the shape followed: a chemistry '
              'process takes its COMIT route unit at sizing_basis throughput.%s'
              % (proc, REF_EP, act, ps, proc, REF_ECUK, basis, REF_WE_C,
                 '' if clean else ' ECUK does not separate coal, biomass and waste-derived '
                 'fuel, so the solid-fuel share is divided equally between the solid vectors '
                 'this process carries. That division is not evidenced.'),
              'medium' if clean else 'low')
        continue

    # ---- 2. service units, down the four-rung ladder
    pool, pick_fam, flag = pool_for(act, proc, fam, g)
    if not pool:
        notes.append(('NO_UNIT', act, ps, proc, fam, d['grade_rank'])); continue
    if flag: notes.append((flag, act, ps, proc, fam, d['grade_rank']))

    # the residual of a CHP split must be a boiler, never another CHP, so generators
    # are kept out of the fuel->unit map that picks the incumbent
    # A CHP can never be its own residual, so the residual pool never holds a generator.
    boilers = {u for u in pool if un[u]['unit_class'] != 'generator'}
    boiler_gap = False
    if fam in ('STM', 'LTH') and not boilers:
        boilers = {u for u in candidates(act, proc, g)
                   if un[u]['duty_family'] == 'LTH' and un[u]['unit_class'] == 'converter'}
        if not boilers:                        # nothing eligible: take the library's boilers
            boilers = {u for u in un if u.startswith('boiler_lt_')
                       and u not in FUTURE_UNITS and u not in NOVEL}
            boiler_gap = True
    boilers = boilers or pool
    # the wider fallback map also keeps generators out on a duty that may take a CHP split
    wide = ({u for u in pool if un[u]['unit_class'] != 'generator'} | boilers) \
           if fam in ('STM', 'LTH') else pool
    byfuel_all = {}
    for u in sorted(wide or pool): byfuel_all.setdefault(un[u]['fuel_carrier_id'], u)
    byfuel = {}
    for u in sorted(boilers): byfuel.setdefault(un[u]['fuel_carrier_id'], u)
    have_vec = bool(vec.get(key))
    mix, basis, clean = fuel_mix(key, act, fam, 'only' if fam in ('MOT','REF') else 'fuel')
    picks, unmatched, fuel_gap = {}, 0.0, False
    if have_vec:
        for v, sh in mix.items():
            u = byfuel.get(VEC_FUEL.get(v, ''))
            if u: picks[u] = picks.get(u, 0.0) + sh
            else: unmatched += sh
        if unmatched > 0 and picks:
            tot = sum(picks.values())
            picks = {u: sh + unmatched*sh/tot for u, sh in picks.items()}
            notes.append(('NO_FUEL_VARIANT', act, ps, proc, fam, round(unmatched, 3)))
    if not picks:
        want = NO_VEC_FUEL.get(fam, 'natural_gas')
        u = (byfuel.get(want) or byfuel.get('natural_gas') or byfuel_all.get(want)
             or byfuel_all.get('natural_gas') or byfuel_all.get('petroleum_products_misc'))
        if u is None and want != 'electricity' and fam in HEAT_FAMS:
            # the process burns a fuel but nothing eligible here burns it; an electric
            # resistance heater is not the 2024 incumbent, so take the library's own
            # unit for that family and fuel and record the eligibility gap
            lib = {x for x in un if un[x]['duty_family'] == (pick_fam or fam)
                   and un[x]['fuel_carrier_id'] == want and not un[x]['process_id']
                   and x not in NOVEL and x not in FUTURE_UNITS
                   and un[x]['unit_class'] not in EXCLUDE_CLASS
                   and un[x]['unit_class'] != 'generator'}
            if not lib:
                lib = {x for x in un if un[x]['duty_family'] in HEAT_FAMS
                       and un[x]['fuel_carrier_id'] == want and not un[x]['process_id']
                       and x not in NOVEL and x not in FUTURE_UNITS
                       and un[x]['unit_class'] not in EXCLUDE_CLASS
                   and un[x]['unit_class'] != 'generator'
                       and (gi(un[x]['grade_out']) is None or g is None
                            or gi(un[x]['grade_out']) >= g)}
            if lib:
                u = sorted(lib)[0]; fuel_gap = True
        u = u or byfuel.get('electricity') or byfuel_all.get('electricity') or sorted(pool)[0]
        picks = {u: 1.0}
        if not have_vec: notes.append(('NO_VECTOR', act, ps, proc, fam, ''))
    tot = sum(picks.values())
    picks = {u: sh/tot for u, sh in picks.items()}

    def deco(base, u, tier, conf):
        if fuel_gap:
            base += (' NO ELIGIBILITY ROW for the incumbent fuel: unit_eligibility.csv offers no '
                     'unit at (%s, %s) that burns the fuel this process actually uses, only '
                     'electric ones. An electric resistance heater is not a 2024 incumbent, so '
                     'the library\'s own unit for that family and fuel is named instead. The gap '
                     'is in unit_eligibility.csv. See DONE_default_unit.md.' % (act, proc))
            tier, conf = 'assumed', 'low'
        if flag:
            base += FLAG_TEXT[flag] % dict(fam=fam, act=act, proc=proc,
                                           g=d['grade_rank'] or 'none', pf=pick_fam or 'any',
                                           go=un[u]['grade_out'] or 'blank')
            tier, conf = 'assumed', 'low'
        if not have_vec:
            base += (' The energy profile carries NO row for (%s, %s, %s) - one of the silent '
                     'coverage gaps section 3.3.1 names - so the incumbent fuel is not evidenced '
                     'and the default carrier for this duty family is used.' % (act, ps, proc))
            tier, conf = 'assumed', 'low'
        return base, tier, conf

    # ---- 3. CHP on the steam and low-temperature-heat duties
    chps = sorted(u for u in cand if u in CHP_UNITS)
    if fam in ('STM','LTH') and share_chp >= CHP_FLOOR and chps and not flag:
        dom = max(mix, key=mix.get) if mix else 'gas'
        want = VEC_FUEL.get(dom, 'natural_gas')
        chp = next((u for u in chps if un[u]['fuel_carrier_id'] == want), None) \
              or next((u for u in chps if un[u]['fuel_carrier_id'] == 'natural_gas'), chps[0])
        p, t, c = deco(
          '%s "Fuel used to generate heat" by sector, 2024, divided by %s Table U4, 2024, '
          '"Low temperature process - total" plus "Drying / separation - total" for the same '
          'sector, both at 1 ktoe = %s GWh. DUKES sector "%s": %s. The activity maps to that '
          'sector through carb3_comit_crosswalk.csv (COMIT sector "%s"). This is a FUEL-basis '
          'ratio, not a delivered-heat ratio: a CHP delivers less heat per unit of fuel than a '
          'boiler, so the share of the DELIVERED duty is lower than this. DUKES publishes no '
          'per-duty or per-site share, which is why the denominator is the sector\'s whole '
          'low-grade heat end use.'
          % (REF_DUKES, REF_ECUK, KTOE_GWH, dukes, CHP_CALC[dukes], xw.get(act, '')),
          chp, 'sector_statistic', 'medium')
        R(d, chp, share_chp, 'duty_annual', t, p, c)
        resid = 1.0 - share_chp
        for u, sh in sorted(picks.items()):
            p, t, c = deco(
              'Residual of the %s/%s CHP share on this duty (1 - %.3f). Boilers serve what the '
              'CHP does not. Fuel vectors present from %s for (%s, %s, %s); the split between '
              'them from %s (%s).%s'
              % (REF_DUKES, REF_ECUK, share_chp, REF_EP, act, ps, proc, REF_ECUK, basis,
                 '' if not boiler_gap else
                 ' NO ELIGIBILITY ROW: unit_eligibility.csv offers no boiler at all for (%s, %s)'
                 ' - only CHP units - so a CHP would have to be its own residual. The '
                 'boiler named is the library default; the gap is in unit_eligibility.csv. '
                 'See DONE_default_unit.md.' % (act, proc)),
              u, 'derived' if not boiler_gap else 'assumed',
              'medium' if not boiler_gap else 'low')
            R(d, u, resid*sh, 'duty_annual', t, p, c)
        continue

    # ---- 4. plain incumbent
    single = len(picks) == 1
    for u, sh in sorted(picks.items()):
        if fam in ('MOT','REF') and single and pick_fam == fam:
            base = ('Only plausible incumbent: %s is the sole %s-family unit in unit.csv and is '
                    'eligible for (%s, %s) in unit_eligibility.csv. %s section 1.12 asserts the '
                    'same unit on the same duty family at evidence_tier assumed.'
                    % (u, fam, act, proc, REF_WE_F))
            tier, conf = 'assumed', 'medium'
        else:
            base = ('Incumbent fuel: the vectors %s carries for (%s, %s, %s) say which fuels '
                    'this process uses; %s gives the split between them (%s), yielding %s. The '
                    'unit is the %s-family variant burning that carrier. The energy profile\'s '
                    'energy_share sums to 1.00 down PROCESSES PER VECTOR, so its values are not '
                    'comparable across vectors and are not used as proportions.'
                    % (REF_EP, act, ps, proc, REF_ECUK, basis,
                       ', '.join('%s %.2f' % (k, v) for k, v in sorted(mix.items())) or 'none',
                       pick_fam or un[u]['duty_family'] or 'ungraded'))
            tier, conf = ('derived', 'medium') if clean else ('assumed', 'low')
        p, t, c = deco(base, u, tier, conf)
        R(d, u, sh, 'duty_annual', t, p, c)

COLS = ['carb3_activity','process_set_id','process_id','duty_family','unit_id',
        'default_share','sizing_basis','evidence_tier','provenance','confidence']
with open(OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(rows)

print('rows: %d over %d duties' % (len(rows), len(dp)))
print('\nCHP shares derived:')
for k in sorted(CHP_CALC): print('  %-46s %s' % (k, CHP_CALC[k]))
print('\nnotes:')
for n in collections.Counter(x[0] for x in notes).items(): print('  ', n)
for n in notes:
    if n[0] == 'NO_UNIT': print('   NO_UNIT', n[1:])
