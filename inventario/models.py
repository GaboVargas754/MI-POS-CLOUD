from django.db import models
from django.db import transaction
from django.core.exceptions import ValidationError

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    codigo_barras = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='productos')
    stock = models.IntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(stock__gte=0), name='producto_stock_no_negativo'),
            models.CheckConstraint(condition=models.Q(stock_minimo__gte=0), name='producto_stock_minimo_no_negativo'),
        ]

    def clean(self):
        if self.codigo_barras:
            self.codigo_barras = self.codigo_barras.strip()
        if self.nombre:
            self.nombre = self.nombre.strip()

        if self.stock < 0:
            raise ValidationError({'stock': 'El stock no puede ser negativo.'})
        if self.stock_minimo < 0:
            raise ValidationError({'stock_minimo': 'El stock mínimo no puede ser negativo.'})

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock})"

class PrecioProducto(models.Model):
    # Relación uno a uno: cada producto tiene un registro de precio
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name='precios')
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    margen_ganancia = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    fecha_ultimo_cambio = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.margen_ganancia = self.precio - self.costo
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Precios de {self.producto.nombre}"


class HistorialPrecio(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='historial_precios')
    tienda = models.ForeignKey('configuraciones.Tienda', on_delete=models.SET_NULL, null=True, blank=True)
    costo_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    costo_nuevo = models.DecimalField(max_digits=10, decimal_places=2)
    precio_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_nuevo = models.DecimalField(max_digits=10, decimal_places=2)
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    motivo = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"Precio {self.producto.nombre}: ${self.precio_nuevo}"


class MovimientoInventario(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        VENTA = 'VENTA', 'Venta'
        CANCELACION = 'CANCELACION', 'Cancelación'
        AJUSTE = 'AJUSTE', 'Ajuste manual'

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    tienda = models.ForeignKey('configuraciones.Tienda', on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    cantidad = models.IntegerField()
    stock_antes = models.IntegerField()
    stock_despues = models.IntegerField()
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    venta = models.ForeignKey('ventas.Venta', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_inventario')
    motivo = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']

    @classmethod
    def registrar(cls, *, producto, tipo, cantidad, stock_antes, stock_despues, usuario=None, venta=None, tienda=None, motivo=''):
        movimiento = cls.objects.create(
            producto=producto,
            tienda=tienda,
            tipo=tipo,
            cantidad=cantidad,
            stock_antes=stock_antes,
            stock_despues=stock_despues,
            usuario=usuario,
            venta=venta,
            motivo=motivo,
        )
        producto.stock = stock_despues
        payload = {
            'producto_id': producto.id,
            'producto': producto.nombre,
            'codigo_barras': producto.codigo_barras,
            'stock': stock_despues,
            'stock_minimo': producto.stock_minimo,
            'tipo': tipo,
            'cantidad': cantidad,
            'movimiento_id': movimiento.id,
        }
        transaction.on_commit(lambda payload=payload: _emitir_eventos_inventario(payload, stock_antes))
        return movimiento

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.nombre} ({self.cantidad:+d})"


def _emitir_eventos_inventario(payload, stock_antes):
    from core import notifications

    notifications.emitir_notificacion_todas_tiendas('inventario.movimiento', payload)

    stock = payload['stock']
    stock_minimo = payload['stock_minimo']
    if stock <= 0 and stock_antes > 0:
        notifications.emitir_notificacion_todas_tiendas('inventario.agotado', {
            **payload,
            'titulo': 'Producto agotado',
            'mensaje': f"{payload['producto']} se quedó sin stock.",
            'nivel': 'danger',
        })
    elif 0 < stock <= stock_minimo and stock_antes > stock_minimo:
        notifications.emitir_notificacion_todas_tiendas('inventario.stock_bajo', {
            **payload,
            'titulo': 'Stock bajo',
            'mensaje': f"{payload['producto']} queda en {stock} unidades.",
            'nivel': 'warning',
        })
