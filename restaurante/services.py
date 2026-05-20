from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.notifications import emitir_notificacion_tienda
from inventario.models import MovimientoInventario, Producto
from restaurante.models import ConfiguracionRestaurante, Mesa, Pedido, PedidoEvento, PedidoItem
from ventas.models import DetalleVenta, SesionCaja, Venta
from ventas.payments import calcular_desglose_pago, calcular_propina, dinero, registrar_pagos_venta


def get_configuracion_restaurante():
    configuracion = ConfiguracionRestaurante.objects.order_by('id').first()
    if configuracion:
        return configuracion
    return ConfiguracionRestaurante.objects.create()


def pedido_payload(pedido):
    return {
        'pedido_id': pedido.id,
        'pedido': f'Pedido #{pedido.id}',
        'tipo': pedido.tipo,
        'mesa': pedido.mesa.nombre if pedido.mesa_id else None,
        'referencia': pedido.referencia,
        'display': pedido.nombre_display,
        'estado': pedido.estado,
    }


def item_payload(item):
    return {
        'item_id': item.id,
        'pedido_id': item.pedido_id,
        'producto_id': item.producto_id,
        'producto': item.producto.nombre,
        'cantidad': item.cantidad,
        'estado': item.estado,
        'nota': item.nota,
    }


def emitir_evento_restaurante(pedido, evento, payload=None):
    emitir_notificacion_tienda(pedido.tienda_id, evento, {
        **pedido_payload(pedido),
        **(payload or {}),
    })


def emitir_evento_item_estado_actualizado(pedido_id, item_id):
    item = PedidoItem.objects.select_related('pedido', 'pedido__mesa', 'pedido__tienda', 'producto').get(id=item_id, pedido_id=pedido_id)
    emitir_evento_restaurante(item.pedido, 'restaurante.item_estado_actualizado', {
        **item_payload(item),
        'pedido_estado': item.pedido.estado,
    })


def registrar_evento(pedido, evento, usuario=None, item=None, descripcion=''):
    PedidoEvento.objects.create(
        pedido=pedido,
        item=item,
        usuario=usuario,
        evento=evento,
        descripcion=descripcion,
    )


def crear_pedido(*, tipo, usuario, tienda, mesa_id=None, referencia=''):
    config = get_configuracion_restaurante()
    if tipo == Pedido.Tipo.PARA_LLEVAR and not config.permitir_para_llevar:
        raise ValidationError('Los pedidos para llevar no están habilitados.')
    if tipo == Pedido.Tipo.MESA and not mesa_id:
        raise ValidationError('Selecciona una mesa.')

    mesa = None
    if tipo == Pedido.Tipo.MESA:
        try:
            mesa = Mesa.objects.get(id=mesa_id, activa=True)
        except Mesa.DoesNotExist:
            raise ValidationError('La mesa seleccionada no está disponible.')
        if Pedido.objects.filter(mesa=mesa).exclude(estado__in=[Pedido.Estado.COBRADO, Pedido.Estado.CANCELADO]).exists():
            raise ValidationError(f'{mesa.nombre} ya tiene un pedido abierto.')

    pedido = Pedido.objects.create(
        tipo=tipo,
        mesa=mesa,
        referencia=referencia.strip(),
        mesero=usuario,
        tienda=tienda,
    )
    registrar_evento(pedido, 'pedido.creado', usuario=usuario)
    transaction.on_commit(lambda pedido_id=pedido.id: emitir_evento_restaurante(
        Pedido.objects.select_related('mesa', 'tienda').get(id=pedido_id),
        'restaurante.pedido_creado',
        {'titulo': 'Pedido abierto', 'mensaje': f'{pedido.nombre_display} abrió comanda.', 'nivel': 'info'},
    ))
    return pedido


