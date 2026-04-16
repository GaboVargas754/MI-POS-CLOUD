from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from ventas.models import Producto, SesionCaja
from core.utils import get_config_context

@login_required
def pantalla_pos(request):
    sesion_abierta = SesionCaja.objects.filter(cajero=request.user, estado=True).first()
    if not sesion_abierta:
        return redirect('abrir_caja')

    productos = Producto.objects.filter(stock__gt=0)
    carrito = request.session.get('carrito', {})
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    contexto = {
        **get_config_context('Caja Registradora', 'border-green-600', nav_items=[]),
        'productos': productos,
        'carrito': carrito,
        'total': total,
        'htmx_enabled': True,
    }
    return render(request, 'ventas/pos.html', contexto)

def buscar_productos(request):
    query = request.GET.get('q', '')

    if query:
        productos = Producto.objects.filter(
            Q(nombre__icontains=query) | Q(codigo_barras__icontains=query)
        )[:15]
    else:
        productos = Producto.objects.none()

    return render(request, 'ventas/partials/resultados_busqueda.html', {'productos': productos})
