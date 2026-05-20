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
            ("acceder_restaurante", "Módulo de Restaurante: Comandas y cocina"),
            ("acceder_configuraciones", "Módulo de Sistema: Usuarios, Roles y Preferencias"),
            ("operar_pos", "Ventas: Operar POS y cobrar"),
            ("abrir_cerrar_caja", "Ventas: Abrir y cerrar caja"),
            ("cancelar_ventas", "Ventas: Cancelar tickets"),
            ("ver_historial_ventas", "Ventas: Ver historial y reimprimir tickets"),
            ("ver_estadisticas", "Ventas: Ver estadísticas"),
            ("ver_turnos", "Ventas: Ver turnos y cortes"),
            ("ver_inventario", "Inventario: Ver productos y movimientos"),
            ("editar_productos", "Inventario: Crear y editar productos/categorías"),
            ("ajustar_stock", "Inventario: Ajustar stock y registrar entradas"),
            ("editar_precios", "Inventario: Editar precios"),
            ("importar_exportar_inventario", "Inventario: Importar y exportar catálogo"),
            ("imprimir_etiquetas", "Inventario: Imprimir etiquetas"),
            ("operar_restaurante", "Restaurante: Abrir comandas, enviar a cocina y cobrar"),
            ("operar_kds", "Restaurante: Operar pantalla de cocina"),
            ("configurar_restaurante", "Restaurante: Configurar mesas y estaciones"),
            ("gestionar_usuarios", "Sistema: Gestionar usuarios"),
            ("gestionar_roles", "Sistema: Gestionar roles"),
            ("gestionar_tiendas", "Sistema: Gestionar tiendas y cajas"),
            ("editar_preferencias", "Sistema: Editar preferencias"),
        ]
