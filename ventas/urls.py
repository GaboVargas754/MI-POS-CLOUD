from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='ventas/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('', views.pantalla_pos, name='pantalla_pos'),
    path('agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('agregar-codigo/', views.agregar_por_codigo, name='agregar_por_codigo'),
    path('vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    path('eliminar/<int:producto_id>/', views.eliminar_item, name='eliminar_item'),
    path('restar/<int:producto_id>/', views.restar_item, name='restar_item'),
    path('buscar/', views.buscar_productos, name='buscar_productos'),
    path('cobrar/', views.procesar_venta, name='procesar_venta'),
    path('ticket/<int:venta_id>/', views.imprimir_ticket, name='imprimir_ticket'),
    path('ticket/<int:venta_id>/cancelar/', views.cancelar_venta, name='cancelar_venta'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/live/', views.dashboard_live, name='dashboard_live'),
    path('historial/', views.historial_ventas, name='historial_ventas'),
    path('turnos/', views.historial_turnos, name='historial_turnos'),
    path('turnos/<int:sesion_id>/corte/', views.imprimir_corte, name='imprimir_corte'),
    path('abrir-caja/', views.abrir_caja, name='abrir_caja'),
    path('cerrar-caja/', views.cerrar_caja, name='cerrar_caja'),
]
