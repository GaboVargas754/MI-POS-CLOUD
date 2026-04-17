from django.contrib import admin
from .models import Categoria, Producto, PrecioProducto # <-- Importamos PrecioProducto

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_barras', 'categoria', 'obtener_precio', 'stock')
    search_fields = ('nombre', 'codigo_barras')
    list_filter = ('categoria',)

    def obtener_precio(self, obj):
        if hasattr(obj, 'precios'):
            return f"${obj.precios.precio}"
        return "Sin precio"
    obtener_precio.short_description = 'Precio de Venta'

@admin.register(PrecioProducto)
class PrecioProductoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'costo', 'precio', 'margen_ganancia', 'fecha_ultimo_cambio')
    search_fields = ('producto__nombre',)
