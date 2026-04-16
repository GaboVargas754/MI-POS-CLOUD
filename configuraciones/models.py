from django.db import models

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
            ("acceder_configuraciones", "Módulo de Configuración: Usuarios, Roles y Ajustes"),
        ]
