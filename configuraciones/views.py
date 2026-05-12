from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator
from .forms import UsuarioForm, ConfiguracionForm, RolForm
from .models import ConfiguracionSistema
from core.utils import get_config_context

@login_required
@permission_required('configuraciones.acceder_configuraciones', login_url='portal_principal')
def dashboard_configuracion(request):
    return render(request, 'configuraciones/dashboard.html', get_config_context('Panel de Control', 'border-yellow-500'))

@login_required
@permission_required('configuraciones.acceder_configuraciones', login_url='portal_principal')
def lista_usuarios(request):
    usuarios_list = User.objects.all().order_by('username')
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(usuarios_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'configuraciones/usuarios/lista.html', {
        **get_config_context('Gestión de Usuarios', 'border-yellow-500'),
        'page_obj': page_obj,
        'per_page': per_page,
    })

@login_required
@permission_required('configuraciones.acceder_configuraciones', login_url='portal_principal')
def editar_usuario(request, pk=None):
    if pk:
        usuario = get_object_or_404(User, pk=pk)
        titulo = "Editar Usuario"
        rol_actual = usuario.groups.first()
        form = UsuarioForm(request.POST or None, instance=usuario, initial={'rol': rol_actual})
    else:
        usuario = None
        titulo = "Nuevo Usuario"
        form = UsuarioForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('lista_usuarios')

    return render(request, 'configuraciones/usuarios/formulario.html', {
        'form': form,
        'is_instance': usuario is not None,
        'titulo': titulo
    })

@login_required
@permission_required('configuraciones.acceder_configuraciones', login_url='portal_principal')
def ajustes_sistema(request):
    config, created = ConfiguracionSistema.objects.get_or_create(id=1)

    if request.method == 'POST':
        form = ConfiguracionForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            return redirect('config_dashboard')
    else:
        form = ConfiguracionForm(instance=config)

    return render(request, 'configuraciones/formulario_ajustes.html', {
        'form': form,
        'titulo': "Preferencias del Sistema",
        'is_instance': True
    })

@login_required
@permission_required('configuraciones.acceder_configuraciones', login_url='portal_principal')
def lista_roles(request):
    roles_list = Group.objects.all().order_by('name')
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(roles_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'configuraciones/roles/lista.html', {
        **get_config_context('Gestión de Roles', 'border-orange-500'),
        'page_obj': page_obj,
        'per_page': per_page,
    })

@login_required
@permission_required('configuraciones.acceder_configuraciones', login_url='portal_principal')
def editar_rol(request, pk=None):
    if pk:
        rol = get_object_or_404(Group, pk=pk)
        titulo = "Editar Rol"
    else:
        rol = None
        titulo = "Nuevo Rol"

    if request.method == 'POST':
        form = RolForm(request.POST, instance=rol)
        if form.is_valid():
            form.save()
            return redirect('lista_roles')
    else:
        form = RolForm(instance=rol)

    return render(request, 'configuraciones/roles/formulario_rol.html', {
        'form': form,
        'titulo': titulo,
        'is_instance': rol is not None
    })
