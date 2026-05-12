from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import render
from core.utils import get_config_context, get_querystring_without_page
from configuraciones.utils import get_tienda_actual
from ventas.models import Venta
from ventas.views.carrito import VENTAS_PERMISSION


@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
def historial_ventas(request):
    tienda_actual = get_tienda_actual(request)
    query = request.GET.get('q', '').strip()
    fecha_desde = request.GET.get('desde', '').strip()
    fecha_hasta = request.GET.get('hasta', '').strip()
    metodo_pago = request.GET.get('metodo_pago', '').strip()
    estado = request.GET.get('estado', '').strip()
    per_page = request.GET.get('per_page', 20)

    ventas = Venta.objects.select_related('cajero', 'sesion', 'tienda').prefetch_related('detalles__producto').filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True)).order_by('-fecha', '-id')

    if fecha_desde:
        ventas = ventas.filter(fecha__date__gte=fecha_desde)

    if fecha_hasta:
        ventas = ventas.filter(fecha__date__lte=fecha_hasta)

    metodos_validos = {metodo for metodo, _ in Venta.METODOS_PAGO}
    if metodo_pago in metodos_validos:
        ventas = ventas.filter(metodo_pago=metodo_pago)

    estados_validos = {estado_venta for estado_venta, _ in Venta.ESTADOS}
    if estado in estados_validos:
        ventas = ventas.filter(estado=estado)

    if query:
        filtros = Q(cajero__username__icontains=query) | Q(detalles__producto__nombre__icontains=query)
        if query.isdigit():
            filtros |= Q(id=int(query))
        ventas = ventas.filter(filtros).distinct()

    ventas_activas = ventas.filter(estado='ACTIVA')
    total_vendido = ventas_activas.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    total_tickets = ventas_activas.count()
    ticket_promedio = total_vendido / total_tickets if total_tickets else Decimal('0.00')

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 20

    paginator = Paginator(ventas, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    contexto = {
        **get_config_context('Estadísticas', 'border-blue-600'),
        'page_obj': page_obj,
        'query': query,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'metodo_pago': metodo_pago,
        'metodos_pago': Venta.METODOS_PAGO,
        'estado': estado,
        'estados_venta': Venta.ESTADOS,
        'per_page': per_page,
        'querystring': get_querystring_without_page(request),
        'total_vendido': total_vendido,
        'total_tickets': total_tickets,
        'ticket_promedio': ticket_promedio,
    }
    return render(request, 'ventas/historial.html', contexto)
