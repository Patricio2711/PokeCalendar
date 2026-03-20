import flet as ft
import calendar
from datetime import date, datetime, timezone
import os
import sys

# Importar lógica (asegurarse de que estemos en el dir correcto)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gacha import obtener_legendario_del_dia, obtener_nombre_especie

# Colores y estilo
COLOR_FONDO = "#1e1e24"
COLOR_PRIMARIO = "#e23636"
COLOR_SECUNDARIO = "#4f5b66"
COLOR_TEXTO = "#ffffff"
COLOR_DIA = "#2b2b36"
COLOR_HOY = "#ffcc00"

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def main(page: ft.Page):
    page.title = "PokéRogue Calendar"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = COLOR_FONDO
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.window_width = 400
    page.window_height = 800

    # Estado
    fecha_actual = date.today()
    mes_view = fecha_actual.month
    ano_view = fecha_actual.year
    fecha_seleccionada = fecha_actual

    # Widgets de UI
    lbl_mes_ano = ft.Text(size=24, weight=ft.FontWeight.BOLD, color=COLOR_PRIMARIO)
    
    # Pokemon Display
    lbl_pokemon_name = ft.Text("Selecciona un día", size=32, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO)
    img_pokemon = ft.Image(src=None, width=200, height=200, fit="contain")
    
    grid_dias = ft.GridView(
        expand=1,
        runs_count=7,
        max_extent=50,
        child_aspect_ratio=1.0,
        spacing=5,
        run_spacing=5,
    )

    def actualizar_info_pokemon(dt: date):
        # Convertir a datetime UTC
        dt_utc = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
        species_id = obtener_legendario_del_dia(dt_utc)
        nombre = obtener_nombre_especie(species_id)
        
        lbl_pokemon_name.value = nombre
        
        # Buscar el sprite local
        ruta_sprites = os.path.join(get_base_path(), "sprites")
        sprite_path = os.path.join(ruta_sprites, f"{species_id}.png")
        
        if os.path.exists(sprite_path):
            img_pokemon.src = sprite_path
        else:
            img_pokemon.src = None # Fallback si no está cacheado
            
        page.update()

    def on_dia_click(e):
        nonlocal fecha_seleccionada
        dia = e.control.data
        if dia > 0:
            fecha_seleccionada = date(ano_view, mes_view, dia)
            actualizar_info_pokemon(fecha_seleccionada)
            render_calendario()

    def render_calendario():
        lbl_mes_ano.value = f"{calendar.month_name[mes_view].capitalize()} {ano_view}"
        grid_dias.controls.clear()
        
        cal = calendar.monthcalendar(ano_view, mes_view)
        
        # Días de la semana
        for index, day_name in enumerate(["L", "M", "X", "J", "V", "S", "D"]):
             color = COLOR_PRIMARIO if index >= 5 else COLOR_SECUNDARIO
             grid_dias.controls.append(
                 ft.Container(
                     content=ft.Text(day_name, size=16, weight=ft.FontWeight.BOLD, color=color, text_align=ft.TextAlign.CENTER),
                     alignment=ft.Alignment(0, 0)
                 )
             )

        for semana in cal:
            for dia in semana:
                if dia == 0:
                    grid_dias.controls.append(ft.Container())
                else:
                    is_selected = (fecha_seleccionada.day == dia and fecha_seleccionada.month == mes_view and fecha_seleccionada.year == ano_view)
                    es_hoy = (dia == fecha_actual.day and mes_view == fecha_actual.month and ano_view == fecha_actual.year)
                    
                    bg_color = COLOR_PRIMARIO if is_selected else (COLOR_HOY if es_hoy else COLOR_DIA)
                    txt_color = COLOR_TEXTO if not es_hoy or is_selected else "#000000"
                    
                    btn = ft.Container(
                        content=ft.Text(str(dia), size=16, color=txt_color, weight=ft.FontWeight.BOLD if es_hoy or is_selected else ft.FontWeight.NORMAL),
                        alignment=ft.Alignment(0, 0),
                        bgcolor=bg_color,
                        border_radius=10,
                        data=dia,
                        on_click=on_dia_click,
                        ink=True
                    )
                    grid_dias.controls.append(btn)
        
        page.update()

    def mes_anterior(e):
        nonlocal mes_view, ano_view
        if mes_view == 1:
            mes_view = 12
            ano_view -= 1
        else:
            mes_view -= 1
        render_calendario()

    def mes_siguiente(e):
        nonlocal mes_view, ano_view
        if mes_view == 12:
            mes_view = 1
            ano_view += 1
        else:
            mes_view += 1
        render_calendario()

    # Contenedor superior para el Pokemon
    card_pokemon = ft.Container(
        content=ft.Column(
            controls=[
                img_pokemon,
                lbl_pokemon_name,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=COLOR_DIA,
        border_radius=20,
        padding=20,
        width=360,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#33000000")
    )

    # Navegación
    nav_mes = ft.Row(
        controls=[
            ft.IconButton(ft.Icons.ARROW_BACK_IOS, on_click=mes_anterior, icon_color=COLOR_TEXTO),
            lbl_mes_ano,
            ft.IconButton(ft.Icons.ARROW_FORWARD_IOS, on_click=mes_siguiente, icon_color=COLOR_TEXTO),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    page.add(
        card_pokemon,
        ft.Divider(height=20, color="transparent"),
        nav_mes,
        ft.Divider(height=10, color="transparent"),
        grid_dias
    )
    
    # Render inicial
    actualizar_info_pokemon(fecha_seleccionada)
    render_calendario()

if __name__ == "__main__":
    ft.app(main)
