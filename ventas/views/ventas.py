from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render, get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from core.notifications import emitir_notificacion_tienda
from core.utils import get_config_context
from core.permissions import any_permission_required
from configuraciones.utils import get_tienda_actual
from inventario.models import MovimientoInventario, Producto
from ventas.models import DetalleVenta, SesionCaja, Venta
from ventas.payments import calcular_desglose_pago, registrar_pagos_venta
from configuraciones.models import ConfiguracionSistema
from ventas.views.carrito import OPERAR_POS_PERMISSION, calcular_total_carrito

CANCELAR_VENTAS_PERMISSION = 'configuraciones.cancelar_ventas'
VER_HISTORIAL_VENTAS_PERMISSION = 'configuraciones.ver_historial_ventas'


@login_required
@any_permission_required([OPERAR_POS_PERMISSION, VER_HISTORIAL_VENTAS_PERMISSION], login_url='portal_principal')
def imprimir_ticket(request, venta_id):
    tienda_actual = get_tienda_actual(request)
    venta = get_object_or_404(Venta.objects.prefetch_related('pagos').filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True)), id=venta_id)
    detalles = DetalleVenta.objects.filter(venta=venta)

    config = ConfiguracionSistema.objects.first()
    return render(request, 'ventas/ticket.html', {
        'venta': venta,
        'detalles': detalles,
        'config': config,
    })


@login_required
@permission_required(CANCELAR_VENTAS_PERMISSION, login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def cancelar_venta(request, venta_id):
    tienda_actual = get_tienda_actual(request)
    venta = get_object_or_404(
        Venta.objects.select_related('cajero', 'sesion').prefetch_related('detalles__producto').filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True)),
        id=venta_id,
    )

    if venta.estado == 'CANCELADA':
        messages.warning(request, f'El ticket #{venta.id} ya estaba cancelado.')
        return redirect('historial_ventas')

    if request.method == 'POST':
        motivo = request.POST.get('motivo_cancelacion', '').strip()
        if not motivo:
            return render(request, 'ventas/cancelar_venta.html', {
                **get_config_context('Estadísticas', 'border-blue-600'),
                'venta': venta,
                'detalles': venta.detalles.all(),
                'error': 'Captura el motivo de cancelación.',
            })

        with transaction.atomic():
            venta = Venta.objects.select_for_update().get(id=venta_id)
            if venta.estado == 'CANCELADA':
                messages.warning(request, f'El ticket #{venta.id} ya estaba cancelado.')
                return redirect('historial_ventas')

            detalles = DetalleVenta.objects.select_related('producto').filter(venta=venta)
            for detalle in detalles:
                producto = Producto.objects.select_for_update().get(id=detalle.producto_id)
                stock_antes = producto.stock
                producto.stock += detalle.cantidad
                producto.save(update_fields=['stock'])
                MovimientoInventario.registrar(
                    producto=producto,
                    tipo=MovimientoInventario.Tipo.CANCELACION,
                    cantidad=detalle.cantidad,
                    stock_antes=stock_antes,
                    stock_despues=producto.stock,
                    usuario=request.user,
                    venta=venta,
                    tienda=tienda_actual,
                    motivo=motivo,
                )

            venta.estado = 'CANCELADA'
            venta.motivo_cancelacion = motivo
            venta.fecha_cancelacion = timezone.now()
            venta.cancelado_por = request.user
            venta.save(update_fields=['estado', 'motivo_cancelacion', 'fecha_cancelacion', 'cancelado_por'])

            venta_id = venta.id
            tienda_id = venta.tienda_id or tienda_actual.id
            total = f'{venta.total:.2f}'
            payload = {
                'titulo': 'Venta cancelada',
                'mensaje': f'Ticket #{venta_id} cancelado por ${total}',
                'venta_id': venta_id,
                'total': total,
            }
            transaction.on_commit(lambda tienda_id=tienda_id, payload=payload: emitir_notificacion_tienda(
                tienda_id,
                'venta.cancelada',
                payload,
            ))

        messages.success(request, f'Ticket #{venta.id} cancelado y stock reintegrado.')
        return redirect('historial_ventas')

    return render(request, 'ventas/cancelar_venta.html', {
        **get_config_context('Estadísticas', 'border-blue-600'),
        'venta': venta,
        'detalles': venta.detalles.all(),
    })


