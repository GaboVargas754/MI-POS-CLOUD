from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.views.decorators.http import require_POST
from inventario.models import Producto
from ventas.models import DetalleVenta, SesionCaja, Venta
from configuraciones.models import ConfiguracionSistema
from ventas.views.carrito import VENTAS_PERMISSION, calcular_total_carrito


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
def imprimir_ticket(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVenta.objects.filter(venta=venta)

    config = ConfiguracionSistema.objects.first()
    return render(request, 'ventas/ticket.html', {
        'venta': venta,
        'detalles': detalles,
        'config': config,
    })


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_POST
def procesar_venta(request):
    carrito = request.session.get('carrito', {})

    if not carrito:
        return render(request, 'ventas/partials/carrito.html', {'carrito': {}, 'total': Decimal('0.00')})

    pago_str = request.POST.get('pago_recibido', '0')
    if not pago_str:
        pago_str = '0'

    try:
        pago_recibido = Decimal(pago_str)

        with transaction.atomic():
            sesion = SesionCaja.objects.select_for_update().filter(cajero=request.user, estado=True).first()
            if not sesion:
                raise ValueError("No hay una caja abierta para procesar la venta.")

            nueva_venta = Venta.objects.create(
                cajero=request.user,
                sesion=sesion,
                total=Decimal('0.00'),
            )

            venta_total = Decimal('0.00')

            for producto_id, datos in carrito.items():
                try:
                    producto = Producto.objects.select_for_update().get(id=producto_id)
                except Producto.DoesNotExist:
                    raise ValueError("Uno de los productos del carrito ya no existe.")

                cantidad_vendida = int(datos['cantidad'])
                precio_unitario = Decimal(str(datos['precio']))

                if cantidad_vendida <= 0:
                    raise ValueError(f"Cantidad inválida para {producto.nombre}.")

                if producto.stock < cantidad_vendida:
                    raise ValueError(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}")

                producto.stock -= cantidad_vendida
                producto.save()

                subtotal = precio_unitario * cantidad_vendida
                venta_total += subtotal

                DetalleVenta.objects.create(
                    venta=nueva_venta,
                    producto=producto,
                    cantidad=cantidad_vendida,
                    precio_unitario=precio_unitario,
                )

            if pago_recibido > 0 and pago_recibido < venta_total:
                raise ValueError(f"El monto recibido (${pago_recibido}) es menor al total a pagar (${venta_total}).")

            nueva_venta.total = venta_total
            nueva_venta.pago_recibido = pago_recibido if pago_recibido > 0 else venta_total
            nueva_venta.cambio = nueva_venta.pago_recibido - venta_total
            nueva_venta.save(update_fields=['total', 'pago_recibido', 'cambio'])

            request.session['carrito'] = {}

            return render(request, 'ventas/partials/venta_exitosa.html', {'venta': nueva_venta})

    except (InvalidOperation, ValueError) as e:
        total = calcular_total_carrito(carrito)
        request.session['carrito'] = carrito
        return render(request, 'ventas/partials/carrito.html', {
            'carrito': carrito,
            'total': total,
            'error_stock': str(e),
        })
