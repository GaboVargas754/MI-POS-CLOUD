from django.urls import path

from restaurante import views


urlpatterns = [
    path('', views.dashboard, name='restaurante_dashboard'),
    path('live/', views.dashboard_live, name='restaurante_dashboard_live'),
    path('pedidos/crear/', views.crear_pedido_view, name='restaurante_crear_pedido'),
    path('pedidos/<int:pedido_id>/', views.comanda, name='restaurante_comanda'),
    path('pedidos/<int:pedido_id>/panel/', views.comanda_panel_live, name='restaurante_comanda_panel_live'),
    path('pedidos/<int:pedido_id>/productos/', views.buscar_productos, name='restaurante_buscar_productos'),
    path('pedidos/<int:pedido_id>/items/agregar/', views.agregar_item, name='restaurante_agregar_item'),
    path('pedidos/<int:pedido_id>/items/<int:item_id>/eliminar/', views.eliminar_item, name='restaurante_eliminar_item'),
    path('pedidos/<int:pedido_id>/enviar-cocina/', views.enviar_cocina, name='restaurante_enviar_cocina'),
    path('pedidos/<int:pedido_id>/cobrar/', views.cobrar_pedido_view, name='restaurante_cobrar_pedido'),
    path('kds/', views.kds, name='restaurante_kds'),
    path('kds/live/', views.kds_live, name='restaurante_kds_live'),
    path('kds/items/<int:item_id>/estado/', views.actualizar_item_kds, name='restaurante_actualizar_item_kds'),
]
