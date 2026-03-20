"""
debug_shuffle.py — Reverse-engineer what the correct shuffled pool should be,
then test different AleaRNG seeding strategies to find which one matches.
"""
from datetime import datetime, timezone
from alea import AleaRNG
from gacha import POOL_LEGENDARIOS_BASE, SPECIES_NAMES, EGG_SEED
import math

# From reference, reconstruct the expected shuffled arrays for offset 820 and 821

# offset 820: responsible for March days 1-12 (indices 13-24)
EXPECTED_820 = {
    # index: expected_species_name
    13: "Zygarde",
    14: "Terapagos",
    15: "Zamazenta",
    16: "Giratina",
    17: "Lugia",
    18: "Zekrom",
    19: "Cosmog",
    20: "Zacian",
    21: "Koraidon",
    22: "Groudon",
    23: "Reshiram",
    24: "Yveltal",
}

# offset 821: responsible for March days 13-30 (indices 0-17)
EXPECTED_821 = {
    0:  "Kyogre",
    1:  "Dialga",
    2:  "Arceus",
    3:  "Miraidon",
    4:  "Cosmog",
    5:  "Giratina",
    6:  "Zygarde",
    7:  "Yveltal",
    8:  "Kyurem",
    9:  "Necrozma",
    10: "Ho-Oh",
    11: "Regigigas",
    12: "Rayquaza",
    13: "Palkia",
    14: "Zamazenta",
    15: "Groudon",
    16: "Terapagos",
    17: "Reshiram",
}

# Build reverse map: name -> species_id
NAME_TO_ID = {v: k for k, v in SPECIES_NAMES.items()}
NAME_TO_ID["Ho-Oh"] = 250  # Fix capitalisation  

print("=== Testing seed strategies ===\n")

def test_seed(seed_str, offset_label, expected_positions):
    rng = AleaRNG([seed_str])
    pool = rng.shuffle(POOL_LEGENDARIOS_BASE.copy())
    correct = 0
    for idx, expected_name in expected_positions.items():
        got_id = pool[idx]
        got_name = SPECIES_NAMES.get(got_id, f"#{got_id}")
        exp_id = NAME_TO_ID.get(expected_name, -1)
        if got_id == exp_id:
            correct += 1
    return correct, pool

strategies = [
    # (description, seed_for_820, seed_for_821)
    ("str(EGG_SEED)+str(offset)",
     str(EGG_SEED) + str(820),
     str(EGG_SEED) + str(821)),
    
    ("str(EGG_SEED+offset) — addition not concat",
     str(EGG_SEED + 820),
     str(EGG_SEED + 821)),
    
    ("str(offset) only",
     str(820),
     str(821)),
    
    ("str(EGG_SEED)+str(offset) with leading zeros (8 digits)",
     str(EGG_SEED) + f"{820:08d}",
     str(EGG_SEED) + f"{821:08d}"),
    
    # Maybe EGG_SEED is passed separately from offset as two seeds
    ("sow([str(EGG_SEED), str(offset)]) — two seeds",
     None, None),  # handled separately below
]

for desc, s820, s821 in strategies:
    if s820 is None:
        # two-seed strategy
        rng820 = AleaRNG([str(EGG_SEED), str(820)])
        pool820 = rng820.shuffle(POOL_LEGENDARIOS_BASE.copy())
        rng821 = AleaRNG([str(EGG_SEED), str(821)])
        pool821 = rng821.shuffle(POOL_LEGENDARIOS_BASE.copy())
    else:
        _, pool820 = test_seed(s820, "820", EXPECTED_820)
        _, pool821 = test_seed(s821, "821", EXPECTED_821)
    
    # Score both offsets
    score820 = sum(1 for i, n in EXPECTED_820.items()
                   if SPECIES_NAMES.get(pool820[i]) == n or 
                   (n == "Ho-Oh" and pool820[i] == 250))
    score821 = sum(1 for i, n in EXPECTED_821.items()
                   if SPECIES_NAMES.get(pool821[i]) == n or
                   (n == "Ho-Oh" and pool821[i] == 250))
    
    print(f"Strategy: {desc}")
    print(f"  Offset 820: {score820}/{len(EXPECTED_820)} correct")
    print(f"  Offset 821: {score821}/{len(EXPECTED_821)} correct")
    print()

# Now show what our current code produces for offset 820 so we can see the pattern
print("=== Current output for offset 820 (seed='1073741824820') ===")
rng = AleaRNG(["1073741824820"])
pool = rng.shuffle(POOL_LEGENDARIOS_BASE.copy())
for i, sid in enumerate(pool):
    expected_820 = EXPECTED_820.get(i, "")
    name = SPECIES_NAMES.get(sid, f"#{sid}")
    mark = "✓" if name == expected_820 or (expected_820 == "Ho-Oh" and sid == 250) else ("  " if not expected_820 else "✗")
    exp_str = f"(expected: {expected_820})" if expected_820 else ""
    print(f"  [{i:2d}] {name:<15} {mark} {exp_str}")
