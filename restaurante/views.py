from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from configuraciones.utils import get_tienda_actual
from core.permissions import any_permission_required
from core.utils import get_config_context
from inventario.models import Producto
from restaurante import services
from restaurante.models import EstacionPreparacion, Mesa, Pedido, PedidoItem
from ventas.models import SesionCaja, Venta


OPERAR_RESTAURANTE_PERMISSION = 'configuraciones.operar_restaurante'
OPERAR_KDS_PERMISSION = 'configuraciones.operar_kds'


def _es_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _mensajes_validacion(error):
    return getattr(error, 'messages', [str(error)])


def _primer_error(error):
    return _mensajes_validacion(error)[0]


def _pedidos_abiertos(tienda):
    return Pedido.objects.select_related('mesa', 'mesero', 'venta').filter(tienda=tienda).exclude(
        estado__in=[Pedido.Estado.COBRADO, Pedido.Estado.CANCELADO]
    ).order_by('-actualizado_en', '-id')


def _dashboard_context(request):
    tienda_actual = get_tienda_actual(request)
    return {
        **get_config_context('Restaurante', 'border-orange-600'),
        'tienda_actual': tienda_actual,
        'config_restaurante': services.get_configuracion_restaurante(),
        'mesas': Mesa.objects.filter(activa=True).order_by('zona', 'nombre'),
        'pedidos': _pedidos_abiertos(tienda_actual),
    }


def _get_pedido(request, pedido_id):
    tienda_actual = get_tienda_actual(request)
    return get_object_or_404(
        Pedido.objects.select_related('mesa', 'mesero', 'tienda', 'venta').filter(tienda=tienda_actual),
        id=pedido_id,
    )


def _comanda_context(request, pedido, **extra):
    tienda_actual = get_tienda_actual(request)
    items = list(pedido.items.select_related('producto', 'estacion').all())
    borradores_count = sum(1 for item in items if item.estado == PedidoItem.Estado.BORRADOR)
    items_cobrables = [item for item in items if item.estado not in [PedidoItem.Estado.BORRADOR, PedidoItem.Estado.CANCELADO]]
    total = sum(item.subtotal() for item in items_cobrables)

    return {
        **get_config_context('Comanda', 'border-orange-600'),
        'pedido': pedido,
        'items': items,
        'total': total,
        'borradores_count': borradores_count,
        'items_cobrables_count': len(items_cobrables),
        'metodos_pago': Venta.METODOS_PAGO,
        'puede_cobrar': bool(items_cobrables)
        and not borradores_count
        and pedido.estado not in [Pedido.Estado.COBRADO, Pedido.Estado.CANCELADO],
        'sesion_abierta': pedido.estado == Pedido.Estado.COBRADO or SesionCaja.objects.filter(
            Q(tienda=tienda_actual) | Q(tienda__isnull=True),
            cajero=request.user,
            estado=True,
        ).exists(),
        **extra,
    }


def _render_comanda_panel(request, pedido, **extra):
    return render(request, 'restaurante/partials/comanda_panel.html', _comanda_context(request, pedido, **extra))


def _respuesta_comanda(request, pedido, **extra):
    if _es_htmx(request):
        return _render_comanda_panel(request, pedido, **extra)
    return redirect('restaurante_comanda', pedido_id=pedido.id)


def _parametro_estacion(request):
    return request.GET.get('estacion', request.POST.get('estacion', '')).strip()


