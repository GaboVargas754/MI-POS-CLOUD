from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_configuracion, name='config_dashboard'),

    # Usuarios
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/nuevo/', views.editar_usuario, name='nuevo_usuario'),
    path('usuarios/editar/<int:pk>/', views.editar_usuario, name='editar_usuario'),

    # Tiendas y puntos de venta
    path('tiendas/', views.lista_tiendas, name='lista_tiendas'),
    path('tiendas/nueva/', views.editar_tienda, name='nueva_tienda'),
    path('tiendas/editar/<int:pk>/', views.editar_tienda, name='editar_tienda'),
    path('puntos-venta/nuevo/', views.editar_punto_venta, name='nuevo_punto_venta'),
    path('puntos-venta/editar/<int:pk>/', views.editar_punto_venta, name='editar_punto_venta'),

    # Mesas de restaurante
    path('mesas/', views.lista_mesas, name='lista_mesas'),
    path('mesas/nueva/', views.editar_mesa, name='nueva_mesa'),
    path('mesas/editar/<int:pk>/', views.editar_mesa, name='editar_mesa'),

    # Preferencias
    path('ajustes/', views.ajustes_sistema, name='ajustes_sistema'),

    # Roles y Permisos
    path('roles/', views.lista_roles, name='lista_roles'),
    path('roles/nuevo/', views.editar_rol, name='nuevo_rol'),
    path('roles/editar/<int:pk>/', views.editar_rol, name='editar_rol'),
]
