from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def grupo_notificaciones_tienda(tienda_id):
    return f'notificaciones_tienda_{tienda_id}'


def tiendas_activas_ids():
    from configuraciones.models import Tienda

    return list(Tienda.objects.filter(activa=True).values_list('id', flat=True))


def producto_payload(producto):
    precio = None
    try:
        precio = f'{producto.precios.precio:.2f}'
    except Exception:
        pass

    return {
        'producto_id': producto.id,
        'producto': producto.nombre,
        'codigo_barras': producto.codigo_barras,
        'stock': producto.stock,
        'stock_minimo': producto.stock_minimo,
        'activo': producto.activo,
        'precio': precio,
    }


def emitir_notificacion_tienda(tienda_id, evento, payload=None):
    if not tienda_id:
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        grupo_notificaciones_tienda(tienda_id),
        {
            'type': 'notificacion.enviar',
            'payload': {
                'event': evento,
                **(payload or {}),
            },
        },
    )


def emitir_notificacion_tiendas(tienda_ids, evento, payload=None):
    for tienda_id in set(tienda_ids or []):
        emitir_notificacion_tienda(tienda_id, evento, payload)


def emitir_notificacion_todas_tiendas(evento, payload=None):
    emitir_notificacion_tiendas(tiendas_activas_ids(), evento, payload)


def emitir_producto_actualizado(producto, evento='producto.actualizado', payload=None):
    emitir_notificacion_todas_tiendas(evento, {
        **producto_payload(producto),
        **(payload or {}),
    })