def _kds_context(request):
    tienda_actual = get_tienda_actual(request)
    config = services.get_configuracion_restaurante()
    estacion_id = _parametro_estacion(request)
    items_query = PedidoItem.objects.select_related('pedido', 'pedido__mesa', 'producto', 'estacion').filter(
        pedido__tienda=tienda_actual,
        estado__in=[PedidoItem.Estado.PENDIENTE, PedidoItem.Estado.PREPARANDO, PedidoItem.Estado.LISTO],
    ).filter(
        Q(producto__preparacion__isnull=True) | Q(producto__preparacion__enviar_a_kds=True)
    ).exclude(pedido__estado__in=[Pedido.Estado.COBRADO, Pedido.Estado.CANCELADO])

    if config.usa_estaciones and estacion_id == 'sin_estacion':
        items_query = items_query.filter(estacion__isnull=True)
    elif config.usa_estaciones and estacion_id:
        items_query = items_query.filter(estacion_id=estacion_id)

    items = list(items_query.order_by('estado', 'enviado_en', 'id'))
    grupos = [
        {
            'estado': PedidoItem.Estado.PENDIENTE,
            'titulo': 'Pendientes',
            'items': [item for item in items if item.estado == PedidoItem.Estado.PENDIENTE],
            'clase': 'border-yellow-200 bg-yellow-50 dark:border-yellow-900/50 dark:bg-yellow-900/20',
        },
        {
            'estado': PedidoItem.Estado.PREPARANDO,
            'titulo': 'Preparando',
            'items': [item for item in items if item.estado == PedidoItem.Estado.PREPARANDO],
            'clase': 'border-blue-200 bg-blue-50 dark:border-blue-900/50 dark:bg-blue-900/20',
        },
        {
            'estado': PedidoItem.Estado.LISTO,
            'titulo': 'Listos',
            'items': [item for item in items if item.estado == PedidoItem.Estado.LISTO],
            'clase': 'border-green-200 bg-green-50 dark:border-green-900/50 dark:bg-green-900/20',
        },
    ]

    return {
        **get_config_context('KDS', 'border-orange-600'),
        'config_restaurante': config,
        'estaciones': EstacionPreparacion.objects.filter(activa=True).order_by('nombre'),
        'estacion_id': estacion_id,
        'grupos': grupos,
    }


@login_required
@any_permission_required([OPERAR_RESTAURANTE_PERMISSION, OPERAR_KDS_PERMISSION], login_url='portal_principal')
def dashboard(request):
    return render(request, 'restaurante/dashboard.html', _dashboard_context(request))


@login_required
@any_permission_required([OPERAR_RESTAURANTE_PERMISSION, OPERAR_KDS_PERMISSION], login_url='portal_principal')
def dashboard_live(request):
    return render(request, 'restaurante/partials/pedidos_abiertos.html', _dashboard_context(request))


