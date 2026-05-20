from django.urls import reverse

def get_config_context(nav_title, accent_color, nav_items=None):
    if nav_items is None:
        nav_items = [
            {
                'label': 'POS',
                'url': reverse('pantalla_pos'),
                'hover_class': 'hover:bg-green-50 dark:hover:bg-green-900/20 hover:text-green-600 dark:hover:text-green-400',
            },
            {
                'label': 'Estadísticas',
                'url': reverse('dashboard'),
                'hover_class': 'hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 dark:hover:text-blue-400',
            },
            {
                'label': 'Inventario',
                'url': reverse('inventario_dashboard'),
                'hover_class': 'hover:bg-purple-50 dark:hover:bg-purple-900/20 hover:text-purple-600 dark:hover:text-purple-400',
            },
            {
                'label': 'Restaurante',
                'url': reverse('restaurante_dashboard'),
                'hover_class': 'hover:bg-orange-50 dark:hover:bg-orange-900/20 hover:text-orange-600 dark:hover:text-orange-400',
            },
            {
                'label': 'Sistema',
                'url': reverse('config_dashboard'),
                'hover_class': 'hover:bg-yellow-50 dark:hover:bg-yellow-900/20 hover:text-yellow-600 dark:hover:text-yellow-400',
            },
        ]
    return {
        'nav_title': nav_title,
        'accent_color': accent_color,
        'nav_items': nav_items,
        'htmx_enabled': True
    }


def get_querystring_without_page(request):
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()
