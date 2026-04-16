from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_configuracion, name='config_dashboard'),

    # Usuarios
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/nuevo/', views.editar_usuario, name='nuevo_usuario'),
    path('usuarios/editar/<int:pk>/', views.editar_usuario, name='editar_usuario'),

    # Preferencias
    path('ajustes/', views.ajustes_sistema, name='ajustes_sistema'),

    # Roles y Permisos
    path('roles/', views.lista_roles, name='lista_roles'),
    path('roles/nuevo/', views.editar_rol, name='nuevo_rol'),
    path('roles/editar/<int:pk>/', views.editar_rol, name='editar_rol'),
]
