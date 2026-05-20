from django.contrib import admin

from restaurante.models import ConfiguracionRestaurante, EstacionPreparacion, Mesa, Pedido, PedidoEvento, PedidoItem, ProductoPreparacion


class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 0
    readonly_fields = ['creado_en', 'actualizado_en', 'enviado_en', 'cancelado_en']


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'tipo', 'nombre_display', 'estado', 'mesero', 'creado_en', 'actualizado_en']
    list_filter = ['tipo', 'estado', 'creado_en']
    search_fields = ['referencia', 'mesa__nombre', 'mesero__username']
    inlines = [PedidoItemInline]


admin.site.register(ConfiguracionRestaurante)
admin.site.register(EstacionPreparacion)
admin.site.register(Mesa)
admin.site.register(ProductoPreparacion)
admin.site.register(PedidoEvento)
