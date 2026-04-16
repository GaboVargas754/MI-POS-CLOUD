from django.urls import reverse

def get_config_context(nav_title, accent_color, nav_items=None):
    if nav_items is None:
        nav_items = [
            {'label': 'Ventas', 'url': reverse('dashboard'), 'hover_color': 'text-yellow-600', 'hover_color_dark': 'text-yellow-500'},
            {'label': 'Inventario', 'url': reverse('inventario_dashboard'), 'hover_color': 'text-yellow-600', 'hover_color_dark': 'text-yellow-500'},
            {'label': 'Configuración', 'url': reverse('config_dashboard'), 'hover_color': 'text-yellow-600', 'hover_color_dark': 'text-yellow-500'},
        ]
    return {
        'nav_title': nav_title,
        'accent_color': accent_color,
        'nav_items': nav_items,
        'htmx_enabled': True
    }
