"""
brute_force_seeds.py — Test seed construction strategies against March 2026 reference.
"""
from datetime import datetime, timezone
from alea import AleaRNG
from gacha import POOL_LEGENDARIOS_BASE, SPECIES_NAMES, EGG_SEED
import math

NAME_TO_ID = {v: k for k, v in SPECIES_NAMES.items()}
NAME_TO_ID["Ho-Oh"] = 250

EXPECTED_IDX = {
    820: {
        13: NAME_TO_ID["Zygarde"],    14: NAME_TO_ID["Terapagos"],
        15: NAME_TO_ID["Zamazenta"],  16: NAME_TO_ID["Giratina"],
        17: NAME_TO_ID["Lugia"],      18: NAME_TO_ID["Zekrom"],
        19: NAME_TO_ID["Cosmog"],     20: NAME_TO_ID["Zacian"],
        21: NAME_TO_ID["Koraidon"],   22: NAME_TO_ID["Groudon"],
        23: NAME_TO_ID["Reshiram"],   24: NAME_TO_ID["Yveltal"],
    },
    821: {
        0:  NAME_TO_ID["Kyogre"],     1:  NAME_TO_ID["Dialga"],
        2:  NAME_TO_ID["Arceus"],     3:  NAME_TO_ID["Miraidon"],
        4:  NAME_TO_ID["Cosmog"],     5:  NAME_TO_ID["Giratina"],
        6:  NAME_TO_ID["Zygarde"],    7:  NAME_TO_ID["Yveltal"],
        8:  NAME_TO_ID["Kyurem"],     9:  NAME_TO_ID["Necrozma"],
        10: 250,                      11: NAME_TO_ID["Regigigas"],
        12: NAME_TO_ID["Rayquaza"],   13: NAME_TO_ID["Palkia"],
        14: NAME_TO_ID["Zamazenta"],  15: NAME_TO_ID["Groudon"],
        16: NAME_TO_ID["Terapagos"],  17: NAME_TO_ID["Reshiram"],
    },
}

EGG_STR = str(EGG_SEED)
TOTAL = sum(len(v) for v in EXPECTED_IDX.values())

def score_seeds(s820, s821):
    rng820 = AleaRNG(s820)
    pool820 = rng820.shuffle(POOL_LEGENDARIOS_BASE.copy())
    rng821 = AleaRNG(s821)
    pool821 = rng821.shuffle(POOL_LEGENDARIOS_BASE.copy())
    s = 0
    for idx, eid in EXPECTED_IDX[820].items():
        if pool820[idx] == eid:
            s += 1
    for idx, eid in EXPECTED_IDX[821].items():
        if pool821[idx] == eid:
            s += 1
    return s, pool820, pool821

# Day numbers for march 1 and march 13
day1 = math.floor(int(datetime(2026,3,1,tzinfo=timezone.utc).timestamp() * 1000) / 86400000)
day13 = math.floor(int(datetime(2026,3,13,tzinfo=timezone.utc).timestamp() * 1000) / 86400000)

strategies = [
    ("concat EGG+OFF",         [EGG_STR+str(820)],       [EGG_STR+str(821)]),
    ("concat OFF+EGG",         [str(820)+EGG_STR],        [str(821)+EGG_STR]),
    ("two seeds [EGG,OFF]",    [EGG_STR, str(820)],       [EGG_STR, str(821)]),
    ("two seeds [OFF,EGG]",    [str(820), EGG_STR],       [str(821), EGG_STR]),
    ("only EGG",               [EGG_STR],                 [EGG_STR]),
    ("only OFF",               [str(820)],                [str(821)]),
    ("EGG+OFF (add)",          [str(EGG_SEED+820)],       [str(EGG_SEED+821)]),
    ("EGG^OFF (xor)",          [str(EGG_SEED^820)],       [str(EGG_SEED^821)]),
    ("day number str",         [str(day1)],               [str(day13)]),
    ("EGG str, OFF hex",       [EGG_STR, hex(820)],       [EGG_STR, hex(821)]),
    ("EGG hex",                [hex(EGG_SEED)],           [hex(EGG_SEED)]),
    ("EGG hex + OFF str",      [hex(EGG_SEED)+str(820)],  [hex(EGG_SEED)+str(821)]),
]

results = []
for desc, s820, s821 in strategies:
    score, p820, p821 = score_seeds(s820, s821)
    results.append((score, desc))

results.sort(reverse=True)
print(f"{'Score':>8}/{TOTAL}  Strategy")
print("-"*50)
for score, desc in results:
    bar = "#" * score
    print(f"  {score:>3}/{TOTAL}  {desc}")

best_score = results[0][0]
best_desc = results[0][1]
print(f"\nBest: {best_score}/{TOTAL} — {best_desc}")
