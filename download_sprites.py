"""
download_sprites.py — Pre-descarga los 25 sprites legendarios para la caché local.
"""
import os
import urllib.request
from gacha import POOL_LEGENDARIOS_BASE

def _descargar_bytes(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read()
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return None

def main():
    ruta_sprites = "sprites"
    os.makedirs(ruta_sprites, exist_ok=True)
    
    # Agregar Ho-Oh (250) que está hardcodeado como corrección a la pool
    pool = set(POOL_LEGENDARIOS_BASE)
    pool.add(250)
    
    descargados = 0
    fallidos = 0
    
    print(f"Iniciando pre-descarga de {len(pool)} sprites...")
    for species_id in pool:
        ruta_archivo = os.path.join(ruta_sprites, f"{species_id}.png")
        if os.path.exists(ruta_archivo):
            print(f"  [{species_id}] Ya existe en caché.")
            descargados += 1
            continue
            
        url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{species_id}.png"
        print(f"  [{species_id}] Descargando...", end=" ", flush=True)
        img_bytes = _descargar_bytes(url)
        
        if img_bytes:
            with open(ruta_archivo, "wb") as f:
                f.write(img_bytes)
            print("Ok!")
            descargados += 1
        else:
            print("Falló.")
            fallidos += 1
            
    print(f"\nFinalizado. Descargados/en caché: {descargados}, Fallidos: {fallidos}")

if __name__ == "__main__":
    main()
