from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.http import require_http_methods
from ventas.models import SesionCaja, Venta
from ventas.views.carrito import VENTAS_PERMISSION

@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def abrir_caja(request):
    if SesionCaja.objects.filter(cajero=request.user, estado=True).exists():
        return redirect('pantalla_pos')

    if request.method == 'POST':
        try:
            fondo = Decimal(request.POST.get('fondo_inicial') or '0')
        except InvalidOperation:
            return render(request, 'ventas/abrir_caja.html', {'error': 'Ingresa un fondo inicial válido.'})

        SesionCaja.objects.create(
            cajero=request.user,
            fondo_inicial=fondo,
            estado=True
        )
        return redirect('pantalla_pos')

    return render(request, 'ventas/abrir_caja.html')

@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def cerrar_caja(request):
    sesion = get_object_or_404(SesionCaja, cajero=request.user, estado=True)
    ventas_efectivo = Venta.objects.filter(sesion=sesion, metodo_pago='EFE').aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    esperado_en_caja = sesion.fondo_inicial + ventas_efectivo

    if request.method == 'POST':
        try:
            efectivo_contado = Decimal(request.POST.get('efectivo_cierre') or '0')
        except InvalidOperation:
            return render(request, 'ventas/cerrar_caja.html', {
                'sesion': sesion,
                'ventas_efectivo': ventas_efectivo,
                'esperado_en_caja': esperado_en_caja,
                'error': 'Ingresa un efectivo de cierre válido.',
            })

        sesion.efectivo_cierre = efectivo_contado
        sesion.fecha_cierre = timezone.now()
        sesion.estado = False
        sesion.save()

        return redirect('dashboard')

    contexto = {
        'sesion': sesion,
        'ventas_efectivo': ventas_efectivo,
        'esperado_en_caja': esperado_en_caja,
    }
    return render(request, 'ventas/cerrar_caja.html', contexto)
