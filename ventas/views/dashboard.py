from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required, permission_required
from inventario.models import Producto
from ventas.models import Venta, DetalleVenta
from core.utils import get_config_context
from configuraciones.utils import get_tienda_actual
VER_ESTADISTICAS_PERMISSION = 'configuraciones.ver_estadisticas'

@login_required
@permission_required(VER_ESTADISTICAS_PERMISSION, login_url='portal_principal')
def dashboard(request):
    contexto = _dashboard_context(request)
    return render(request, 'ventas/dashboard.html', contexto)


@login_required
@permission_required(VER_ESTADISTICAS_PERMISSION, login_url='portal_principal')
def dashboard_live(request):
    contexto = _dashboard_context(request)
    return render(request, 'ventas/partials/dashboard_estadisticas.html', contexto)


def _dashboard_context(request):
    tienda_actual = get_tienda_actual(request)
    hoy = timezone.now().date()
    filtro_tienda = Q(tienda=tienda_actual) | Q(tienda__isnull=True)
    ventas_hoy = Venta.objects.filter(filtro_tienda, fecha__date=hoy, estado='ACTIVA')
    total_ventas = ventas_hoy.aggregate(Sum('total'))['total__sum'] or 0
    num_tickets = ventas_hoy.count()

    if num_tickets > 0:
        ticket_promedio = total_ventas / num_tickets
    else:
        ticket_promedio = 0

    productos_top = DetalleVenta.objects.filter(Q(venta__tienda=tienda_actual) | Q(venta__tienda__isnull=True), venta__fecha__date=hoy, venta__estado='ACTIVA') \
        .values('producto__nombre') \
        .annotate(total_vendido=Sum('cantidad')) \
        .order_by('-total_vendido')[:5]

    stock_bajo = Producto.objects.filter(stock__lt=5)

    return {
        **get_config_context('Estadísticas', 'border-blue-600'),
        'total_ventas': total_ventas,
        'num_tickets': num_tickets,
        'productos_top': productos_top,
        'ticket_promedio': ticket_promedio,
        'stock_bajo': stock_bajo,
        'hoy': hoy,
    }
