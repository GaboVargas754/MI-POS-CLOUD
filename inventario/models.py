from django.db import models

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
