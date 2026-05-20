from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from core.utils import get_config_context, get_querystring_without_page
from configuraciones.utils import get_tienda_actual
from configuraciones.models import ConfiguracionSistema
from ventas.models import SesionCaja, Venta
from ventas.payments import total_pagos_por_metodo
VER_TURNOS_PERMISSION = 'configuraciones.ver_turnos'


def _decimal(value):
    return value or Decimal('0.00')


def _totales_turno(sesion):
    ventas = Venta.objects.filter(Q(tienda=sesion.tienda) | Q(tienda__isnull=True), sesion=sesion, estado='ACTIVA')
    ventas_efectivo = total_pagos_por_metodo(ventas, 'EFE')
    ventas_tarjeta = total_pagos_por_metodo(ventas, 'TAR')
    ventas_transferencia = total_pagos_por_metodo(ventas, 'TRA')
    total_ventas = ventas_efectivo + ventas_tarjeta + ventas_transferencia
    total_propinas = _decimal(ventas.aggregate(total=Sum('propina'))['total'])
    esperado_en_caja = sesion.fondo_inicial + ventas_efectivo
    diferencia = None

    if sesion.efectivo_cierre is not None:
        diferencia = sesion.efectivo_cierre - esperado_en_caja

    return {
        'ventas_efectivo': ventas_efectivo,
        'ventas_tarjeta': ventas_tarjeta,
        'ventas_transferencia': ventas_transferencia,
        'total_ventas': total_ventas,
        'total_propinas': total_propinas,
        'total_tickets': ventas.count(),
        'esperado_en_caja': esperado_en_caja,
        'diferencia': diferencia,
    }


def _enriquecer_turno(sesion):
    for key, value in _totales_turno(sesion).items():
        setattr(sesion, key, value)
    return sesion


@login_required
@permission_required(VER_TURNOS_PERMISSION, login_url='portal_principal')
def historial_turnos(request):
    tienda_actual = get_tienda_actual(request)
    query = request.GET.get('q', '').strip()
    fecha_desde = request.GET.get('desde', '').strip()
    fecha_hasta = request.GET.get('hasta', '').strip()
    estado = request.GET.get('estado', '').strip()
    cajero_id = request.GET.get('cajero', '').strip()
    per_page = request.GET.get('per_page', 20)

    turnos = SesionCaja.objects.select_related('cajero', 'tienda', 'punto_venta').filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True)).order_by('-fecha_apertura', '-id')

    if query:
        filtros = Q(cajero__username__icontains=query)
        if query.isdigit():
            filtros |= Q(id=int(query))
        turnos = turnos.filter(filtros)

    if fecha_desde:
        turnos = turnos.filter(fecha_apertura__date__gte=fecha_desde)

    if fecha_hasta:
        turnos = turnos.filter(fecha_apertura__date__lte=fecha_hasta)

    if estado == 'abierta':
        turnos = turnos.filter(estado=True)
    elif estado == 'cerrada':
        turnos = turnos.filter(estado=False)

    if cajero_id:
        turnos = turnos.filter(cajero_id=cajero_id)

    resumen = turnos.aggregate(
        total_ventas=Sum('venta__total', filter=Q(venta__estado='ACTIVA')),
        total_tickets=Count('venta', filter=Q(venta__estado='ACTIVA')),
    )
    ventas_turnos = Venta.objects.filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True), sesion__in=turnos, estado='ACTIVA')
    total_turnos = turnos.count()

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 20

    paginator = Paginator(turnos, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))
    page_obj.object_list = [_enriquecer_turno(sesion) for sesion in page_obj.object_list]

    contexto = {
        **get_config_context('Estadísticas', 'border-blue-600'),
        'page_obj': page_obj,
        'query': query,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'estado': estado,
        'cajero_id': cajero_id,
        'cajeros': User.objects.filter(sesioncaja__isnull=False).distinct().order_by('username'),
        'per_page': per_page,
        'querystring': get_querystring_without_page(request),
        'total_turnos': total_turnos,
        'total_ventas': _decimal(resumen['total_ventas']),
        'ventas_efectivo': total_pagos_por_metodo(ventas_turnos, 'EFE'),
        'total_tickets': resumen['total_tickets'] or 0,
    }
    return render(request, 'ventas/turnos_historial.html', contexto)


@login_required
@permission_required(VER_TURNOS_PERMISSION, login_url='portal_principal')
def imprimir_corte(request, sesion_id):
    tienda_actual = get_tienda_actual(request)
    sesion = get_object_or_404(SesionCaja.objects.select_related('cajero', 'tienda', 'punto_venta').filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True)), id=sesion_id)
    totales = _totales_turno(sesion)
    config = ConfiguracionSistema.objects.first()

    contexto = {
        'sesion': sesion,
        'config': config,
        'fecha_impresion': timezone.now(),
        **totales,
    }
    return render(request, 'ventas/corte_ticket.html', contexto)