def agregar_item_borrador(*, pedido, producto_id, cantidad, nota='', usuario=None):
    if pedido.estado in [Pedido.Estado.COBRADO, Pedido.Estado.CANCELADO]:
        raise ValidationError('No se puede modificar un pedido cerrado.')
    producto = Producto.objects.select_related('precios').get(id=producto_id, activo=True)
    if not hasattr(producto, 'precios'):
        raise ValidationError(f'{producto.nombre} no tiene precio asignado.')
    cantidad = int(cantidad)
    if cantidad <= 0:
        raise ValidationError('La cantidad debe ser mayor a cero.')

    preparacion = getattr(producto, 'preparacion', None)
    item = PedidoItem.objects.create(
        pedido=pedido,
        producto=producto,
        estacion=preparacion.estacion if preparacion else None,
        cantidad=cantidad,
        precio_unitario=producto.precios.precio,
        nota=nota.strip(),
    )
    registrar_evento(pedido, 'item.borrador_agregado', usuario=usuario, item=item)
    emitir_evento_restaurante(pedido, 'restaurante.pedido_actualizado', item_payload(item))
    return item


def eliminar_o_cancelar_item(*, item, usuario=None, motivo=''):
    pedido = item.pedido
    config = get_configuracion_restaurante()
    if item.estado == PedidoItem.Estado.BORRADOR:
        item_id = item.id
        producto = item.producto.nombre
        item.delete()
        registrar_evento(pedido, 'item.borrador_eliminado', usuario=usuario, descripcion=producto)
        emitir_evento_restaurante(pedido, 'restaurante.pedido_actualizado', {'item_id': item_id})
        return True

    if item.estado in [PedidoItem.Estado.CANCELADO, PedidoItem.Estado.ENTREGADO]:
        raise ValidationError('Este item no se puede eliminar desde la comanda.')
    if config.requerir_motivo_cancelacion_enviados and not motivo.strip():
        raise ValidationError('Captura un motivo para cancelar este item.')

    reintegrar = (
        item.estado == PedidoItem.Estado.PENDIENTE and config.reintegrar_pendiente
        or item.estado == PedidoItem.Estado.PREPARANDO and config.reintegrar_preparando
        or item.estado == PedidoItem.Estado.LISTO and config.reintegrar_listo
    )

    with transaction.atomic():
        item = PedidoItem.objects.select_for_update().select_related('pedido', 'producto').get(id=item.id)
        if item.estado == PedidoItem.Estado.BORRADOR:
            item.delete()
            return True

        item.estado = PedidoItem.Estado.CANCELADO
        item.motivo_cancelacion = motivo.strip()
        item.cancelado_en = timezone.now()
        item.reintegro_stock = reintegrar
        item.save(update_fields=['estado', 'motivo_cancelacion', 'cancelado_en', 'reintegro_stock', 'actualizado_en'])

        if reintegrar:
            producto = Producto.objects.select_for_update().get(id=item.producto_id)
            stock_antes = producto.stock
            producto.stock += item.cantidad
            producto.save(update_fields=['stock'])
            MovimientoInventario.registrar(
                producto=producto,
                tipo=MovimientoInventario.Tipo.CANCELACION,
                cantidad=item.cantidad,
                stock_antes=stock_antes,
                stock_despues=producto.stock,
                usuario=usuario,
                tienda=pedido.tienda,
                motivo=f'Cancelación item comanda #{pedido.id}: {motivo}',
            )

        actualizar_estado_pedido(pedido)
        registrar_evento(pedido, 'item.cancelado', usuario=usuario, item=item, descripcion=motivo)
        transaction.on_commit(lambda pedido_id=pedido.id, item_id=item.id: emitir_evento_restaurante(
            Pedido.objects.select_related('mesa', 'tienda').get(id=pedido_id),
            'restaurante.item_cancelado',
            {
                **item_payload(PedidoItem.objects.select_related('producto').get(id=item_id)),
                'titulo': 'Item cancelado',
                'mensaje': f'{item.producto.nombre} cancelado en {pedido.nombre_display}.',
                'nivel': 'warning',
            },
        ))
    return True