@login_required
@permission_required(OPERAR_POS_PERMISSION, login_url='portal_principal')
@require_POST
def procesar_venta(request):
    carrito = request.session.get('carrito', {})
    tienda_actual = get_tienda_actual(request)
    sesion_abierta = SesionCaja.objects.filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True), cajero=request.user, estado=True).exists()
    if not sesion_abierta:
        total = calcular_total_carrito(carrito)
        request.session['carrito'] = carrito
        return render(request, 'ventas/partials/carrito.html', {
            'carrito': carrito,
            'total': total,
            'error_stock': 'Abre caja antes de cobrar una venta.',
        })

    if not carrito:
        return render(request, 'ventas/partials/carrito.html', {'carrito': {}, 'total': Decimal('0.00')})

    try:
        with transaction.atomic():
            sesion = SesionCaja.objects.select_for_update().filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True), cajero=request.user, estado=True).first()
            if not sesion:
                raise ValueError("No hay una caja abierta para procesar la venta.")

            nueva_venta = Venta.objects.create(
                cajero=request.user,
                sesion=sesion,
                tienda=tienda_actual,
                metodo_pago='EFE',
                subtotal=Decimal('0.00'),
                propina=Decimal('0.00'),
                porcentaje_propina=Decimal('0.00'),
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

                if not producto.activo:
                    raise ValueError(f"{producto.nombre} está inactivo y no puede venderse.")

                if producto.stock < cantidad_vendida:
                    raise ValueError(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}")

                stock_antes = producto.stock
                producto.stock -= cantidad_vendida
                producto.save(update_fields=['stock'])

                subtotal = precio_unitario * cantidad_vendida
                venta_total += subtotal

                DetalleVenta.objects.create(
                    venta=nueva_venta,
                    producto=producto,
                    cantidad=cantidad_vendida,
                    precio_unitario=precio_unitario,
                )
                MovimientoInventario.registrar(
                    producto=producto,
                    tipo=MovimientoInventario.Tipo.VENTA,
                    cantidad=-cantidad_vendida,
                    stock_antes=stock_antes,
                    stock_despues=producto.stock,
                    usuario=request.user,
                    venta=nueva_venta,
                    tienda=tienda_actual,
                    motivo=f'Venta ticket #{nueva_venta.id}',
                )

            desglose_pago = calcular_desglose_pago(
                total=venta_total,
                metodo_pago=request.POST.get('metodo_pago', 'EFE'),
                pago_recibido=request.POST.get('pago_recibido', '0'),
                pago_efectivo=request.POST.get('pago_efectivo', '0'),
                pago_tarjeta=request.POST.get('pago_tarjeta', '0'),
                pago_transferencia=request.POST.get('pago_transferencia', '0'),
            )

            nueva_venta.subtotal = venta_total
            nueva_venta.propina = Decimal('0.00')
            nueva_venta.porcentaje_propina = Decimal('0.00')
            nueva_venta.total = venta_total
            nueva_venta.metodo_pago = desglose_pago['metodo_pago']
            nueva_venta.pago_recibido = desglose_pago['pago_recibido']
            nueva_venta.cambio = desglose_pago['cambio']
            nueva_venta.save(update_fields=['subtotal', 'propina', 'porcentaje_propina', 'total', 'metodo_pago', 'pago_recibido', 'cambio'])
            registrar_pagos_venta(nueva_venta, desglose_pago['pagos'])

            venta_id = nueva_venta.id
            tienda_id = nueva_venta.tienda_id or tienda_actual.id
            total = f'{nueva_venta.total:.2f}'
            metodo = nueva_venta.get_metodo_pago_display()
            payload = {
                'titulo': 'Nueva venta registrada',
                'mensaje': f'Ticket #{venta_id} por ${total} ({metodo})',
                'venta_id': venta_id,
                'total': total,
                'metodo_pago': nueva_venta.metodo_pago,
            }
            transaction.on_commit(lambda tienda_id=tienda_id, payload=payload: emitir_notificacion_tienda(
                tienda_id,
                'venta.creada',
                payload,
            ))

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
