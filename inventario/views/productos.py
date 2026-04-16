from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from inventario.models import Producto
from inventario.forms import ProductoForm
from core.utils import get_config_context

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='/configuraciones/portal/')
def lista_inventario(request):
    productos_list = Producto.objects.all().order_by('nombre')
    per_page = request.GET.get('per_page', 10)

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(productos_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventario/productos/lista.html', {
        **get_config_context('Catálogo de Productos', 'border-purple-600'),
        'page_obj': page_obj,
        'per_page': per_page,
    })

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='/configuraciones/portal/')
def editar_producto(request, pk=None):
    if pk:
        producto = get_object_or_404(Producto, pk=pk)
        titulo = "Editar Producto"
    else:
        producto = None
        titulo = "Nuevo Producto"

    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('lista_inventario')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'inventario/productos/formulario.html', {
        'form': form,
        'producto': producto,
        'titulo': titulo,
        'is_instance': producto is not None
    })
