"""
test_shift.py — Test shiftCharCodes implementation explicitly.
"""
from datetime import datetime, timezone
from alea import AleaRNG
from gacha import POOL_LEGENDARIOS_BASE, SPECIES_NAMES, EGG_SEED
import math

def shift_char_codes(s: str, shift_count: int) -> str:
    if not shift_count:
        shift_count = 0
    new_str = ""
    for char in s:
        new_str += chr(ord(char) + shift_count)
    return new_str

NAME_TO_ID = {v: k for k, v in SPECIES_NAMES.items()}
NAME_TO_ID["Ho-Oh"] = 250

REFERENCE = {
    1:  "Zygarde",    2:  "Terapagos",  3:  "Zamazenta",  4:  "Giratina",
    5:  "Lugia",      6:  "Zekrom",     7:  "Cosmog",      8:  "Zacian",
    9:  "Koraidon",   10: "Groudon",    11: "Reshiram",    12: "Yveltal",
    13: "Kyogre",     14: "Dialga",     15: "Arceus",      16: "Miraidon",
    17: "Cosmog",     18: "Giratina",   19: "Zygarde",     20: "Yveltal",
    21: "Kyurem",     22: "Necrozma",   23: "Ho-Oh",       24: "Regigigas",
    25: "Rayquaza",   26: "Palkia",     27: "Zamazenta",   28: "Groudon",
    29: "Terapagos",  30: "Reshiram",
}

print("Testing shiftCharCodes vs Reference for March 2026...")
print(f"{'Day':<4} {'Got':<15} {'Expected':<15} {'OK'}")
print("-" * 40)

correct = 0
for day in range(1, 31):
    fecha = datetime(2026, 3, day, tzinfo=timezone.utc)
    day_ts_ms = int(fecha.timestamp() * 1000)
    days = math.floor(day_ts_ms / 86_400_000)
    pool_size = len(POOL_LEGENDARIOS_BASE)
    offset = math.floor(days / pool_size)
    index = days % pool_size

    # The magic fix!
    seed_str = shift_char_codes(str(EGG_SEED), offset)
    
    rng = AleaRNG([seed_str])
    pool = rng.shuffle(POOL_LEGENDARIOS_BASE.copy())
    species_id = pool[index]

    got = SPECIES_NAMES.get(species_id, f"#{species_id}")
    expected = REFERENCE.get(day, "?")
    ok = "✓" if got.lower() == expected.lower() else "✗"
    if ok == "✓":
        correct += 1

    print(f"{day:<4} {got:<15} {expected:<15} {ok}")

print()
print(f"Score: {correct}/30 correct")
