from django.contrib import admin
from .models import Venta, DetalleVenta

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1 # Muestra una fila vacía por defecto para agregar productos

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'cajero', 'total', 'metodo_pago')
    list_filter = ('fecha', 'metodo_pago')
    inlines = [DetalleVentaInline] # Aquí incrustamos los detalles dentro de la venta
