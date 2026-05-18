from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='inventario_dashboard'),
    path('live/', views.dashboard_live, name='inventario_dashboard_live'),

    path('productos/', views.lista_inventario, name='lista_inventario'),
    path('productos/live/', views.lista_inventario_live, name='lista_inventario_live'),
    path('productos/nuevo/', views.editar_producto, name='nuevo_producto'),
    path('productos/resolver-codigo/', views.resolver_codigo_producto, name='resolver_codigo_producto'),
    path('productos/entrada-rapida/', views.entrada_rapida, name='entrada_rapida'),
    path('productos/importar-csv/', views.importar_productos_csv, name='importar_productos_csv'),
    path('productos/exportar-csv/', views.exportar_productos_csv, name='exportar_productos_csv'),
    path('productos/etiquetas/', views.imprimir_etiquetas, name='imprimir_etiquetas'),
    path('productos/editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('productos/<int:pk>/ajustar-stock/', views.ajustar_stock, name='ajustar_stock'),
    path('productos/<int:pk>/movimientos/', views.movimientos_producto, name='movimientos_producto'),
    path('productos/<int:pk>/historial-precios/', views.historial_precios_producto, name='historial_precios_producto'),

    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/nueva/', views.editar_categoria, name='nueva_categoria'),
    path('categorias/editar/<int:pk>/', views.editar_categoria, name='editar_categoria'),

    path('precios/', views.lista_precios, name='lista_precios'),
    path('precios/nuevo/', views.editar_precio, name='nuevo_precio'),
    path('precios/editar/<int:pk>/', views.editar_precio, name='editar_precio'),
    path('precios/actualizar-inline/<int:producto_id>/', views.actualizar_precio_inline, name='actualizar_precio_inline'),
]