def enviar_a_cocina(*, pedido, usuario=None):
    borradores = list(pedido.items.select_related('producto', 'producto__precios', 'producto__preparacion', 'estacion').filter(estado=PedidoItem.Estado.BORRADOR))
    if not borradores:
        raise ValidationError('No hay productos nuevos para enviar a cocina.')

    cantidades_por_producto = defaultdict(int)
    for item in borradores:
        cantidades_por_producto[item.producto_id] += item.cantidad

    with transaction.atomic():
        productos = {
            producto.id: producto
            for producto in Producto.objects.select_for_update().filter(id__in=cantidades_por_producto.keys())
        }
        errores = []
        for producto_id, cantidad in cantidades_por_producto.items():
            producto = productos[producto_id]
            if not producto.activo:
                errores.append(f'{producto.nombre} está inactivo.')
            elif producto.stock < cantidad:
                errores.append(f'Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}, solicitado: {cantidad}.')
        if errores:
            raise ValidationError(errores)

        ahora = timezone.now()
        for producto_id, cantidad in cantidades_por_producto.items():
            producto = productos[producto_id]
            stock_antes = producto.stock
            producto.stock -= cantidad
            producto.save(update_fields=['stock'])
            MovimientoInventario.registrar(
                producto=producto,
                tipo=MovimientoInventario.Tipo.VENTA,
                cantidad=-cantidad,
                stock_antes=stock_antes,
                stock_despues=producto.stock,
                usuario=usuario,
                tienda=pedido.tienda,
                motivo=f'Envío a cocina comanda #{pedido.id}',
            )

        for item in borradores:
            preparacion = getattr(item.producto, 'preparacion', None)
            item.estado = PedidoItem.Estado.PENDIENTE if not preparacion or preparacion.enviar_a_kds else PedidoItem.Estado.LISTO
            item.enviado_en = ahora
            item.actualizado_en = ahora
            item.save(update_fields=['estado', 'enviado_en', 'actualizado_en'])
        pedido.enviado_en = pedido.enviado_en or ahora
        pedido.estado = Pedido.Estado.EN_COCINA
        pedido.save(update_fields=['enviado_en', 'estado', 'actualizado_en'])
        actualizar_estado_pedido(pedido)
        registrar_evento(pedido, 'pedido.enviado_cocina', usuario=usuario, descripcion=f'{len(borradores)} items')
        transaction.on_commit(lambda pedido_id=pedido.id: emitir_evento_restaurante(
            Pedido.objects.select_related('mesa', 'tienda').get(id=pedido_id),
            'restaurante.pedido_enviado_cocina',
            {'titulo': 'Pedido enviado a cocina', 'mensaje': f'{pedido.nombre_display} enviado a cocina.', 'nivel': 'info'},
        ))
    return pedido


def actualizar_estado_item(*, item, nuevo_estado, usuario=None):
    estados_validos = {
        PedidoItem.Estado.PENDIENTE,
        PedidoItem.Estado.PREPARANDO,
        PedidoItem.Estado.LISTO,
        PedidoItem.Estado.ENTREGADO,
    }
    if nuevo_estado not in estados_validos:
        raise ValidationError('Estado inválido para cocina.')
    with transaction.atomic():
        item = PedidoItem.objects.select_for_update().select_related('pedido', 'producto').get(id=item.id)
        if item.estado in [PedidoItem.Estado.BORRADOR, PedidoItem.Estado.CANCELADO]:
            raise ValidationError('Este item no se puede actualizar en KDS.')

        item.estado = nuevo_estado
        item.save(update_fields=['estado', 'actualizado_en'])
        actualizar_estado_pedido(item.pedido)
        registrar_evento(item.pedido, f'item.{nuevo_estado.lower()}', usuario=usuario, item=item)
        transaction.on_commit(lambda pedido_id=item.pedido_id, item_id=item.id: emitir_evento_item_estado_actualizado(pedido_id, item_id))
    return item


