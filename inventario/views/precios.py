from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from inventario.models import HistorialPrecio, Producto
from inventario.models import PrecioProducto
from inventario.forms import PrecioProductoForm
from configuraciones.utils import get_tienda_actual
from core.utils import get_config_context, get_querystring_without_page

EDITAR_PRECIOS_PERMISSION = 'configuraciones.editar_precios'

@login_required
@permission_required(EDITAR_PRECIOS_PERMISSION, login_url='portal_principal')
def lista_precios(request):
    query = request.GET.get('q', '').strip()
    precios_list = PrecioProducto.objects.all().select_related('producto').order_by('producto__nombre')

    if query:
        precios_list = precios_list.filter(
            Q(producto__nombre__icontains=query) | Q(producto__codigo_barras__icontains=query)
        )

    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10
    paginator = Paginator(precios_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventario/precios/lista.html', {
        **get_config_context('Inventario', 'border-purple-600'),
        'page_obj': page_obj,
        'per_page': per_page,
        'query': query,
        'querystring': get_querystring_without_page(request),
    })

@login_required
@permission_required(EDITAR_PRECIOS_PERMISSION, login_url='portal_principal')
def editar_precio(request, pk=None):
    tienda_actual = get_tienda_actual(request)
    precio_obj = get_object_or_404(PrecioProducto, pk=pk) if pk else None
    form = PrecioProductoForm(request.POST or None, instance=precio_obj)

    if request.method == 'POST' and form.is_valid():
        costo_anterior = precio_obj.costo if precio_obj else None
        precio_anterior = precio_obj.precio if precio_obj else None
        precio_guardado = form.save()
        if costo_anterior != precio_guardado.costo or precio_anterior != precio_guardado.precio:
            HistorialPrecio.objects.create(
                producto=precio_guardado.producto,
                tienda=tienda_actual,
                costo_anterior=costo_anterior,
                costo_nuevo=precio_guardado.costo,
                precio_anterior=precio_anterior,
                precio_nuevo=precio_guardado.precio,
                usuario=request.user,
                motivo='Edición de precios',
            )
        return redirect('lista_precios')

    return render(request, 'inventario/precios/formulario.html', {
        'form': form,
        'titulo': "Editar Precios" if pk else "Asignar Precios",
        'is_instance': precio_obj is not None
    })

@login_required
@permission_required(EDITAR_PRECIOS_PERMISSION, login_url='portal_principal')
@require_POST
def actualizar_precio_inline(request, producto_id):
    tienda_actual = get_tienda_actual(request)
    producto = get_object_or_404(Producto, id=producto_id)

    try:
        nuevo_precio = Decimal(request.POST.get('precio', '0') or '0')
    except InvalidOperation:
        return render(request, 'inventario/productos/partials/precio_inline.html', {
            'p': producto,
            'error_precio': 'Precio inválido.',
        })

    if nuevo_precio < 0:
        return render(request, 'inventario/productos/partials/precio_inline.html', {
            'p': producto,
            'error_precio': 'El precio no puede ser negativo.',
        })

    precio_obj, created = PrecioProducto.objects.get_or_create(
        producto=producto,
        defaults={'costo': Decimal('0.00'), 'precio': nuevo_precio}
    )

    if not created:
        precio_anterior = precio_obj.precio
        costo_anterior = precio_obj.costo
        if precio_anterior == nuevo_precio:
            producto = Producto.objects.select_related('precios').get(id=producto.id)
            return render(request, 'inventario/productos/partials/precio_inline.html', {'p': producto})

        precio_obj.precio = nuevo_precio
        precio_obj.save()
    else:
        precio_anterior = None
        costo_anterior = None

    HistorialPrecio.objects.create(
        producto=producto,
        tienda=tienda_actual,
        costo_anterior=costo_anterior,
        costo_nuevo=precio_obj.costo,
        precio_anterior=precio_anterior,
        precio_nuevo=precio_obj.precio,
        usuario=request.user,
        motivo='Precio inline',
    )

    producto = Producto.objects.select_related('precios').get(id=producto.id)
    return render(request, 'inventario/productos/partials/precio_inline.html', {'p': producto})
