from django import forms
from .models import Producto, Categoria, PrecioProducto

clases_comunes = 'w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors'

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['codigo_barras', 'nombre', 'categoria', 'stock']
        widgets = {
            'codigo_barras': forms.TextInput(attrs={'class': clases_comunes, 'id': 'id_codigo_barras', 'placeholder': 'Escanea o escribe el código'}),
            'nombre': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Nombre del producto'}),
            'categoria': forms.Select(attrs={'class': clases_comunes}),
            'stock': forms.NumberInput(attrs={'class': clases_comunes}),
        }

class PrecioProductoForm(forms.ModelForm):
    costo = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': clases_comunes, 'step': '0.50', 'placeholder': '0.00'})
    )

    class Meta:
        model = PrecioProducto
        fields = ['producto', 'costo', 'precio']
        widgets = {
            'producto': forms.Select(attrs={'class': clases_comunes}),
            'precio': forms.NumberInput(attrs={'class': clases_comunes, 'step': '0.50', 'placeholder': 'Ej. 15.50'}),
        }
        labels = {
            'producto': 'Selecciona el Producto',
            'costo': 'Costo de Compra ($) - Opcional',
            'precio': 'Precio de Venta al Público ($)',
        }

    def clean_costo(self):
        costo = self.cleaned_data.get('costo')
        if costo is None:
            return 0
        return costo

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. Lácteos'}),
            'descripcion': forms.Textarea(attrs={'class': clases_comunes, 'rows': 3, 'placeholder': 'Descripción opcional...'}),
        }
