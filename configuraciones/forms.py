from django import forms
from django.contrib.auth.models import User, Group, Permission
from .models import ConfiguracionSistema, PerfilUsuario, PuntoVenta, Tienda
from .utils import get_tienda_principal

# Clases base para el estilo amarillo
clases_comunes = 'w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-yellow-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors'

class UsuarioForm(forms.ModelForm):
    # Campo extra para elegir el Rol
    rol = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        empty_label="--- Sin Rol ---",
        widget=forms.Select(attrs={'class': clases_comunes})
    )

    # Campo extra para la contraseña
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': clases_comunes, 'placeholder': 'Dejar en blanco para no cambiar'}),
        required=False,
        label="Contraseña"
    )
    tienda = forms.ModelChoiceField(
        queryset=Tienda.objects.filter(activa=True).order_by('nombre'),
        widget=forms.Select(attrs={'class': clases_comunes}),
        label='Tienda / sucursal'
    )
    punto_venta = forms.ModelChoiceField(
        queryset=PuntoVenta.objects.filter(activo=True).select_related('tienda').order_by('tienda__nombre', 'nombre'),
        required=False,
        empty_label='--- Sin punto fijo ---',
        widget=forms.Select(attrs={'class': clases_comunes}),
        label='Punto de venta'
    )
    puede_ver_todas_las_tiendas = forms.BooleanField(
        required=False,
        label='Puede ver todas las tiendas',
        widget=forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-yellow-600 rounded focus:ring-yellow-500'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': clases_comunes}),
            'first_name': forms.TextInput(attrs={'class': clases_comunes}),
            'last_name': forms.TextInput(attrs={'class': clases_comunes}),
            'email': forms.EmailInput(attrs={'class': clases_comunes}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-yellow-600 rounded focus:ring-yellow-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si es un usuario nuevo, la contraseña es obligatoria
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['password'].widget.attrs['placeholder'] = 'Contraseña obligatoria'

        tienda_principal = get_tienda_principal()
        self.fields['tienda'].initial = tienda_principal
        if self.instance.pk:
            perfil = getattr(self.instance, 'perfil', None)
            if perfil:
                self.fields['tienda'].initial = perfil.tienda
                self.fields['punto_venta'].initial = perfil.punto_venta
                self.fields['puede_ver_todas_las_tiendas'].initial = perfil.puede_ver_todas_las_tiendas

    def clean(self):
        cleaned_data = super().clean()
        tienda = cleaned_data.get('tienda')
        punto_venta = cleaned_data.get('punto_venta')
        if tienda and punto_venta and punto_venta.tienda_id != tienda.id:
            self.add_error('punto_venta', 'El punto de venta debe pertenecer a la tienda seleccionada.')
        return cleaned_data

    def save(self, commit=True):
        # Guardamos el usuario pero pausamos el envío a la base de datos
        user = super().save(commit=False)

        # Encriptamos la contraseña si se escribió una
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)

        if commit:
            user.save()
            # Asignamos el Grupo (Rol)
            rol = self.cleaned_data.get('rol')
            user.groups.clear() # Limpiamos roles anteriores
            if rol:
                user.groups.add(rol)
            tienda = self.cleaned_data.get('tienda') or get_tienda_principal()
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user, defaults={'tienda': tienda})
            perfil.tienda = tienda
            perfil.punto_venta = self.cleaned_data.get('punto_venta')
            perfil.puede_ver_todas_las_tiendas = self.cleaned_data.get('puede_ver_todas_las_tiendas')
            perfil.save()
        return user


class TiendaForm(forms.ModelForm):
    class Meta:
        model = Tienda
        fields = ['nombre', 'codigo', 'direccion', 'telefono', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. Sucursal Centro'}),
            'codigo': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. CENTRO'}),
            'direccion': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Dirección de la sucursal'}),
            'telefono': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Teléfono'}),
            'activa': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-yellow-600 rounded focus:ring-yellow-500'}),
        }


class PuntoVentaForm(forms.ModelForm):
    class Meta:
        model = PuntoVenta
        fields = ['tienda', 'nombre', 'codigo', 'activo']
        widgets = {
            'tienda': forms.Select(attrs={'class': clases_comunes}),
            'nombre': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. Caja 1'}),
            'codigo': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. CAJA-1'}),
            'activo': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-yellow-600 rounded focus:ring-yellow-500'}),
        }

class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = ['nombre_negocio', 'ubicacion', 'telefono']
        widgets = {
            'nombre_negocio': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. Abarrotes Doña Mary'}),
            'ubicacion': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. Av. Siempre Viva 123, Col. Centro'}),
            'telefono': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Ej. 55-1234-5678'}),
        }
        labels = {
            'nombre_negocio': 'Nombre de la Tienda / Local',
            'ubicacion': 'Dirección Completa',
            'telefono': 'Teléfono de Contacto',
        }

class RolForm(forms.ModelForm):
    permisos = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(content_type__app_label__in=['ventas', 'inventario', 'configuraciones', 'auth']).order_by('content_type__app_label', 'name'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'w-4 h-4 text-yellow-500 bg-gray-100 border-gray-300 rounded focus:ring-yellow-500 dark:bg-gray-700 dark:border-gray-600'}),
        required=False,
        label="Permisos Asignados"
    )

    class Meta:
        model = Group
        fields = ['name']
        labels = {'name': 'Nombre del Rol (Ej. Supervisor)'}
        widgets = {
            'name': forms.TextInput(attrs={'class': clases_comunes, 'placeholder': 'Nombre del Rol'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nombres_permisos = ['acceder_ventas', 'acceder_inventario', 'acceder_configuraciones']
        self.fields['permisos'].queryset = Permission.objects.filter(codename__in=nombres_permisos).order_by('name')

        if self.instance.pk:
            self.fields['permisos'].initial = self.instance.permissions.all()

    def save(self, commit=True):
        grupo = super().save(commit)
        if commit:
            grupo.permissions.set(self.cleaned_data['permisos'])
        return grupo
