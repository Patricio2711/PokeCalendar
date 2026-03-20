"""
app.py — Calendario desktop PokéRogue (Tkinter)
================================================
Aplicación principal. Muestra un calendario mensual y, al hacer clic en
un día, consulta qué legendario está activo en el Gacha de ese día
usando la lógica replicada de PokéRogue + la PokéAPI para el sprite.

Arquitectura UI → Lógica:
  - `gacha.obtener_legendario_del_dia(fecha)` → nombre del Pokémon
  - `pokeapi.obtener_datos_pokemon_async(nombre)` → Future con datos+sprite
  - `root.after(100, ...)` → bucle de polling para actualizar UI sin freeze

Requisitos:
  pip install pillow

Inyección de Pokérus:
  Busca los comentarios marcados con "PUNTO DE INYECCIÓN — POKÉRUS" para
  agregar lógica de Pokérus o cualquier dato extra de game cuando estés listo.
"""

import tkinter as tk
from tkinter import ttk, font as tkfont
import calendar
from datetime import datetime, timezone
from io import BytesIO
from concurrent.futures import Future
from typing import Optional

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFilter
    PIL_DISPONIBLE = True
except ImportError:
    PIL_DISPONIBLE = False

from gacha import obtener_legendario_del_dia, POOL_LEGENDARIOS_BASE, obtener_nombre_especie
from pokeapi import obtener_datos_pokemon_async

# ---------------------------------------------------------------------------
# Paleta de colores y constantes de diseño
# ---------------------------------------------------------------------------

COLORES = {
    "fondo":           "#0d0f1a",   # Azul medianoche profundo
    "panel":           "#151929",   # Panel lateral oscuro
    "acento":          "#e63946",   # Rojo PokéRogue
    "acento2":         "#457b9d",   # Azul complementario
    "texto":           "#f1faee",   # Blanco marfil
    "texto_suave":     "#a8dadc",   # Cian tenue para subtítulos
    "celda_normal":    "#1d2035",   # Celda de día normal
    "celda_hover":     "#2a2f50",   # Hover sobre día
    "celda_hoy":       "#e63946",   # Destaque del día actual
    "celda_seleccion": "#457b9d",   # Día seleccionado
    "borde":           "#2a2f50",   # Bordes sutiles
    "sombra":          "#070910",   # Sombra profunda
    "cargando":        "#a8dadc",   # Color de texto de cargando
    "tipo_fuego":      "#ff6b35",
    "tipo_agua":       "#4a90d9",
    "tipo_planta":     "#4caf50",
    "tipo_psiquico":   "#e91e8c",
    "tipo_dragón":     "#5c35d4",
    "tipo_normal":     "#9e9e9e",
}

TIPOS_COLORES: dict[str, str] = {
    "Fire":     "#ff6b35", "Water":    "#4a90d9", "Grass":    "#4caf50",
    "Psychic":  "#e91e8c", "Dragon":   "#5c35d4", "Normal":   "#9e9e9e",
    "Electric": "#f4d03f", "Ice":      "#74d7f4", "Fighting": "#c0392b",
    "Poison":   "#9b59b6", "Ground":   "#d4a857", "Flying":   "#74a0d9",
    "Bug":      "#8bc34a", "Rock":     "#a5856a", "Ghost":    "#7c4dff",
    "Dark":     "#4a4a4a", "Steel":    "#90a4ae", "Fairy":    "#f48fb1",
}

DIAS_SEMANA = ["L", "M", "X", "J", "V", "S", "D"]
MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


# ---------------------------------------------------------------------------
# Clase principal de la aplicación
# ---------------------------------------------------------------------------

