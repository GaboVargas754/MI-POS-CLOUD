from django import forms
from django.contrib.auth.models import User, Group, Permission
from .models import ConfiguracionSistema

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
        return user

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