@login_required
@permission_required(OPERAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
@require_POST
def crear_pedido_view(request):
    tienda_actual = get_tienda_actual(request)
    try:
        pedido = services.crear_pedido(
            tipo=request.POST.get('tipo') or Pedido.Tipo.MESA,
            mesa_id=request.POST.get('mesa') or None,
            referencia=request.POST.get('referencia', ''),
            usuario=request.user,
            tienda=tienda_actual,
        )
    except (Mesa.DoesNotExist, ValidationError) as error:
        for mensaje in _mensajes_validacion(error):
            messages.error(request, mensaje)
        return redirect('restaurante_dashboard')

    messages.success(request, f'Comanda abierta: {pedido.nombre_display}.')
    return redirect('restaurante_comanda', pedido_id=pedido.id)


@login_required
@permission_required(OPERAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
def comanda(request, pedido_id):
    pedido = _get_pedido(request, pedido_id)
    return render(request, 'restaurante/comanda.html', _comanda_context(request, pedido))


@login_required
@permission_required(OPERAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
def comanda_panel_live(request, pedido_id):
    return _render_comanda_panel(request, _get_pedido(request, pedido_id))


@login_required
@permission_required(OPERAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
def buscar_productos(request, pedido_id):
    _get_pedido(request, pedido_id)
    query = request.GET.get('q', '').strip()
    productos = Producto.objects.select_related('precios', 'categoria').filter(activo=True, stock__gt=0, precios__isnull=False)
    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(codigo_barras__icontains=query) | Q(categoria__nombre__icontains=query))[:20]
    else:
        productos = Producto.objects.none()

    return render(request, 'restaurante/partials/productos.html', {
        'pedido_id': pedido_id,
        'productos': productos,
    })


@login_required
@permission_required(OPERAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
@require_POST
def agregar_item(request, pedido_id):
    pedido = _get_pedido(request, pedido_id)
    try:
        services.agregar_item_borrador(
            pedido=pedido,
            producto_id=request.POST.get('producto_id'),
            cantidad=request.POST.get('cantidad', 1),
            nota=request.POST.get('nota', ''),
            usuario=request.user,
        )
    except (Producto.DoesNotExist, ValueError, ValidationError) as error:
        return _respuesta_comanda(request, _get_pedido(request, pedido_id), error=_primer_error(error))

    return _respuesta_comanda(request, _get_pedido(request, pedido_id), success='Producto agregado a la comanda.')


@login_required
@permission_required(OPERAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
@require_POST
def eliminar_item(request, pedido_id, item_id):
    pedido = _get_pedido(request, pedido_id)
    item = get_object_or_404(PedidoItem.objects.select_related('pedido', 'producto'), id=item_id, pedido=pedido)
    try:
        services.eliminar_o_cancelar_item(item=item, usuario=request.user, motivo=request.POST.get('motivo', ''))
    except ValidationError as error:
        return _respuesta_comanda(request, _get_pedido(request, pedido_id), error=_primer_error(error))

    return _respuesta_comanda(request, _get_pedido(request, pedido_id), success='Item cerrado en la comanda.')


@login_required
@permission_required(OPERAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
@require_POST
def enviar_cocina(request, pedido_id):
    pedido = _get_pedido(request, pedido_id)
    try:
        services.enviar_a_cocina(pedido=pedido, usuario=request.user)
    except ValidationError as error:
        return _respuesta_comanda(request, _get_pedido(request, pedido_id), error=_primer_error(error))

    return _respuesta_comanda(request, _get_pedido(request, pedido_id), success='Pedido enviado a cocina.')


@login_required
@permission_required(OPERAR_RESTAURANTE_PERMISSION, login_url='portal_principal')
@require_POST
def cobrar_pedido_view(request, pedido_id):
    pedido = _get_pedido(request, pedido_id)
    try:
        venta = services.cobrar_pedido(
            pedido=pedido,
            usuario=request.user,
            metodo_pago=request.POST.get('metodo_pago', 'EFE'),
            pago_recibido=request.POST.get('pago_recibido', '0'),
            porcentaje_propina=request.POST.get('porcentaje_propina', '0'),
            pago_efectivo=request.POST.get('pago_efectivo', '0'),
            pago_tarjeta=request.POST.get('pago_tarjeta', '0'),
            pago_transferencia=request.POST.get('pago_transferencia', '0'),
        )
    except ValidationError as error:
        return _respuesta_comanda(request, _get_pedido(request, pedido_id), error=_primer_error(error))

    if _es_htmx(request):
        return _render_comanda_panel(request, _get_pedido(request, pedido_id), success=f'Pedido cobrado como ticket #{venta.id}.', venta_cobrada=venta)
    return redirect('imprimir_ticket', venta_id=venta.id)


@login_required
@permission_required(OPERAR_KDS_PERMISSION, login_url='portal_principal')
def kds(request):
    return render(request, 'restaurante/kds.html', _kds_context(request))


@login_required
@permission_required(OPERAR_KDS_PERMISSION, login_url='portal_principal')
def kds_live(request):
    return render(request, 'restaurante/partials/kds_panel.html', _kds_context(request))


@login_required
@permission_required(OPERAR_KDS_PERMISSION, login_url='portal_principal')
@require_POST
def actualizar_item_kds(request, item_id):
    tienda_actual = get_tienda_actual(request)
    item = get_object_or_404(
        PedidoItem.objects.select_related('pedido', 'producto').filter(pedido__tienda=tienda_actual),
        id=item_id,
    )
    try:
        services.actualizar_estado_item(item=item, nuevo_estado=request.POST.get('estado'), usuario=request.user)
    except ValidationError as error:
        if _es_htmx(request):
            return render(request, 'restaurante/partials/kds_panel.html', {**_kds_context(request), 'error': _primer_error(error)})
        messages.error(request, _primer_error(error))

    if _es_htmx(request):
        return render(request, 'restaurante/partials/kds_panel.html', _kds_context(request))
    return redirect('restaurante_kds')
