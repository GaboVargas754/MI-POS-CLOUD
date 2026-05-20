from django import forms
from decimal import Decimal
from .models import Producto, Categoria, PrecioProducto

clases_comunes = 'w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors'

class ProductoForm(forms.ModelForm):
    costo = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        label='Costo de compra',
        widget=forms.NumberInput(attrs={'class': clases_comunes, 'step': '0.01', 'data-decimal-places': '2', 'placeholder': '0.00'})
    )
    precio = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        label='Precio de venta',
        widget=forms.NumberInput(attrs={'class': clases_comunes, 'step': '0.01', 'data-decimal-places': '2', 'placeholder': '0.00'})
    )

    class Meta:
        model = Producto
        fields = ['codigo_barras', 'nombre', 'categoria', 'stock', 'stock_minimo', 'activo']
        widgets = {
            'codigo_barras': forms.TextInput(attrs={'class': clases_comunes, 'id': 'id_codigo_barras', 'placeholder': 'Escanea o escribe el código'}),
            'nombre': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Nombre del producto'}),
            'categoria': forms.Select(attrs={'class': clases_comunes}),
            'stock': forms.NumberInput(attrs={'class': clases_comunes}),
            'stock_minimo': forms.NumberInput(attrs={'class': clases_comunes}),
            'activo': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500'}),
        }
        labels = {
            'stock_minimo': 'Stock mínimo',
            'activo': 'Producto activo para venta',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(['codigo_barras', 'nombre', 'categoria', 'stock', 'stock_minimo', 'activo', 'costo', 'precio'])

        if self.instance and self.instance.pk:
            try:
                self.fields['costo'].initial = self.instance.precios.costo
                self.fields['precio'].initial = self.instance.precios.precio
            except PrecioProducto.DoesNotExist:
                pass

    def clean_codigo_barras(self):
        return self.cleaned_data['codigo_barras'].strip()

    def clean_nombre(self):
        return self.cleaned_data['nombre'].strip()

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock < 0:
            raise forms.ValidationError('El stock no puede ser negativo.')
        return stock

    def clean_stock_minimo(self):
        stock_minimo = self.cleaned_data['stock_minimo']
        if stock_minimo < 0:
            raise forms.ValidationError('El stock mínimo no puede ser negativo.')
        return stock_minimo

    def clean_costo(self):
        costo = self.cleaned_data.get('costo')
        if costo is None:
            return Decimal('0.00')
        if costo < 0:
            raise forms.ValidationError('El costo no puede ser negativo.')
        return costo

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is not None and precio < 0:
            raise forms.ValidationError('El precio no puede ser negativo.')
        return precio

class PrecioProductoForm(forms.ModelForm):
    costo = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': clases_comunes, 'step': '0.01', 'data-decimal-places': '2', 'placeholder': '0.00'})
    )

    class Meta:
        model = PrecioProducto
        fields = ['producto', 'costo', 'precio']
        widgets = {
            'producto': forms.Select(attrs={'class': clases_comunes}),
            'precio': forms.NumberInput(attrs={'class': clases_comunes, 'step': '0.01', 'data-decimal-places': '2', 'placeholder': 'Ej. 15.50'}),
        }
        labels = {
            'producto': 'Selecciona el Producto',
            'costo': 'Costo de Compra ($) - Opcional',
            'precio': 'Precio de Venta al Público ($)',
        }

    def clean_costo(self):
        costo = self.cleaned_data.get('costo')
        if costo is None:
            return Decimal('0.00')
        if costo < 0:
            raise forms.ValidationError('El costo no puede ser negativo.')
        return costo

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is not None and precio < 0:
            raise forms.ValidationError('El precio no puede ser negativo.')
        return precio


class AjusteStockForm(forms.Form):
    nuevo_stock = forms.IntegerField(
        min_value=0,
        label='Nuevo stock',
        widget=forms.NumberInput(attrs={'class': clases_comunes, 'placeholder': 'Cantidad real en inventario'})
    )
    motivo = forms.CharField(
        label='Motivo del ajuste',
        widget=forms.Textarea(attrs={'class': clases_comunes, 'rows': 3, 'placeholder': 'Ej. Conteo físico, merma, entrada de mercancía...'}),
    )


class EntradaRapidaForm(forms.Form):
    codigo_barras = forms.CharField(
        label='Código de barras',
        widget=forms.TextInput(attrs={'class': clases_comunes, 'id': 'id_entrada_codigo_barras', 'placeholder': 'Escanea o escribe el código'})
    )
    cantidad = forms.IntegerField(
        min_value=1,
        label='Cantidad a recibir',
        widget=forms.NumberInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. 12'})
    )
    motivo = forms.CharField(
        label='Motivo',
        initial='Entrada rápida de mercancía',
        widget=forms.Textarea(attrs={'class': clases_comunes, 'rows': 2, 'placeholder': 'Ej. Entrada de proveedor'}),
    )

    def clean_codigo_barras(self):
        return self.cleaned_data['codigo_barras'].strip()

    def clean_motivo(self):
        return self.cleaned_data['motivo'].strip()


class ImportarProductosForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo CSV',
        widget=forms.FileInput(attrs={'class': clases_comunes, 'accept': '.csv,text/csv'})
    )

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. Lácteos'}),
            'descripcion': forms.Textarea(attrs={'class': clases_comunes, 'rows': 3, 'placeholder': 'Descripción opcional...'}),
        }
