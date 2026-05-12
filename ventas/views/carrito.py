from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from inventario.models import Producto
from ventas.models import SesionCaja

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


def _render_carrito_con_resultado(request, carrito, resultado, **extra_context):
    response = _render_carrito(request, carrito, **extra_context)
    response['X-Carrito-Resultado'] = resultado
    return response


def _respuesta_si_no_hay_turno(request, carrito):
    if SesionCaja.objects.filter(cajero=request.user, estado=True).exists():
        return None

    return _render_carrito_con_resultado(
        request,
        carrito,
        'sin_turno',
        error_stock='Abre caja antes de modificar el carrito.',
    )


def _agregar_producto_a_carrito(carrito, producto):
    producto_id_str = str(producto.id)
    cantidad_actual = carrito.get(producto_id_str, {}).get('cantidad', 0)

    if producto.stock <= 0 or cantidad_actual >= producto.stock:
        return 'stock', f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}"

    if not hasattr(producto, 'precios'):
        return 'sin_precio', f"{producto.nombre} no tiene precio asignado."

    if producto_id_str in carrito:
        carrito[producto_id_str]['cantidad'] += 1
    else:
        carrito[producto_id_str] = {
            'nombre': producto.nombre,
            'precio': f'{producto.precios.precio:.2f}',
            'cantidad': 1,
        }

    return 'agregado', None


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def agregar_al_carrito(request, producto_id):
    carrito = request.session.get('carrito', {})
    respuesta_sin_turno = _respuesta_si_no_hay_turno(request, carrito)
    if respuesta_sin_turno is not None:
        return respuesta_sin_turno

    producto = get_object_or_404(
        Producto.objects.select_related('precios'),
        id=producto_id,
    )
    resultado, error = _agregar_producto_a_carrito(carrito, producto)

    if error:
        return _render_carrito_con_resultado(
            request,
            carrito,
            resultado,
            error_stock=error,
        )

    return _render_carrito_con_resultado(request, carrito, resultado)


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def agregar_por_codigo(request):
    codigo_barras = request.POST.get('codigo_barras', '').strip()
    carrito = request.session.get('carrito', {})
    respuesta_sin_turno = _respuesta_si_no_hay_turno(request, carrito)
    if respuesta_sin_turno is not None:
        return respuesta_sin_turno

    producto = Producto.objects.select_related('precios').filter(codigo_barras=codigo_barras).first()
    if not producto:
        return _render_carrito_con_resultado(request, carrito, 'no_encontrado')

    resultado, error = _agregar_producto_a_carrito(carrito, producto)
    if error:
        return _render_carrito_con_resultado(request, carrito, resultado, error_stock=error)

    return _render_carrito_con_resultado(request, carrito, resultado)


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def vaciar_carrito(request):
    carrito = request.session.get('carrito', {})
    respuesta_sin_turno = _respuesta_si_no_hay_turno(request, carrito)
    if respuesta_sin_turno is not None:
        return respuesta_sin_turno

    return _render_carrito(request, {})


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def eliminar_item(request, producto_id):
    carrito = request.session.get('carrito', {})
    respuesta_sin_turno = _respuesta_si_no_hay_turno(request, carrito)
    if respuesta_sin_turno is not None:
        return respuesta_sin_turno

    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        del carrito[producto_id_str]

    return _render_carrito(request, carrito)


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def restar_item(request, producto_id):
    carrito = request.session.get('carrito', {})
    respuesta_sin_turno = _respuesta_si_no_hay_turno(request, carrito)
    if respuesta_sin_turno is not None:
        return respuesta_sin_turno

    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        carrito[producto_id_str]['cantidad'] -= 1

        if carrito[producto_id_str]['cantidad'] <= 0:
            del carrito[producto_id_str]

    return _render_carrito(request, carrito)
