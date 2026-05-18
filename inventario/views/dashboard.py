from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from core.utils import get_config_context
from configuraciones.utils import get_tienda_actual
from inventario.models import MovimientoInventario, Producto

@login_required
@permission_required('configuraciones.ver_inventario', login_url='portal_principal')
def dashboard(request):
    contexto = _dashboard_context(request)
    return render(request, 'inventario/dashboard.html', contexto)


@login_required
@permission_required('configuraciones.ver_inventario', login_url='portal_principal')
def dashboard_live(request):
    contexto = _dashboard_context(request)
    return render(request, 'inventario/partials/dashboard_contenido.html', contexto)


def _dashboard_context(request):
    tienda_actual = get_tienda_actual(request)
    productos_activos = Producto.objects.filter(activo=True)
    valor_inventario = productos_activos.aggregate(
        total=Sum(
            ExpressionWrapper(F('stock') * F('precios__precio'), output_field=DecimalField(max_digits=12, decimal_places=2))
        )
    )['total'] or 0
    resumen = productos_activos.aggregate(
        total_productos=Count('id'),
        agotados=Count('id', filter=Q(stock__lte=0)),
        bajo_stock=Count('id', filter=Q(stock__gt=0, stock__lte=F('stock_minimo'))),
        sin_precio=Count('id', filter=Q(precios__isnull=True)),
    )
    resumen['inactivos'] = Producto.objects.filter(activo=False).count()

    return {
        **get_config_context('Inventario', 'border-purple-600'),
        **resumen,
        'valor_inventario': valor_inventario,
        'productos_alerta': productos_activos.select_related('categoria', 'precios')
            .filter(Q(stock__lte=0) | Q(stock__lte=F('stock_minimo')) | Q(precios__isnull=True))
            .order_by('stock', 'nombre')[:8],
        'movimientos_recientes': MovimientoInventario.objects.select_related('producto', 'usuario', 'venta', 'tienda').filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True))[:8],
    }
