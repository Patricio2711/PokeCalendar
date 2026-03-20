"""
gacha.py — Lógica de rotación diaria de legendarios de PokéRogue
=================================================================
Porta la función `getLegendaryGachaSpeciesForTimestamp` del archivo
`egg.ts` del juego PokéRogue a Python, usando el PRNG Alea replicado
en `alea.py`.

La semilla que PokéRogue pasa a `executeWithSeedOffset` se construye
concatenando `EGG_SEED.toString()` con el `offset` del ciclo actual.
En código TypeScript esto equivale a:

    seed_str = String(EGG_SEED) + String(offset)
      →  "1073741824" + "0"  = "10737418240"  (para el primer ciclo)
      →  "1073741824" + "1"  = "10737418241"  (segundo ciclo), etc.

Luego se llama a `executeWithSeedOffset(callback, offset, seedStr)` que
internamente hace:
    Phaser.Math.RND.sow([seedStr])
    callback()
    Phaser.Math.RND.sow([estadoAnterior])   ← ignorable para cálculo

El resultado es barajar `POOL_LEGENDARIOS_BASE` con esa semilla y tomar
el elemento en la posición `index`.
"""

import math
from datetime import datetime, timezone
from alea import AleaRNG

def shift_char_codes(s: str, shift_count: int) -> str:
    """Implementa shiftCharCodes de Pokerogue (utils/common.ts).
       Desplaza cada código ASCII de los caracteres de la semilla base
       por el valor del offset."""
    if not shift_count:
        shift_count = 0
    return "".join(chr(ord(char) + shift_count) for char in s)

# ---------------------------------------------------------------------------
# CONSTANTES — provenientes de egg.ts
# ---------------------------------------------------------------------------

#: Semilla base del sistema de huevos legendarios de PokéRogue.
EGG_SEED: int = 1073741824   # 0x40000000

# ---------------------------------------------------------------------------
# POOL BASE DE LEGENDARIOS
# ---------------------------------------------------------------------------
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  PUNTO DE INYECCIÓN — POOL_LEGENDARIOS_BASE                             ║
# ║  Reemplaza los nombres de abajo con los IDs numéricos (SpeciesId) o     ║
# ║  nombres reales de las especies que `getValidLegendaryGachaSpecies()`   ║
# ║  retorna en el juego. El orden aquí debe ser IDÉNTICO al orden en que   ║
# ║  el juego los obtiene de `speciesEggTiers`, que es un objeto indexado   ║
# ║  por SpeciesId numérico en orden ascendente (sin incluir Eternatus).    ║
# ╚══════════════════════════════════════════════════════════════════════════╝
POOL_LEGENDARIOS_BASE: list[int] = [
    150,   # Mewtwo
    249,   # Lugia
    250,   # Ho-Oh
    382,   # Kyogre
    383,   # Groudon
    384,   # Rayquaza
    483,   # Dialga
    484,   # Palkia
    486,   # Regigigas
    487,   # Giratina
    493,   # Arceus
    643,   # Reshiram
    644,   # Zekrom
    646,   # Kyurem
    716,   # Xerneas
    717,   # Yveltal
    718,   # Zygarde
    789,   # Cosmog
    800,   # Necrozma
    888,   # Zacian
    889,   # Zamazenta
    898,   # Calyrex
    1007,  # Koraidon
    1008,  # Miraidon
    1024   # Terapagos

    # ╔══════════════════════════════════════════════════════════════════════╗
    # ║  PUNTO DE INYECCIÓN — POKÉRUS / DATOS EXTRA                        ║
    # ║  Si el juego añade nuevas especies legendarias en actualizaciones   ║
    # ║  futuras, agrégalas aquí manteniendo el orden por SpeciesId.        ║
    # ╚══════════════════════════════════════════════════════════════════════╝
]

# ---------------------------------------------------------------------------
# NOMBRES LOCALES — evitan depender de la red para mostrar el nombre
# ---------------------------------------------------------------------------

