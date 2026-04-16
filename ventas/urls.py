from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='ventas/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('', views.pantalla_pos, name='pantalla_pos'),
    path('agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    path('eliminar/<int:producto_id>/', views.eliminar_item, name='eliminar_item'),
    path('restar/<int:producto_id>/', views.restar_item, name='restar_item'),
    path('buscar/', views.buscar_productos, name='buscar_productos'),
    path('cobrar/', views.procesar_venta, name='procesar_venta'),
    path('ticket/<int:venta_id>/', views.imprimir_ticket, name='imprimir_ticket'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('abrir-caja/', views.abrir_caja, name='abrir_caja'),
    path('cerrar-caja/', views.cerrar_caja, name='cerrar_caja'),
]