def actualizar_estado_pedido(pedido):
    estados = list(pedido.items.exclude(estado__in=[PedidoItem.Estado.BORRADOR, PedidoItem.Estado.CANCELADO]).values_list('estado', flat=True))
    if pedido.estado in [Pedido.Estado.COBRADO, Pedido.Estado.CANCELADO]:
        return pedido
    if not estados:
        pedido.estado = Pedido.Estado.ABIERTO
    elif all(estado == PedidoItem.Estado.ENTREGADO for estado in estados):
        pedido.estado = Pedido.Estado.ENTREGADO
    elif all(estado in [PedidoItem.Estado.LISTO, PedidoItem.Estado.ENTREGADO] for estado in estados):
        pedido.estado = Pedido.Estado.LISTO
    else:
        pedido.estado = Pedido.Estado.EN_COCINA
    pedido.save(update_fields=['estado', 'actualizado_en'])
    return pedido


def cobrar_pedido(
    *,
    pedido,
    usuario,
    metodo_pago,
    pago_recibido=Decimal('0.00'),
    porcentaje_propina=Decimal('0.00'),
    pago_efectivo=Decimal('0.00'),
    pago_tarjeta=Decimal('0.00'),
    pago_transferencia=Decimal('0.00'),
):
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().select_related('tienda').get(id=pedido.id)
        if pedido.estado == Pedido.Estado.COBRADO:
            raise ValidationError('Este pedido ya fue cobrado.')
        if pedido.estado == Pedido.Estado.CANCELADO:
            raise ValidationError('Este pedido está cancelado.')
        if pedido.items.filter(estado=PedidoItem.Estado.BORRADOR).exists():
            raise ValidationError('Envía o elimina los productos pendientes antes de cobrar.')

        items = list(pedido.items.select_related('producto').exclude(estado__in=[PedidoItem.Estado.BORRADOR, PedidoItem.Estado.CANCELADO]))
        if not items:
            raise ValidationError('No hay productos enviados para cobrar.')

        try:
            subtotal = sum(item.subtotal() for item in items)
            porcentaje_propina = dinero(porcentaje_propina, 'porcentaje de propina')
            propina = calcular_propina(subtotal, porcentaje_propina)
            total = subtotal + propina
            desglose_pago = calcular_desglose_pago(
                total=total,
                metodo_pago=metodo_pago,
                pago_recibido=pago_recibido,
                pago_efectivo=pago_efectivo,
                pago_tarjeta=pago_tarjeta,
                pago_transferencia=pago_transferencia,
            )
        except ValueError as error:
            raise ValidationError(str(error))

        sesion = SesionCaja.objects.select_for_update().filter(
            Q(tienda=pedido.tienda) | Q(tienda__isnull=True),
            cajero=usuario,
            estado=True,
        ).first()
        if not sesion:
            raise ValidationError('Abre caja antes de cobrar el pedido.')

        venta = Venta.objects.create(
            cajero=usuario,
            sesion=sesion,
            tienda=pedido.tienda,
            metodo_pago=desglose_pago['metodo_pago'],
            subtotal=subtotal,
            propina=propina,
            porcentaje_propina=porcentaje_propina,
            total=total,
            pago_recibido=desglose_pago['pago_recibido'],
            cambio=desglose_pago['cambio'],
        )
        registrar_pagos_venta(venta, desglose_pago['pagos'])
        for item in items:
            DetalleVenta.objects.create(
                venta=venta,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            )
        pedido.venta = venta
        pedido.estado = Pedido.Estado.COBRADO
        pedido.cobrado_en = timezone.now()
        pedido.save(update_fields=['venta', 'estado', 'cobrado_en', 'actualizado_en'])
        registrar_evento(pedido, 'pedido.cobrado', usuario=usuario, descripcion=f'Venta #{venta.id}')
        transaction.on_commit(lambda pedido_id=pedido.id, venta_id=venta.id: emitir_evento_restaurante(
            Pedido.objects.select_related('mesa', 'tienda').get(id=pedido_id),
            'restaurante.pedido_cobrado',
            {
                'titulo': 'Pedido cobrado',
                'mensaje': f'Pedido #{pedido_id} cobrado como ticket #{venta_id}.',
                'venta_id': venta_id,
                'total': f'{total:.2f}',
                'nivel': 'success',
            },
        ))
    return venta
