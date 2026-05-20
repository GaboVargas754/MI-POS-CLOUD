from django.contrib import admin
from .models import DetalleVenta, PagoVenta, Venta

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1 # Muestra una fila vacía por defecto para agregar productos


class PagoVentaInline(admin.TabularInline):
    model = PagoVenta
    extra = 0
    readonly_fields = ('creado_en',)

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'cajero', 'subtotal', 'propina', 'total', 'metodo_pago')
    list_filter = ('fecha', 'metodo_pago')
    inlines = [DetalleVentaInline, PagoVentaInline] # Aquí incrustamos los detalles dentro de la venta
