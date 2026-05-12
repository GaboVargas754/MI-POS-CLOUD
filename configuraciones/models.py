from django.db import models
from django.conf import settings


class Tienda(models.Model):
    nombre = models.CharField(max_length=120)
    codigo = models.CharField(max_length=30, unique=True)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class PuntoVenta(models.Model):
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='puntos_venta')
    nombre = models.CharField(max_length=80)
    codigo = models.CharField(max_length=30)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['tienda__nombre', 'nombre']
        constraints = [
            models.UniqueConstraint(fields=['tienda', 'codigo'], name='punto_venta_codigo_unico_por_tienda'),
        ]

    def __str__(self):
        return f"{self.tienda.nombre} - {self.nombre}"


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    tienda = models.ForeignKey(Tienda, on_delete=models.PROTECT, related_name='usuarios')
    punto_venta = models.ForeignKey(PuntoVenta, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios')
    puede_ver_todas_las_tiendas = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.usuario.username} - {self.tienda.nombre}"

class ConfiguracionSistema(models.Model):
    nombre_negocio = models.CharField(max_length=100, default="Mi Negocio")
    ubicacion = models.CharField(max_length=255, blank=True, null=True, help_text="Dirección que aparecerá en el ticket")
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Configuración: {self.nombre_negocio}"

    class Meta:
        verbose_name = "Configuración del Sistema"
        # Mantenemos los permisos que creamos en el paso anterior
        permissions = [
            ("acceder_ventas", "Módulo de Ventas: Acceso al Punto de Venta y Cobro"),
            ("acceder_inventario", "Módulo de Inventario: Gestión de Productos y Categorías"),
            ("acceder_configuraciones", "Módulo de Sistema: Usuarios, Roles y Preferencias"),
        ]
