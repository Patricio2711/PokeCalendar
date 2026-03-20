"""
debug_march.py — Compare our output vs. reference for March 2026
"""
from datetime import datetime, timezone
from gacha import obtener_legendario_del_dia, SPECIES_NAMES, POOL_LEGENDARIOS_BASE
import math

# Reference from user's screenshot (March 2026)
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

print(f"Pool size: {len(POOL_LEGENDARIOS_BASE)}")
print()
print(f"{'Day':<4} {'Got':<15} {'Expected':<15} {'ID':<6} {'Offset':<8} {'Index':<6} {'OK'}")
print("-" * 65)

for day in range(1, 31):
    fecha = datetime(2026, 3, day, tzinfo=timezone.utc)
    day_ts_ms = int(fecha.timestamp() * 1000)
    days = math.floor(day_ts_ms / 86_400_000)
    pool_size = len(POOL_LEGENDARIOS_BASE)
    offset = math.floor(days / pool_size)
    index = days % pool_size

    species_id = obtener_legendario_del_dia(fecha)
    got = SPECIES_NAMES.get(species_id, f"#{species_id}")
    expected = REFERENCE.get(day, "?")
    ok = "✓" if got.lower() == expected.lower() else "✗"

    print(f"{day:<4} {got:<15} {expected:<15} {species_id:<6} {offset:<8} {index:<6} {ok}")

print()
correct = sum(1 for d in range(1, 31)
              if SPECIES_NAMES.get(obtener_legendario_del_dia(datetime(2026,3,d,tzinfo=timezone.utc)), "").lower() == REFERENCE.get(d,"").lower())
print(f"Score: {correct}/30 correct")
