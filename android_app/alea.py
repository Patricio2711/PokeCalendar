"""
alea.py — Replicación exacta del PRNG Alea de Phaser 3
=======================================================
Porta fielmente la clase `Phaser.Math.RandomDataGenerator` de Phaser 3
(src/math/random-data-generator/RandomDataGenerator.js) a Python.

El juego PokéRogue utiliza `Phaser.Math.RND` (una instancia global de esta
clase) para barajar el pool de legendarios de forma determinista. Al replicar
el mismo algoritmo bit a bit podemos obtener el mismo resultado que el juego
real solo con conocer la semilla y el offset del día.

Puntos críticos de fidelidad:
  - El operador >>> 0 de JS (unsigned right-shift 0) equivale a
    `valor & 0xFFFFFFFF` en Python (convierte a entero sin signo 32-bit).
  - Las multiplicaciones intermedias desbordantes en JS usan precisión
    double IEEE-754, igual que Python con float.
  - shuffle() usa frac() (dos llamadas a rnd()) — NO Math.random().
"""

import copy
from typing import TypeVar

T = TypeVar("T")

# Constante de escala: 2^-32
_INV_2_32 = 2.3283064365386963e-10
# Constante de escala: 2^-53
_INV_2_53 = 1.1102230246251565e-16


class AleaRNG:
    """
    Replicación en Python de Phaser.Math.RandomDataGenerator.

    Uso básico:
        rng = AleaRNG(["1073741824", "0"])
        val = rng.frac()          # float en [0, 1)
        lst = rng.shuffle([...])  # lista mezclada in-place
    """

    def __init__(self, seeds: list[str] | None = None):
        """
        Inicializa el generador con las semillas dadas.

        Args:
            seeds: Lista de strings con las semillas. Si es None o vacía,
                   se usa la semilla por defecto del motor.
        """
        # Estado interno idéntico al de RandomDataGenerator
        self.c: int = 1
        self.s0: float = 0.0
        self.s1: float = 0.0
        self.s2: float = 0.0
        self.n: float = 0.0  # Acumulador interno del hash (float como JS number)

        if seeds:
            self.sow(seeds)

    # ------------------------------------------------------------------
    # Métodos privados del motor
    # ------------------------------------------------------------------

    def _hash(self, data: str) -> float:
        """
        Función de hash interna, idéntica a RandomDataGenerator.hash().

        Convierte un string en un float en [0, 1) actualizando el estado `n`.

        NOTA CRÍTICA sobre JavaScript vs Python:
          - En JS, `n` es un `number` (float64) a lo largo de toda la función.
          - `n = h >>> 0` en JS trunca h a un entero sin signo de 32 bits,
            pero el resultado sigue siendo un JS number (float64).
          - `n += h * 0x100000000` lleva n de vuelta a float (puede ser > 2^32).
          - La clave: `int(h) & 0xFFFFFFFF` replica `h >>> 0` en los dos sitios
            internos del loop; pero `n` en sí se mantiene como float Python
            porque la siguiente iteración puede sumar h * 2^32.
          - `self.n` almacena este float entre llamadas, igual que en JS.
          - Solo el return final aplica la máscara de 32 bits para la salida.

        Args:
            data: El string a hashear.

        Returns:
            Un float en [0, 1) derivado del hash.
        """
        # n se trata como float para replicar el comportamiento de JS number
        n: float = float(self.n)

        data = str(data)

        for char in data:
            n += ord(char)
            # JS: h = 0.02519603282416938 * n
            h: float = 0.02519603282416938 * n
            # JS: n = h >>> 0  →  truncar h a entero sin signo 32-bit
            n = float(int(h) & 0xFFFFFFFF)
            h -= n
            h *= n
            # JS: n = h >>> 0  (segunda vez)
            n = float(int(h) & 0xFFFFFFFF)
            h -= n
            # JS: n += h * 0x100000000  →  n vuelve a ser float grande
            n += h * 4294967296.0  # 0x100000000 = 2^32

        # Persistir el estado interno (como float, igual que JS)
        self.n = n

        # JS: return (n >>> 0) * 2^-32
        # Aplicar máscara de 32 bits solo en el valor de retorno
        return float(int(n) & 0xFFFFFFFF) * _INV_2_32

    def _rnd(self) -> float:
        """
        Generador de número pseudoaleatorio interno (Alea puro).

        Este es el núcleo del algoritmo. Cada llamada avanza el estado
        (s0, s1, s2, c) exactamente como lo hace Phaser 3.

        Returns:
            Un float pseudoaleatorio.
        """
        # JS: var t = 2091639 * this.s0 + this.c * 2^-32
        t = 2091639.0 * self.s0 + self.c * _INV_2_32

        # JS: this.c = t | 0  →  Python: parte entera con signo 32-bit
        # En JS `t | 0` trunca al entero de 32 bits con signo.
        # Como t es siempre positivo aquí, int(t) es equivalente.
        self.c = int(t)

        self.s0 = self.s1
        self.s1 = self.s2
        # s2 es la fracción de t (la parte decimal)
        self.s2 = t - self.c

        return self.s2

    # ------------------------------------------------------------------
    # Métodos de inicialización (réplica exacta de sow / init)
    # ------------------------------------------------------------------

    def sow(self, seeds: list[str]) -> None:
        """
        Inicializa/reinicia el estado a partir de una lista de semillas.
        Réplica exacta de RandomDataGenerator.sow().

        El estado base se calcula hasheando tres veces el espacio ' '
        con el valor inicial n = 0xefc8249d.

        Args:
            seeds: Lista de semillas (como strings).
        """
        # Siempre reiniciar al estado por defecto primero
        self.n = 0xefc8249d
        self.s0 = self._hash(" ")
        self.s1 = self._hash(" ")
        self.s2 = self._hash(" ")
        self.c = 1

        if not seeds:
            return

        # Aplicar cada semilla
        for seed in seeds:
            if seed is None:
                break

            seed_str = str(seed)

            # JS: this.s0 -= this.hash(seed)
            self.s0 -= self._hash(seed_str)
            # JS: this.s0 += ~~(this.s0 < 0)  →  +1 si negativo, +0 si no
            if self.s0 < 0:
                self.s0 += 1

            self.s1 -= self._hash(seed_str)
            if self.s1 < 0:
                self.s1 += 1

            self.s2 -= self._hash(seed_str)
            if self.s2 < 0:
                self.s2 += 1

    # ------------------------------------------------------------------
    # API pública — réplica de los métodos públicos de Phaser RND
    # ------------------------------------------------------------------

    def frac(self) -> float:
        """
        Retorna un float pseudoaleatorio en [0, 1).
        Réplica de RandomDataGenerator.frac() — llama a _rnd() DOS veces.

        Returns:
            Float en [0, 1).
        """
        # JS: return this.rnd() + (this.rnd() * 0x200000 | 0) * 2^-53
        a = self._rnd()
        b = int(self._rnd() * 0x200000) * _INV_2_53
        return a + b

    def integer(self) -> float:
        """
        Retorna un entero pseudoaleatorio entre 0 y 2^32.
        Réplica de RandomDataGenerator.integer().

        Returns:
            Float representando un entero en [0, 2^32).
        """
        return self._rnd() * 0x100000000

    def real_in_range(self, min_val: float, max_val: float) -> float:
        """
        Retorna un float pseudoaleatorio en [min_val, max_val).
        Réplica de RandomDataGenerator.realInRange().

        Args:
            min_val: Límite inferior.
            max_val: Límite superior.

        Returns:
            Float en [min_val, max_val).
        """
        return self.frac() * (max_val - min_val) + min_val

    def shuffle(self, array: list[T]) -> list[T]:
        """
        Baraja la lista usando Fisher-Yates con frac() como fuente de
        aleatoriedad. Réplica EXACTA de RandomDataGenerator.shuffle().

        IMPORTANTE: Opera sobre la lista pasada directamente (in-place)
        y también la retorna, igual que la versión JS. Pasa una copia
        si no quieres modificar el original.

        Args:
            array: La lista a barajar.

        Returns:
            La misma lista barajada (in-place).
        """
        last_idx = len(array) - 1

        # JS: for (var i = len; i > 0; i--)
        for i in range(last_idx, 0, -1):
            # JS: var randomIndex = Math.floor(this.frac() * (i + 1))
            random_index = int(self.frac() * (i + 1))

            # Swap
            array[random_index], array[i] = array[i], array[random_index]

        return array
