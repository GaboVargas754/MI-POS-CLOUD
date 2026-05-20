from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator
from .forms import ConfiguracionForm, MesaForm, PuntoVentaForm, RolForm, TiendaForm, UsuarioForm
from .models import ConfiguracionSistema, PuntoVenta, Tienda
from .utils import get_perfil_usuario
from core.permissions import any_permission_required
from core.utils import get_config_context
from restaurante.models import Mesa

GESTIONAR_USUARIOS_PERMISSION = 'configuraciones.gestionar_usuarios'
GESTIONAR_ROLES_PERMISSION = 'configuraciones.gestionar_roles'
GESTIONAR_TIENDAS_PERMISSION = 'configuraciones.gestionar_tiendas'
EDITAR_PREFERENCIAS_PERMISSION = 'configuraciones.editar_preferencias'
CONFIGURAR_RESTAURANTE_PERMISSION = 'configuraciones.configurar_restaurante'
SISTEMA_PERMISSIONS = [
    GESTIONAR_USUARIOS_PERMISSION,
    GESTIONAR_ROLES_PERMISSION,
    GESTIONAR_TIENDAS_PERMISSION,
    EDITAR_PREFERENCIAS_PERMISSION,
    CONFIGURAR_RESTAURANTE_PERMISSION,
]

@login_required
@any_permission_required(SISTEMA_PERMISSIONS, login_url='portal_principal')
def dashboard_configuracion(request):
    return render(request, 'configuraciones/dashboard.html', get_config_context('Sistema', 'border-yellow-500'))

@login_required
@permission_required(GESTIONAR_USUARIOS_PERMISSION, login_url='portal_principal')
def lista_usuarios(request):
    usuarios_list = User.objects.select_related('perfil__tienda', 'perfil__punto_venta').all().order_by('username')
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(usuarios_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    for usuario in page_obj:
        get_perfil_usuario(usuario)

    return render(request, 'configuraciones/usuarios/lista.html', {
        **get_config_context('Sistema', 'border-yellow-500'),
        'page_obj': page_obj,
        'per_page': per_page,
    })

@login_required
@permission_required(GESTIONAR_USUARIOS_PERMISSION, login_url='portal_principal')
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
@permission_required(EDITAR_PREFERENCIAS_PERMISSION, login_url='portal_principal')
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
@permission_required(GESTIONAR_ROLES_PERMISSION, login_url='portal_principal')
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
        **get_config_context('Sistema', 'border-yellow-500'),
        'page_obj': page_obj,
        'per_page': per_page,
    })

@login_required
@permission_required(GESTIONAR_ROLES_PERMISSION, login_url='portal_principal')
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


@login_required
@permission_required(GESTIONAR_TIENDAS_PERMISSION, login_url='portal_principal')
def lista_tiendas(request):
    tiendas_list = Tienda.objects.prefetch_related('puntos_venta').order_by('nombre')
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(tiendas_list, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'configuraciones/tiendas/lista.html', {
        **get_config_context('Sistema', 'border-yellow-500'),
        'page_obj': page_obj,
        'per_page': per_page,
    })


@login_required
@permission_required(GESTIONAR_TIENDAS_PERMISSION, login_url='portal_principal')
def editar_tienda(request, pk=None):
    tienda = get_object_or_404(Tienda, pk=pk) if pk else None
    form = TiendaForm(request.POST or None, instance=tienda)

    if request.method == 'POST' and form.is_valid():
        tienda = form.save()
        PuntoVenta.objects.get_or_create(
            tienda=tienda,
            codigo='CAJA-1',
            defaults={'nombre': 'Caja 1', 'activo': True},
        )
        return redirect('lista_tiendas')

    return render(request, 'configuraciones/tiendas/formulario_tienda.html', {
        'form': form,
        'titulo': 'Editar Tienda' if tienda else 'Nueva Tienda',
        'is_instance': tienda is not None,
    })


@login_required
@permission_required(GESTIONAR_TIENDAS_PERMISSION, login_url='portal_principal')
def editar_punto_venta(request, pk=None):
    punto = get_object_or_404(PuntoVenta, pk=pk) if pk else None
    form = PuntoVentaForm(request.POST or None, instance=punto)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('lista_tiendas')

    return render(request, 'configuraciones/tiendas/formulario_punto_venta.html', {
        'form': form,
        'titulo': 'Editar Punto de Venta' if punto else 'Nuevo Punto de Venta',
        'is_instance': punto is not None,
    })


@login_required
@permission_required(CONFIGURAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
def lista_mesas(request):
    mesas_list = Mesa.objects.all().order_by('zona', 'nombre')
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(mesas_list, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'configuraciones/mesas/lista.html', {
        **get_config_context('Sistema', 'border-yellow-500'),
        'page_obj': page_obj,
        'per_page': per_page,
    })


@login_required
@permission_required(CONFIGURAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
def editar_mesa(request, pk=None):
    mesa = get_object_or_404(Mesa, pk=pk) if pk else None
    form = MesaForm(request.POST or None, instance=mesa)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('lista_mesas')

    return render(request, 'configuraciones/mesas/formulario_mesa.html', {
        'form': form,
        'titulo': 'Editar Mesa' if mesa else 'Nueva Mesa',
        'is_instance': mesa is not None,
    })
