from django.shortcuts import render, get_object_or_404
from django.db import transaction
from ventas.models import Venta, DetalleVenta, Producto
from configuraciones.models import ConfiguracionSistema

def imprimir_ticket(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVenta.objects.filter(venta=venta)

    config = ConfiguracionSistema.objects.first()
    return render(request, 'ventas/ticket.html', {
        'venta': venta,
        'detalles': detalles,
        'config': config,
    })

def procesar_venta(request):
    carrito = request.session.get('carrito', {})

    if not carrito:
        return render(request, 'ventas/partials/carrito.html', {'carrito': {}, 'total': 0})

    pago_str = request.POST.get('pago_recibido', '0')
    if not pago_str:
        pago_str = '0'
    pago_recibido = float(pago_str)

    try:
        with transaction.atomic():
            nueva_venta = Venta.objects.create(
                cajero=request.user if request.user.is_authenticated else None,
                total=0
            )

            venta_total = 0

            for producto_id, datos in carrito.items():
                producto = Producto.objects.select_for_update().get(id=producto_id)
                cantidad_vendida = datos['cantidad']

                if producto.stock < cantidad_vendida:
                    raise ValueError(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}")

                producto.stock -= cantidad_vendida
                producto.save()

                subtotal = float(datos['precio']) * cantidad_vendida
                venta_total += subtotal

                DetalleVenta.objects.create(
                    venta=nueva_venta,
                    producto=producto,
                    cantidad=cantidad_vendida,
                    precio_unitario=datos['precio']
                )

            if pago_recibido > 0 and pago_recibido < venta_total:
                raise ValueError(f"El monto recibido (${pago_recibido}) es menor al total a pagar (${venta_total}).")

            nueva_venta.total = venta_total
            nueva_venta.pago_recibido = pago_recibido if pago_recibido > 0 else venta_total
            nueva_venta.cambio = nueva_venta.pago_recibido - venta_total
            nueva_venta.save()

            request.session['carrito'] = {}

            return render(request, 'ventas/partials/venta_exitosa.html', {'venta': nueva_venta})

    except ValueError as e:
        total = sum(item['precio'] * item['cantidad'] for item in carrito.values())
        return render(request, 'ventas/partials/carrito.html', {
            'carrito': carrito,
            'total': total,
            'error_stock': str(e)
        })
