from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from inventario.models import Producto

VENTAS_PERMISSION = 'configuraciones.acceder_ventas'


def calcular_total_carrito(carrito):
    total = Decimal('0.00')

    for item in carrito.values():
        precio = Decimal(str(item.get('precio', '0')))
        cantidad = int(item.get('cantidad', 0))
        subtotal = precio * cantidad

        item['precio'] = f'{precio:.2f}'
        item['subtotal'] = f'{subtotal:.2f}'
        total += subtotal

    return total


def _render_carrito(request, carrito, **extra_context):
    total = calcular_total_carrito(carrito)
    request.session['carrito'] = carrito

    contexto = {
        'carrito': carrito,
        'total': total,
        **extra_context,
    }
    return render(request, 'ventas/partials/carrito.html', contexto)


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('precios'),
        id=producto_id,
        stock__gt=0,
        precios__isnull=False,
    )
    carrito = request.session.get('carrito', {})
    producto_id_str = str(producto_id)
    cantidad_actual = carrito.get(producto_id_str, {}).get('cantidad', 0)

    if cantidad_actual >= producto.stock:
        return _render_carrito(
            request,
            carrito,
            error_stock=f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}",
        )

    if producto_id_str in carrito:
        carrito[producto_id_str]['cantidad'] += 1
    else:
        carrito[producto_id_str] = {
            'nombre': producto.nombre,
            'precio': f'{producto.precios.precio:.2f}',
            'cantidad': 1,
        }

    return _render_carrito(request, carrito)


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def vaciar_carrito(request):
    return _render_carrito(request, {})


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def eliminar_item(request, producto_id):
    carrito = request.session.get('carrito', {})
    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        del carrito[producto_id_str]

    return _render_carrito(request, carrito)


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def restar_item(request, producto_id):
    carrito = request.session.get('carrito', {})
    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        carrito[producto_id_str]['cantidad'] -= 1

        if carrito[producto_id_str]['cantidad'] <= 0:
            del carrito[producto_id_str]

    return _render_carrito(request, carrito)
