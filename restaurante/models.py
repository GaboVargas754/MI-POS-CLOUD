from django.conf import settings
from django.db import models
from django.utils import timezone


class ConfiguracionRestaurante(models.Model):
    permitir_para_llevar = models.BooleanField(default=True)
    usa_estaciones = models.BooleanField(default=False)
    reintegrar_pendiente = models.BooleanField(default=True)
    reintegrar_preparando = models.BooleanField(default=False)
    reintegrar_listo = models.BooleanField(default=False)
    requerir_motivo_cancelacion_enviados = models.BooleanField(default=True)

    def __str__(self):
        return 'Configuración de Restaurante'


class EstacionPreparacion(models.Model):
    nombre = models.CharField(max_length=80)
    codigo = models.CharField(max_length=30, unique=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Mesa(models.Model):
    nombre = models.CharField(max_length=80)
    codigo = models.CharField(max_length=30, unique=True)
    zona = models.CharField(max_length=80, blank=True)
    capacidad = models.PositiveIntegerField(default=4)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['zona', 'nombre']

    def __str__(self):
        return self.nombre


class ProductoPreparacion(models.Model):
    producto = models.OneToOneField('inventario.Producto', on_delete=models.CASCADE, related_name='preparacion')
    estacion = models.ForeignKey(EstacionPreparacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')
    enviar_a_kds = models.BooleanField(default=True)

    def __str__(self):
        return self.producto.nombre


class Pedido(models.Model):
    class Tipo(models.TextChoices):
        MESA = 'MESA', 'Mesa'
        PARA_LLEVAR = 'PARA_LLEVAR', 'Para llevar'

    class Estado(models.TextChoices):
        ABIERTO = 'ABIERTO', 'Abierto'
        EN_COCINA = 'EN_COCINA', 'En cocina'
        LISTO = 'LISTO', 'Listo'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        COBRADO = 'COBRADO', 'Cobrado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    tipo = models.CharField(max_length=14, choices=Tipo.choices, default=Tipo.MESA)
    mesa = models.ForeignKey(Mesa, on_delete=models.PROTECT, null=True, blank=True, related_name='pedidos')
    referencia = models.CharField(max_length=120, blank=True)
    tienda = models.ForeignKey('configuraciones.Tienda', on_delete=models.PROTECT, null=True, blank=True)
    mesero = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_restaurante')
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ABIERTO)
    venta = models.OneToOneField('ventas.Venta', on_delete=models.SET_NULL, null=True, blank=True, related_name='pedido_restaurante')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    enviado_en = models.DateTimeField(null=True, blank=True)
    cobrado_en = models.DateTimeField(null=True, blank=True)
    cancelado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-actualizado_en', '-id']

    def __str__(self):
        return f'Pedido #{self.id} - {self.nombre_display}'

    @property
    def nombre_display(self):
        if self.tipo == self.Tipo.MESA and self.mesa_id:
            return self.mesa.nombre
        return self.referencia or 'Para llevar'

    def total(self):
        return sum(item.subtotal() for item in self.items.exclude(estado=PedidoItem.Estado.CANCELADO))


class PedidoItem(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', 'Borrador'
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PREPARANDO = 'PREPARANDO', 'Preparando'
        LISTO = 'LISTO', 'Listo'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT, related_name='items_restaurante')
    estacion = models.ForeignKey(EstacionPreparacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    nota = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.BORRADOR)
    creado_en = models.DateTimeField(auto_now_add=True)
    enviado_en = models.DateTimeField(null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    cancelado_en = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.TextField(blank=True)
    reintegro_stock = models.BooleanField(default=False)

    class Meta:
        ordering = ['creado_en', 'id']

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre}'

    def subtotal(self):
        return self.cantidad * self.precio_unitario


class PedidoEvento(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='eventos')
    item = models.ForeignKey(PedidoItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='eventos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    evento = models.CharField(max_length=80)
    descripcion = models.TextField(blank=True)
    creado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-creado_en', '-id']

    def __str__(self):
        return self.evento
