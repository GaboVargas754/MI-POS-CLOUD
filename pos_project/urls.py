from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('core.urls')),

    path('ventas/', include('ventas.urls')),

    path('inventario/', include('inventario.urls')),
    path('configuraciones/', include('configuraciones.urls')),
]
