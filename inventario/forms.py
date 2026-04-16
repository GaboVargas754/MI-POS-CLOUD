from django import forms
from .models import Producto, Categoria

clases_comunes = 'w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors'

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['codigo_barras', 'nombre', 'precio', 'stock']
        widgets = {
            'codigo_barras': forms.TextInput(attrs={
                'class': clases_comunes,
                'placeholder': 'Ej. 7501234567890'
            }),
            'nombre': forms.TextInput(attrs={
                'class': clases_comunes,
                'placeholder': 'Nombre del producto'
            }),
            'precio': forms.NumberInput(attrs={
                'class': clases_comunes,
                'step': '0.50'
            }),
            'stock': forms.NumberInput(attrs={
                'class': clases_comunes
            }),
        }

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. Lácteos'}),
            'descripcion': forms.Textarea(attrs={'class': clases_comunes, 'rows': 3, 'placeholder': 'Descripción opcional...'}),
        }
