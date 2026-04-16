from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='inventario_dashboard'),

    path('productos/', views.lista_inventario, name='lista_inventario'),
    path('productos/nuevo/', views.editar_producto, name='nuevo_producto'),
    path('productos/editar/<int:pk>/', views.editar_producto, name='editar_producto'),

    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/nueva/', views.editar_categoria, name='nueva_categoria'),
    path('categorias/editar/<int:pk>/', views.editar_categoria, name='editar_categoria'),
]
