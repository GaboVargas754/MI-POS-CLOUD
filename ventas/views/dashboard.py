from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, permission_required
from inventario.models import Producto
from ventas.models import Venta, DetalleVenta
from core.utils import get_config_context
from ventas.views.carrito import VENTAS_PERMISSION

@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
def dashboard(request):
    hoy = timezone.now().date()
    ventas_hoy = Venta.objects.filter(fecha__date=hoy)
    total_ventas = ventas_hoy.aggregate(Sum('total'))['total__sum'] or 0
    num_tickets = ventas_hoy.count()

    if num_tickets > 0:
        ticket_promedio = total_ventas / num_tickets
    else:
        ticket_promedio = 0

    productos_top = DetalleVenta.objects.filter(venta__fecha__date=hoy) \
        .values('producto__nombre') \
        .annotate(total_vendido=Sum('cantidad')) \
        .order_by('-total_vendido')[:5]

    stock_bajo = Producto.objects.filter(stock__lt=5)

    contexto = {
        **get_config_context('Panel de Control - Ventas', 'border-blue-600'),
        'total_ventas': total_ventas,
        'num_tickets': num_tickets,
        'productos_top': productos_top,
        'ticket_promedio': ticket_promedio,
        'stock_bajo': stock_bajo,
        'hoy': hoy,
    }
    return render(request, 'ventas/dashboard.html', contexto)
