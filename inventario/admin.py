from django.contrib import admin
from .models import Categoria, Producto

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # Esto define qué columnas se ven en la tabla principal
    list_display = ('nombre', 'codigo_barras', 'categoria', 'precio', 'stock')
    # Agrega un buscador
    search_fields = ('nombre', 'codigo_barras')
    # Agrega filtros laterales
    list_filter = ('categoria',)