class PokeRogueCalendario(tk.Tk):
    """
    Ventana principal del Calendario PokéRogue.

    Gestiona el estado del calendario, el ciclo de polling para
    peticiones asíncronas y todos los widgets de la UI.
    """

    def __init__(self):
        super().__init__()

        # --- Configuración de ventana ---
        self.title("PokéRogue — Calendario Gacha Legendario")
        self.configure(bg=COLORES["fondo"])
        self.resizable(False, False)

        # --- Estado interno ---
        hoy = datetime.now(timezone.utc)
        self.año_actual: int = hoy.year
        self.mes_actual: int = hoy.month
        self.hoy: datetime = hoy

        self.dia_seleccionado: Optional[int] = None
        self.fecha_seleccionada: Optional[datetime] = None

        # Future activo de la petición a PokéAPI
        self._future_activo: Optional[Future] = None
        self._polling_activo: bool = False

        # Referencia persistente al objeto ImageTk (evita garbage collection)
        self._sprite_img: Optional[ImageTk.PhotoImage] = None

        # Widget labels de celdas de días {numero_dia: tk.Label}
        self._celdas_dias: dict[int, tk.Label] = {}

        # --- Fuentes ---
        self._configurar_fuentes()

        # --- Widgets ---
        self._construir_ui()

        # Seleccionar el día de hoy al iniciar
        self._seleccionar_dia_hoy()

    # -----------------------------------------------------------------------
    # Configuración de fuentes
    # -----------------------------------------------------------------------

    def _configurar_fuentes(self) -> None:
        """Registra las fuentes personalizadas usadas en la app."""
        self.fuente_titulo = tkfont.Font(
            family="Segoe UI", size=15, weight="bold")
        self.fuente_mes    = tkfont.Font(
            family="Segoe UI", size=13, weight="bold")
        self.fuente_dia    = tkfont.Font(
            family="Segoe UI", size=11)
        self.fuente_dia_bold = tkfont.Font(
            family="Segoe UI", size=11, weight="bold")
        self.fuente_encab  = tkfont.Font(
            family="Segoe UI", size=9, weight="bold")
        self.fuente_small  = tkfont.Font(
            family="Segoe UI", size=9)
        self.fuente_poke_nombre = tkfont.Font(
            family="Segoe UI", size=16, weight="bold")
        self.fuente_info   = tkfont.Font(
            family="Segoe UI", size=10)

    # -----------------------------------------------------------------------
    # Construcción de la UI
    # -----------------------------------------------------------------------

    def _construir_ui(self) -> None:
        """Construye todos los widgets de la aplicación."""
        # === Contenedor raíz ===
        raiz = tk.Frame(self, bg=COLORES["fondo"])
        raiz.pack(padx=20, pady=20, fill="both", expand=True)

        # === Título de la app ===
        encabezado = tk.Frame(raiz, bg=COLORES["fondo"])
        encabezado.pack(fill="x", pady=(0, 16))

        tk.Label(
            encabezado,
            text="⬡ PokéRogue",
            font=self.fuente_titulo,
            bg=COLORES["fondo"],
            fg=COLORES["acento"],
        ).pack(side="left")

        tk.Label(
            encabezado,
            text=" — Gacha Legendario",
            font=self.fuente_titulo,
            bg=COLORES["fondo"],
            fg=COLORES["texto"],
        ).pack(side="left")

        # === Cuerpo horizontal: calendar + panel info ===
        cuerpo = tk.Frame(raiz, bg=COLORES["fondo"])
        cuerpo.pack(fill="both", expand=True)

        self._construir_calendario(cuerpo)
        self._construir_panel_info(cuerpo)

    def _construir_calendario(self, padre: tk.Frame) -> None:
        """Construye la sección del calendario mensual."""
        marco_cal = tk.Frame(
            padre,
            bg=COLORES["panel"],
            bd=0,
            highlightbackground=COLORES["borde"],
            highlightthickness=1,
        )
        marco_cal.pack(side="left", fill="both", padx=(0, 16))

        # --- Barra de navegación mes/año ---
        nav = tk.Frame(marco_cal, bg=COLORES["panel"])
        nav.pack(fill="x", padx=16, pady=(14, 8))

        btn_estilo = {
            "bg": COLORES["panel"],
            "fg": COLORES["texto_suave"],
            "font": self.fuente_mes,
            "bd": 0,
            "padx": 6,
            "cursor": "hand2",
            "activebackground": COLORES["celda_hover"],
            "activeforeground": COLORES["texto"],
        }

        tk.Button(nav, text="◀", command=self._mes_anterior,
                  **btn_estilo).pack(side="left")

        self.lbl_mes_año = tk.Label(
            nav,
            text="",
            font=self.fuente_mes,
            bg=COLORES["panel"],
            fg=COLORES["texto"],
            width=20,
            anchor="center",
        )
        self.lbl_mes_año.pack(side="left", expand=True)

        tk.Button(nav, text="▶", command=self._mes_siguiente,
                  **btn_estilo).pack(side="right")

        # --- Cabecera de días de la semana ---
        cabecera = tk.Frame(marco_cal, bg=COLORES["panel"])
        cabecera.pack(fill="x", padx=10, pady=(0, 4))

        for dia in DIAS_SEMANA:
            lbl = tk.Label(
                cabecera,
                text=dia,
                font=self.fuente_encab,
                bg=COLORES["panel"],
                fg=COLORES["texto_suave"],
                width=4,
                anchor="center",
            )
            lbl.pack(side="left", expand=True, fill="x")

        # --- Grid de días ---
        self.grid_dias = tk.Frame(marco_cal, bg=COLORES["panel"])
        self.grid_dias.pack(padx=10, pady=(0, 14))

        # Guardamos la referencia al frame del grid para renderizarlo
        self._renderizar_mes()

    def _construir_panel_info(self, padre: tk.Frame) -> None:
        """Construye el panel lateral de información del legendario."""
        self.panel_info = tk.Frame(
            padre,
            bg=COLORES["panel"],
            bd=0,
            highlightbackground=COLORES["borde"],
            highlightthickness=1,
            width=240,
        )
        self.panel_info.pack(side="left", fill="both", expand=True)
        self.panel_info.pack_propagate(False)

        # --- Título del panel ---
        tk.Label(
            self.panel_info,
            text="Gacha de Hoy",
            font=self.fuente_encab,
            bg=COLORES["panel"],
            fg=COLORES["texto_suave"],
        ).pack(pady=(16, 0))

        # Separador
        sep = tk.Frame(self.panel_info, bg=COLORES["borde"], height=1)
        sep.pack(fill="x", padx=16, pady=(6, 12))

        # --- Sprite del Pokémon ---
        self.canvas_sprite = tk.Label(
            self.panel_info,
            bg=COLORES["panel"],
            text="",
            anchor="center",
        )
        self.canvas_sprite.pack(pady=(0, 8))

        # --- Nombre del Pokémon ---
        self.lbl_nombre = tk.Label(
            self.panel_info,
            text="—",
            font=self.fuente_poke_nombre,
            bg=COLORES["panel"],
            fg=COLORES["texto"],
            wraplength=210,
        )
        self.lbl_nombre.pack()

        # --- Frame para los tipos (badges) ---
        self.frame_tipos = tk.Frame(self.panel_info, bg=COLORES["panel"])
        self.frame_tipos.pack(pady=(6, 0))

        # --- Label de ID Pokédex ---
        self.lbl_id = tk.Label(
            self.panel_info,
            text="",
            font=self.fuente_small,
            bg=COLORES["panel"],
            fg=COLORES["texto_suave"],
        )
        self.lbl_id.pack(pady=(4, 0))

        # --- Label de fecha seleccionada ---
        self.lbl_fecha = tk.Label(
            self.panel_info,
            text="",
            font=self.fuente_info,
            bg=COLORES["panel"],
            fg=COLORES["texto_suave"],
        )
        self.lbl_fecha.pack(pady=(2, 0))

        # --- Label de estado (cargando / error) ---
        self.lbl_estado = tk.Label(
            self.panel_info,
            text="Selecciona un día",
            font=self.fuente_small,
            bg=COLORES["panel"],
            fg=COLORES["cargando"],
            wraplength=210,
        )
        self.lbl_estado.pack(pady=(12, 0))

        # ╔════════════════════════════════════════════════════════════════╗
        # ║  PUNTO DE INYECCIÓN — POKÉRUS                                 ║
        # ║  Aquí puedes añadir widgets extra para mostrar los datos de   ║
        # ║  Pokérus asociados al legendario del día. Por ejemplo:        ║
        # ║                                                               ║
        # ║  self.lbl_pokérus = tk.Label(                                 ║
        # ║      self.panel_info, text="Pokérus: —",                     ║
        # ║      font=self.fuente_small, bg=COLORES["panel"],             ║
        # ║      fg=COLORES["acento"])                                    ║
        # ║  self.lbl_pokérus.pack(pady=(4, 0))                          ║
        # ╚════════════════════════════════════════════════════════════════╝

        # --- Indicador de pool size ---
        tk.Label(
            self.panel_info,
            text=f"Pool: {len(POOL_LEGENDARIOS_BASE)} legendarios",
            font=self.fuente_small,
            bg=COLORES["panel"],
            fg=COLORES["borde"],
        ).pack(side="bottom", pady=(0, 10))

    # -----------------------------------------------------------------------
    # Renderizado del calendario
    # -----------------------------------------------------------------------

    def _renderizar_mes(self) -> None:
        """Limpia y redibuja el grid de días del mes actual."""
        # Limpiar celdas anteriores
        for widget in self.grid_dias.winfo_children():
            widget.destroy()
        self._celdas_dias.clear()

        # Actualizar label de mes/año
        self.lbl_mes_año.config(
            text=f"{MESES_ES[self.mes_actual]} {self.año_actual}"
        )

        # Obtener matriz del mes (lunes=0, domingo=6)
        cal = calendar.monthcalendar(self.año_actual, self.mes_actual)

        hoy_dia = (self.hoy.year == self.año_actual
                   and self.hoy.month == self.mes_actual)

        for semana_idx, semana in enumerate(cal):
            fila = tk.Frame(self.grid_dias, bg=COLORES["panel"])
            fila.pack(fill="x", pady=2)

            for dia in semana:
                if dia == 0:
                    # Celda vacía (días de otro mes)
                    tk.Label(
                        fila,
                        text="",
                        width=4,
                        height=2,
                        bg=COLORES["panel"],
                    ).pack(side="left", padx=2)
                    continue

                es_hoy = hoy_dia and dia == self.hoy.day
                es_sel = dia == self.dia_seleccionado

                bg = (COLORES["celda_hoy"] if es_hoy
                      else COLORES["celda_seleccion"] if es_sel
                      else COLORES["celda_normal"])
                fg = COLORES["texto"]
                fuente = self.fuente_dia_bold if es_hoy else self.fuente_dia

                celda = tk.Label(
                    fila,
                    text=str(dia),
                    width=4,
                    height=2,
                    bg=bg,
                    fg=fg,
                    font=fuente,
                    cursor="hand2",
                    relief="flat",
                )
                celda.pack(side="left", padx=2)

                # Eventos de hover y clic
                celda.bind("<Enter>",
                           lambda e, c=celda, d=dia: self._hover_enter(c, d))
                celda.bind("<Leave>",
                           lambda e, c=celda, d=dia: self._hover_leave(c, d))
                celda.bind("<Button-1>",
                           lambda e, d=dia: self._on_dia_click(d))

                self._celdas_dias[dia] = celda

    # -----------------------------------------------------------------------
    # Eventos de interacción del calendario
    # -----------------------------------------------------------------------

    def _hover_enter(self, celda: tk.Label, dia: int) -> None:
        """Efecto hover: iluminar celda."""
        if dia != self.dia_seleccionado and not (
            self.hoy.year == self.año_actual
            and self.hoy.month == self.mes_actual
            and dia == self.hoy.day
        ):
            celda.config(bg=COLORES["celda_hover"])

    def _hover_leave(self, celda: tk.Label, dia: int) -> None:
        """Efecto hover: restaurar color."""
        if dia == self.dia_seleccionado:
            celda.config(bg=COLORES["celda_seleccion"])
        elif (self.hoy.year == self.año_actual
              and self.hoy.month == self.mes_actual
              and dia == self.hoy.day):
            celda.config(bg=COLORES["celda_hoy"])
        else:
            celda.config(bg=COLORES["celda_normal"])

    def _on_dia_click(self, dia: int) -> None:
        """
        Gestiona el clic en un día del calendario.

        1. Actualiza la selección visual.
        2. Calcula el legendario del Gacha para ese día.
        3. Lanza la petición asíncrona a PokéAPI.
        """
        # Actualizar celda anterior
        if self.dia_seleccionado and self.dia_seleccionado in self._celdas_dias:
            celda_ant = self._celdas_dias[self.dia_seleccionado]
            es_hoy_ant = (
                self.hoy.year == self.año_actual
                and self.hoy.month == self.mes_actual
                and self.dia_seleccionado == self.hoy.day
            )
            celda_ant.config(bg=COLORES["celda_hoy"] if es_hoy_ant
                             else COLORES["celda_normal"])

        # Marcar nueva selección
        self.dia_seleccionado = dia
        if dia in self._celdas_dias:
            self._celdas_dias[dia].config(bg=COLORES["celda_seleccion"])

        # Construir la fecha completa
        fecha = datetime(
            self.año_actual, self.mes_actual, dia,
            tzinfo=timezone.utc
        )
        self.fecha_seleccionada = fecha

        # Mostrar fecha en panel
        self.lbl_fecha.config(
            text=f"{dia:02d}/{self.mes_actual:02d}/{self.año_actual}"
        )

        # --- Calcular legendario del Gacha ---
        species_id = obtener_legendario_del_dia(fecha)
        nombre_local = obtener_nombre_especie(species_id)

        # Mostrar nombre localmente de inmediato (sin red)
        self.lbl_nombre.config(text=nombre_local)
        self.lbl_id.config(text=f"Nº {species_id:04d}")
        self.lbl_estado.config(text="⟳ Cargando sprite...",
                               fg=COLORES["cargando"])
        self._limpiar_tipos()
        self._limpiar_sprite()

        # ╔════════════════════════════════════════════════════════════════╗
        # ║  PUNTO DE INYECCIÓN — POKÉRUS                                 ║
        # ║  Antes del fetch asíncrono, aquí podrías consultar tu módulo  ║
        # ║  de Pokérus con `nombre_legendario` y actualizar los          ║
        # ║  widgets de Pokérus en consecuencia.                          ║
        # ╚════════════════════════════════════════════════════════════════╝

        # --- Lanzar petición asíncrona ---
        self._future_activo = obtener_datos_pokemon_async(species_id)

        # Iniciar polling si no estaba activo
        if not self._polling_activo:
            self._polling_activo = True
            self.after(100, self._verificar_future)

    # -----------------------------------------------------------------------
    # Polling asíncrono (after-loop)
    # -----------------------------------------------------------------------

    def _verificar_future(self) -> None:
        """
        Bucle de polling que verifica cada 100ms si el Future de PokéAPI
        ha resuelto. Actualiza el panel de info cuando los datos están listos.

        SEGURO para Tkinter: toda actualización de widgets ocurre en el
        hilo principal gracias a `after()`.
        """
        if self._future_activo is None:
            self._polling_activo = False
            return

        if not self._future_activo.done():
            # Aún esperando — reintentar en 100ms
            self.after(100, self._verificar_future)
            return

        # Future resuelto — procesar resultado
        self._polling_activo = False
        datos = self._future_activo.result()
        self._future_activo = None

        if datos.get("error"):
            # Error de red — el nombre ya se mostró localmente, solo avisa
            self.lbl_estado.config(
                text=f"⚠ Sin sprite (sin red)",
                fg=COLORES["acento"]
            )
            return

        # --- Actualizar nombre e ID ---
        self.lbl_nombre.config(text=datos["nombre"])
        if datos.get("id"):
            self.lbl_id.config(text=f"Nº {datos['id']:04d}")

        # --- Actualizar badges de tipos ---
        self._limpiar_tipos()
        for tipo in datos.get("tipos", []):
            color = TIPOS_COLORES.get(tipo, COLORES["borde"])
            badge = tk.Label(
                self.frame_tipos,
                text=tipo,
                font=self.fuente_small,
                bg=color,
                fg="white",
                padx=8,
                pady=2,
                relief="flat",
            )
            badge.pack(side="left", padx=3)

        # --- Actualizar sprite ---
        sprite_bytes = datos.get("sprite_bytes")
        if sprite_bytes and PIL_DISPONIBLE:
            try:
                img = Image.open(BytesIO(sprite_bytes))
                img = img.resize((175, 175), Image.LANCZOS)
                self._sprite_img = ImageTk.PhotoImage(img)
                self.canvas_sprite.config(
                    image=self._sprite_img, text="")
            except Exception:
                self.canvas_sprite.config(
                    image="", text="🔴 Error al cargar imagen",
                    fg=COLORES["texto_suave"], font=self.fuente_small)
        elif sprite_bytes and not PIL_DISPONIBLE:
            self.canvas_sprite.config(
                image="",
                text="📦 Instala Pillow\n`pip install pillow`",
                fg=COLORES["texto_suave"],
                font=self.fuente_small)
        else:
            self.canvas_sprite.config(
                image="", text="Sin sprite",
                fg=COLORES["texto_suave"], font=self.fuente_small)

        self.lbl_estado.config(text="", fg=COLORES["cargando"])

    # -----------------------------------------------------------------------
    # Navegación de mes
    # -----------------------------------------------------------------------

    def _mes_anterior(self) -> None:
        """Navega al mes anterior y re-renderiza el calendario."""
        if self.mes_actual == 1:
            self.mes_actual = 12
            self.año_actual -= 1
        else:
            self.mes_actual -= 1

        self.dia_seleccionado = None
        self._renderizar_mes()
        self._limpiar_panel_info()

    def _mes_siguiente(self) -> None:
        """Navega al mes siguiente y re-renderiza el calendario."""
        if self.mes_actual == 12:
            self.mes_actual = 1
            self.año_actual += 1
        else:
            self.mes_actual += 1

        self.dia_seleccionado = None
        self._renderizar_mes()
        self._limpiar_panel_info()

    # -----------------------------------------------------------------------
    # Helpers de UI
    # -----------------------------------------------------------------------

    def _limpiar_tipos(self) -> None:
        """Elimina todos los badges de tipo del frame de tipos."""
        for widget in self.frame_tipos.winfo_children():
            widget.destroy()

    def _limpiar_sprite(self) -> None:
        """Limpia el widget del sprite."""
        self._sprite_img = None
        self.canvas_sprite.config(image="", text="")

    def _limpiar_panel_info(self) -> None:
        """Restaura el panel de información a su estado inicial."""
        self.lbl_nombre.config(text="—")
        self.lbl_id.config(text="")
        self.lbl_fecha.config(text="")
        self.lbl_estado.config(text="Selecciona un día",
                               fg=COLORES["cargando"])
        self._limpiar_tipos()
        self._limpiar_sprite()

    def _seleccionar_dia_hoy(self) -> None:
        """Selecciona automáticamente el día de hoy al abrir la app."""
        if self.hoy.day in self._celdas_dias:
            self._on_dia_click(self.hoy.day)


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = PokeRogueCalendario()
    app.mainloop()
