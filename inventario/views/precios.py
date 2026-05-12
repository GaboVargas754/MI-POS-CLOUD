from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from inventario.models import Producto
from inventario.models import PrecioProducto
from inventario.forms import PrecioProductoForm
from core.utils import get_config_context

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def lista_precios(request):
    precios_list = PrecioProducto.objects.all().select_related('producto').order_by('producto__nombre')

    per_page = request.GET.get('per_page', 10)
    paginator = Paginator(precios_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventario/precios/lista.html', {
        **get_config_context('Gestión de Precios', 'border-purple-600'),
        'page_obj': page_obj,
        'per_page': per_page,
    })

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def editar_precio(request, pk=None):
    precio_obj = get_object_or_404(PrecioProducto, pk=pk) if pk else None
    form = PrecioProductoForm(request.POST or None, instance=precio_obj)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('lista_precios')

    return render(request, 'inventario/precios/formulario.html', {
        'form': form,
        'titulo': "Editar Precios" if pk else "Asignar Precios",
        'is_instance': precio_obj is not None
    })

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
@require_POST
def actualizar_precio_inline(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    nuevo_precio = request.POST.get('precio', 0)
    try:
        nuevo_precio = float(nuevo_precio)
    except ValueError:
        nuevo_precio = 0

    precio_obj, created = PrecioProducto.objects.get_or_create(
        producto=producto,
        defaults={'costo': 0, 'precio': nuevo_precio}
    )

    if not created:
        precio_obj.precio = nuevo_precio
        precio_obj.save()

    return render(request, 'inventario/productos/partials/precio_inline.html', {'p': producto})
