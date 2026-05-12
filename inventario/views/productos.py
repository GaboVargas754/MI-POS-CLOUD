from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from inventario.models import Categoria, Producto
from inventario.forms import ProductoForm
from core.utils import get_config_context, get_querystring_without_page

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def lista_inventario(request):
    query = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    stock = request.GET.get('stock', '').strip()
    productos_list = Producto.objects.select_related('categoria', 'precios').all().order_by('nombre')

    if query:
        productos_list = productos_list.filter(
            Q(nombre__icontains=query)
            | Q(codigo_barras__icontains=query)
            | Q(categoria__nombre__icontains=query)
        )

    if categoria_id:
        productos_list = productos_list.filter(categoria_id=categoria_id)

    if stock == 'con_stock':
        productos_list = productos_list.filter(stock__gt=0)
    elif stock == 'bajo':
        productos_list = productos_list.filter(stock__gt=0, stock__lte=5)
    elif stock == 'agotado':
        productos_list = productos_list.filter(stock__lte=0)

    per_page = request.GET.get('per_page', 10)

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(productos_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventario/productos/lista.html', {
        **get_config_context('Inventario', 'border-purple-600'),
        'page_obj': page_obj,
        'per_page': per_page,
        'query': query,
        'categoria_id': categoria_id,
        'stock': stock,
        'categorias': Categoria.objects.all().order_by('nombre'),
        'querystring': get_querystring_without_page(request),
    })

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
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
