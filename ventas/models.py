from django.db import models
from inventario.models import Producto
from django.contrib.auth.models import User

class SesionCaja(models.Model):
    cajero = models.ForeignKey(User, on_delete=models.PROTECT)
    tienda = models.ForeignKey('configuraciones.Tienda', on_delete=models.PROTECT, null=True, blank=True)
    punto_venta = models.ForeignKey('configuraciones.PuntoVenta', on_delete=models.SET_NULL, null=True, blank=True)
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    fondo_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    efectivo_cierre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estado = models.BooleanField(default=True)

    def __str__(self):
        estado_str = "Abierta" if self.estado else "Cerrada"
        return f"Turno {self.id} - {self.cajero.username} ({estado_str})"


class Venta(models.Model):
    METODOS_PAGO = [
        ('EFE', 'Efectivo'),
        ('TAR', 'Tarjeta'),
        ('TRA', 'Transferencia'),
        ('MIX', 'Mixto'),
    ]
    ESTADOS = [
        ('ACTIVA', 'Activa'),
        ('CANCELADA', 'Cancelada'),
    ]
    sesion = models.ForeignKey(SesionCaja, on_delete=models.SET_NULL, null=True, blank=True)
    tienda = models.ForeignKey('configuraciones.Tienda', on_delete=models.PROTECT, null=True, blank=True)

    fecha = models.DateTimeField(auto_now_add=True)
    cajero = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    propina = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    porcentaje_propina = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    metodo_pago = models.CharField(max_length=3, choices=METODOS_PAGO, default='EFE')
    pago_recibido = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cambio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estado = models.CharField(max_length=12, choices=ESTADOS, default='ACTIVA')
    motivo_cancelacion = models.TextField(blank=True, null=True)
    fecha_cancelacion = models.DateTimeField(blank=True, null=True)
    cancelado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas_canceladas')

    def __str__(self):
        return f"Ticket #{self.id} - {self.fecha.strftime('%d/%m/%Y')} - ${self.total}"


class PagoVenta(models.Model):
    METODOS_PAGO = [
        ('EFE', 'Efectivo'),
        ('TAR', 'Tarjeta'),
        ('TRA', 'Transferencia'),
    ]
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos')
    metodo_pago = models.CharField(max_length=3, choices=METODOS_PAGO)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.get_metodo_pago_display()} - ${self.monto}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"
