from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from inventario.models import Producto
from ventas.models import SesionCaja
from core.utils import get_config_context
from configuraciones.utils import get_tienda_actual
from ventas.views.carrito import VENTAS_PERMISSION, calcular_total_carrito

@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
def pantalla_pos(request):
    tienda_actual = get_tienda_actual(request)
    sesion_abierta = SesionCaja.objects.filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True), cajero=request.user, estado=True).first()
    if not sesion_abierta:
        messages.warning(request, 'Abre caja antes de entrar al POS.')
        return redirect('abrir_caja')

    productos = Producto.objects.select_related('precios').filter(activo=True, stock__gt=0, precios__isnull=False)
    carrito = request.session.get('carrito', {})
    total = calcular_total_carrito(carrito)
    request.session['carrito'] = carrito

    contexto = {
        **get_config_context('Caja Registradora', 'border-green-600', nav_items=[]),
        'productos': productos,
        'carrito': carrito,
        'total': total,
        'htmx_enabled': True,
        'tienda_actual': tienda_actual,
    }
    return render(request, 'ventas/pos.html', contexto)

@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
def buscar_productos(request):
    get_tienda_actual(request)
    query = request.GET.get('q', '')

    if query:
        productos = Producto.objects.select_related('precios').filter(
            Q(nombre__icontains=query) | Q(codigo_barras__icontains=query)
        ).filter(activo=True, stock__gt=0, precios__isnull=False)[:15]
    else:
        productos = Producto.objects.none()

    return render(request, 'ventas/partials/resultados_busqueda.html', {'productos': productos})