SPECIES_NAMES: dict[int, str] = {
    150:  "Mewtwo",
    249:  "Lugia",
    250:  "Ho-Oh",
    382:  "Kyogre",
    383:  "Groudon",
    384:  "Rayquaza",
    483:  "Dialga",
    484:  "Palkia",
    486:  "Regigigas",
    487:  "Giratina",
    493:  "Arceus",
    643:  "Reshiram",
    644:  "Zekrom",
    646:  "Kyurem",
    716:  "Xerneas",
    717:  "Yveltal",
    718:  "Zygarde",
    789:  "Cosmog",
    800:  "Necrozma",
    888:  "Zacian",
    889:  "Zamazenta",
    898:  "Calyrex",
    1007: "Koraidon",
    1008: "Miraidon",
    1024: "Terapagos",
}


def obtener_nombre_especie(species_id: int) -> str:
    """Retorna el nombre del Pokémon para un ID dado, o '#ID' si no se conoce."""
    return SPECIES_NAMES.get(species_id, f"#{species_id}")


# ---------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL — réplica de getLegendaryGachaSpeciesForTimestamp
# ---------------------------------------------------------------------------

def obtener_legendario_del_dia(fecha: datetime) -> int:
    """
    Calcula qué legendario está activo en el Gacha de huevos para una fecha
    dada, replicando exactamente `getLegendaryGachaSpeciesForTimestamp`.

    La lógica es la siguiente:
        1. Calcular el timestamp del INICIO del día UTC (medianoche).
        2. `days`   = floor(day_ts_ms / 86_400_000)
        3. `offset` = floor(days / len(pool))  ← qué ciclo de barajado
        4. `index`  = days % len(pool)          ← posición dentro del ciclo
        5. Semilla  = str(EGG_SEED) + str(offset)  ← igual que JS
        6. Barajar pool con AleaRNG(semilla) → retornar elemento en `index`

    Args:
        fecha: Un objeto datetime (puede ser naive o aware). Se usará la
               fecha en UTC. Si es naive se asume UTC directamente.

    Returns:
        El nombre (o ID) del Pokémon legendario del día según el Gacha.

    Raises:
        ValueError: Si POOL_LEGENDARIOS_BASE está vacía.
    """
    if not POOL_LEGENDARIOS_BASE:
        raise ValueError("POOL_LEGENDARIOS_BASE está vacía. "
                         "Inyecta los IDs de especies antes de usar esta función.")

    # ------------------------------------------------------------------
    # Paso 1: calcular el timestamp del inicio del día en UTC (ms)
    # Esto replica `new Date(timestamp)` con la normalización a medianoche.
    #
    # El juego pasa el timestamp tal cual (con hora), pero la aritmética
    # de divisiones enteras por 86_400_000 lo normaliza automáticamente
    # al número del día desde el epoch UNIX.
    # ------------------------------------------------------------------
    if fecha.tzinfo is not None:
        # Convertir a UTC si tiene timezone
        fecha_utc = fecha.astimezone(timezone.utc)
    else:
        # Si es naive, asumir UTC
        fecha_utc = fecha.replace(tzinfo=timezone.utc)

    # Timestamp del INICIO del día UTC en milisegundos
    inicio_dia_utc = fecha_utc.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    day_ts_ms: int = int(inicio_dia_utc.timestamp() * 1000)

    # ------------------------------------------------------------------
    # Paso 2: cálculos de ciclo e índice (réplica exacta del TS)
    # ------------------------------------------------------------------
    pool_size: int = len(POOL_LEGENDARIOS_BASE)

    days: int = math.floor(day_ts_ms / 86_400_000)
    offset: int = math.floor(days / pool_size)
    index: int = days % pool_size

    # ------------------------------------------------------------------
    # Paso 3: construir la semilla y barajar
    # La semilla concatena EGG_SEED.toString() + offset (como strings JS)
    # -- LA SEMILLA PARA ALEA --
    # Pokerogue usa globalScene.executeWithSeedOffset(..., offset, EGG_SEED.toString())
    # Esto internamente llama a: Phaser.Math.RND.sow([shiftCharCodes(EGG_SEED.toString(), offset)])
    semilla_shift = shift_char_codes(str(EGG_SEED), offset)

    # 4) Inicializar el PRNG
    rng = AleaRNG([semilla_shift])

    # 5) Barajar la pool (AleaRNG.shuffle NO muta si le pasamos una copia,
    # pero nuestro método devuelve la lista mutada, así que mejor copiar).
    pool_barajado: list[int] = rng.shuffle(POOL_LEGENDARIOS_BASE.copy())

    return pool_barajado[index]
