"""
pokeapi.py — Cliente asíncrono para la PokéAPI
================================================
Proporciona funciones para obtener datos de Pokémon desde
https://pokeapi.co/ sin bloquear el hilo principal de Tkinter.

Estrategia de asincronía:
  - Usamos `concurrent.futures.ThreadPoolExecutor` en lugar de asyncio.
  - Esto es deliberado: asyncio + Tkinter requiere un loop de eventos
    compartido y complica la arquitectura. Con hilos nativos, Tkinter
    puede seguir usando `after()` para leer resultados de forma segura.

Cache:
  - `_cache` guarda los resultados ya descargados, evitando peticiones
    repetidas para el mismo Pokémon durante la sesión de la app.

Puntos de inyección:
  - Si en el futuro quieres añadir datos de Pokérus, agrega los campos
    al diccionario retornado por `obtener_datos_pokemon()`.
"""

import urllib.request
import urllib.error
import json
import threading
import os
import sys
from concurrent.futures import ThreadPoolExecutor, Future

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

POKEAPI_BASE_URL: str = "https://pokeapi.co/api/v2"
TIMEOUT_SEGUNDOS: int = 10   # Tiempo máximo de espera por petición HTTP

# Pool de threads — máximo 4 peticiones simultáneas
_executor = ThreadPoolExecutor(max_workers=4)

# Cache en memoria: clave = nombre/id normalizado, valor = dict con datos
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Módulo de descarga de sprites
# ---------------------------------------------------------------------------

def _descargar_bytes(url: str) -> bytes | None:
    """
    Descarga los bytes de una URL HTTP. Retorna None en caso de error.

    Args:
        url: URL a descargar.

    Returns:
        Bytes del contenido, o None si falló.
    """
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SEGUNDOS) as resp:
            return resp.read()
    except Exception:
        return None


def _obtener_datos_pokemon_sync(nombre_o_id: str | int) -> dict:
    """
    Obtención SINCRÓNICA de datos de un Pokémon desde la PokéAPI.
    Se ejecuta en un hilo del pool, nunca en el hilo principal.

    Args:
        nombre_o_id: Nombre en minúsculas o ID numérico del Pokémon.

    Returns:
        Diccionario con claves:
          - 'nombre'        (str)  : Nombre del Pokémon capitalizado
          - 'id'            (int)  : ID de la PokéDex
          - 'tipos'         (list) : Lista de tipos (strings)
          - 'sprite_url'    (str)  : URL del sprite oficial front-default
          - 'sprite_bytes'  (bytes): Bytes PNG del sprite (para Tkinter/PIL)
          - 'error'         (str|None): Mensaje de error si algo falló
          
          # ╔════════════════════════════════════════════════════════════╗
          # ║  PUNTO DE INYECCIÓN — DATOS POKÉRUS                       ║
          # ║  Agrega aquí campos adicionales como:                     ║
          # ║   - 'tiene_pokérus': bool                                 ║
          # ║   - 'ev_yields': dict                                     ║
          # ║   - 'movepool_especial': list                             ║
          # ╚════════════════════════════════════════════════════════════╝
    """
    clave_cache = str(nombre_o_id).lower().strip()

    # Revisar cache primero
    with _cache_lock:
        if clave_cache in _cache:
            return _cache[clave_cache]

    # Resultado vacío por defecto (fallback seguro si la red falla)
    resultado_vacio = {
        "nombre": str(nombre_o_id).capitalize(),
        "id": None,
        "tipos": [],
        "sprite_url": None,
        "sprite_bytes": None,
        "error": None,
    }

    try:
        # --- Caché local en disco o Bundle de PyInstaller ---
        # Si estamos ejecutando compilado desde PyInstaller:
        if getattr(sys, 'frozen', False):
            ruta_sprites = os.path.join(sys._MEIPASS, "sprites")
        else:
            ruta_sprites = "sprites"
            
        # Asegurar que el directorio exista (solo estrictamente necesario modo source)
        if not os.path.exists(ruta_sprites):
            os.makedirs(ruta_sprites, exist_ok=True)
        
        ruta_archivo = os.path.join(ruta_sprites, f"{clave_cache}.png")
        sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{clave_cache}.png"

        # 1. Intentar cargar desde el disco local o desde el bundle de PyInstaller
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, "rb") as f:
                sprite_bytes = f.read()
        else:
            # 2. Descargar si no existe localmente
            sprite_bytes = _descargar_bytes(sprite_url)
            if sprite_bytes is None:
                raise urllib.error.URLError("No se pudo descargar el sprite del CDN.")
            
            # Guardar el sprite localmente para futuras ejecuciones (si no estamos en frozen bundle de solo lectura)
            if not getattr(sys, 'frozen', False):
                with open(ruta_archivo, "wb") as f:
                    f.write(sprite_bytes)

        resultado = {
            "nombre": str(nombre_o_id).capitalize(),
            "id": int(nombre_o_id) if str(nombre_o_id).isdigit() else None,
            "tipos": [],
            "sprite_url": sprite_url, # Solo informativo ahora
            "sprite_bytes": sprite_bytes,
            "error": None,
        }

    except Exception as e:
        resultado = {**resultado_vacio, "error": str(e)}

    # Guardar en cache (incluso errores, para no reintentar en la sesión)
    with _cache_lock:
        _cache[clave_cache] = resultado

    return resultado


def obtener_datos_pokemon_async(nombre_o_id: str | int) -> Future:
    """
    Versión ASÍNCRONA de la obtención de datos de Pokémon.
    Devuelve un `Future` que resuelve al dict de datos.

    Uso desde Tkinter:
        future = obtener_datos_pokemon_async("lugia")
        # ... en el callback de after() de Tkinter:
        if future.done():
            datos = future.result()

    Args:
        nombre_o_id: Nombre en minúsculas o ID numérico.

    Returns:
        concurrent.futures.Future que resolverá al dict de datos.
    """
    return _executor.submit(_obtener_datos_pokemon_sync, nombre_o_id)


def limpiar_cache() -> None:
    """
    Vacía la caché en memoria. Útil para testing o para refrescar datos.
    """
    with _cache_lock:
        _cache.clear()
